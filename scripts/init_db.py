"""
scripts/init_db.py
Initialises the database: creates all tables and optionally seeds test data.

Usage:
    python -m scripts.init_db             # Create tables only
    python -m scripts.init_db --seed      # Create tables + seed sample claims
"""
import asyncio
import sys
import os
import argparse
from uuid import uuid4
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.db.models import init_db, AsyncSessionLocal
from app.infrastructure.db.repository import (
    ClaimRepository, AuditRepository, DecisionRepository
)
from app.models.schemas import ClaimStatus


SAMPLE_CLAIMS = [
    {
        "id": f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-DEMO01",
        "status": ClaimStatus.APPROVED,
        "claimant_name": "Rajesh Kumar",
        "policy_number": "LIC/2022/HLT/001234",
        "insurance_type": "HEALTH",
        "claimed_amount": 45000.0,
        "currency": "INR",
        "fraud_score": 0.08,
        "fraud_level": "LOW",
        "decision": "APPROVE",
        "decision_confidence": 0.92,
        "decision_explanation": "Claim approved. Medical bills verified. Hospitalization at network hospital. All documents in order.",
        "approved_amount": 45000.0,
        "extracted_data": {
            "claimant": {"name": "Rajesh Kumar", "dob": "15/06/1980", "gender": "MALE",
                         "contact_number": "9876543210", "aadhaar_number": "XXXX-XXXX-1234"},
            "policy": {"policy_number": "LIC/2022/HLT/001234", "insurance_company": "LIC",
                       "policy_type": "HEALTH", "sum_insured": 300000.0, "currency": "INR"},
            "incident": {"incident_date": "01/06/2024", "hospital_name": "Apollo Hospitals Chennai",
                         "diagnosis": "Appendicitis - Laparoscopic Appendectomy",
                         "doctor_name": "Dr. Priya Menon"},
            "amounts": {"claimed_amount": 45000.0, "currency": "INR"},
            "country": "IN", "extraction_confidence": 0.94
        },
    },
    {
        "id": f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-DEMO02",
        "status": ClaimStatus.HITL_REVIEW,
        "claimant_name": "Ananya Sharma",
        "policy_number": "HDFC/MOT/2023/987654",
        "insurance_type": "MOTOR",
        "claimed_amount": 185000.0,
        "currency": "INR",
        "fraud_score": 0.52,
        "fraud_level": "MEDIUM",
        "decision": "INVESTIGATE",
        "decision_confidence": 0.68,
        "decision_explanation": "Elevated fraud score due to claim filed 22 days after policy start. High-value motor claim requires human review.",
        "approved_amount": None,
        "extracted_data": {
            "claimant": {"name": "Ananya Sharma", "dob": "22/11/1992", "gender": "FEMALE",
                         "contact_number": "8765432109", "pan_number": "ABCDE1234F"},
            "policy": {"policy_number": "HDFC/MOT/2023/987654", "insurance_company": "HDFC ERGO",
                       "policy_type": "MOTOR", "sum_insured": 850000.0, "currency": "INR",
                       "policy_start_date": "01/05/2024"},
            "incident": {"incident_date": "23/05/2024", "incident_location": "NH-44, Nagpur",
                         "incident_description": "Vehicle lost control and hit divider. Significant damage to front section.",
                         "vehicle_number": "MH31AB1234", "reported_date": "24/05/2024"},
            "amounts": {"claimed_amount": 185000.0, "currency": "INR"},
            "country": "IN", "extraction_confidence": 0.88
        },
    },
    {
        "id": f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-DEMO03",
        "status": ClaimStatus.REJECTED,
        "claimant_name": "Mohammed Al-Rashid",
        "policy_number": "STAR/INTL/2024/UAE789",
        "insurance_type": "HEALTH",
        "claimed_amount": 15000.0,
        "currency": "USD",
        "fraud_score": 0.91,
        "fraud_level": "CRITICAL",
        "decision": "REJECT",
        "decision_confidence": 0.97,
        "decision_explanation": "Claim rejected due to critical fraud indicators: policy purchased 3 days before claim, claimed amount equals exact sum insured limit, hospital details unverifiable.",
        "approved_amount": None,
        "extracted_data": {
            "claimant": {"name": "Mohammed Al-Rashid", "contact_number": "+971501234567"},
            "policy": {"policy_number": "STAR/INTL/2024/UAE789", "insurance_company": "Star Health UAE",
                       "policy_type": "HEALTH", "sum_insured": 15000.0, "currency": "USD",
                       "policy_start_date": "01/06/2024"},
            "incident": {"incident_date": "04/06/2024", "hospital_name": "Hospital",
                         "diagnosis": "General treatment"},
            "amounts": {"claimed_amount": 15000.0, "currency": "USD"},
            "country": "AE", "extraction_confidence": 0.71
        },
    },
    {
        "id": f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-DEMO04",
        "status": ClaimStatus.OCR_PROCESSING,
        "claimant_name": None,
        "policy_number": None,
        "insurance_type": None,
        "claimed_amount": None,
        "currency": "INR",
        "fraud_score": None,
        "fraud_level": None,
        "decision": None,
        "decision_confidence": None,
        "decision_explanation": None,
        "approved_amount": None,
        "extracted_data": None,
    },
    {
        "id": f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-DEMO05",
        "status": ClaimStatus.APPROVED,
        "claimant_name": "Meenakshi Iyer",
        "policy_number": "NIA/PMFBY/2024/KAR5678",
        "insurance_type": "CROP",
        "claimed_amount": 32000.0,
        "currency": "INR",
        "fraud_score": 0.05,
        "fraud_level": "LOW",
        "decision": "APPROVE",
        "decision_confidence": 0.95,
        "decision_explanation": "PMFBY crop loss claim approved. Yield data from state CCE confirms drought-related crop failure in district. Settlement processed via NEFT.",
        "approved_amount": 32000.0,
        "extracted_data": {
            "claimant": {"name": "Meenakshi Iyer", "aadhaar_number": "XXXX-XXXX-5678",
                         "contact_number": "9123456780"},
            "policy": {"policy_number": "NIA/PMFBY/2024/KAR5678",
                       "insurance_company": "New India Assurance", "policy_type": "CROP",
                       "sum_insured": 35000.0, "currency": "INR"},
            "incident": {"incident_date": "15/07/2024", "incident_location": "Raichur District, Karnataka",
                         "incident_description": "Kharif paddy crop failed due to deficit monsoon rainfall (67% below normal)"},
            "amounts": {"claimed_amount": 32000.0, "currency": "INR"},
            "country": "IN", "extraction_confidence": 0.91
        },
    },
]


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...", end=" ")
    await init_db()
    print("✓ Done")


