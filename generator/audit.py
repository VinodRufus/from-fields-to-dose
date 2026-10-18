"""Automated realism audit by a model family NOT under test (Protocol 8.2). Reports flag rate; flagged
records are listed for the author to fix or remove before lock.
Usage: python -m generator.audit --split dev [--fake]"""
from __future__ import annotations
import argparse, json, os, sys
from harness.common import ROOT, load_config, call_model, extract_json, ModelError

RUBRIC = """You are auditing a SYNTHETIC pediatric clinical note for a research benchmark. Answer strictly as JSON:
{"reads_as_plausible_note": true/false, "regimen_recoverable": true/false, "unintended_contradiction": true/false,
 "contains_identifiers_or_phi": true/false, "comment": "<one sentence>"}
Definitions: plausible = a clinician would recognize it as a real note style; recoverable = a careful reader can determine the
target medication's current weight, dose, frequency and route (or can tell that one is missing); unintended_contradiction =
values conflict in a way that looks like a generator mistake rather than a deliberate documented discrepancy.
Note:
<<<
{text}
>>>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    cfg = load_config(); aud = cfg.get("auditor") or cfg.get("generator") or {}
    if not a.fake and not aud.get("id"): sys.exit("config/models.yaml: auditor.id (or generator.id) is empty")
    d = os.path.join(ROOT, "data", a.split)
    if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("refusing: split is locked")
    recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
    if a.limit: recs = recs[: a.limit]
    out = os.path.join(d, "audit.jsonl"); flags = 0; errs = 0
    with open(out, "w") as f:
        for i, r in enumerate(recs, 1):
            if a.fake:
                res = {"reads_as_plausible_note": True, "regimen_recoverable": True, "unintended_contradiction": False, "contains_identifiers_or_phi": False, "comment": "fake"}
            else:
                try:
                    res = extract_json(call_model(aud, "You are a careful clinical documentation auditor.", RUBRIC.replace("{text}", r["text"]), want_json=True)) or {}
                except ModelError as e:
                    res = {"error": str(e)}; errs += 1
            flagged = (not res.get("reads_as_plausible_note", True)) or (not res.get("regimen_recoverable", True)) or res.get("unintended_contradiction", False) or res.get("contains_identifiers_or_phi", False)
            if flagged: flags += 1
            f.write(json.dumps({"record_id": r["record_id"], "flagged": flagged, "audit": res}) + "\n")
            if i % 25 == 0: print(f"  {i}/{len(recs)} flagged={flags}")
    print(f"[{a.split}] audited={len(recs)} flagged={flags} ({100*flags/max(1,len(recs)):.1f}%) errors={errs} -> {out}")
    print("Review flagged records: python -m generator.show_flagged --split", a.split)

if __name__ == "__main__": main()
