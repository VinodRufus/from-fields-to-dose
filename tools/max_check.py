"""Post hoc check (added after registration, exploratory): does the written per-dose amount exceed the maximum the
model itself extracted? Tests both limits: dose_per_admin_mg against max_per_dose_mg, and dose_per_admin_mg times
frequency_per_day against max_per_day_mg, with a 0.1 percent tolerance. Also tests against the scenario's maxima.
Non-abstention run1 records, both workflows. Writes results/max_check_run1.csv.

Usage: python -m tools.max_check
"""
import csv, glob, json, os
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def main():
    sc = {}
    for l in open(os.path.join(ROOT, "data", "test", "scenarios.jsonl")):
        o = json.loads(l); sc[o["scenario_id"]] = o
    rows = []; tally = Counter()
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "scored_test_*_run1.jsonl"))):
        lines = [json.loads(l) for l in open(f)]; cfg = lines[0]["_config"]; mid, wf = cfg["model"]["id"], cfg["workflow"]
        raw = f.replace("scored_", "raw_")
        parsed = {}
        for l in open(raw):
            o = json.loads(l)
            if o.get("record_id") and o.get("parsed") is not None: parsed[o["record_id"]] = o["parsed"]
        for r in lines[1:]:
            if "record_id" not in r or r.get("abstention_case"): continue
            p = parsed.get(r["record_id"], {}) or {}; s = sc[r["scenario_id"]]
            w = num(p.get("dose_per_admin_mg")); fq = num(p.get("frequency_per_day")) or num(s.get("frequency_per_day"))
            own_d, own_day = num(p.get("max_per_dose_mg")), num(p.get("max_per_day_mg"))
            sc_d, sc_day = num(s.get("max_per_dose_mg")), num(s.get("max_per_day_mg"))
            f_own = w is not None and ((own_d is not None and w > own_d * 1.001) or (own_day is not None and fq and w * fq > own_day * 1.001))
            f_sc = w is not None and ((sc_d is not None and w > sc_d * 1.001) or (sc_day is not None and fq and w * fq > sc_day * 1.001))
            tally[(mid, wf, "flag_own")] += f_own; tally[(mid, wf, "flag_scenario")] += f_sc; tally[(mid, wf, "n")] += 1
            if f_own or f_sc:
                rows.append({"model": mid, "workflow": wf, "record_id": r["record_id"], "written_mg": w, "frequency": fq,
                             "own_max_per_dose": own_d, "own_max_per_day": own_day, "scenario_max_per_dose": sc_d, "scenario_max_per_day": sc_day,
                             "flag_own_max": f_own, "flag_scenario_max": f_sc, "dose_consequential": r.get("dose_consequential")})
    out = os.path.join(ROOT, "results", "max_check_run1.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["none"]); w.writeheader(); w.writerows(rows)
    print(f"wrote {out} ({len(rows)} flagged rows)")
    for (mid, wf) in sorted({(k[0], k[1]) for k in tally}):
        print(f"{mid:22s} {wf}  n={tally[(mid,wf,'n')]:3d}  flagged by model's own maxima={tally[(mid,wf,'flag_own')]:3d}  by scenario maxima={tally[(mid,wf,'flag_scenario')]:3d}")
    for r in rows:
        if not r["model"].startswith("llama"): print(f"  {r['model'][:10]} {r['workflow']} {r['record_id'][:50]} written={r['written_mg']} own_max={r['own_max_per_dose']}/{r['own_max_per_day']} flag_own={r['flag_own_max']} flag_scenario={r['flag_scenario_max']}")
if __name__ == "__main__": main()
