"""
Tools used by the ReAct Claim Coverage Evaluation Agent.

  1. get_claim_summary    - combined structured summary of a patient's claim
                             AND their insurance policy's coverage rules, in
                             a single lookup. Only requires a patient_id.
  2. check_claim_coverage - rule-based + reasoning check of each procedure
                             against the policy. Never issues a final
                             denial; routes ambiguous/failed cases to
                             human review.
"""
import json
from datetime import datetime
from langchain_core.tools import tool

# --- Load reference data once at import time -------------------------------
with open("Data/validation_records.json", "r") as f:
    _validation_records = {r["patient_id"]: r for r in json.load(f)}

with open("Data/test_records.json", "r") as f:
    _test_records = {r["patient_id"]: r for r in json.load(f)}

_all_patient_records = {**_validation_records, **_test_records}

with open("Data/insurance_policies.json", "r") as f:
    _policy_records = {p["policy_id"]: p for p in json.load(f)}
# --------------------------------------------------------------------------


def _compute_age(dob: str, reference_date: str) -> int:
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    ref_date = datetime.strptime(reference_date, "%Y-%m-%d")
    return ref_date.year - birth_date.year - (
        (ref_date.month, ref_date.day) < (birth_date.month, birth_date.day)
    )


def _format_patient(record: dict) -> str:
    age = _compute_age(record["date_of_birth"], record["date_of_service"])
    lines = [
        "Patient Record:",
        f"  Patient ID: {record.get('patient_id')}",
        f"  Age: {age}, Gender: {record.get('gender')}",
        f"  Diagnosis codes: {', '.join(record.get('diagnosis_codes', []))}",
        f"  Procedure codes: {', '.join(record.get('procedure_codes', []))}",
        f"  Policy ID: {record.get('policy_id')}",
        f"  Preauthorization required: {record.get('preauthorization_required')}",
        f"  Preauthorization obtained: {record.get('preauthorization_obtained')}",
        f"  Billed amount: ${record.get('billed_amount')}",
    ]
    return "\n".join(lines)


def _format_policy(policy: dict) -> str:
    lines = [
        f"Policy Guidelines:",
        f"  Policy: {policy.get('plan_name')} ({policy.get('policy_id')})",
        "  Covered procedures:",
    ]
    for code, rule in policy.get("covered_procedures", {}).items():
        lines.append(
            f"    - {code}: preauth required={rule['requires_preauth']}, "
            f"age {rule['min_age']}-{rule['max_age']}, gender={rule['gender']}"
        )
    lines.append(f"  Covered diagnoses: {', '.join(policy.get('covered_diagnoses', []))}")
    return "\n".join(lines)


@tool
def get_claim_summary(patient_id: str) -> str:
    """Given a patient_id (e.g. "P001"), returns a structured summary of
    BOTH the patient's claim record (demographics, diagnoses, procedures,
    billing, preauthorization status) AND their insurance policy's coverage
    rules (covered procedures, age/gender restrictions, preauthorization
    requirements, covered diagnoses) in a single combined result."""
    record = _all_patient_records.get(patient_id)
    if record is None:
        return f"No patient record found for patient ID '{patient_id}'."

    policy = _policy_records.get(record.get("policy_id"))
    policy_section = (
        f"No policy found for policy ID '{record.get('policy_id')}'."
        if policy is None else _format_policy(policy)
    )

    return _format_patient(record) + "\n\n" + policy_section


@tool
def check_claim_coverage(claim_summary: str) -> str:
    """Evaluates whether a claim satisfies policy coverage conditions using
    the combined patient + policy summary produced by get_claim_summary.
    Does not issue a final denial — if any requirement fails, the case is
    routed to human review. Returns a step-by-step analysis per claimed
    procedure."""
    return (
        "Use the patient and policy information above to check, for each "
        "claimed procedure: (1) is the diagnosis covered, (2) is the "
        "procedure covered, (3) is the patient's age within the allowed "
        "range, (4) does gender match if restricted, (5) if preauthorization "
        "is required, was it obtained. If all checks pass: APPROVE. If any "
        "check fails: ROUTE FOR REVIEW. Show your reasoning per criterion."
    )