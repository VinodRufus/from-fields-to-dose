"""Canonical regimen schema (Protocol v1, Section 3.1). Stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import json

DOSE_BASES = ("mg/kg/dose", "mg/kg/day", "mcg/kg/dose", "mcg/kg/day", "fixed")
ORDER_STATUS = ("active", "discontinued", "historical")
COMPLEXITY = (1, 2, 3)

@dataclass
class DistractorOrder:
    drug: str
    dose_text: str            # as it will appear in the note
    status: str               # active | discontinued | historical
    timestamp: str

@dataclass
class CanonicalScenario:
    scenario_id: str
    drug: str
    indication: str
    age_days: int
    age_band: str
    sex: str                          # "M" | "F"
    current_weight_value: float       # as documented
    current_weight_unit: str          # "kg" | "lb"
    weight_timestamp: str
    dose_basis: str                   # see DOSE_BASES
    weight_normalized_dose: float     # in the unit of dose_basis (mg or mcg per kg)
    dose_unit: str                    # "mg" | "mcg"
    frequency_per_day: int
    frequency_text: str               # e.g. "q8h", "TID"
    route: str
    order_status: str = "active"
    order_timestamp: str = ""
    formulation: Optional[str] = None
    concentration_mg_per_ml: Optional[float] = None
    max_per_dose_mg: Optional[float] = None
    max_per_day_mg: Optional[float] = None
    prior_weight_value: Optional[float] = None
    prior_weight_unit: Optional[str] = None
    prior_weight_timestamp: Optional[str] = None
    birth_weight_kg: Optional[float] = None
    distractor_orders: List[DistractorOrder] = field(default_factory=list)
    abstention_case: bool = False
    missing_fields: List[str] = field(default_factory=list)
    conflict_fields: List[str] = field(default_factory=list)
    complexity: int = 1
    challenges: List[str] = field(default_factory=list)
    generation_method: str = "template"
    generator_model: Optional[str] = None
    # computed by calculator.expected_exposure()
    expected_dose_per_admin_mg: Optional[float] = None
    expected_mg_per_kg_per_dose: Optional[float] = None
    expected_mg_per_kg_per_day: Optional[float] = None
    expected_volume_ml: Optional[float] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CanonicalScenario":
        d = dict(d)
        d["distractor_orders"] = [DistractorOrder(**x) for x in d.get("distractor_orders", [])]
        return CanonicalScenario(**d)

# Required fields a model must return per record (Protocol Section 12, Level 2).
REQUIRED_FIELDS = [
    "drug", "current_weight_kg", "dose_basis", "weight_normalized_dose",
    "dose_unit", "dose_per_admin_mg", "frequency_per_day", "route",
]
OPTIONAL_FIELDS = ["concentration_mg_per_ml", "volume_ml", "max_per_dose_mg", "max_per_day_mg"]

def validate(s: CanonicalScenario) -> List[str]:
    errs = []
    if s.dose_basis not in DOSE_BASES: errs.append("dose_basis")
    if s.order_status not in ORDER_STATUS: errs.append("order_status")
    if s.complexity not in COMPLEXITY: errs.append("complexity")
    if s.current_weight_unit not in ("kg", "lb"): errs.append("current_weight_unit")
    if s.dose_unit not in ("mg", "mcg"): errs.append("dose_unit")
    if s.frequency_per_day <= 0: errs.append("frequency_per_day")
    if not s.abstention_case and s.current_weight_value <= 0: errs.append("current_weight_value")
    return errs
