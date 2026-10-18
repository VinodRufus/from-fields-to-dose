import json
from scoring.score import score_record, truth_fields
from generator.schema import CanonicalScenario
from generator.calculator import expected_exposure
from dataclasses import asdict

def base():
    s = CanonicalScenario(scenario_id="t", drug="X", indication="i", age_days=1000, age_band="toddler", sex="M",
        current_weight_value=20, current_weight_unit="kg", weight_timestamp="2026-03-10", dose_basis="mg/kg/dose",
        weight_normalized_dose=15, dose_unit="mg", frequency_per_day=3, frequency_text="q8h", route="oral",
        order_timestamp="2026-03-10", complexity=1)
    expected_exposure(s); return json.loads(s.to_json())

def parsed(**over):
    p = {"drug": "X", "current_weight_kg": 20, "dose_basis": "mg/kg/dose", "weight_normalized_dose": 15, "dose_unit": "mg",
         "dose_per_admin_mg": 300, "frequency_per_day": 3, "route": "PO", "concentration_mg_per_ml": None,
         "max_per_dose_mg": None, "max_per_day_mg": None, "insufficient_information": []}
    p.update(over); return p

def test_perfect():
    s = base(); r = score_record({"record_id": "r", "parsed": parsed()}, s, "C", 0.10, 0.20)
    assert r["complete_regimen"] and r["dosing_consistent"] and r["primary_endpoint"] and r["codes"] == []

def test_frequency_error_is_dose_consequential_and_coded():
    s = base(); r = score_record({"record_id": "r", "parsed": parsed(frequency_per_day=4)}, s, "C", 0.10, 0.20)
    assert not r["complete_regimen"] and r["dose_consequential"] and "frequency" in r["codes"]
    assert abs(r["dev_day"] - 1/3) < 1e-9 and r["field_acc"] == 7/8

def test_dose_basis_error_coded():
    s = base(); s["dose_basis"] = "mg/kg/day"; s["weight_normalized_dose"] = 45; s["expected_dose_per_admin_mg"] = 300
    r = score_record({"record_id": "r", "parsed": parsed(dose_basis="mg/kg/dose", weight_normalized_dose=45, dose_per_admin_mg=900)}, s, "C", 0.10, 0.20)
    assert "dose_basis" in r["codes"] and r["dose_consequential"]

def test_lb_as_kg_coded_weight_unit():
    s = base(); s["current_weight_unit"] = "lb"; s["current_weight_value"] = 44.1
    r = score_record({"record_id": "r", "parsed": parsed(current_weight_kg=44.1, dose_per_admin_mg=661.5)}, s, "C", 0.10, 0.20)
    assert "weight_unit" in r["codes"]

def test_abstention_hallucination():
    s = base(); s["abstention_case"] = True; s["missing_fields"] = ["current_weight_value"]; s["current_weight_value"] = 20
    r = score_record({"record_id": "r", "parsed": parsed(current_weight_kg=12.0)}, s, "C", 0.10, 0.20)
    assert r["hallucinated"] and not r["appropriate_abstention"]
    r2 = score_record({"record_id": "r", "parsed": parsed(current_weight_kg=None, dose_per_admin_mg=None, insufficient_information=["current_weight_kg"])}, s, "C", 0.10, 0.20)
    assert r2["appropriate_abstention"] and not r2["hallucinated"]

def test_malformed():
    s = base(); r = score_record({"record_id": "r", "parsed": None}, s, "C", 0.10, 0.20)
    assert r["malformed"] and "malformed_output" in r["codes"]

def test_small_rounding_within_tolerance():
    s = base(); r = score_record({"record_id": "r", "parsed": parsed(dose_per_admin_mg=299.9)}, s, "C", 0.10, 0.20)
    assert r["complete_regimen"] and r["dosing_consistent"]
