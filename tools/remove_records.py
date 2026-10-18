"""Remove records (and their scenarios if no records remain) before lock. Usage: python -m tools.remove_records --split dev --ids id1 id2 ..."""
import argparse, json, os, sys
from harness.common import ROOT
ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); ap.add_argument("--ids", nargs="+", required=True); a = ap.parse_args()
d = os.path.join(ROOT, "data", a.split)
if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("refusing: split is locked")
recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
keep = [r for r in recs if r["record_id"] not in set(a.ids)]
used = {r["scenario_id"] for r in keep}
scen = [json.loads(l) for l in open(os.path.join(d, "scenarios.jsonl"))]
scen_keep = [s for s in scen if s["scenario_id"] in used]
open(os.path.join(d, "records.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in keep))
open(os.path.join(d, "scenarios.jsonl"), "w").write("".join(json.dumps(s) + "\n" for s in scen_keep))
with open(os.path.join(d, "removals.log"), "a") as f:
    for i in a.ids: f.write(i + "\n")
print(f"removed {len(recs)-len(keep)} records; {len(keep)} records, {len(scen_keep)} scenarios remain")
