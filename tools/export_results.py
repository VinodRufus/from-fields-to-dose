"""Export everything the paper and the article will quote: summary.json, CSV tables, run manifest, lock, deviations."""
import csv, glob, json, os, shutil, subprocess, sys, time
from collections import defaultdict
from harness.common import ROOT
from analysis.analyze import load, by_scenario, cluster_boot_mean, paired_cluster_boot
out = os.path.join(ROOT, "results", "export"); os.makedirs(out, exist_ok=True)
files = glob.glob(os.path.join(ROOT, "results", "scored_test_*.jsonl"))
if not files: sys.exit("no scored test files")
summary = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "models": {}, "comparisons": {}, "manifest": []}
runs = {}
for f in files:
    cfg, rows = load(f); c = cfg["_config"]
    rows = [r for r in rows if "record_id" in r]
    summary["manifest"].append({"file": os.path.basename(f), "model": c["model"], "workflow": c["workflow"], "run_id": c["run_id"], "subset": c.get("subset"), "started": c.get("started"), "system_prompt_sha256": c.get("system_prompt_sha256"), "task_prompt_sha256": c.get("task_prompt_sha256"), "n": len(rows)})
    if not c.get("subset"): runs[(c["model"]["id"], c["workflow"])] = rows
tab = []
for (mid, wf), rows in sorted(runs.items()):
    na = [r for r in rows if not r["abstention_case"]]; ab = [r for r in rows if r["abstention_case"]]
    m = {}
    for key in ("primary_endpoint", "field_acc", "complete_regimen", "dosing_consistent", "dose_consequential", "dose_consequential_sens", "exceeds_labeled_max"):
        est, lo, hi = cluster_boot_mean(by_scenario(na, key)); m[key] = {"est": est, "ci": [lo, hi]}
    for key in ("appropriate_abstention", "unnecessary_abstention", "hallucinated"):
        est, lo, hi = cluster_boot_mean(by_scenario(ab, key)); m[key] = {"est": est, "ci": [lo, hi], "n": len(ab)}
    m["n_records"] = len(rows); m["malformed"] = sum(1 for r in rows if r.get("malformed"))
    m["by_band"] = {b: cluster_boot_mean(by_scenario([r for r in na if r["age_band"] == b], "primary_endpoint"), B=500)[0] for b in sorted({r["age_band"] for r in na})}
    m["by_complexity"] = {c: cluster_boot_mean(by_scenario([r for r in na if r["complexity"] == c], "primary_endpoint"), B=500)[0] for c in (1, 2, 3)}
    codes = defaultdict(int)
    for r in na:
        for c in r.get("codes", []): codes[c] += 1
    m["error_codes"] = dict(sorted(codes.items(), key=lambda x: -x[1]))
    summary["models"][f"{mid}|{wf}"] = m
    tab.append([mid, wf, len(rows), round(m["primary_endpoint"]["est"], 3), round(m["primary_endpoint"]["ci"][0], 3), round(m["primary_endpoint"]["ci"][1], 3), round(m["field_acc"]["est"], 3), round(m["complete_regimen"]["est"], 3), round(m["dose_consequential"]["est"], 3), round(m["appropriate_abstention"]["est"], 3), round(m["hallucinated"]["est"], 3), m["malformed"]])
for mid in {k[0] for k in runs}:
    if (mid, "C") in runs and (mid, "B") in runs:
        dC = by_scenario([r for r in runs[(mid, "C")] if not r["abstention_case"]], "dose_consequential"); dB = by_scenario([r for r in runs[(mid, "B")] if not r["abstention_case"]], "dose_consequential")
        est, lo, hi = paired_cluster_boot(dC, dB); summary["comparisons"][mid] = {"C_minus_B_dose_consequential": est, "ci": [lo, hi]}
with open(os.path.join(out, "table_primary.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "workflow", "n", "primary", "ci_lo", "ci_hi", "field_acc", "complete_regimen", "dose_consequential", "appropriate_abstention", "hallucinated", "malformed"]); w.writerows(tab)
json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=2)
for p in ("data/test/LOCK.json", "protocol/DEVIATIONS.md", "config/models.yaml", "sources/dosing_sources.csv", "data/test/self_audit.jsonl", "data/test/audit.jsonl", "data/test/paraphrase.log"):
    src = os.path.join(ROOT, p)
    if os.path.exists(src): shutil.copy(src, os.path.join(out, os.path.basename(p)))
for p in glob.glob(os.path.join(ROOT, "results", "analysis_*.txt")) + glob.glob(os.path.join(ROOT, "results", "manual_codes*.jsonl")): shutil.copy(p, out)
print("exported to", out); print(open(os.path.join(out, "table_primary.csv")).read())
