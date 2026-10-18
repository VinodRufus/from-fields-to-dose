import math, pytest
from generator.calculator import to_kg, to_mg, reconstruct, relative_deviation

def test_units():
    assert abs(to_kg(22.0462262185, "lb") - 10.0) < 1e-9
    assert to_kg(10, "kg") == 10
    assert to_mg(1000, "mcg") == 1.0
    assert to_mg(1, "g") == 1000

def test_worked_example_20kg_15mgkg_q8h():
    r = reconstruct(20, "mg/kg/dose", 15, "mg", 3)
    assert r["dose_per_admin_mg"] == 300
    assert r["mg_per_kg_per_day"] == 45
    r6 = reconstruct(20, "mg/kg/dose", 15, "mg", 4)   # frequency misread q8h -> q6h
    assert r6["mg_per_kg_per_day"] == 60

def test_per_day_basis_divides_by_frequency():
    r = reconstruct(20, "mg/kg/day", 45, "mg", 3)
    assert r["dose_per_admin_mg"] == 300 and r["mg_per_kg_per_dose"] == 15

def test_dose_basis_confusion_changes_exposure():
    a = reconstruct(20, "mg/kg/day", 60, "mg", 3)
    b = reconstruct(20, "mg/kg/dose", 60, "mg", 3)
    assert a["mg_per_kg_per_day"] == 60 and b["mg_per_kg_per_day"] == 180

def test_mcg_scale():
    r = reconstruct(10, "mcg/kg/dose", 2, "mcg", 4)
    assert r["dose_per_admin_mg"] == 0.02 and r["mg_per_kg_per_day"] == 0.008

def test_caps():
    r = reconstruct(50, "mg/kg/dose", 10, "mg", 3, max_per_dose_mg=400)
    assert r["dose_per_admin_mg"] == 400
    r = reconstruct(50, "mg/kg/dose", 10, "mg", 3, max_per_day_mg=1200)
    assert r["daily_mg"] == 1200 and r["dose_per_admin_mg"] == 400

def test_volume():
    r = reconstruct(20, "mg/kg/dose", 15, "mg", 3, concentration_mg_per_ml=80)
    assert r["volume_ml"] == 3.75

def test_missing_inputs_raise():
    with pytest.raises(ValueError): reconstruct(None, "mg/kg/dose", 15, "mg", 3)
    with pytest.raises(ValueError): reconstruct(20, "mg/kg/dose", 15, "mg", None)

def test_relative_deviation():
    assert abs(relative_deviation(60, 45) - 1/3) < 1e-9
    assert relative_deviation(None, 45) is None
