"""
Validation Agent: Applies business rules to extracted claim data.
Validates completeness, logical consistency, and regulatory compliance.
India-specific rules included (IRDAI regulations).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from app.models.schemas import (
    WorkflowState, ClaimStatus, ValidationResult, ValidationError,
    ExtractedClaimData, InsuranceType, Country
)
from app.core.config import settings
from app.core.logging import get_logger, log_agent_start, log_agent_complete, log_agent_error

logger = get_logger(__name__)


class BusinessRuleEngine:
    """
    Stateless rule engine for insurance claim validation.
    Rules are prioritized and tagged for reporting.
    """

    def validate(self, data: ExtractedClaimData) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        rules_applied: list[str] = []

        # Run all rules
        for rule_fn in [
            self._rule_required_fields,
            self._rule_claimant_identity,
            self._rule_policy_validity,
            self._rule_incident_date,
            self._rule_amount_limits,
            self._rule_policy_lapse,
            self._rule_india_specific,
            self._rule_logical_consistency,
            self._rule_contact_info,
        ]:
            rule_errors, rule_warnings, rule_name = rule_fn(data)
            errors.extend(rule_errors)
            warnings.extend(rule_warnings)
            rules_applied.append(rule_name)

        # Calculate completeness score
        completeness = self._calculate_completeness(data)

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            completeness_score=completeness,
            rules_applied=rules_applied,
        )

    def _rule_required_fields(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        if not data.claimant.name:
            errors.append(ValidationError(field="claimant.name", error="Claimant name is required", severity="ERROR"))

        if not data.policy.policy_number:
            warnings.append(ValidationError(field="policy.policy_number", error="Policy number not found - manual verification needed", severity="WARNING"))

        if not data.incident.incident_date:
            errors.append(ValidationError(field="incident.incident_date", error="Incident date is required", severity="ERROR"))

        if data.amounts.claimed_amount is None:
            errors.append(ValidationError(field="amounts.claimed_amount", error="Claimed amount is required", severity="ERROR"))

        if not data.policy.policy_type or data.policy.policy_type == InsuranceType.OTHER:
            warnings.append(ValidationError(field="policy.policy_type", error="Policy type unclear - defaulting to OTHER", severity="WARNING"))

        return errors, warnings, "REQUIRED_FIELDS"

    def _rule_claimant_identity(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        # For Indian claims, at least one identity document
        if data.country == Country.INDIA:
            has_id = any([
                data.claimant.aadhaar_number,
                data.claimant.pan_number,
                data.claimant.national_id,
            ])
            if not has_id:
                warnings.append(ValidationError(
                    field="claimant.identity",
                    error="No identity document (Aadhaar/PAN) found - required for Indian claims",
                    severity="WARNING"
                ))

        # Email format validation
        if data.claimant.email:
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.claimant.email):
                warnings.append(ValidationError(
                    field="claimant.email",
                    error=f"Invalid email format: {data.claimant.email}",
                    severity="WARNING"
                ))

        return errors, warnings, "CLAIMANT_IDENTITY"

    def _rule_policy_validity(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        # Check policy dates are present
        if not data.policy.policy_start_date and not data.policy.policy_end_date:
            warnings.append(ValidationError(
                field="policy.dates",
                error="Policy validity dates missing - cannot verify active coverage",
                severity="WARNING"
            ))

        # Check sum insured is positive
        if data.policy.sum_insured is not None and data.policy.sum_insured <= 0:
            errors.append(ValidationError(
                field="policy.sum_insured",
                error=f"Invalid sum insured: {data.policy.sum_insured}",
                severity="ERROR"
            ))

        # Check claimed amount doesn't exceed sum insured
        if (data.amounts.claimed_amount and data.policy.sum_insured and
                data.amounts.claimed_amount > data.policy.sum_insured):
            errors.append(ValidationError(
                field="amounts.claimed_amount",
                error=f"Claimed amount ({data.amounts.claimed_amount}) exceeds sum insured ({data.policy.sum_insured})",
                severity="ERROR"
            ))

        return errors, warnings, "POLICY_VALIDITY"

    def _rule_incident_date(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        if not data.incident.incident_date:
            return errors, warnings, "INCIDENT_DATE"

        try:
            # Parse Indian date format DD/MM/YYYY
            incident_dt = self._parse_date(data.incident.incident_date)
            if incident_dt is None:
                warnings.append(ValidationError(
                    field="incident.incident_date",
                    error=f"Cannot parse incident date: {data.incident.incident_date}",
                    severity="WARNING"
                ))
                return errors, warnings, "INCIDENT_DATE"

            today = datetime.utcnow()

            # Future date check
            if incident_dt > today:
                errors.append(ValidationError(
                    field="incident.incident_date",
                    error=f"Incident date {data.incident.incident_date} is in the future",
                    severity="ERROR"
                ))

            # Stale claim check (India: claims must be filed within 30-90 days typically)
            days_old = (today - incident_dt).days
            if days_old > 180:
                warnings.append(ValidationError(
                    field="incident.incident_date",
                    error=f"Claim is {days_old} days old - verify limitation period compliance",
                    severity="WARNING"
                ))

            # Reported date vs incident date
            if data.incident.reported_date:
                reported_dt = self._parse_date(data.incident.reported_date)
                if reported_dt and reported_dt < incident_dt:
                    errors.append(ValidationError(
                        field="incident.reported_date",
                        error="Reported date is before incident date",
                        severity="ERROR"
                    ))

        except Exception as e:
            warnings.append(ValidationError(
                field="incident.incident_date",
                error=f"Date validation error: {str(e)}",
                severity="WARNING"
            ))

        return errors, warnings, "INCIDENT_DATE"

    def _rule_amount_limits(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        amount = data.amounts.claimed_amount
        if amount is None:
            return errors, warnings, "AMOUNT_LIMITS"

        if amount <= 0:
            errors.append(ValidationError(
                field="amounts.claimed_amount",
                error=f"Claimed amount must be positive: {amount}",
                severity="ERROR"
            ))

        # High-value claim flag (India-specific threshold)
        currency = data.amounts.currency or "INR"
        if currency == "INR":
            if amount > settings.HIGH_VALUE_THRESHOLD_INR:
                warnings.append(ValidationError(
                    field="amounts.claimed_amount",
                    error=f"High-value claim: ₹{amount:,.2f} - requires senior reviewer",
                    severity="WARNING"
                ))
        elif currency in ["USD", "GBP"]:
            usd_equivalent = amount
            if usd_equivalent > 50000:
                warnings.append(ValidationError(
                    field="amounts.claimed_amount",
                    error=f"High-value international claim: {currency} {amount:,.2f}",
                    severity="WARNING"
                ))

        return errors, warnings, "AMOUNT_LIMITS"

    def _rule_policy_lapse(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        if not data.policy.policy_end_date or not data.incident.incident_date:
            return errors, warnings, "POLICY_LAPSE"

        try:
            end_dt = self._parse_date(data.policy.policy_end_date)
            incident_dt = self._parse_date(data.incident.incident_date)

            if end_dt and incident_dt and incident_dt > end_dt:
                errors.append(ValidationError(
                    field="policy.policy_end_date",
                    error=f"Incident ({data.incident.incident_date}) occurred after policy expiry ({data.policy.policy_end_date})",
                    severity="ERROR"
                ))
        except Exception:
            pass

        return errors, warnings, "POLICY_LAPSE"

    def _rule_india_specific(self, data: ExtractedClaimData) -> tuple:
        """India-specific IRDAI regulatory validation rules."""
        errors, warnings = [], []

        if data.country != Country.INDIA:
            return errors, warnings, "INDIA_SPECIFIC"

        # IRDAI: Health claims need hospital details
        if data.policy.policy_type == InsuranceType.HEALTH:
            if not data.incident.hospital_name:
                warnings.append(ValidationError(
                    field="incident.hospital_name",
                    error="Hospital name required for health insurance claims (IRDAI regulation)",
                    severity="WARNING"
                ))
            if not data.incident.diagnosis:
                warnings.append(ValidationError(
                    field="incident.diagnosis",
                    error="Diagnosis/medical condition required for health claims",
                    severity="WARNING"
                ))

        # Motor insurance: vehicle number required
        if data.policy.policy_type == InsuranceType.MOTOR:
            if not data.incident.vehicle_number:
                errors.append(ValidationError(
                    field="incident.vehicle_number",
                    error="Vehicle registration number required for motor insurance claims",
                    severity="ERROR"
                ))

        # Crop insurance (PMFBY): location required
        if data.policy.policy_type in [InsuranceType.CROP, InsuranceType.PRADHAN_MANTRI]:
            if not data.incident.incident_location:
                errors.append(ValidationError(
                    field="incident.incident_location",
                    error="Location/plot details required for crop/government scheme claims",
                    severity="ERROR"
                ))

        return errors, warnings, "INDIA_SPECIFIC"

    def _rule_logical_consistency(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        # DOB consistency (claimant can't be too young or too old)
        if data.claimant.dob:
            dob = self._parse_date(data.claimant.dob)
            if dob:
                age = (datetime.utcnow() - dob).days / 365.25
                if age < 0 or age > 130:
                    errors.append(ValidationError(
                        field="claimant.dob",
                        error=f"Invalid date of birth yields age {age:.0f} years",
                        severity="ERROR"
                    ))
                elif age < 1:
                    warnings.append(ValidationError(
                        field="claimant.dob",
                        error="Claimant appears to be less than 1 year old - verify",
                        severity="WARNING"
                    ))

        return errors, warnings, "LOGICAL_CONSISTENCY"

    def _rule_contact_info(self, data: ExtractedClaimData) -> tuple:
        errors, warnings = [], []

        # Indian phone number validation
        if data.claimant.contact_number and data.country == Country.INDIA:
            import re
            phone = re.sub(r'[\s\-+]', '', data.claimant.contact_number)
            if not re.match(r'^[6-9]\d{9}$', phone) and not phone.startswith('91'):
                warnings.append(ValidationError(
                    field="claimant.contact_number",
                    error=f"Phone number may be invalid for India: {data.claimant.contact_number}",
                    severity="WARNING"
                ))

        return errors, warnings, "CONTACT_INFO"

    def _calculate_completeness(self, data: ExtractedClaimData) -> float:
        """Calculate data completeness score (0-1)."""
        fields = [
            data.claimant.name,
            data.claimant.contact_number,
            data.policy.policy_number,
            data.policy.policy_type,
            data.policy.insurance_company,
            data.incident.incident_date,
            data.incident.incident_description,
            data.amounts.claimed_amount,
        ]
        filled = sum(1 for f in fields if f is not None)
        return round(filled / len(fields), 2)

    def _parse_date(self, date_str: str) -> datetime | None:
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y",
            "%B %d, %Y", "%d %B %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except (ValueError, AttributeError):
                continue
        return None


_rule_engine = BusinessRuleEngine()


async def validation_agent(state: WorkflowState) -> WorkflowState:
    """LangGraph node: Validate extracted claim data against business rules."""
    log_agent_start(logger, "ValidationAgent", state.claim_id)
    state.status = ClaimStatus.VALIDATING

    if not state.extracted_data:
        state.errors.append("No extracted data to validate")
        state.should_skip_downstream = True
        return state

    try:
        result = _rule_engine.validate(state.extracted_data)
        state.validation_result = result

        if not result.is_valid:
            logger.warning(
                f"Validation failed with {len(result.errors)} errors",
                extra={
                    "extra_data": {
                        "claim_id": state.claim_id,
                        "errors": [e.error for e in result.errors],
                        "completeness": result.completeness_score,
                    }
                },
            )
            # Only skip downstream for critical errors (not warnings)
            critical_errors = [e for e in result.errors if e.severity == "ERROR"]
            if len(critical_errors) >= 3:
                state.should_skip_downstream = True
                state.errors.append(f"Too many validation errors ({len(critical_errors)}) - skipping downstream processing")
        else:
            logger.info(
                f"Validation passed",
                extra={"extra_data": {"claim_id": state.claim_id, "completeness": result.completeness_score}}
            )

        log_agent_complete(logger, "ValidationAgent", state.claim_id, {
            "is_valid": result.is_valid,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
        })

    except Exception as e:
        log_agent_error(logger, "ValidationAgent", state.claim_id, e)
        state.errors.append(f"Validation agent error: {str(e)}")
        state.validation_result = ValidationResult(
            is_valid=False,
            errors=[ValidationError(field="system", error=str(e))],
            completeness_score=0.0,
        )

    return state
