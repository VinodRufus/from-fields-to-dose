"""Run-to-run stability (Protocol 15). Compares scored files of the SAME model+workflow with different run ids
on the records they share. Usage: python -m analysis.stability --scored results/scored_test_C_<model>_run1.jsonl results/scored_test_C_<model>_run2.jsonl results/scored_test_C_<model>_run3.jsonl"""
import argparse, json
from collections import defaultdict
def load(p):
    lines = [json.loads(l) for l in open(p)]
    return lines[0]["_config"], {x["record_id"]: x for x in lines[1:] if "record_id" in x}
ap = argparse.ArgumentParser(); ap.add_argument("--scored", nargs="+", required=True); a = ap.parse_args()
runs = [load(p) for p in a.scored]
ids = set.intersection(*[set(r[1].keys()) for r in runs])
print(f"model={runs[0][0]['model']['id']} wf={runs[0][0]['workflow']} runs={len(runs)} shared_records={len(ids)}")
def agree(key, sub=None):
    n = ok = 0
    for i in ids:
        vals = []
        for _, d in runs:
            v = d[i].get(key)
            if sub: v = (v or {}).get(sub)
            vals.append(json.dumps(v, sort_keys=True))
        n += 1; ok += all(v == vals[0] for v in vals)
    return ok / n if n else float("nan")
print(f"complete_regimen stable:   {agree('complete_regimen'):.3f}")
print(f"dosing_consistent stable:  {agree('dosing_consistent'):.3f}")
print(f"dose_consequential stable: {agree('dose_consequential'):.3f}")
for fld in ["drug", "current_weight_kg", "dose_basis", "weight_normalized_dose", "dose_unit", "dose_per_admin_mg", "frequency_per_day", "route"]:
    print(f"  field {fld:24s} stable: {agree('fields', fld):.3f}")
