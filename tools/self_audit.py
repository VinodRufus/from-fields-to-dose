"""Blinded self-audit (Protocol 3.3 step 5): shows a random 10% of records with canonical values hidden; you type
what the note says; the script compares with the canonical values and reports the correction rate.
Usage: python -m tools.self_audit --split test --fraction 0.10"""
import argparse, json, os, random, sys
from harness.common import ROOT
from generator.calculator import to_kg
ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); ap.add_argument("--fraction", type=float, default=0.10); ap.add_argument("--seed", type=int, default=11); a = ap.parse_args()
d = os.path.join(ROOT, "data", a.split)
if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("split is locked; the self-audit must happen before lock")
recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
scen = {json.loads(l)["scenario_id"]: json.loads(l) for l in open(os.path.join(d, "scenarios.jsonl"))}
rng = random.Random(a.seed); sample = rng.sample(recs, max(1, int(len(recs) * a.fraction)))
out = open(os.path.join(d, "self_audit.jsonl"), "a"); n = 0; corrections = 0
print(f"{len(sample)} records. For each, type: weight_kg, dose_per_kg, frequency_per_day, route  (or 'missing' for a field, or 'q' to stop)\n")
for r in sample:
    s = scen[r["scenario_id"]]
    print("=" * 80); print(r["record_id"]); print(r["text"])
    ans = input("> ").strip()
    if ans == "q": break
    parts = [x.strip() for x in ans.split(",")]
    truth = {"weight_kg": None if "current_weight_value" in s.get("missing_fields", []) + s.get("conflict_fields", []) else round(to_kg(s["current_weight_value"], s["current_weight_unit"]), 2),
             "dose_per_kg": s["weight_normalized_dose"], "frequency_per_day": None if "frequency_per_day" in s.get("missing_fields", []) else s["frequency_per_day"], "route": s["route"]}
    def eq(x, t):
        if t is None: return x.lower() == "missing"
        try: return abs(float(x) - float(t)) / max(abs(float(t)), 1e-9) <= 0.02
        except Exception: return x.lower() == str(t).lower()
    ok = len(parts) == 4 and all(eq(parts[i], list(truth.values())[i]) for i in range(4))
    n += 1; corrections += (0 if ok else 1)
    print("match" if ok else f"MISMATCH vs canonical {truth}  (if the NOTE is wrong, fix the generator; if your reading was wrong, that is fine)")
    out.write(json.dumps({"record_id": r["record_id"], "answer": ans, "truth": truth, "match": ok}) + "\n")
print(f"\naudited={n} mismatches={corrections} rate={corrections/max(1,n):.3f}  (report this rate in the paper)")