async def seed_sample_data():
    """Insert sample claims for testing."""
    print("Seeding sample data...")
    from app.infrastructure.db.models import ClaimDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(ClaimDB).limit(1))
        if result.scalar_one_or_none():
            print("  Sample data already exists. Skipping seed.")
            return

        for i, sample in enumerate(SAMPLE_CLAIMS, 1):
            claim = ClaimDB(
                id=sample["id"],
                correlation_id=str(uuid4()),
                status=sample["status"].value,
                country="IN",
                currency=sample["currency"],
                claimant_name=sample["claimant_name"],
                policy_number=sample["policy_number"],
                insurance_type=sample["insurance_type"],
                claimed_amount=sample["claimed_amount"],
                fraud_score=sample["fraud_score"],
                fraud_level=sample["fraud_level"],
                decision=sample["decision"],
                decision_confidence=sample["decision_confidence"],
                decision_explanation=sample["decision_explanation"],
                approved_amount=sample["approved_amount"],
                extracted_data=sample["extracted_data"],
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                updated_at=datetime.utcnow(),
            )
            db.add(claim)
            print(f"  [{i}] {sample['id']} — {sample['status'].value}")

        await db.commit()
        print(f"\n  ✓ {len(SAMPLE_CLAIMS)} sample claims inserted")


async def main(seed: bool = False):
    print()
    print("=" * 55)
    print("  INSURANCE CLAIMS PLATFORM — DB INITIALISATION")
    print("=" * 55)
    print()

    await create_tables()

    if seed:
        await seed_sample_data()

    print()
    print("  ✓ Database ready.")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialise the claims database")
    parser.add_argument("--seed", action="store_true", help="Insert sample demo claims")
    args = parser.parse_args()
    asyncio.run(main(seed=args.seed))
