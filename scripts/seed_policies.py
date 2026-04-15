"""
scripts/seed_policies.py
Seeds the ChromaDB vector store with comprehensive Indian and international
insurance policy documents. Run once before starting the API.

Usage:
    python -m scripts.seed_policies
    # or from project root:
    python scripts/seed_policies.py
"""
import asyncio
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.vectorstore.chroma_store import get_vector_store
from app.models.schemas import InsuranceType, Country

# ─────────────────────────────────────────────
# POLICY LIBRARY
# ─────────────────────────────────────────────
POLICIES = [

    # ──────── INDIA: HEALTH ────────
    {
        "name": "Star Health - Comprehensive Individual Health Insurance",
        "type": InsuranceType.HEALTH,
        "country": Country.INDIA,
        "company": "Star Health and Allied Insurance",
        "text": """
STAR COMPREHENSIVE INDIVIDUAL HEALTH INSURANCE POLICY

COVERAGE BENEFITS:
1. In-patient Hospitalization: Covered in full up to sum insured for minimum 24-hour admission.
   Sub-limits: Single standard AC room eligible. ICU: 2x room rent per day.
2. Pre-hospitalization: Medical expenses 60 days prior to admission covered.
3. Post-hospitalization: 90 days after discharge covered for related treatment.
4. Day Care Treatments: 405 listed day care procedures covered without 24-hour admission.
5. Domiciliary Treatment: Home treatment on doctor's advice for conditions where hospitalization
   not possible. Covered up to 10% of sum insured.
6. Organ Donor Expenses: Inpatient hospitalization expenses of donor covered.
7. Ayurvedic/Homeopathic/Unani Treatment: Covered in NABH-accredited hospitals.
8. Emergency Ambulance: Covered up to INR 3,000 per hospitalization.
9. Annual Health Check-up: Covered once per policy year after 3 continuous years.
10. Mental Illness Hospitalization: Covered as per Mental Healthcare Act 2017.

WAITING PERIODS:
- Initial waiting period: 30 days from first policy inception (except accidents).
- Pre-existing diseases: 36 months waiting period from first policy inception.
- Specific diseases (cataracts, hernia, joint replacement): 24 months.
- Maternity (if opted as add-on): 9 months.

EXCLUSIONS:
- Cosmetic surgery, gender change treatment.
- Dental treatment unless requiring hospitalization due to accident.
- Experimental/investigational treatment not approved by Indian medical authorities.
- HIV/AIDS (first 3 policy years).
- Suicide, self-harm, substance abuse.
- Non-allopathic treatment not in NABH hospital.
- Treatment outside India (unless add-on purchased).
- Obesity-related treatment (unless BMI > 40 and life-threatening).
- Congenital anomalies detected post-birth (waiting period applies).

CLAIM PROCESS:
Cashless: Empaneled network hospitals (7,000+). Pre-authorization mandatory 48 hours for planned.
Reimbursement: Submit within 15 days of discharge to nearest Star Health branch.
TPA: Medi Assist / Health India TPA for processing.
Documents required: Discharge summary, all original bills/receipts, investigation reports,
indoor case papers, pharmacy bills, attending doctor's certificate, filled claim form,
KYC documents (Aadhaar/PAN), policy copy, bank account details for NEFT.

IRDAI COMPLIANCE: This policy is compliant with IRDAI (Health Insurance) Regulations 2016.
Grievance: igms.irda.gov.in | Toll-free: 155255 | Ombudsman applicable.
""",
    },

    # ──────── INDIA: LIC LIFE ────────
    {
        "name": "LIC Jeevan Arogya - Health Insurance Plan",
        "type": InsuranceType.HEALTH,
        "country": Country.INDIA,
        "company": "Life Insurance Corporation of India",
        "text": """
LIC JEEVAN AROGYA - NON-LINKED HEALTH PLAN (Plan No. 904)

BENEFITS:
1. Hospital Cash Benefit (HCB): Daily cash allowance for each day of hospitalization.
   Entry age 18-65. Sum assured INR 1,000 to INR 4,000 per day.
2. Major Surgical Benefit (MSB): Lump sum benefit for listed surgical procedures.
   Categories A (100% MSB), B (60% MSB), C (40% MSB), D (20% MSB).
   MSB = 250 x HCB for self.
3. Other Surgical Benefit: 50% of MSB for surgeries not in major category.
4. Day Care Procedure Benefit: 5x HCB for listed 140 day care procedures.
5. Premium Waiver: Premium waived for 3 years after a major surgery claim.

ELIGIBLE CONDITIONS FOR MSB (Selection):
- Open heart surgery for coronary artery bypass grafting (Category A).
- Kidney transplant (Category A).
- Liver transplant requiring donor (Category A).
- Hip replacement surgery (Category B).
- Hysterectomy (Category B).
- Appendectomy (Category C).
- Hernia repair surgery (Category C).
- Cataract surgery (Category D).

EXCLUSIONS:
- Pre-existing conditions in first 4 years.
- Maternity and childbirth-related expenses.
- Sexually transmitted diseases.
- Experimental treatment.
- Dental treatment.
- Self-inflicted injuries.
- War and nuclear perils.

CLAIM PROCEDURE:
Notify LIC branch within 30 days of hospitalization.
Claim intimation form available at all LIC branch offices or www.licindia.in.
Submit: Discharge summary, operation notes (for surgical claims), bills, pathology reports.
Settlement within 30 days of complete document submission.
Grievance: licindia.in or visit nearest LIC branch/Divisional Office.

NOTE: LIC Jeevan Arogya is a yearly renewable plan. Premium increases with age.
IRDA Registration No. 512.
""",
    },

    # ──────── INDIA: MOTOR ────────
    {
        "name": "HDFC ERGO Motor Insurance - Private Car Comprehensive",
        "type": InsuranceType.MOTOR,
        "country": Country.INDIA,
        "company": "HDFC ERGO General Insurance",
        "text": """
HDFC ERGO PRIVATE CAR PACKAGE POLICY

SECTION I: OWN DAMAGE (OD) COVER
Covers sudden accidental external means loss/damage to the insured vehicle including:
- Collision, overturning, fire, explosion, self-ignition.
- Lightning, earthquake, flood, cyclone, inundation, hailstorm.
- Burglary, theft, house-breaking.
- Malicious act, terrorist activity (Third Party Act compliance).
- While in transit by road, rail, air, or inland waterway.
- Landslide, rock slide.

DEPRECIATION SCHEDULE (as per IRDAI):
Not exceeding 6 months: NIL
Exceeding 6 months but not 1 year: 5%
Exceeding 1 year but not 2 years: 10%
Exceeding 2 years but not 3 years: 15%
Exceeding 3 years but not 4 years: 25%
Exceeding 4 years but not 5 years: 35%
Exceeding 5 years but not 10 years: 40%
Exceeding 10 years: 50%
Rubber/nylon/plastic/tyres/tubes: 50% always.
Glass: NIL depreciation.

SECTION II: THIRD PARTY LIABILITY
Compulsory under Motor Vehicles Act 1988.
Unlimited liability for death or bodily injury to third parties.
Property damage: Up to INR 7.5 lakh.
CNG/LPG bi-fuel kit: Additional TP premium required.

ADD-ON COVERS (optional):
- Zero Depreciation (Nil Dep): Full part value without depreciation for first 2 claims/year.
- Return to Invoice: IDV = Original invoice value minus depreciation.
- Engine Protect: Covers hydrostatic lock, oil leakage from damaged parts.
- Consumable Cover: Nuts/bolts, engine oil, AC gas covered.
- Key and Lock Protect: Replacement of lost/stolen keys.
- NCB Protect: No Claim Bonus preserved after one claim.
- Roadside Assistance: 24/7 towing, fuel delivery, battery jumpstart.

CLAIM PROCEDURE:
Accident: Report to nearest police station (for third-party or theft; mandatory).
Register claim: HDFC ERGO website / app / helpline 022-6234-6234 within 24 hours.
Surveyor appointed within 48 hours for own damage claims.
Cashless: 7,000+ network garages. Authorization required before repair.
Reimbursement: Get estimate approved, repair, submit bills within 30 days.
Total loss settlement: Based on agreed IDV.

REQUIRED DOCUMENTS:
- Filled and signed claim form.
- Original RC Book.
- Valid Driving License (at time of accident).
- Original repair bills/estimate.
- FIR copy (theft, third-party, major accident).
- Cancelled cheque for NEFT settlement.
""",
    },

    # ──────── INDIA: AYUSHMAN BHARAT ────────
    {
        "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
        "type": InsuranceType.AYUSHMAN_BHARAT,
        "country": Country.INDIA,
        "company": "National Health Authority, Government of India",
        "text": """
AYUSHMAN BHARAT - PM JAN AROGYA YOJANA (AB PM-JAY)

SCHEME OVERVIEW:
World's largest government-funded health insurance scheme.
Coverage: INR 5,00,000 per family per year.
Beneficiaries: ~55 crore people (10.74 crore poor/vulnerable families).
Identification: SECC 2011 database / State BPL list.

COVERAGE BENEFITS:
- 3 days pre-hospitalization expenses.
- 15 days post-hospitalization expenses including medicines and diagnostics.
- All pre-existing conditions covered from Day 1.
- All government hospital and empaneled private hospital treatments.
- 1,929 treatment packages across 27 medical specialties.
- Includes: surgery, medical, day care procedures.
- No cap on family size, age, or gender.
- Free Aarogya Mitra assistance at hospital.

COVERED SPECIALTIES (Selection):
- Oncology (cancer treatment): Chemotherapy, radiotherapy.
- Cardiology: Bypass surgery, valve replacement, pacemaker.
- Neurology: Brain surgeries, spinal cord procedures.
- Orthopedics: Joint replacement, spinal fusion.
- Nephrology: Dialysis, kidney transplant.
- Pulmonology: COPD management, TB treatment.
- Neonatology: NICU, premature baby care.
- Burn injuries management.

ELIGIBILITY VERIFICATION:
Check eligibility: mera.pmjay.gov.in or helpline 14555.
Aadhaar-based or ration card-based verification at hospital.
Beneficiary Identification System (BIS) at empaneled hospitals.

CLAIM PROCESS FOR HOSPITAL:
Hospital submits claim through NHA portal after patient discharge.
Pre-authorization required for elective procedures.
Claims settled directly to hospital within 15 days.
Beneficiary pays NOTHING - fully cashless, paperless.

GRIEVANCE:
Central Grievance Redressal: 14555 (toll-free).
State health agencies manage local grievances.
CPGRAMS portal for escalation.
National Health Authority: nhp.gov.in.

FRAUD PREVENTION:
Anti-fraud unit operational. Claims audited.
Beneficiary can verify claims through mera.pmjay.gov.in.
Empaneled hospitals monitored through concurrent audits.
""",
    },

    # ──────── INDIA: CROP / PMFBY ────────
    {
        "name": "Pradhan Mantri Fasal Bima Yojana - Detailed Guidelines",
        "type": InsuranceType.CROP,
        "country": Country.INDIA,
        "company": "Ministry of Agriculture and Farmers Welfare",
        "text": """
PMFBY - PRADHAN MANTRI FASAL BIMA YOJANA

SCHEME OBJECTIVE:
Financial support to farmers suffering crop loss due to unforeseen natural calamities.
Stabilize farm income to ensure continuity in farming.
Encourage adoption of innovative and modern agricultural practices.

PREMIUM STRUCTURE:
Kharif crops: Maximum 2% of sum insured paid by farmer.
Rabi crops: Maximum 1.5% of sum insured paid by farmer.
Annual commercial/horticultural crops: Maximum 5% of sum insured.
Government (Centre+State) subsidy: Balance actuarial premium equally shared.

SUM INSURED CALCULATION:
Scale of Finance (SoF) declared by District Level Technical Committee (DLTC).
Sum insured = Highest of: SoF x Area, or Previous year's actual productivity.
Enhanced sum insured available on actual cost basis for specific crops.

COVERAGE STAGES:
Stage 1 - Prevented Sowing/Planting Risk: If majority (>75%) of insured farmers
           prevented from sowing due to deficit rainfall or adverse weather.
Stage 2 - Standing Crop (Sowing to Harvesting): Comprehensive coverage for yield losses.
Stage 3 - Post-Harvest Losses: Coverage for 14 days post-harvest for cut and spread crops.
Stage 4 - Localized Calamities: Hailstorm, landslide, inundated/waterlogged fields.
           Individual farm-level assessment for this stage.
Stage 5 - Add-on: Mid-Season Adversity for selected states.

CLAIM NOTIFICATION REQUIREMENTS:
- Localized/post-harvest loss: Notify within 72 hours via Crop Insurance App, 
  call 14447, or inform bank/insurance company/state agriculture department.
- Standing crop yield loss: Based on Crop Cutting Experiments (CCE) by state government.
  No individual claim filing required for yield loss component.

LOSS ASSESSMENT:
- Yield loss: Trigger = if actual yield < threshold yield (moving average of past 7 years x indemnity level).
- Loss: (Threshold yield - Actual yield) / Threshold yield x Sum insured.
- Indemnity levels: 70%, 80%, 90% depending on crop and state.

ENROLLMENT:
- Loanee farmers: Mandatory auto-enrollment through KCC/crop loan bank.
  Opt-out option available 7 days before cut-off.
- Non-loanee: Voluntary enrollment via bank branch, CSC, or 
  pmfby.gov.in portal before cut-off date.
- Required: Aadhaar, land records, bank account, sowing declaration.

CLAIM SETTLEMENT TIMELINE:
Advance payment: State governments may release up to 25% advance on crop damage.
Final settlement: Within 2 months of harvest/yield data availability.
Direct benefit transfer: NEFT/RTGS to farmer's Aadhaar-linked bank account.

GRIEVANCE REDRESSAL:
District Grievance Redressal Committee (DGRC).
State portal grievance mechanism.
National: pgportal.gov.in or 14447.
""",
    },

    # ──────── INDIA: PROPERTY / HOME ────────
    {
        "name": "Home Insurance - Standard Fire and Special Perils Policy India",
        "type": InsuranceType.PROPERTY,
        "country": Country.INDIA,
        "company": "Generic IRDAI Property Policy",
        "text": """
STANDARD FIRE AND SPECIAL PERILS POLICY (SFSP) - INDIA

SECTION A: BUILDING COVER
Covers physical loss, destruction, or damage to insured building structure caused by:
1. Fire (accidental, not intentional by insured).
2. Lightning.
3. Explosion/implosion.
4. Aircraft and other aerial devices.
5. Riot, strike, malicious damage (RSMD) - additional premium.
6. Storm, cyclone, typhoon, tempest, hurricane, tornado.
7. Flood and inundation.
8. Subsidence, landslide (STFI cover).
9. Impact damage by vehicles, animals (not own vehicles).
10. Missile testing operations.
11. Leakage from automatic sprinkler installations.
12. Bush fire.

SECTION B: CONTENTS COVER
Household goods, furniture, electronics, appliances covered for same perils as building.
Jewellery and valuables: Sub-limit of 10% of contents sum insured or INR 1 lakh, whichever lower.
Cash: Not covered under standard policy. Add-on available.

ADD-ON COVERS:
- Burglary and theft cover.
- Breakdown of domestic appliances.
- Terrorism cover.
- Earthquake cover (DIC - Difference in Conditions).
- Public liability.
- Alternate accommodation costs.

EXCLUSIONS:
- Gradually operating causes (wear and tear, dampness, shrinkage).
- Electrical/mechanical breakdown (unless caused by covered peril).
- Consequential loss / loss of profit.
- Property undergoing alteration or repair.
- War, nuclear perils.
- Willful act or gross negligence.
- Theft during/after fire/flood unless separately covered.
- Cutlery, sports gear, securities, documents (not standard cover).

SUM INSURED BASIS:
Building: Reinstatement value or market value basis.
Contents: Market value at time of loss (depreciation applied).
Underinsurance: Average clause applies (pro-rata settlement if underinsured).

CLAIM PROCEDURE:
Immediate loss intimation to insurer/surveyor/TPA.
Preserve damaged property for survey - do not dispose without permission.
File FIR for theft, burglary, or riot-related damage.
Submit: Claim form, photos/videos of damage, purchase bills/invoices for contents,
title deed or rent agreement for building, municipal assessment, repair estimates.
Surveyor appointed within 72 hours. Final survey within 30 days.
Settlement within 30 days of survey report and document submission.
""",
    },

    # ──────── INDIA: LIFE ────────
    {
        "name": "Term Life Insurance - Pure Protection Plan India",
        "type": InsuranceType.LIFE,
        "country": Country.INDIA,
        "company": "Generic IRDAI Life Policy",
        "text": """
TERM LIFE INSURANCE - PURE PROTECTION POLICY

DEATH BENEFIT:
Sum assured paid to nominee on death of life assured during policy term.
Payment options: Lump sum / Monthly income / Increasing monthly income.
Enhanced cover: Extra sum assured available for accidental death rider.

ELIGIBILITY:
Minimum entry age: 18 years.
Maximum entry age: 65 years.
Policy term: 5 to 40 years (maximum maturity age 80 years).
Minimum sum assured: INR 50 lakhs.
Maximum sum assured: Based on income proof and underwriting.

RIDERS (OPTIONAL):
1. Accidental Death Benefit: Additional sum assured for accidental death.
2. Critical Illness: Lump sum on diagnosis of 34 listed critical illnesses
   (cancer, heart attack, stroke, kidney failure, etc.).
3. Accidental Permanent/Total Disability: Waiver of future premiums + monthly benefit.
4. Waiver of Premium: Future premiums waived on disability.

CRITICAL ILLNESS COVERED (Selection):
- First diagnosis of cancer (of specified severity).
- Open heart replacement or repair of heart valves.
- Coronary artery bypass surgery.
- Stroke resulting in permanent neurological deficit.
- Kidney failure requiring permanent dialysis.
- Major organ transplant (heart, lung, liver, kidney, bone marrow).
- Paralysis of limbs (permanent).
- Total blindness.
- Aplastic anaemia.
- Motor neuron disease.

CLAIM PROCEDURE - DEATH CLAIM:
Intimation: Nominee intimates insurer within 90 days of death.
Documents:
- Death claim form (company-specific).
- Original policy document.
- Certified copy of death certificate from municipal authority.
- ID proof of claimant/nominee.
- Passbook/cancelled cheque for NEFT.
For accidental death: FIR, post-mortem report, final police report.
For early claim (within 3 years): Additional documents including treating doctor certificate.
Settlement: Within 30 days of complete documentation.

EXCLUSIONS:
- Suicide within first 12 months of policy inception.
- Death due to pre-existing condition not disclosed at proposal.
- Participation in hazardous activities not disclosed.
- Death in war or nuclear peril.
- Death under influence of drugs/alcohol (if cause of death).

IRDAI GRIEVANCE: igms.irda.gov.in | Ombudsman for disputes up to INR 30 lakhs.
Free Look Period: 15 days from receipt of policy (30 days if sold through distance mode).
""",
    },

    # ──────── USA: HEALTH ────────
    {
        "name": "ACA-Compliant Health Insurance - United States",
        "type": InsuranceType.HEALTH,
        "country": Country.USA,
        "company": "Generic ACA Compliant Plan",
        "text": """
ACA-COMPLIANT INDIVIDUAL HEALTH INSURANCE PLAN (UNITED STATES)

ESSENTIAL HEALTH BENEFITS (10 Categories - ACA Mandated):
1. Ambulatory (outpatient) care.
2. Emergency services (ER visits).
3. Hospitalization (inpatient care).
4. Maternity and newborn care.
5. Mental health and substance use disorder services.
6. Prescription drugs.
7. Rehabilitative and habilitative services.
8. Laboratory services.
9. Preventive care and wellness.
10. Pediatric care including dental/vision.

METAL TIERS:
- Bronze: Plan pays 60% average costs; deductible ~$6,000-$8,000.
- Silver: Plan pays 70%; deductible ~$3,000-$5,000. CSR subsidies available.
- Gold: Plan pays 80%; deductible ~$1,000-$2,000.
- Platinum: Plan pays 90%; deductible near $0.

OUT-OF-POCKET MAXIMUM (2024):
Individual: $9,450. Family: $18,900.
After OOP max met, plan pays 100% of covered in-network services.

NETWORK TYPES:
HMO: Requires PCP referral for specialist. Lower cost.
PPO: No referral needed. Higher cost but more flexibility.
EPO: No referral, but no out-of-network coverage (except emergencies).
HDHP: High deductible, eligible for Health Savings Account (HSA).

CLAIMS PROCESS:
In-network: Provider bills insurance directly.
Out-of-network (PPO): Pay upfront, submit claim with Explanation of Benefits (EOB).
Claim appeal rights: Internal appeal within 180 days. External review available.
Surprise billing: No Surprise Act protects from out-of-network ER bills.
""",
    },

    # ──────── UK: HEALTH ────────
    {
        "name": "Private Medical Insurance UK",
        "type": InsuranceType.HEALTH,
        "country": Country.UK,
        "company": "Generic UK PMI",
        "text": """
PRIVATE MEDICAL INSURANCE (PMI) - UNITED KINGDOM

COVERAGE:
Specialist consultations, diagnostic tests, and in-patient and day-patient treatment.
Complementary treatment available as optional add-on.
Mental health treatment (inpatient and outpatient) - standard.

RELATIONSHIP WITH NHS:
PMI is supplementary to NHS entitlement.
PMI does not replace NHS - it provides faster access and private facilities.
Insurers may require NHS treatment first for non-urgent conditions.

MORATORIUM UNDERWRITING:
Common in UK: Pre-existing conditions excluded for first 2 years of cover.
After 2 continuous years symptom/treatment-free, condition may become covered.
Alternative: Full medical underwriting (FMU) with known exclusion list.

CLAIM PROCEDURE:
GP referral letter usually required before specialist consultation.
Call insurer pre-authorisation number before booking private treatment.
Pre-authorisation reference number required - treatment not covered without this.
Direct billing: Most registered hospitals bill insurer directly.
Excess: Annual excess chosen at inception reduces premium.

FCA COMPLIANCE: All PMI plans regulated by Financial Conduct Authority (FCA).
Financial Ombudsman Service (FOS): For unresolved disputes within 8 weeks.
""",
    },

    # ──────── UAE ────────
    {
        "name": "Mandatory Health Insurance UAE - Dubai and Abu Dhabi",
        "type": InsuranceType.HEALTH,
        "country": Country.UAE,
        "company": "Generic UAE DHA/HAAD Compliant",
        "text": """
MANDATORY HEALTH INSURANCE - UAE

REGULATORY FRAMEWORK:
Dubai: Dubai Health Authority (DHA) - Dubai Health Insurance Law No. 11 of 2013.
Abu Dhabi: Health Authority Abu Dhabi (HAAD).
Other Emirates: Central government mandatory scheme in progress.

ESSENTIAL BENEFITS PACKAGE (EBP) - DUBAI:
Minimum mandatory coverage for all employees and dependents:
- Inpatient: Unlimited annual benefit (no cap on hospital stays).
- Outpatient: DHA network consultations, diagnostics, pharmacy.
- Maternity: Normal delivery and C-section covered.
- Emergency treatment: Always covered even outside network.
- Dental: Emergency dental treatment covered.
- Mental health: Inpatient covered.

CO-PAYMENT:
EBP: 20% co-payment by insured (maximum AED 500 per visit, AED 1,000 per month).
Enhanced plans: Co-payment may be reduced or waived.
Salary less than AED 4,000/month: Co-payment waived.

NETWORK:
DHA-approved network providers across Dubai.
Emergency treatment at any licensed UAE facility covered regardless of network.

CLAIM PROCESS:
Network: Present insurance card; provider bills insurer directly.
Emergency out-of-network: Pay and submit reimbursement claim within 60 days.
Documents: Original bills, medical reports, prescription copies, Emirates ID.
Grievance: DHA Insurance Complaints System (ICS) at dha.gov.ae.

VISA COMPLIANCE:
Health insurance mandatory for all UAE residence visa applications.
Sponsor (employer) responsible for employee insurance.
Domestic workers: Employer provides DHA basic package minimum.
""",
    },

]


