"""Plausibility gates (Protocol v1, Section 8.1). Hard gates: a scenario failing any gate
is rejected at generation and the rejection is logged."""
from __future__ import annotations
import csv, math, os
from typing import Dict, List, Optional, Tuple
from .calculator import to_kg

SOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "sources")

# ---------- CDC LMS weight-for-age ----------
def load_lms(path: str) -> List[Dict[str, float]]:
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({"sex": int(float(r["Sex"])), "agemos": float(r["Agemos"]),
                             "L": float(r["L"]), "M": float(r["M"]), "S": float(r["S"])})
            except (KeyError, ValueError):
                continue
    return rows

def lms_z(x: float, L: float, M: float, S: float) -> float:
    if abs(L) < 1e-9: return math.log(x / M) / S
    return ((x / M) ** L - 1.0) / (L * S)

def weight_z(weight_kg: float, age_days: int, sex: str, lms_rows: List[Dict[str, float]]) -> Optional[float]:
    """Nearest-age-month lookup. Returns None if no LMS rows loaded."""
    if not lms_rows: return None
    sex_code = 1 if sex.upper().startswith("M") else 2
    agemos = age_days / 30.4375
    cand = [r for r in lms_rows if r["sex"] == sex_code]
    if not cand: return None
    r = min(cand, key=lambda r: abs(r["agemos"] - agemos))
    return lms_z(weight_kg, r["L"], r["M"], r["S"])

def gate_weight(weight_kg: float, age_days: int, sex: str, lms_rows, z_limit: float = 2.0, tail_ok: bool = False) -> Tuple[bool, str]:
    z = weight_z(weight_kg, age_days, sex, lms_rows)
    if z is None: return (True, "weight_z:skipped(no LMS file)")
    if tail_ok: return (abs(z) <= 4.0, f"weight_z={z:.2f}(tail)")
    return (abs(z) <= z_limit, f"weight_z={z:.2f}")

# ---------- dosing source table ----------
def load_sources(path: str) -> List[Dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def source_for(drug: str, dose_basis: str, sources: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    for r in sources:
        if r["drug"] == drug and r["dose_basis"] == dose_basis:
            return r
    return None

def _f(x: str) -> Optional[float]:
    x = (x or "").strip()
    return float(x) if x else None

def gate_dose(s, sources) -> Tuple[bool, str]:
    src = source_for(s.drug, s.dose_basis, sources)
    if src is None: return (False, "no_source_row")
    lo, hi = _f(src["dose_min"]), _f(src["dose_max"])
    if lo is None or hi is None: return (False, "source_missing_range")
    if not (lo <= s.weight_normalized_dose <= hi): return (False, f"dose_out_of_range[{lo},{hi}]")
    freqs = {int(x) for x in src["frequency_per_day_options"].split("|") if x.strip()}
    if s.frequency_per_day not in freqs: return (False, f"freq_not_allowed{sorted(freqs)}")
    amin, amax = _f(src["age_min_days"]), _f(src["age_max_days"])
    if amin is not None and s.age_days < amin: return (False, "below_age_min")
    if amax is not None and s.age_days > amax: return (False, "above_age_max")
    if src["route"] and src["route"].lower() != s.route.lower(): return (False, "route_mismatch")
    return (True, "dose_ok")

def gate_verified(s, sources, require_verified: bool) -> Tuple[bool, str]:
    src = source_for(s.drug, s.dose_basis, sources)
    if src is None: return (False, "no_source_row")
    v = (src.get("verified", "false").strip().lower() == "true")
    if require_verified and not v: return (False, "source_not_verified")
    return (True, "verified_ok" if v else "unverified_demo")

def gate_timestamps(s) -> Tuple[bool, str]:
    if s.prior_weight_timestamp and s.weight_timestamp and s.prior_weight_timestamp >= s.weight_timestamp:
        return (False, "prior_weight_not_before_current")
    for d in s.distractor_orders:
        if d.status == "discontinued" and s.order_timestamp and d.timestamp > s.order_timestamp:
            return (False, "discontinued_order_after_active")
    return (True, "timestamps_ok")

def run_gates(s, sources, lms_rows, require_verified: bool, tail_ok: bool = False) -> List[Tuple[str, bool, str]]:
    out = []
    ok, msg = gate_verified(s, sources, require_verified); out.append(("verified", ok, msg))
    if not s.abstention_case or "current_weight_value" not in s.missing_fields:
        kg = to_kg(s.current_weight_value, s.current_weight_unit)
        ok, msg = gate_weight(kg, s.age_days, s.sex, lms_rows, tail_ok=tail_ok); out.append(("weight", ok, msg))
    ok, msg = gate_dose(s, sources); out.append(("dose", ok, msg))
    ok, msg = gate_timestamps(s); out.append(("timestamps", ok, msg))
    return out
