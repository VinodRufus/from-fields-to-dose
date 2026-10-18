"""Author-written note templates for complexity Levels 1-3 (Protocol Section 7). Deterministic."""
from __future__ import annotations
import random
from .calculator import to_kg

FREQ_TEXT = {1: ["once daily", "daily", "q24h"], 2: ["BID", "twice daily", "q12h"],
             3: ["TID", "three times daily", "q8h"], 4: ["QID", "four times daily", "q6h"], 6: ["q4h", "every 4 hours"], 8: ["q3h", "every 3 hours"]}
ROUTE_TEXT = {"oral": ["PO", "by mouth", "oral"], "IV": ["IV", "intravenous"], "IM": ["IM"]}

def age_text(days: int) -> str:
    if days < 28: return f"{days}-day-old"
    if days < 730: return f"{max(1, days // 30)}-month-old"
    return f"{days // 365}-year-old"

def fmt_dose(mg: float, unit: str) -> str:
    return f"{mg*1000:g} mcg" if unit == "mcg" else f"{mg:g} mg"

def _wt(v: float, u: str) -> str:
    return f"{v:g} {u}"

def dose_line(s, rng: random.Random, show_per_dose: bool = True, show_volume: bool = False) -> str:
    unit = s.dose_unit
    per_kg = f"{s.weight_normalized_dose:g} {unit}/kg/{'dose' if s.dose_basis.endswith('/dose') else 'day'}"
    freq = rng.choice(FREQ_TEXT[s.frequency_per_day])
    route = rng.choice(ROUTE_TEXT.get(s.route, [s.route]))
    if s.dose_basis.endswith("/day"):
        line = f"{s.drug} {per_kg} {route} {freq}" if s.frequency_per_day == 1 else f"{s.drug} {per_kg} {route} divided {freq}"
    else:
        line = f"{s.drug} {per_kg} {route} {freq}"
    if show_per_dose and s.expected_dose_per_admin_mg is not None:
        line += f" ({fmt_dose(s.expected_dose_per_admin_mg, unit)} per dose"
        if show_volume and s.expected_volume_ml:
            line += f" = {s.expected_volume_ml:g} mL"
        line += ")"
    if s.concentration_mg_per_ml and s.formulation:
        line += f"; {s.formulation} {s.concentration_mg_per_ml:g} mg/mL"
    if s.max_per_day_mg: line += f"; not to exceed {s.max_per_day_mg:g} mg/day"
    if s.max_per_dose_mg: line += f"; max {fmt_dose(s.max_per_dose_mg, unit)}/dose"
    return line

def _no_freq_line(s) -> str:
    return f"{s.drug} {s.weight_normalized_dose:g} {s.dose_unit}/kg/{'dose' if s.dose_basis.endswith('/dose') else 'day'} {s.route}, interval to be confirmed"

def level1(s, rng: random.Random) -> str:
    kg_line = "" if "current_weight_value" in s.missing_fields else f"Weight: {_wt(s.current_weight_value, s.current_weight_unit)} ({s.weight_timestamp}).\n"
    dose = dose_line(s, rng) if "frequency_per_day" not in s.missing_fields else _no_freq_line(s)
    return (f"Patient: {age_text(s.age_days)} {'male' if s.sex=='M' else 'female'}.\n"
            f"{kg_line}"
            f"Medication order ({s.order_timestamp}): {dose}.\n")

def level2(s, rng: random.Random) -> str:
    vitals = f"Vitals: T 37.{rng.randint(0,9)} C, HR {rng.randint(80,150)}, RR {rng.randint(18,40)}, SpO2 {rng.randint(95,100)}%."
    kg_line = "" if "current_weight_value" in s.missing_fields else f" Wt {_wt(s.current_weight_value, s.current_weight_unit)} obtained {s.weight_timestamp}."
    other = "".join(f" Also on {d.drug} {d.dose_text}." for d in s.distractor_orders if d.status == "active")
    dose = dose_line(s, rng, show_volume=bool(s.concentration_mg_per_ml)) if "frequency_per_day" not in s.missing_fields else _no_freq_line(s)
    return (f"HPI: {age_text(s.age_days)} {'boy' if s.sex=='M' else 'girl'} presenting for {s.indication}. {vitals}{kg_line}\n"
            f"Assessment/Plan: {s.indication}. Start {dose}.{other} Return precautions reviewed. Room {rng.randint(3,42)}.\n")

def level3(s, rng: random.Random) -> str:
    parts = [f"Admission note. {age_text(s.age_days)} {'male' if s.sex=='M' else 'female'} with {s.indication}."]
    if s.birth_weight_kg: parts.append(f"Birth weight {s.birth_weight_kg:g} kg.")
    if s.prior_weight_value is not None:
        parts.append(f"Weight at prior visit ({s.prior_weight_timestamp}): {_wt(s.prior_weight_value, s.prior_weight_unit)}.")
    if "current_weight_value" not in s.missing_fields:
        parts.append(f"Today's weight ({s.weight_timestamp}): {_wt(s.current_weight_value, s.current_weight_unit)}.")
    for d in s.distractor_orders:
        if d.status == "discontinued": parts.append(f"Medications: {d.drug} {d.dose_text} was discontinued on {d.timestamp}.")
        elif d.status == "historical": parts.append(f"Previously received {d.drug} {d.dose_text} ({d.timestamp}).")
        else: parts.append(f"Continues {d.drug} {d.dose_text}.")
    if "frequency_per_day" in s.missing_fields:
        parts.append(f"Plan: {_no_freq_line(s)}.")
    else:
        show_per_dose = "derive_per_dose" not in s.challenges
        parts.append(f"Plan ({s.order_timestamp}): {dose_line(s, rng, show_per_dose=show_per_dose, show_volume=show_per_dose and bool(s.concentration_mg_per_ml))}.")
    if "current_weight_value" in s.conflict_fields:
        parts.append(f"Nursing intake note: weight recorded as {_wt(round(s.current_weight_value*1.15,1), s.current_weight_unit)}; discrepancy not yet reconciled.")
    parts.append(f"Labs pending. Bed {rng.randint(1,30)}.")
    return " ".join(parts) + "\n"

def render(s, rng: random.Random) -> str:
    return {1: level1, 2: level2, 3: level3}[s.complexity](s, rng)
