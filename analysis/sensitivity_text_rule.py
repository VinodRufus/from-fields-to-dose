"""Sensitivity analysis: Level 3 under the protocol-text rule versus the locked scorer.
Added 14 November 2026 after external review of the manuscript draft, with all results known. Revised the same day
after review of the script itself: input validation, stopping checks against the stored scored-row flags, mutually
exclusive failure components, and primary-endpoint disagreements reported separately.

Protocol v1.0 Section 12 (text): "A record is dosing-consistent if both recomputed values are within the Level 4
tolerance of the canonical values." The locked scorer (scoring/score.py, hash in LOCK_hashes.txt) takes the worst of
the deviations that are available, so a record with one mg/kg value missing passes Level 3 if the other value is
within tolerance. The two rules differ only on records where exactly one of mg/kg/dose and mg/kg/day is present.

The locked scorer is not touched. This script reads the committed scored run-1 files and, for each model and
workflow:
  - validates the input set (exactly the five registered model identifiers in both workflows, run 1 only, full test
    split, no duplicates, identical scenario sets across B and C for each model; stored flags must be present and boolean);
  - recomputes the locked Level 3 flag from dev_dose and dev_day and STOPS unless it equals the stored
    dosing_consistent, dose_consequential and primary_endpoint on every record (and dose_consequential_sens at the
    sensitivity tolerance);
  - reports the primary endpoint and dose-consequential rate under both rules with the same clustered bootstrap as
    analysis/analyze.py (2,000 resamples over scenarios, seeds 1 and 2);
  - reports failure components that are mutually exclusive: both values present and off tolerance; exactly one value
    missing; both missing; malformed output;
  - reports how many records change Level 3 and how many change the primary endpoint;
  - reports H3 under both protocol wordings under the text rule, C minus B, paired by scenario.

Usage: python -m analysis.sensitivity_text_rule --scored 'results/scored_test_*_run1.jsonl' --out results/analysis_sensitivity_text_rule.txt
The report is buffered and written to a temporary file that is renamed to --out only after every check and
computation has succeeded; on any failure a STOP line goes to stderr, the exit status is non-zero and --out is not
touched. Without --out the report goes to stdout at the end.
"""
from __future__ import annotations
import argparse, glob, hashlib, io, os, sys, tempfile
from collections import defaultdict
from analysis.analyze import load, by_scenario, cluster_boot_mean, paired_cluster_boot

ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]
EXPECTED_RECORDS = 361
EXPECTED_NON_ABSTENTION = 304


OUT = io.StringIO()


def emit(*parts: object) -> None:
    print(*parts, file=OUT)


def fail(msg: str) -> None:
    print(f"STOP: {msg}", file=sys.stderr)
    sys.exit(1)


def text_rule(r: dict, tol: float) -> bool:
    """Protocol-text Level 3: both exposures present and both within tol. Malformed outputs fail (Section 12)."""
    if r.get("malformed"):
        return False
    dd, dy = r.get("dev_dose"), r.get("dev_day")
    return dd is not None and dy is not None and dd <= tol and dy <= tol


def locked_rule(r: dict, tol: float) -> bool:
    """Locked scorer Level 3 as committed: worst available deviation within tol."""
    if r.get("malformed"):
        return False
    devs = [d for d in (r.get("dev_dose"), r.get("dev_day")) if d is not None]
    return bool(devs) and max(devs) <= tol


def component(r: dict, tol: float) -> str:
    """Mutually exclusive description of a record's exposure values."""
    if r.get("malformed"):
        return "malformed"
    dd, dy = r.get("dev_dose"), r.get("dev_day")
    if dd is None and dy is None:
        return "both_missing"
    if (dd is None) != (dy is None):
        present = dd if dd is not None else dy
        return "one_missing_other_within" if present <= tol else "one_missing_other_off"
    return "both_present_within" if (dd <= tol and dy <= tol) else "both_present_off"


def annotate(rows, tol):
    out = []
    for r in rows:
        r = dict(r)
        lk, tx = locked_rule(r, tol), text_rule(r, tol)
        r["dc_locked"], r["dc_text"] = lk, tx
        r["dq_locked"], r["dq_text"] = (not lk), (not tx)
        r["pe_locked"] = bool(r.get("complete_regimen")) and lk
        r["pe_text"] = bool(r.get("complete_regimen")) and tx
        r["component"] = component(r, tol)
        out.append(r)
    return out


def stored_flag(r: dict, key: str, label: str):
    """A stored flag must be present and boolean; a malformed row stores no primary_endpoint and is False by Section 12."""
    if key not in r:
        if r.get("malformed") and key in ("primary_endpoint", "dose_consequential_sens"):
            return key == "dose_consequential_sens"
        fail(f"{label}: record {r.get('record_id')} has no stored field {key}")
    v = r[key]
    if not isinstance(v, bool):
        fail(f"{label}: record {r.get('record_id')} stored field {key} is {v!r}, not boolean")
    return v


