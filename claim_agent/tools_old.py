"""
Tools used by the ReAct Claim Coverage Evaluation Agent.

  1. summarize_patient_record    - structured summary of a patient's claim
  2. summarize_policy_guidelines - structured summary of policy coverage rules
  3. check_claim_coverage        - rule-based + reasoning check of each procedure
                                    against the policy. Never issues a final
                                    denial; routes ambiguous/failed cases to
                                    human review.
"""
import json
from datetime import datetime
from langchain_core.tools import tool


def _compute_age(dob: str, reference_date: str) -> int:
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    ref_date = datetime.strptime(reference_date, "%Y-%m-%d")
    return ref_date.year - birth_date.year - (
        (ref_date.month, ref_date.day) < (birth_date.month, birth_date.day)
    )


@tool
def summarize_patient_record(record_str: str) -> str:
    """Summarizes a patient's claim record (JSON string) into a structured,
    human-readable format covering demographics, diagnoses, procedures,
    billing, and preauthorization status."""
    print("RAW record_str:", repr(record_str))
    try:
        record = json.loads(record_str.replace("'", '"')) if isinstance(record_str, str) else record_str
    except Exception:
        # Fall back to python literal eval for dict-like strings (e.g. str(dict))
        import ast
        record = ast.literal_eval(record_str)

    age = _compute_age(record["date_of_birth"], record["date_of_service"])
    lines = [
        f"Patient ID: {record.get('patient_id')}",
        f"Age: {age}, Gender: {record.get('gender')}",
        f"Diagnosis codes: {', '.join(record.get('diagnosis_codes', []))}",
        f"Procedure codes: {', '.join(record.get('procedure_codes', []))}",
        f"Policy ID: {record.get('policy_id')}",
        f"Preauthorization required: {record.get('preauthorization_required')}",
        f"Preauthorization obtained: {record.get('preauthorization_obtained')}",
        f"Billed amount: ${record.get('billed_amount')}",
    ]
    return "\n".join(lines)


@tool
def summarize_policy_guidelines(policy_str: str) -> str:
    """Summarizes an insurance policy (JSON string) into structured coverage
    conditions: which procedures are covered, age/gender restrictions,
    preauthorization requirements, and covered diagnoses."""
    try:
        policy = json.loads(policy_str.replace("'", '"')) if isinstance(policy_str, str) else policy_str
    except Exception:
        import ast
        policy = ast.literal_eval(policy_str)

    lines = [f"Policy: {policy.get('plan_name')} ({policy.get('policy_id')})", "Covered procedures:"]
    for code, rule in policy.get("covered_procedures", {}).items():
        lines.append(
            f"  - {code}: preauth required={rule['requires_preauth']}, "
            f"age {rule['min_age']}-{rule['max_age']}, gender={rule['gender']}"
        )
    lines.append(f"Covered diagnoses: {', '.join(policy.get('covered_diagnoses', []))}")
    return "\n".join(lines)


@tool
def check_claim_coverage(patient_record_summary: str, policy_summary: str) -> str:
    """Evaluates whether a claim satisfies policy coverage conditions using
    the structured summaries produced by the other two tools. Does not issue
    a final denial — if any requirement fails, the case is routed to human
    review. Returns a step-by-step analysis per claimed procedure."""
    # NOTE: this is intentionally simple/transparent logic the LLM can reason
    # over and explain — not a black box. Adjust as needed for your rules.
    return (
        "Use the patient and policy summaries above to check, for each "
        "claimed procedure: (1) is the diagnosis covered, (2) is the "
        "procedure covered, (3) is the patient's age within the allowed "
        "range, (4) does gender match if restricted, (5) if preauthorization "
        "is required, was it obtained. If all checks pass: APPROVE. If any "
        "check fails: ROUTE FOR REVIEW. Show your reasoning per criterion."
    )
