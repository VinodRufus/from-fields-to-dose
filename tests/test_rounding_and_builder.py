import json, random
from generator.calculator import round_documented, expected_exposure
from generator.schema import CanonicalScenario
from generator.build_corpus import nice_dose, sample_weight_kg
from generator.templates import render, fmt_dose

def test_round_documented():
    assert round_documented(99.471, "mg") == 99.0
    assert round_documented(2.345, "mg") == 2.3
    assert round_documented(0.4567, "mg") == 0.46
    assert round_documented(0.02, "mcg") == 0.02          # 20 mcg
    assert round_documented(0.0074, "mcg") == 0.0075      # 7.4 mcg -> 7.5 mcg

def test_fmt_dose():
    assert fmt_dose(0.02, "mcg") == "20 mcg" and fmt_dose(300, "mg") == "300 mg"

def test_nice_dose_in_range():
    rng = random.Random(1)
    for lo, hi in [(10, 15), (25, 45), (1, 2), (0.1, 0.3), (20, 100)]:
        for _ in range(50):
            v = nice_dose(lo, hi, rng); assert lo - 1e-9 <= v <= hi + 1e-9

def test_weight_fallback_monotone():
    rng = random.Random(2)
    w1 = sample_weight_kg(10, "M", rng, [], False); w2 = sample_weight_kg(3000, "M", rng, [], False)
    assert 2 < w1 < 5 and w2 > w1

def test_expected_exposure_documented_vs_exact():
    s = CanonicalScenario(scenario_id="t", drug="X", indication="i", age_days=1000, age_band="toddler", sex="M",
        current_weight_value=7.1, current_weight_unit="kg", weight_timestamp="d", dose_basis="mg/kg/dose",
        weight_normalized_dose=14, dose_unit="mg", frequency_per_day=3, frequency_text="", route="oral", concentration_mg_per_ml=80)
    expected_exposure(s)
    assert s.expected_dose_per_admin_mg == 99.0            # documented (rounded)
    assert abs(s.expected_mg_per_kg_per_dose - 14) < 1e-9  # exact by construction
    assert s.expected_volume_ml == 1.24
    txt = render(s, random.Random(3))
    assert "99 mg per dose" in txt and "14 mg/kg/dose" in txt

def test_per_day_template_says_divided():
    s = CanonicalScenario(scenario_id="t", drug="X", indication="i", age_days=1000, age_band="toddler", sex="F",
        current_weight_value=20, current_weight_unit="kg", weight_timestamp="d", dose_basis="mg/kg/day",
        weight_normalized_dose=45, dose_unit="mg", frequency_per_day=3, frequency_text="", route="oral", complexity=1)
    expected_exposure(s)
    assert "divided" in render(s, random.Random(4)) and s.expected_dose_per_admin_mg == 300
