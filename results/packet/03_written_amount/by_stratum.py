"""Stratified results for the heat-map figures (supplementary; exploratory beyond the pre-specified strata).

For each model and workflow, on non-abstention run1 records, the primary endpoint rate and the composite
dose-consequential failure rate within each stratum: complexity level, age band, generation method, each
challenge tag, and drug. Malformed outputs count as failures (Section 12). Strata are overlapping for
challenge tags (a record carries several), so those rows do not sum to the total.

Writes results/by_stratum_run1.csv (long format) and prints two pivots (primary endpoint; composite failure).

Usage: python -m tools.by_stratum --scored 'results/scored_test_*_run1.jsonl'
"""
import argparse, csv, glob, json, os
from collections import defaultdict, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "by_stratum_run1.csv"))
    a = ap.parse_args()
    acc = defaultdict(lambda: {"n": 0, "primary": 0, "dc": 0})
    cols = []
    for f in sorted(glob.glob(a.scored)):
        lines = [json.loads(l) for l in open(f)]
        cfg = lines[0]["_config"]
        split, mid, wf = cfg["split"], cfg["model"]["id"], cfg["workflow"]
        col = (mid, wf)
        if col not in cols:
            cols.append(col)
        drug_of = {}
        for l in open(os.path.join(ROOT, "data", split, "scenarios.jsonl")):
            o = json.loads(l); drug_of[o["scenario_id"]] = o["drug"]
        for r in lines[1:]:
            if "record_id" not in r or r.get("abstention_case"):
                continue
            pe = r.get("primary_endpoint")
            if pe is None and r.get("malformed"):
                pe = False
            dc = r.get("dose_consequential")
            if dc is None and r.get("malformed"):
                dc = True
            strata = [("all", "all records"), ("complexity", f"Level {r.get('complexity')}"), ("age_band", str(r.get("age_band"))),
                      ("generation", "paraphrase" if str(r.get("generation_method", "")).startswith("paraphrase") else "template"),
                      ("drug", drug_of.get(r["scenario_id"], "?"))]
            for c in (r.get("challenges") or []):
                strata.append(("challenge", c))
            for kind, name in strata:
                k = (kind, name, col)
                acc[k]["n"] += 1
                acc[k]["primary"] += 1 if pe else 0
                acc[k]["dc"] += 1 if dc else 0
    cols.sort(key=lambda c: (ORDER.index(c[0]) if c[0] in ORDER else 99, c[1]))
    rows = []
    for (kind, name, (mid, wf)), v in sorted(acc.items()):
        rows.append({"stratum_kind": kind, "stratum": name, "model": mid, "workflow": wf, "n": v["n"],
                     "primary_endpoint_rate": round(v["primary"] / v["n"], 3), "composite_failure_rate": round(v["dc"] / v["n"], 3)})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"wrote {a.out} ({len(rows)} rows)")
    names = OrderedDict()
    for (kind, name, col) in acc:
        names.setdefault((kind, name), None)
    kind_order = {"all": 0, "complexity": 1, "age_band": 2, "generation": 3, "challenge": 4, "drug": 5}
    keys = sorted(names, key=lambda x: (kind_order.get(x[0], 9), x[1]))
    head = "stratum".ljust(34) + "n".rjust(4) + "".join(f"  {m.split('-')[0][:8]}/{w}".rjust(13) for m, w in cols)
    for metric, label in (("primary", "PRIMARY ENDPOINT RATE"), ("dc", "COMPOSITE FAILURE RATE (dose-consequential)")):
        print(f"\n== {label} ==\n{head}")
        for kind, name in keys:
            n = next((acc[(kind, name, c)]["n"] for c in cols if (kind, name, c) in acc), 0)
            cells = []
            for c in cols:
                v = acc.get((kind, name, c))
                cells.append(f"{v[metric] / v['n']:.3f}".rjust(13) if v and v["n"] else "    .".rjust(13))
            print(f"{(kind + ': ' + name)[:34].ljust(34)}{n:4d}" + "".join(cells))


if __name__ == "__main__":
    main()
