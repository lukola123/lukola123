"""
Runs the claim review agent over validation_records.json (with known human
results for sanity-checking) and test_records.json (writes submission.csv).

Usage:
    python run_agent.py
"""
import json
import pandas as pd

from claim_agent.agent import build_agent, call_agent


def load_db(path, key):
    with open(path, "r") as f:
        records = json.load(f)
    return {r[key]: r for r in records}


def main():
    patient_db = load_db("Data/validation_records.json", "patient_id")
    agent = build_agent()

    print(f"Running agent on {len(patient_db)} validation records...\n")
    results = []
    for pid, record in patient_db.items():
        print(f"Processing {pid}...")
        response = call_agent(agent, query=f"Evaluate this claim: {record}")
        print(response, "\n")
        results.append({"patient_id": pid, "generated_response": response})

    validation_df = pd.DataFrame(results)
    human_df = pd.read_csv("Data/validation_reference_results.csv")
    merged = validation_df.merge(human_df, on="patient_id", how="inner")
    merged.to_csv("validation_comparison.csv", index=False)
    print("Saved validation_comparison.csv\n")

    # Test set -> submission.csv
    with open("Data/test_records.json", "r") as f:
        test_patients = json.load(f)

    print(f"Running agent on {len(test_patients)} test records...\n")
    test_results = []
    for record in test_patients:
        pid = record["patient_id"]
        print(f"Processing {pid}...")
        response = call_agent(agent, query=f"Evaluate this claim: {record}")
        test_results.append({"patient_id": pid, "generated_response": response})

    pd.DataFrame(test_results).to_csv("submission.csv", index=False)
    print("Saved submission.csv")


if __name__ == "__main__":
    main()