def stopping_checks(na, tol, tol_sens, label):
    """Recomputed locked flags must equal the stored scorer output on every record."""
    bad = []
    for r in na:
        lk = locked_rule(r, tol)
        stored_dc = stored_flag(r, "dosing_consistent", label)
        stored_dq = stored_flag(r, "dose_consequential", label)
        stored_pe = stored_flag(r, "primary_endpoint", label)
        if lk != stored_dc:
            bad.append((r["record_id"], "dosing_consistent", lk, stored_dc))
        if (not lk) != stored_dq:
            bad.append((r["record_id"], "dose_consequential", not lk, stored_dq))
        if (bool(r.get("complete_regimen")) and lk) != stored_pe:
            bad.append((r["record_id"], "primary_endpoint", bool(r.get("complete_regimen")) and lk, stored_pe))
        lk_s = locked_rule(r, tol_sens)
        stored_dqs = stored_flag(r, "dose_consequential_sens", label)
        if (not lk_s) != stored_dqs:
            bad.append((r["record_id"], "dose_consequential_sens", not lk_s, stored_dqs))
    if bad:
        for b in bad[:20]:
            emit(f"  {label}: record {b[0]} field {b[1]} recomputed={b[2]} stored={b[3]}")
        fail(f"{label}: {len(bad)} recomputed locked flags differ from the stored scored rows")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(t):
    return f"{t[0]:.3f} [{t[1]:.3f},{t[2]:.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", nargs="+", required=True)
    ap.add_argument("--tol", type=float, default=0.10)
    ap.add_argument("--tol-sens", type=float, default=0.20)
    ap.add_argument("--out", default=None, help="report path; written atomically on success")
    a = ap.parse_args()

    # Input validation
    files = []
    for pat in a.scored:
        m = sorted(glob.glob(pat))
        if not m:
            fail(f"pattern matched no files: {pat}")
        files.extend(m)
    runs, headers = {}, {}
    emit("== Inputs ==")
    for f in files:
        cfg, rows = load(f)
        c = cfg["_config"]
        mid, wf, run_id, split, subset = c["model"]["id"], c["workflow"], c.get("run_id"), c.get("split"), c.get("subset")
        if run_id != "run1":
            fail(f"{f}: run_id is {run_id}, expected run1")
        if split != "test":
            fail(f"{f}: split is {split}, expected test")
        if subset:
            fail(f"{f}: file is a subset run")
        if (mid, wf) in runs:
            fail(f"{f}: duplicate model/workflow {mid} {wf} (already loaded {headers[(mid, wf)]['file']})")
        if abs(cfg.get("tol", a.tol) - a.tol) > 1e-12 or abs(cfg.get("tol_sens", a.tol_sens) - a.tol_sens) > 1e-12:
            fail(f"{f}: file tolerances {cfg.get('tol')}/{cfg.get('tol_sens')} differ from {a.tol}/{a.tol_sens}")
        recs = [r for r in rows if "record_id" in r]
        if len(recs) != EXPECTED_RECORDS:
            fail(f"{f}: {len(recs)} records, expected {EXPECTED_RECORDS}")
        na = [r for r in recs if not r.get("abstention_case")]
        if len(na) != EXPECTED_NON_ABSTENTION:
            fail(f"{f}: {len(na)} non-abstention records, expected {EXPECTED_NON_ABSTENTION}")
        if len({r["record_id"] for r in na}) != len(na):
            fail(f"{f}: duplicate record_id")
        runs[(mid, wf)] = na
        headers[(mid, wf)] = {"file": f, "sha256": sha256(f), "started": c.get("started")}
        emit(f"{os.path.basename(f)}  model={mid} wf={wf} run={run_id} records={len(recs)} non_abstention={len(na)} sha256={headers[(mid, wf)]['sha256']}")
    expected_keys = {(m, wf) for m in ORDER for wf in ("B", "C")}
    if set(runs) != expected_keys:
        fail(f"input set is not the ten registered model/workflow files: missing {sorted(expected_keys - set(runs))}, unexpected {sorted(set(runs) - expected_keys)}")
    models = list(ORDER)
    for mid in models:
        sb = {r["scenario_id"] for r in runs[(mid, "B")]}
        sc = {r["scenario_id"] for r in runs[(mid, "C")]}
        if sb != sc:
            fail(f"{mid}: scenario sets differ between B and C ({len(sb ^ sc)} differences)")
    emit(f"Validated {len(runs)} files for {len(models)} models.")
    emit()

    # Stopping checks against the stored scorer output
    emit("== Stopping checks: recomputed locked flags against stored scored rows ==")
    for (mid, wf), na in sorted(runs.items()):
        stopping_checks(na, a.tol, a.tol_sens, f"{mid} wf={wf}")
        emit(f"{mid:24s} wf={wf}  {len(na)} records: dosing_consistent, dose_consequential, primary_endpoint at {a.tol:.2f} and dose_consequential_sens at {a.tol_sens:.2f} all match")
    emit()

    for tol, label in ((a.tol, "primary tolerance"), (a.tol_sens, "sensitivity tolerance")):
        emit(f"== Level 3 rule sensitivity at {label} {tol:.2f}: locked scorer (worst available deviation) versus protocol text (both values) ==")
        for mid in models:
            for wf in ("B", "C"):
                na = annotate(runs[(mid, wf)], tol)
                n = len(na)
                comps = defaultdict(int)
                for r in na:
                    comps[r["component"]] += 1
                l3_change = sum(1 for r in na if r["dc_locked"] != r["dc_text"])
                pe_change = sum(1 for r in na if r["pe_locked"] != r["pe_text"])
                pe_l, pe_t = cluster_boot_mean(by_scenario(na, "pe_locked")), cluster_boot_mean(by_scenario(na, "pe_text"))
                dq_l, dq_t = cluster_boot_mean(by_scenario(na, "dq_locked")), cluster_boot_mean(by_scenario(na, "dq_text"))
                emit(f"{mid:24s} wf={wf} n={n}")
                emit(f"{'':24s}   primary endpoint   locked={fmt(pe_l)} ({sum(r['pe_locked'] for r in na)}/{n})   text={fmt(pe_t)} ({sum(r['pe_text'] for r in na)}/{n})")
                emit(f"{'':24s}   dose-consequential locked={fmt(dq_l)} ({sum(r['dq_locked'] for r in na)}/{n})   text={fmt(dq_t)} ({sum(r['dq_text'] for r in na)}/{n})")
                emit(f"{'':24s}   exposure components (mutually exclusive): both_present_within={comps['both_present_within']} both_present_off={comps['both_present_off']} "
                      f"one_missing_other_within={comps['one_missing_other_within']} one_missing_other_off={comps['one_missing_other_off']} both_missing={comps['both_missing']} malformed={comps['malformed']}")
                emit(f"{'':24s}   composite failures: locked = both_present_off + one_missing_other_off + both_missing + malformed = {comps['both_present_off'] + comps['one_missing_other_off'] + comps['both_missing'] + comps['malformed']}; "
                      f"text = locked + one_missing_other_within = {comps['both_present_off'] + comps['one_missing_other_off'] + comps['both_missing'] + comps['malformed'] + comps['one_missing_other_within']}")
                emit(f"{'':24s}   records changing Level 3={l3_change}; records changing primary endpoint={pe_change}")
                if l3_change:
                    comp = defaultdict(int)
                    for r in na:
                        if r["dc_locked"] != r["dc_text"]:
                            comp[r["complexity"]] += 1
                    emit(f"{'':24s}   Level 3 changes by note complexity tier={dict(sorted(comp.items()))}")
                    for key, name in (("dq_locked", "locked"), ("dq_text", "text")):
                        bc = {c: round(cluster_boot_mean(by_scenario([r for r in na if r["complexity"] == c], key), B=200)[0], 3) for c in (1, 2, 3)}
                        emit(f"{'':24s}   dose-consequential by complexity tier ({name}, H2)={bc}")
        emit()
        emit(f"== H3 under the protocol-text rule at tolerance {tol:.2f}: Workflow C minus B, paired by scenario, clustered bootstrap ==")
        emit("Section 1 wording: dose-consequential error rate (negative favours hybrid; supported if upper bound < 0).")
        emit("Section 16 wording: primary endpoint (positive favours hybrid; supported if lower bound > 0).")
        s1 = s16 = 0
        for mid in models:
            C, B = annotate(runs[(mid, "C")], tol), annotate(runs[(mid, "B")], tol)
            e1 = paired_cluster_boot(by_scenario(C, "dq_text"), by_scenario(B, "dq_text"))
            e16 = paired_cluster_boot(by_scenario(C, "pe_text"), by_scenario(B, "pe_text"))
            s1 += e1[2] < 0
            s16 += e16[1] > 0
            emit(f"{mid:24s} S1 diff={e1[0]:+.3f} [{e1[1]:+.3f},{e1[2]:+.3f}] supported={'yes' if e1[2] < 0 else 'no'}   S16 diff={e16[0]:+.3f} [{e16[1]:+.3f},{e16[2]:+.3f}] supported={'yes' if e16[1] > 0 else 'no'}")
        emit(f"Majority rule: Section 1 criterion met for {s1} of {len(models)} models; Section 16 criterion met for {s16} of {len(models)} models.")
        emit()

    report = OUT.getvalue()
    if a.out:
        d = os.path.dirname(os.path.abspath(a.out)) or "."
        fd, tmp = tempfile.mkstemp(prefix=".sensitivity_text_rule_", suffix=".tmp", dir=d)
        with os.fdopen(fd, "w") as f:
            f.write(report)
        os.replace(tmp, a.out)
        print(f"wrote {a.out} ({len(report.splitlines())} lines)", file=sys.stderr)
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()