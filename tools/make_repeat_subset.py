"""Stratified repeat subset (Protocol 15): 30% of test records by band x complexity. Run BEFORE lock."""
import argparse, json, os, random, sys
from collections import defaultdict
from harness.common import ROOT
ap = argparse.ArgumentParser(); ap.add_argument("--split", default="test"); ap.add_argument("--fraction", type=float, default=0.30); ap.add_argument("--seed", type=int, default=5); a = ap.parse_args()
d = os.path.join(ROOT, "data", a.split)
if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("refusing: split is locked (subset must be fixed before lock)")
recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
strata = defaultdict(list)
for r in recs: strata[(r["age_band"], r["complexity"])].append(r["record_id"])
rng = random.Random(a.seed); chosen = []
for k, ids in sorted(strata.items()):
    n = max(1, round(len(ids) * a.fraction)); rng.shuffle(ids); chosen += ids[:n]
out = os.path.join(d, "repeat_subset.txt")
open(out, "w").write("\n".join(sorted(chosen)) + "\n")
print(f"repeat subset: {len(chosen)} of {len(recs)} records -> {out}")
