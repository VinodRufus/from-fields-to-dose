"""Manual coding of residual errors (Protocol 13), blinded to model identity, random order.
Usage: python -m tools.code_errors --scored 'results/scored_test_*_run1.jsonl'      # first pass
       python -m tools.code_errors --recode 0.10                                      # re-code a 10% sample later"""
import argparse, glob, json, os, random, sys
from harness.common import ROOT
CODES = ["E1 extraction", "E2 normalization", "E3 association", "E4 temporal", "E5 volume_vs_dose", "E6 other"]
ap = argparse.ArgumentParser(); ap.add_argument("--scored", nargs="*"); ap.add_argument("--recode", type=float, default=None); ap.add_argument("--seed", type=int, default=3); a = ap.parse_args()
path = os.path.join(ROOT, "results", "manual_codes.jsonl"); done = {}
if os.path.exists(path):
    for l in open(path): x = json.loads(l); done[(x["file"], x["record_id"])] = x
if a.recode:
    items = list(done.values()); rng = random.Random(a.seed + 1); sample = rng.sample(items, max(1, int(len(items) * a.recode)))
    agree = 0; out = open(os.path.join(ROOT, "results", "manual_codes_recode.jsonl"), "a")
    for x in sample:
        print("=" * 80); print(x["text"]); print("OUTPUT:", json.dumps(x["parsed"])); print("auto codes:", x["codes"])
        print("Codes:", " | ".join(CODES)); c = input("code> ").strip()
        agree += (c.split()[0] == x["code"].split()[0]); out.write(json.dumps({**x, "recode": c}) + "\n")
    print(f"intra-rater agreement: {agree}/{len(sample)} = {agree/len(sample):.3f}"); sys.exit(0)
files = [f for pat in a.scored for f in glob.glob(pat)]
items = []
for f in files:
    lines = [json.loads(l) for l in open(f)]; split = lines[0]["_config"]["split"]
    recs = {json.loads(l)["record_id"]: json.loads(l) for l in open(os.path.join(ROOT, "data", split, "records.jsonl"))}
    raw_path = f.replace("scored_", "raw_"); raws = {}
    for l in open(raw_path):
        d = json.loads(l)
        if "record_id" in d: raws[d["record_id"]] = d
    for x in lines[1:]:
        if "record_id" not in x or x.get("abstention_case"): continue
        if x.get("complete_regimen") and x.get("dosing_consistent"): continue
        if any(c.startswith("extraction:") for c in x.get("codes", [])) and (os.path.basename(f), x["record_id"]) not in done:
            items.append({"file": os.path.basename(f), "record_id": x["record_id"], "text": recs[x["record_id"]]["text"], "parsed": raws[x["record_id"]].get("parsed"), "codes": x["codes"]})
random.Random(a.seed).shuffle(items)
print(f"{len(items)} residual errors to code (model identity hidden). 'q' to stop; progress is saved.")
with open(path, "a") as out:
    for it in items:
        print("=" * 80); print(it["text"]); print("OUTPUT:", json.dumps(it["parsed"])); print("auto codes:", it["codes"])
        print("Codes:", " | ".join(CODES)); c = input("code> ").strip()
        if c == "q": break
        it["code"] = c; out.write(json.dumps(it) + "\n"); out.flush()
