from generator.gates import lms_z, gate_dose, gate_verified
from generator.schema import CanonicalScenario

def test_lms_z_formula():
    # L=1 reduces to (x/M - 1)/S
    assert abs(lms_z(11.0, 1.0, 10.0, 0.1) - 1.0) < 1e-9
    # L=0 log form
    import math
    assert abs(lms_z(10.0, 0.0, 10.0, 0.1)) < 1e-9

def scen(**o):
    d = dict(scenario_id="t", drug="DEMO_DRUG_A", indication="i", age_days=1000, age_band="toddler", sex="M",
             current_weight_value=12, current_weight_unit="kg", weight_timestamp="2026-03-10", dose_basis="mg/kg/dose",
             weight_normalized_dose=12, dose_unit="mg", frequency_per_day=3, frequency_text="", route="oral")
    d.update(o); return CanonicalScenario(**d)

SRC = [{"drug": "DEMO_DRUG_A", "dose_basis": "mg/kg/dose", "dose_min": "10", "dose_max": "15", "frequency_per_day_options": "2|3",
        "age_min_days": "28", "age_max_days": "6574", "route": "oral", "verified": "false"}]

def test_gate_dose_ok_and_fail():
    assert gate_dose(scen(), SRC)[0]
    assert not gate_dose(scen(weight_normalized_dose=30), SRC)[0]
    assert not gate_dose(scen(frequency_per_day=6), SRC)[0]
    assert not gate_dose(scen(age_days=5), SRC)[0]

def test_test_set_requires_verified():
    assert not gate_verified(scen(), SRC, require_verified=True)[0]
    assert gate_verified(scen(), SRC, require_verified=False)[0]
