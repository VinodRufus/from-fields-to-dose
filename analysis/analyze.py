"""Clustered bootstrap by scenario, primary comparison C minus B, Holm correction (Protocol Section 16).
Usage: python -m analysis.analyze --scored results/scored_*.jsonl"""
from __future__ import annotations
import argparse, json, random, glob, os
from collections import defaultdict
from typing import Dict, List, Tuple

def load(path: str):
    lines = [json.loads(l) for l in open(path)]
    return lines[0], lines[1:]

def by_scenario(rows: List[Dict], key: str) -> Dict[str, List[float]]:
    d = defaultdict(list)
    for r in rows:
        v = r.get(key)
        if v is None: continue
        d[r["scenario_id"]].append(1.0 if v is True else 0.0 if v is False else float(v))
    return d

def cluster_boot_mean(d: Dict[str, List[float]], B: int = 2000, seed: int = 1) -> Tuple[float, float, float]:
    rng = random.Random(seed); ids = list(d.keys())
    if not ids: return (float("nan"),) * 3
    def mean_of(sample):
        vals = [x for i in sample for x in d[i]]
        return sum(vals) / len(vals) if vals else float("nan")
    est = mean_of(ids)
    boots = sorted(mean_of([rng.choice(ids) for _ in ids]) for _ in range(B))
    return est, boots[int(0.025 * B)], boots[int(0.975 * B) - 1]

def paired_cluster_boot(dC: Dict[str, List[float]], dB: Dict[str, List[float]], B: int = 2000, seed: int = 2):
    rng = random.Random(seed); ids = [i for i in dC if i in dB]
    def diff(sample):
        c = [x for i in sample for x in dC[i]]; b = [x for i in sample for x in dB[i]]
        return (sum(c) / len(c)) - (sum(b) / len(b)) if c and b else float("nan")
    est = diff(ids); boots = sorted(diff([rng.choice(ids) for _ in ids]) for _ in range(B))
    return est, boots[int(0.025 * B)], boots[int(0.975 * B) - 1]

def holm(pvals: List[Tuple[str, float]]) -> List[Tuple[str, float, float]]:
    m = len(pvals); srt = sorted(pvals, key=lambda x: x[1]); out = []; running = 0.0
    for i, (name, p) in enumerate(srt):
        adj = min(1.0, (m - i) * p); running = max(running, adj); out.append((name, p, running))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--scored", nargs="+", required=True); a = ap.parse_args()
    files = [f for pat in a.scored for f in glob.glob(pat)]
    runs = {}
    for f in files:
        cfg, rows = load(f)
        if cfg["_config"].get("subset"): continue   # repeat-subset runs are analyzed by analysis.stability
        rows = [r for r in rows if "record_id" in r]
        runs[(cfg["_config"]["model"]["id"], cfg["_config"]["workflow"])] = rows
    print("\n== Primary endpoint (complete dose-consistent regimen accuracy), non-abstention records ==")
    for (mid, wf), rows in sorted(runs.items()):
        na = [r for r in rows if not r["abstention_case"]]
        est, lo, hi = cluster_boot_mean(by_scenario(na, "primary_endpoint"))
        fa, flo, fhi = cluster_boot_mean(by_scenario(na, "field_acc"))
        cr, clo, chi = cluster_boot_mean(by_scenario(na, "complete_regimen"))
        dc, dlo, dhi = cluster_boot_mean(by_scenario(na, "dose_consequential"))
        print(f"{mid:12s} wf={wf}  primary={est:.3f} [{lo:.3f},{hi:.3f}]  field_acc={fa:.3f}  complete_regimen={cr:.3f} [{clo:.3f},{chi:.3f}]  dose_consequential={dc:.3f} [{dlo:.3f},{dhi:.3f}]  (H1 gap={fa-cr:+.3f})")
        ab = [r for r in rows if r["abstention_case"]]
        if ab:
            aa, alo, ahi = cluster_boot_mean(by_scenario(ab, "appropriate_abstention"))
            hl, _, _ = cluster_boot_mean(by_scenario(ab, "hallucinated"))
            print(f"{'':12s}        abstention: appropriate={aa:.3f} [{alo:.3f},{ahi:.3f}]  hallucinated={hl:.3f}  n={len(ab)}")
        print(f"{'':12s}        by complexity:", {c: round(cluster_boot_mean(by_scenario([r for r in na if r['complexity']==c], 'dose_consequential'), B=200)[0], 3) for c in (1,2,3)})
        print(f"{'':12s}        by band:", {b: round(cluster_boot_mean(by_scenario([r for r in na if r['age_band']==b], 'dose_consequential'), B=200)[0], 3) for b in sorted({r['age_band'] for r in na})})
        gms = sorted({(r.get('generation_method') or 'template').split(':')[0] for r in na})
        if len(gms) > 1:
            print(f"{'':12s}        by generation method (exploratory):", {g: round(cluster_boot_mean(by_scenario([r for r in na if (r.get('generation_method') or 'template').startswith(g)], 'primary_endpoint'), B=200)[0], 3) for g in gms})
        print(f"{'':12s}        malformed outputs: {sum(1 for r in rows if r.get('malformed'))}/{len(rows)}")
        codes = defaultdict(int)
        for r in na:
            for c in r.get("codes", []): codes[c] += 1
        print(f"{'':12s}        top error codes:", dict(sorted(codes.items(), key=lambda x: -x[1])[:8]))
    print("\n== Primary comparison H3: Workflow C minus B on dose-consequential error rate (negative favors hybrid) ==")
    for mid in {k[0] for k in runs}:
        if (mid, "C") in runs and (mid, "B") in runs:
            dC = by_scenario([r for r in runs[(mid, "C")] if not r["abstention_case"]], "dose_consequential")
            dB = by_scenario([r for r in runs[(mid, "B")] if not r["abstention_case"]], "dose_consequential")
            est, lo, hi = paired_cluster_boot(dC, dB)
            print(f"{mid:12s} diff={est:+.3f} [{lo:+.3f},{hi:+.3f}]  supported={'yes' if hi < 0 else 'no'}")

if __name__ == "__main__": main()
