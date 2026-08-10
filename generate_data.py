"""
Generates synthetic, open-style data to replicate the claim-review agent project
without using any real patient/claims data.

Run: python generate_data.py
Outputs into ./Data/:
  - reference_codes.json
  - insurance_policies.json
  - validation_records.json
  - test_records.json
  - validation_reference_results.csv
"""
import json
import random
import csv
from datetime import date, timedelta

random.seed(42)

# ---------------------------------------------------------------------------
# 1. Reference codes (small open-style subset of real CPT / ICD-10 categories)
# ---------------------------------------------------------------------------
CPT_CODES = {
    "99213": "Office visit, established patient, low complexity",
    "99214": "Office visit, established patient, moderate complexity",
    "93000": "Electrocardiogram, routine ECG with interpretation",
    "71046": "Chest X-ray, 2 views",
    "29881": "Knee arthroscopy with meniscectomy",
    "45378": "Diagnostic colonoscopy",
    "27447": "Total knee replacement",
    "70551": "MRI brain without contrast",
    "73721": "MRI lower extremity joint without contrast",
    "97110": "Therapeutic exercise, physical therapy",
}

ICD10_CODES = {
    "I10": "Essential (primary) hypertension",
    "E11.9": "Type 2 diabetes mellitus without complications",
    "M17.0": "Bilateral primary osteoarthritis of knee",
    "J45.909": "Unspecified asthma, uncomplicated",
    "K21.9": "Gastro-esophageal reflux disease without esophagitis",
    "M54.5": "Low back pain",
    "R07.9": "Chest pain, unspecified",
    "S83.511A": "Sprain of anterior cruciate ligament of knee, initial encounter",
    "Z00.00": "Encounter for general adult medical exam without abnormal findings",
    "K57.30": "Diverticulosis of large intestine without perforation or abscess",
}

with open("Data/reference_codes.json", "w") as f:
    json.dump({"CPT": CPT_CODES, "ICD10": ICD10_CODES}, f, indent=2)

# ---------------------------------------------------------------------------
# 2. Insurance policies
# ---------------------------------------------------------------------------
policies = [
    {
        "policy_id": "POL001",
        "plan_name": "Bronze Essential",
        "covered_procedures": {
            "99213": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
            "93000": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
            "97110": {"requires_preauth": True, "min_age": 0, "max_age": 120, "gender": "any"},
        },
        "covered_diagnoses": ["I10", "E11.9", "M54.5", "J45.909"],
    },
    {
        "policy_id": "POL002",
        "plan_name": "Silver Plus",
        "covered_procedures": {
            "99214": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
            "71046": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
            "29881": {"requires_preauth": True, "min_age": 18, "max_age": 90, "gender": "any"},
            "45378": {"requires_preauth": True, "min_age": 45, "max_age": 120, "gender": "any"},
        },
        "covered_diagnoses": ["M17.0", "K21.9", "M54.5", "K57.30", "R07.9"],
    },
    {
        "policy_id": "POL003",
        "plan_name": "Gold Comprehensive",
        "covered_procedures": {
            "27447": {"requires_preauth": True, "min_age": 40, "max_age": 100, "gender": "any"},
            "70551": {"requires_preauth": True, "min_age": 0, "max_age": 120, "gender": "any"},
            "73721": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
            "99213": {"requires_preauth": False, "min_age": 0, "max_age": 120, "gender": "any"},
        },
        "covered_diagnoses": ["M17.0", "S83.511A", "R07.9", "Z00.00"],
    },
]

with open("Data/insurance_policies.json", "w") as f:
    json.dump(policies, f, indent=2)

# ---------------------------------------------------------------------------
# 3. Synthetic patient claim records
# ---------------------------------------------------------------------------
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Sam", "Drew", "Reese"]
LAST_NAMES = ["Nguyen", "Smith", "Garcia", "Patel", "Johnson", "Kim", "Brown", "Davis", "Lopez", "Wilson"]
GENDERS = ["male", "female"]


def random_dob(min_age=1, max_age=85):
    today = date(2025, 5, 1)
    age = random.randint(min_age, max_age)
    birth_year = today.year - age
    return date(birth_year, random.randint(1, 12), random.randint(1, 28)).isoformat()


def make_patient(pid, policy):
    proc_code = random.choice(list(policy["covered_procedures"].keys()) + list(CPT_CODES.keys()))
    diag_code = random.choice(policy["covered_diagnoses"] + list(ICD10_CODES.keys()))
    rule = policy["covered_procedures"].get(proc_code)
    preauth_required = rule["requires_preauth"] if rule else random.choice([True, False])
    preauth_obtained = random.choice([True, False]) if preauth_required else False

    return {
        "patient_id": pid,
        "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "gender": random.choice(GENDERS),
        "date_of_birth": random_dob(),
        "date_of_service": "2025-05-01",
        "policy_id": policy["policy_id"],
        "diagnosis_codes": [diag_code],
        "procedure_codes": [proc_code],
        "preauthorization_required": preauth_required,
        "preauthorization_obtained": preauth_obtained,
        "billed_amount": round(random.uniform(150, 12000), 2),
    }


def expected_decision(patient, policy):
    """Simple ground-truth logic used to label synthetic validation data."""
    proc_code = patient["procedure_codes"][0]
    diag_code = patient["diagnosis_codes"][0]
    rule = policy["covered_procedures"].get(proc_code)

    if not rule:
        return "Route for Review"
    if diag_code not in policy["covered_diagnoses"]:
        return "Route for Review"

    dob = date.fromisoformat(patient["date_of_birth"])
    svc = date.fromisoformat(patient["date_of_service"])
    age = svc.year - dob.year - ((svc.month, svc.day) < (dob.month, dob.day))
    if not (rule["min_age"] <= age <= rule["max_age"]):
        return "Route for Review"

    if rule["requires_preauth"] and not patient["preauthorization_obtained"]:
        return "Route for Review"

    return "Approved"


policy_by_id = {p["policy_id"]: p for p in policies}

validation_records = []
validation_rows = []
for i in range(1, 16):
    pid = f"P{i:03d}"
    policy = random.choice(policies)
    patient = make_patient(pid, policy)
    validation_records.append(patient)
    validation_rows.append({
        "patient_id": pid,
        "human_decision": expected_decision(patient, policy),
    })

test_records = []
for i in range(16, 26):
    pid = f"P{i:03d}"
    policy = random.choice(policies)
    test_records.append(make_patient(pid, policy))

with open("Data/validation_records.json", "w") as f:
    json.dump(validation_records, f, indent=2)

with open("Data/test_records.json", "w") as f:
    json.dump(test_records, f, indent=2)

with open("Data/validation_reference_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["patient_id", "human_decision"])
    writer.writeheader()
    writer.writerows(validation_rows)

print("Synthetic data generated in ./Data/")
print(f"  - {len(validation_records)} validation records")
print(f"  - {len(test_records)} test records")
print(f"  - {len(policies)} policies, {len(CPT_CODES)} CPT codes, {len(ICD10_CODES)} ICD-10 codes")
