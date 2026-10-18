"""Per-drug breakdown of run1 results (supplementary table).

For each model and workflow: records per drug, primary endpoint rate, dose-consequential error rate,
and the count of abstention records. Writes results/per_drug_run1.csv and prints a compact table.
Malformed outputs count as failures (Section 12).

Usage: python -m tools.per_drug --scored 'results/scored_test_*_run1.jsonl'
"""
import argparse, csv, glob, json, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "per_drug_run1.csv"))
    a = ap.parse_args()
    split = None
    acc = defaultdict(lambda: {"n": 0, "primary": 0, "dc": 0, "abst": 0, "abst_ok": 0})
    for f in sorted(glob.glob(a.scored)):
        lines = [json.loads(l) for l in open(f)]
        cfg = lines[0]["_config"]; split = split or cfg["split"]
        drug_of = {json.loads(l)["scenario_id"]: json.loads(l)["drug"] for l in open(os.path.join(ROOT, "data", split, "scenarios.jsonl"))}
        mid, wf = cfg["model"]["id"], cfg["workflow"]
        for r in lines[1:]:
            if "record_id" not in r:
                continue
            k = (mid, wf, drug_of.get(r["scenario_id"], "?"))
            if r.get("abstention_case"):
                acc[k]["abst"] += 1
                if r.get("appropriate_abstention") is True:
                    acc[k]["abst_ok"] += 1
                continue
            acc[k]["n"] += 1
            pe = r.get("primary_endpoint")
            if pe is None and r.get("malformed"):
                pe = False
            acc[k]["primary"] += 1 if pe else 0
            acc[k]["dc"] += 1 if r.get("dose_consequential") else 0
    rows = []
    for (mid, wf, drug), v in sorted(acc.items()):
        rows.append({"model": mid, "workflow": wf, "drug": drug, "n_non_abstention": v["n"],
                     "primary_endpoint_rate": round(v["primary"] / v["n"], 3) if v["n"] else "",
                     "dose_consequential_rate": round(v["dc"] / v["n"], 3) if v["n"] else "",
                     "n_abstention": v["abst"], "appropriate_abstention": v["abst_ok"]})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"wrote {a.out} ({len(rows)} rows)")
    for r in rows:
        if r["n_non_abstention"]:
            print(f"{r['model']:22s} wf={r['workflow']} {r['drug']:26s} n={r['n_non_abstention']:3d} primary={r['primary_endpoint_rate']:<6} dose_conseq={r['dose_consequential_rate']:<6} abst={r['n_abstention']}/{r['appropriate_abstention']}")


if __name__ == "__main__":
    main()
