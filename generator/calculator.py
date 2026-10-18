"""Deterministic dose reconstruction (Protocol v1, Section 3.2 and Levels 3-4).
Single audited implementation used for BOTH ground truth and model-output recompute."""
from __future__ import annotations
from typing import Optional, Dict

LB_PER_KG = 2.20462262185

def to_kg(value: float, unit: str) -> float:
    if unit == "kg": return float(value)
    if unit == "lb": return float(value) / LB_PER_KG
    raise ValueError(f"unknown weight unit {unit}")

def to_mg(value: float, unit: str) -> float:
    if unit == "mg": return float(value)
    if unit == "mcg": return float(value) / 1000.0
    if unit == "g": return float(value) * 1000.0
    raise ValueError(f"unknown dose unit {unit}")

def round_documented(mg: float, dose_unit: str) -> float:
    """How an order would be written: mcg drugs to whole mcg (0.5 below 10 mcg);
    mg drugs: 2 decimals below 1 mg, 1 decimal below 10 mg, whole mg above. Returns mg."""
    if dose_unit == "mcg":
        mcg = mg * 1000.0
        mcg = round(mcg * 2) / 2 if mcg < 10 else round(mcg)
        return mcg / 1000.0
    if mg < 1: return round(mg, 2)
    if mg < 10: return round(mg, 1)
    return float(round(mg))

def reconstruct(weight_kg: float, dose_basis: str, weight_normalized_dose: float,
                dose_unit: str, frequency_per_day: int,
                max_per_dose_mg: Optional[float] = None,
                max_per_day_mg: Optional[float] = None,
                concentration_mg_per_ml: Optional[float] = None,
                fixed_dose_per_admin: Optional[float] = None) -> Dict[str, Optional[float]]:
    """Returns dose_per_admin_mg, daily_mg, mg_per_kg_per_dose, mg_per_kg_per_day, volume_ml.
    Caps: per-dose cap on the administered dose, per-day cap on the daily total."""
    if weight_kg is None or weight_kg <= 0:
        raise ValueError("weight_kg required and > 0")
    if frequency_per_day is None or frequency_per_day <= 0:
        raise ValueError("frequency_per_day required and > 0")
    if dose_basis == "fixed":
        if fixed_dose_per_admin is None: raise ValueError("fixed basis needs fixed_dose_per_admin")
        per_admin = to_mg(fixed_dose_per_admin, dose_unit)
    else:
        if weight_normalized_dose is None: raise ValueError("weight_normalized_dose required")
        wnd_mg = to_mg(weight_normalized_dose, dose_unit)
        if dose_basis.endswith("/dose"):
            per_admin = wnd_mg * weight_kg
        elif dose_basis.endswith("/day"):
            per_admin = (wnd_mg * weight_kg) / frequency_per_day
        else:
            raise ValueError(f"unknown dose_basis {dose_basis}")
    if max_per_dose_mg is not None:
        per_admin = min(per_admin, float(max_per_dose_mg))
    daily = per_admin * frequency_per_day
    if max_per_day_mg is not None and daily > float(max_per_day_mg):
        daily = float(max_per_day_mg)
        per_admin = daily / frequency_per_day
    vol = (per_admin / concentration_mg_per_ml) if concentration_mg_per_ml else None
    return {
        "dose_per_admin_mg": round(per_admin, 6),
        "daily_mg": round(daily, 6),
        "mg_per_kg_per_dose": round(per_admin / weight_kg, 6),
        "mg_per_kg_per_day": round(daily / weight_kg, 6),
        "volume_ml": round(vol, 6) if vol is not None else None,
    }

def relative_deviation(observed: Optional[float], expected: Optional[float]) -> Optional[float]:
    if observed is None or expected is None or expected == 0: return None
    return abs(observed - expected) / abs(expected)

def expected_exposure(s) -> None:
    """Fill expected_* on a CanonicalScenario. The documented per-dose figure is the exact value
    rounded the way an order is written; exposure values stay exact (known by construction)."""
    blocked = {"current_weight_value", "frequency_per_day", "weight_normalized_dose"}
    if s.abstention_case and (set(s.missing_fields) & blocked or set(s.conflict_fields) & blocked):
        s.expected_dose_per_admin_mg = None; s.expected_mg_per_kg_per_dose = None
        s.expected_mg_per_kg_per_day = None; s.expected_volume_ml = None
        return
    kg = to_kg(s.current_weight_value, s.current_weight_unit)
    r = reconstruct(kg, s.dose_basis, s.weight_normalized_dose, s.dose_unit, s.frequency_per_day,
                    s.max_per_dose_mg, s.max_per_day_mg, s.concentration_mg_per_ml)
    s.expected_dose_per_admin_mg = round_documented(r["dose_per_admin_mg"], s.dose_unit)
    s.expected_mg_per_kg_per_dose = r["mg_per_kg_per_dose"]
    s.expected_mg_per_kg_per_day = r["mg_per_kg_per_day"]
    s.expected_volume_ml = (round(s.expected_dose_per_admin_mg / s.concentration_mg_per_ml, 2)
                            if s.concentration_mg_per_ml else None)
