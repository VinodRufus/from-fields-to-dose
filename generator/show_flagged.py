"""Print flagged records from audit.jsonl with their text, for manual fix or removal before lock."""
import argparse, json, os
from harness.common import ROOT
ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); a = ap.parse_args()
d = os.path.join(ROOT, "data", a.split)
recs = {json.loads(l)["record_id"]: json.loads(l) for l in open(os.path.join(d, "records.jsonl"))}
for l in open(os.path.join(d, "audit.jsonl")):
    x = json.loads(l)
    if x["flagged"]:
        print("=" * 80); print(x["record_id"], json.dumps(x["audit"])); print(recs[x["record_id"]]["text"])
