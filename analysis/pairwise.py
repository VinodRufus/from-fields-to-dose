"""Secondary pairwise model contrasts on the primary endpoint (Protocol Section 16).

For each workflow and each pair of models, the difference in complete dose-consistent regimen accuracy
on non-abstention run1 records, paired at the record level, with a clustered bootstrap (resampling
scenarios, 2,000 draws) for the 95 percent interval and a two-sided bootstrap p value. Holm correction
is applied across all contrasts. Malformed outputs count as failures (Section 12).

Usage: python -m analysis.pairwise --scored 'results/scored_test_*_run1.jsonl'
"""
import argparse, glob, itertools, json, random
from collections import defaultdict
from typing import Dict, List, Tuple

KEY = "primary_endpoint"


def load(path: str):
    lines = [json.loads(l) for l in open(path)]
    cfg = lines[0]["_config"]
    rows = {}
    for r in lines[1:]:
        if "record_id" not in r or r.get("abstention_case"):
            continue
        v = r.get(KEY)
        if v is None:
            v = False if r.get("malformed") else None
        if v is None:
            continue
        rows[r["record_id"]] = (r["scenario_id"], 1.0 if v else 0.0)
    return cfg["model"]["id"], cfg["workflow"], rows


def paired_boot(a: Dict[str, Tuple[str, float]], b: Dict[str, Tuple[str, float]], B: int, seed: int):
    ids = sorted(set(a) & set(b))
    by_sc: Dict[str, List[float]] = defaultdict(list)
    for i in ids:
        by_sc[a[i][0]].append(a[i][1] - b[i][1])
    sc = sorted(by_sc)
    if not sc:
        return float("nan"), float("nan"), float("nan"), float("nan"), 0
    def mean_of(sample):
        vals = [x for s in sample for x in by_sc[s]]
        return sum(vals) / len(vals)
    est = mean_of(sc)
    rng = random.Random(seed)
    boots = []
    for _ in range(B):
        boots.append(mean_of([sc[rng.randrange(len(sc))] for _ in sc]))
    boots.sort()
    lo, hi = boots[int(0.025 * B)], boots[min(B - 1, int(0.975 * B))]
    le = sum(1 for x in boots if x <= 0) / B
    ge = sum(1 for x in boots if x >= 0) / B
    p = min(1.0, 2 * min(le, ge))
    return est, lo, hi, p, len(ids)


def holm(items: List[Tuple[str, float]]):
    m = len(items)
    order = sorted(range(m), key=lambda i: items[i][1])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * items[i][1])
        running = max(running, val)
        adj[i] = running
    return [(items[i][0], items[i][1], adj[i]) for i in range(m)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True, help="glob of run1 scored files")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    files = sorted(glob.glob(a.scored))
    data: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for f in files:
        mid, wf, rows = load(f)
        data[wf][mid] = rows
    results = []
    for wf in sorted(data):
        models = sorted(data[wf])
        for m1, m2 in itertools.combinations(models, 2):
            est, lo, hi, p, n = paired_boot(data[wf][m1], data[wf][m2], a.B, a.seed)
            results.append((f"wf={wf} {m1} minus {m2}", est, lo, hi, p, n))
    adjusted = holm([(r[0], r[4]) for r in results])
    print(f"== Secondary pairwise contrasts on {KEY}, paired by record, clustered bootstrap (B={a.B}), Holm-adjusted p ==")
    for (label, est, lo, hi, p, n), (_, _, padj) in zip(results, adjusted):
        flag = "yes" if padj < 0.05 else "no"
        print(f"{label:70s} diff={est:+.3f} [{lo:+.3f},{hi:+.3f}]  n={n}  p={p:.4f}  p_holm={padj:.4f}  significant={flag}")


if __name__ == "__main__":
    main()
