"""Lock the test set: SHA-256 of records, scenarios, repeat subset, scoring code, prompts, schema. Put the hashes in the OSF registration."""
import hashlib, json, os, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def hash_file(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
def hash_scoring():
    h = hashlib.sha256()
    for p in ("scoring/score.py", "generator/calculator.py", "harness/prompts/system.txt", "harness/prompts/task_B.txt", "harness/prompts/task_C.txt", "harness/output_schema.json", "analysis/analyze.py"):
        h.update(open(os.path.join(ROOT, p), "rb").read())
    return h.hexdigest()
def main():
    d = os.path.join(ROOT, "data", "test")
    if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("already locked")
    for req in ("records.jsonl", "scenarios.jsonl", "repeat_subset.txt"):
        if not os.path.exists(os.path.join(d, req)): sys.exit(f"missing data/test/{req} (build the test set and run tools.make_repeat_subset first)")
    lock = {"locked_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "records_sha256": hash_file(os.path.join(d, "records.jsonl")),
            "scenarios_sha256": hash_file(os.path.join(d, "scenarios.jsonl")), "repeat_subset_sha256": hash_file(os.path.join(d, "repeat_subset.txt")),
            "scoring_sha256": hash_scoring(), "n_records": sum(1 for _ in open(os.path.join(d, "records.jsonl"))),
            "smoke": os.path.exists(os.path.join(d, "SMOKE"))}
    json.dump(lock, open(os.path.join(d, "LOCK.json"), "w"), indent=2)
    print(json.dumps(lock, indent=2)); print("\nCopy these hashes into the OSF registration. Do not modify data/test/ after this point.")
if __name__ == "__main__": main()