async def seed_all_policies():
    """Index all policies in the library."""
    print("=" * 60)
    print("  INSURANCE CLAIMS PLATFORM - POLICY SEEDER")
    print("=" * 60)
    print()

    vs = get_vector_store()

    # Always re-index — reset existing collection for clean state
    try:
        client = vs._get_client()
        # Delete existing collection and recreate for clean re-index
        try:
            client.delete_collection(name="insurance_policies")
            print("  ✓ Cleared old vector store data")
        except Exception:
            pass
        vs._collection = None  # Force recreation
    except Exception as e:
        print(f"  ⚠ Could not reset collection: {e}")

    total_chunks = 0
    for i, policy in enumerate(POLICIES, 1):
        print(f"[{i}/{len(POLICIES)}] Indexing: {policy['name'][:55]}...")
        try:
            chunks = await vs.index_policy(
                policy_text=policy["text"],
                policy_name=policy["name"],
                insurance_type=policy["type"],
                country=policy["country"],
                company=policy.get("company", ""),
            )
            total_chunks += chunks
            print(f"         ✓ {chunks} chunks indexed")
        except Exception as e:
            print(f"         ✗ Failed: {e}")

    print()
    print(f"═══════════════════════════════════════════")
    print(f"  Done! {total_chunks} total chunks indexed")
    print(f"  Policies: {len(POLICIES)} documents")
    final_stats = vs.get_stats()
    print(f"  Vector store total: {final_stats.get('total_chunks', 0)} chunks")
    print(f"═══════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(seed_all_policies())
