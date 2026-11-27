"""H4: dose-consequential errors by automatic class as proportions with clustered-bootstrap intervals (Protocol v1.0
Section 16), plus the manual coding of residual extraction errors (Section 13) and the re-code agreement.

Reads results/scored_test_*_run1.jsonl, results/manual_codes.jsonl and results/manual_codes_recode.jsonl (the two
manual files are in the working repository; the script says so if they are absent). Automatic classes are not
mutually exclusive: one output can carry several, so the shares in a cell can sum to more than 1.

H4 as registered: "Dose-basis confusion (mg/kg/day vs mg/kg/dose) and weight-selection errors will together account
for the largest share of dose-consequential errors." The registered classes for those two terms are dose_basis and
weight_selection (plus extraction:weight_wrong, a wrong weight value). adult_fixed_dose_assumption (a weight-based
order labelled fixed) is a different registered class and is reported separately; the verdict is stated under the
registered definition and the broader reading is shown beside it.

Usage: python -m tools.h4_classes --out results/h4_classes.txt
"""
from __future__ import annotations
import argparse, collections, glob, io, json, os, sys, tempfile
from analysis.analyze import load, by_scenario, cluster_boot_mean

ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]
H4_CLASSES = ("dose_basis", "weight_selection", "extraction:weight_wrong")
OUT = io.StringIO()


def emit(*a):
    print(*a, file=OUT)


def fmt(t):
    return f"{t[0]:.3f} [{t[1]:.3f},{t[2]:.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", nargs="+", default=["results/scored_test_*_run1.jsonl"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    files = sorted(f for p in a.scored for f in glob.glob(p))
    if not files:
        print("STOP: no scored files", file=sys.stderr); sys.exit(1)
    cells = {}
    for f in files:
        cfg, rows = load(f)
        mid, wf = cfg["_config"]["model"]["id"], cfg["_config"]["workflow"]
        na = [r for r in rows if "record_id" in r and not r.get("abstention_case")]
        cells[(mid, wf)] = na

    emit("== H4: dose-consequential errors by automatic class, run 1, non-abstention records ==")
    emit("Share = proportion of a cell's dose-consequential outputs carrying the class; clustered bootstrap over scenarios, 2,000 resamples. Classes are not mutually exclusive.")
    pooled_dq = []
    for mid in ORDER:
        for wf in ("B", "C"):
            na = cells.get((mid, wf))
            if not na:
                continue
            dq = [r for r in na if r.get("dose_consequential")]
            pooled_dq += dq
            emit(f"{mid:24s} wf={wf}  dose-consequential outputs: {len(dq)} of {len(na)}")
            if not dq:
                continue
            counts = collections.Counter(c for r in dq for c in r.get("codes", []))
            for cls, n in counts.most_common():
                flagged = [dict(r, _f=(cls in r.get("codes", []))) for r in dq]
                ci = cluster_boot_mean(by_scenario(flagged, "_f"))
                emit(f"{'':24s}   {cls:32s} {n:4d}  share={fmt(ci)}")
            h4 = [dict(r, _f=any(c in H4_CLASSES for c in r.get("codes", []))) for r in dq]
            broad = [dict(r, _f=any(c in H4_CLASSES + ('adult_fixed_dose_assumption',) for c in r.get("codes", []))) for r in dq]
            emit(f"{'':24s}   H4 classes (dose_basis, weight_selection, extraction:weight_wrong): {sum(r['_f'] for r in h4)} of {len(dq)}  share={fmt(cluster_boot_mean(by_scenario(h4, '_f')))}")
            emit(f"{'':24s}   broader reading adding adult_fixed_dose_assumption:                 {sum(r['_f'] for r in broad)} of {len(dq)}  share={fmt(cluster_boot_mean(by_scenario(broad, '_f')))}")
    emit()
    emit(f"Pooled over all cells: {len(pooled_dq)} dose-consequential outputs.")
    pc = collections.Counter(c for r in pooled_dq for c in r.get("codes", []))
    for cls, n in pc.most_common():
        emit(f"   {cls:32s} {n:4d}  {n / len(pooled_dq):.3f}")
    nh4 = sum(1 for r in pooled_dq if any(c in H4_CLASSES for c in r.get("codes", [])))
    nbroad = sum(1 for r in pooled_dq if any(c in H4_CLASSES + ('adult_fixed_dose_assumption',) for c in r.get("codes", [])))
    emit(f"   H4 classes together: {nh4} of {len(pooled_dq)} ({nh4 / len(pooled_dq):.3f}); broader reading: {nbroad} ({nbroad / len(pooled_dq):.3f})")
    emit()

    emit("== Manual coding of residual extraction errors (Protocol Section 13) ==")
    mc, rc = "results/manual_codes.jsonl", "results/manual_codes_recode.jsonl"
    if not os.path.exists(mc):
        emit(f"{mc} not present in this checkout (it lives in the working repository until release v1.0.3).")
    else:
        rows = [json.loads(l) for l in open(mc)]
        cc = collections.Counter(r["code"] for r in rows)
        emit(f"First pass: {len(rows)} residual errors; codes {dict(sorted(cc.items()))}")
        for code, n in sorted(cc.items()):
            emit(f"   {code}: {n}  share={n / len(rows):.3f}")
        byfile = collections.Counter(r["file"] for r in rows)
        emit(f"By file: {dict(byfile)}")
        if os.path.exists(rc):
            rr = [json.loads(l) for l in open(rc)]
            first = {(r["file"], r["record_id"]): r["code"] for r in rows}
            agree = sum(1 for r in rr if first.get((r["file"], r["record_id"])) == r["recode"])
            emit(f"Re-code: {len(rr)} records; agreement {agree}/{len(rr)} = {agree / len(rr):.3f}; re-code distribution {dict(collections.Counter(r['recode'] for r in rr))}")
            pairs = [(first.get((r["file"], r["record_id"])), r["recode"]) for r in rr]
            cats = sorted({c for p in pairs for c in p})
            po = agree / len(rr)
            pe = sum((sum(1 for p in pairs if p[0] == c) / len(rr)) * (sum(1 for p in pairs if p[1] == c) / len(rr)) for c in cats)
            kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
            emit(f"Cohen's kappa (two passes by the same coder): {kappa:.3f} (p_o={po:.3f}, p_e={pe:.3f}); uninformative when one pass has a single category.")
            dis = [(r["record_id"], first.get((r["file"], r["record_id"])), r["recode"]) for r in rr if first.get((r["file"], r["record_id"])) != r["recode"]]
            for d in dis:
                emit(f"   disagreement: {d[0]}  first={d[1]}  recode={d[2]}")
        else:
            emit(f"{rc} not present.")
    report = OUT.getvalue()
    if a.out:
        d = os.path.dirname(os.path.abspath(a.out)) or "."
        fd, tmp = tempfile.mkstemp(prefix=".h4_", suffix=".tmp", dir=d)
        with os.fdopen(fd, "w") as fh:
            fh.write(report)
        os.replace(tmp, a.out)
        print(f"wrote {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()
