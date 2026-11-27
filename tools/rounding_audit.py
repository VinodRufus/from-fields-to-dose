"""Rounding audit of the printed per-dose amount (Study Report 3.2; manuscript 2.2 and Limitations).

For every locked scenario with a printed per-dose amount, recompute the exact per-administration amount with the
committed calculator (generator/calculator.py, a hashed file: weight, basis, mg/kg value, unit, frequency, maxima)
and compare it with the printed amount expected_dose_per_admin_mg, which the generator rounded with
round_documented(). Two deviations are reported: the printed amount relative to the exact product (what the rounding
did), and the exact product relative to the printed amount (what a model that writes the exact product is scored
against at Level 2, where the printed amount is the reference and the tolerance is 1 percent).

Usage: python -m tools.rounding_audit > results/rounding_audit.md
"""
from __future__ import annotations
import collections, hashlib, json, sys
from generator.calculator import to_kg, reconstruct


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    lock = json.load(open("data/test/LOCK.json"))
    if sha256("data/test/scenarios.jsonl") != lock["scenarios_sha256"]:
        sys.exit("STOP: data/test/scenarios.jsonl does not match LOCK.json")
    S = [json.loads(l) for l in open("data/test/scenarios.jsonl")]
    rows = []
    for s in S:
        if s.get("expected_dose_per_admin_mg") is None:
            continue
        kg = to_kg(s["current_weight_value"], s["current_weight_unit"])
        r = reconstruct(kg, s["dose_basis"], s["weight_normalized_dose"], s["dose_unit"], s["frequency_per_day"],
                        s.get("max_per_dose_mg"), s.get("max_per_day_mg"), s.get("concentration_mg_per_ml"))
        exact = r["dose_per_admin_mg"]; printed = s["expected_dose_per_admin_mg"]
        dev_vs_exact = abs(printed - exact) / exact if exact else None
        dev_vs_printed = abs(exact - printed) / printed if printed else None
        rows.append((s["scenario_id"], s["abstention_case"], s["complexity"], s["drug"], s["dose_unit"], printed, exact, dev_vs_exact, dev_vs_printed))
    na = [x for x in rows if not x[1]]
    print("## Rounding audit of the printed per-dose amount (tools/rounding_audit.py)\n")
    print(f"Scenarios with a printed amount: {len(rows)} ({len(na)} non-abstention, {len(rows) - len(na)} abstention cases whose missing element is not needed for the amount).\n")
    for label, subset in (("Non-abstention scenarios (304)", na), ("All scenarios with a printed amount", rows)):
        n1 = sum(1 for x in subset if x[7] > 0.01); n10 = sum(1 for x in subset if x[7] > 0.10)
        m1 = sum(1 for x in subset if x[8] > 0.01); m10 = sum(1 for x in subset if x[8] > 0.10)
        print(f"### {label}\n")
        print(f"- Printed amount more than 1 percent from the exact product: {n1}; more than 10 percent: {n10}.")
        print(f"- Exact product more than 1 percent from the printed amount (fails Level 2 if written): {m1}; more than 10 percent: {m10}.")
        by_unit = collections.Counter(x[4] for x in subset if x[7] > 0.01)
        by_level = collections.Counter(x[2] for x in subset if x[7] > 0.01)
        print(f"- Of those more than 1 percent (printed vs exact): by dose unit {dict(by_unit)}; by complexity {dict(sorted(by_level.items()))}.\n")
    print("### Records where the printed amount is more than 1 percent from the exact product (non-abstention)\n")
    print("| Scenario | Level | Drug | Printed mg | Exact mg | Printed vs exact | Exact vs printed |")
    print("|---|---|---|---|---|---|---|")
    for x in sorted(na, key=lambda x: -x[7]):
        if x[7] > 0.01:
            print(f"| {x[0]} | {x[2]} | {x[3]} | {x[5]} | {x[6]:.6g} | {x[7]:.3f} | {x[8]:.3f} |")


if __name__ == "__main__":
    main()
