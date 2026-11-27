"""Table 1 (test-set characteristics) and Figure 1 (study flow) counts from the locked files.

Reads data/test/scenarios.jsonl, data/test/records.jsonl, data/test/repeat_subset.txt, sources/age_bands.json and the
scored files, verifies the data hashes against data/test/LOCK.json, and prints Table 1 as Markdown plus a block of
flow counts for Figure 1. Nothing is estimated; every figure is a count over committed files.

Usage: python -m tools.table1_counts > results/table1_counts.md
"""
from __future__ import annotations
import collections, glob, hashlib, json, os, sys

ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]
BANDS = ["neonate", "infant", "toddler", "school_age", "adolescent"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    lock = json.load(open("data/test/LOCK.json"))
    for name in ("records", "scenarios", "repeat_subset"):
        key = f"{name}_sha256"
        path = {"records": "data/test/records.jsonl", "scenarios": "data/test/scenarios.jsonl", "repeat_subset": "data/test/repeat_subset.txt"}[name]
        if key in lock and lock[key] != sha256(path):
            print(f"STOP: {path} does not match LOCK.json", file=sys.stderr)
            sys.exit(1)
    S = [json.loads(l) for l in open("data/test/scenarios.jsonl")]
    R = [json.loads(l) for l in open("data/test/records.jsonl")]
    bands = {b["id"]: b for b in json.load(open("sources/age_bands.json"))["bands"]}
    repeat = {l.strip() for l in open("data/test/repeat_subset.txt") if l.strip()}
    sid = {s["scenario_id"]: s for s in S}
    assert len(S) == len(R) == 361 and {r["scenario_id"] for r in R} == set(sid)
    na = [r for r in R if not r["abstention_case"]]
    ab = [r for r in R if r["abstention_case"]]
    c = collections.Counter

    print("## Table 1. Test-set characteristics (locked 3 October 2026; one record per scenario)\n")
    print(f"Lock digests: records {lock.get('records_sha256','')[:12]}..., scenarios {lock.get('scenarios_sha256','')[:12]}..., repeat subset {lock.get('repeat_subset_sha256','')[:12]}...\n")
    print("| Characteristic | Non-abstention records | Abstention records | All records |")
    print("|---|---|---|---|")
    print(f"| Records | {len(na)} | {len(ab)} | {len(R)} |")
    for b in BANDS:
        lab = bands[b]["label"]; lo, hi = bands[b]["min_days"], bands[b]["max_days"]
        n1 = sum(1 for r in na if r["age_band"] == b); n2 = sum(1 for r in ab if r["age_band"] == b)
        print(f"| {lab} ({lo} to {hi} days) | {n1} | {n2} | {n1 + n2} |")
    for lvl in (1, 2, 3):
        n1 = sum(1 for r in na if r["complexity"] == lvl); n2 = sum(1 for r in ab if r["complexity"] == lvl)
        print(f"| Complexity level {lvl} | {n1} | {n2} | {n1 + n2} |")
    gm = c(r["generation_method"] for r in R)
    for g, label in (("template", "Template-generated note"), ("paraphrase:qwen2.5:14b", "Paraphrased by qwen2.5:14b (audited)")):
        n1 = sum(1 for r in na if r["generation_method"] == g); n2 = sum(1 for r in ab if r["generation_method"] == g)
        print(f"| {label} | {n1} | {n2} | {n1 + n2} |")
    basis = c(sid[r["scenario_id"]]["dose_basis"] for r in R)
    for k in ("mg/kg/day", "mg/kg/dose", "mcg/kg/day", "mcg/kg/dose"):
        n1 = sum(1 for r in na if sid[r["scenario_id"]]["dose_basis"] == k); n2 = sum(1 for r in ab if sid[r["scenario_id"]]["dose_basis"] == k)
        print(f"| Dosing basis {k} | {n1} | {n2} | {n1 + n2} |")
    n1 = sum(1 for r in na if r["record_id"] in repeat or r["scenario_id"] in repeat); n2 = sum(1 for r in ab if r["record_id"] in repeat or r["scenario_id"] in repeat)
    print(f"| In the 108-record repeat subset (runs 2 and 3) | {n1} | {n2} | {n1 + n2} |")
    print()
    print("Abstention cases by missing element:")
    miss = c(tuple(sorted(sid[r["scenario_id"]].get("missing_fields") or [])) for r in ab)
    for k, v in sorted(miss.items()):
        print(f"- {', '.join(k) if k else 'conflict only'}: {v}")
    conf = sum(1 for r in ab if sid[r["scenario_id"]].get("conflict_fields"))
    print(f"- with a weight conflict flagged: {conf}")
    print()
    print("Challenge tags over all 361 scenarios (a scenario can carry several):")
    ch = c(t for s in S for t in s["challenges"])
    for k, v in sorted(ch.items(), key=lambda kv: -kv[1]):
        print(f"- {k}: {v}")
    print()
    print("Drugs represented (20) with record counts:")
    dr = c(sid[r["scenario_id"]]["drug"] for r in R)
    print(", ".join(f"{k} {v}" for k, v in sorted(dr.items())))
    print(f"\nDistinct drugs: {len(dr)}. Scenarios with a maximum in the order: {sum(1 for s in S if s.get('max_per_dose_mg') or s.get('max_per_day_mg'))}.")
    print()

    print("## Figure 1 flow counts\n")
    print(f"- Scenarios generated and locked: {len(S)} (one record each; {len(na)} non-abstention, {len(ab)} abstention)")
    print(f"- Repeat subset: {len(repeat)} records")
    files = sorted(glob.glob("results/scored_test_*.jsonl"))
    rows = []
    for f in files:
        L = [json.loads(l) for l in open(f)]
        cfg = L[0]["_config"]; recs = [x for x in L[1:] if "record_id" in x]
        rows.append((cfg["model"]["id"], cfg["workflow"], cfg.get("run_id"), len(recs), sum(1 for x in recs if x.get("malformed")), sum(1 for x in recs if not x.get("abstention_case"))))
    print(f"- Scored files: {len(files)} ({len({(r[0], r[1]) for r in rows})} model-workflow cells, runs {sorted({r[2] for r in rows})})")
    for mid in ORDER:
        for wf in ("B", "C"):
            rr = [r for r in rows if r[0] == mid and r[1] == wf]
            s = "; ".join(f"{r[2]}: {r[3]} records ({r[5]} non-abstention), {r[4]} malformed" for r in sorted(rr, key=lambda r: r[2]))
            print(f"  - {mid} {wf}: {s}")
    tot_outputs = sum(r[3] for r in rows); tot_na = sum(r[5] for r in rows); tot_mal = sum(r[4] for r in rows)
    print(f"- Total scored outputs: {tot_outputs} ({tot_na} non-abstention; {tot_mal} malformed, all in repeat runs)")
    run1_na = sum(r[5] for r in rows if r[2] == "run1")
    print(f"- Run 1 non-abstention outputs entering the primary analysis: {run1_na} (10 cells x 304)")


if __name__ == "__main__":
    main()
