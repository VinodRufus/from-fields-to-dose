"""Exploratory secondary analysis (added after registration): the written per-dose amount.

For every model and workflow, on the 304 non-abstention run1 records, compares the per-dose amount the
model actually wrote (dose_per_admin_mg in its parsed output) with the scenario's expected_dose_per_admin_mg,
which is the printed order amount: practical rounding applied, labelled maximum applied, in mg. This is a
different question from Level 4, which recomputes exposure from the extracted weight and mg/kg value: here
the question is whether the number the model wrote down is itself usable.

Rules: a written amount is "off" when its absolute relative deviation from the reference exceeds 10 percent;
"missing" when the field is absent, null or non-numeric; records whose scenario has no reference amount are
counted separately and excluded from the comparison. No unit conversion is applied: both sides are mg.

Writes results/admin_amount_run1.csv (one row per record) and prints a table by model, workflow and level.

Usage: python -m tools.admin_amount --scored 'results/scored_test_*_run1.jsonl'
"""
import argparse, csv, glob, json, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--tol", type=float, default=0.10)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "admin_amount_run1.csv"))
    a = ap.parse_args()
    rows_out = []
    table = defaultdict(lambda: {"n": 0, "compared": 0, "off": 0, "missing": 0, "no_ref": 0})
    for f in sorted(glob.glob(a.scored)):
        lines = [json.loads(l) for l in open(f)]
        cfg = lines[0]["_config"]
        split, mid, wf = cfg["split"], cfg["model"]["id"], cfg["workflow"]
        sc = {}
        for l in open(os.path.join(ROOT, "data", split, "scenarios.jsonl")):
            o = json.loads(l); sc[o["scenario_id"]] = o
        raw_path = os.path.join(ROOT, "results", f"raw_{split}_{wf}_{mid.replace(':', '_')}_run1.jsonl")
        if not os.path.exists(raw_path):
            raw_path = f.replace("scored_", "raw_")
        parsed = {}
        for l in open(raw_path):
            o = json.loads(l)
            if o.get("record_id") and o.get("parsed") is not None:
                parsed[o["record_id"]] = o["parsed"]
        for r in lines[1:]:
            if "record_id" not in r or r.get("abstention_case"):
                continue
            s = sc.get(r["scenario_id"], {})
            k = (mid, wf, int(r.get("complexity", 0)))
            table[k]["n"] += 1
            ref = s.get("expected_dose_per_admin_mg")
            try:
                ref = float(ref)
            except (TypeError, ValueError):
                ref = None
            p = parsed.get(r["record_id"], {}) or {}
            val = p.get("dose_per_admin_mg")
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = None
            status, dev = "", ""
            if ref is None or ref == 0:
                status = "no_reference"; table[k]["no_ref"] += 1
            elif val is None:
                status = "missing"; table[k]["missing"] += 1
            else:
                dev = abs(val - ref) / ref
                table[k]["compared"] += 1
                if dev > a.tol:
                    status = "off"; table[k]["off"] += 1
                else:
                    status = "within"
            rows_out.append({"model": mid, "workflow": wf, "record_id": r["record_id"], "scenario_id": r["scenario_id"],
                             "complexity": r.get("complexity"), "drug": s.get("drug"), "reference_mg": ref,
                             "written_mg": val, "relative_deviation": round(dev, 4) if dev != "" else "", "status": status,
                             "dose_consequential_level4": r.get("dose_consequential")})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)
    print(f"wrote {a.out} ({len(rows_out)} rows); tolerance {a.tol:.0%}; reference = scenario expected_dose_per_admin_mg (printed, capped, mg)")
    print(f"{'model':22s} wf  level  n    compared  off   missing  no_ref")
    totals = defaultdict(lambda: {"n": 0, "compared": 0, "off": 0, "missing": 0, "no_ref": 0})
    for (mid, wf, lvl), v in sorted(table.items()):
        print(f"{mid:22s} {wf}   L{lvl}     {v['n']:3d}  {v['compared']:5d}     {v['off']:3d}   {v['missing']:4d}     {v['no_ref']:3d}")
        for kk in v: totals[(mid, wf)][kk] += v[kk]
    print("-- totals --")
    for (mid, wf), v in sorted(totals.items()):
        print(f"{mid:22s} {wf}   all    {v['n']:3d}  {v['compared']:5d}     {v['off']:3d}   {v['missing']:4d}     {v['no_ref']:3d}")


if __name__ == "__main__":
    main()
