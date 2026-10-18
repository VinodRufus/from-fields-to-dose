"""Build canonical scenarios and synthetic records; split by scenario (Protocol Sections 7, 9, 14).
Usage:
  python -m generator.build_corpus --dev  [--sources sources/dosing_sources.csv] [--variants 2] [--allow-unverified]
  python -m generator.build_corpus --test [--sources sources/dosing_sources.csv] [--variants 2]
One scenario per (source row x age band x complexity x variant). Test set refuses unverified rows."""
from __future__ import annotations
import argparse, json, math, os, random, sys
import datetime as _dt
from typing import List, Dict, Optional
from .schema import CanonicalScenario, DistractorOrder, validate
from .calculator import expected_exposure, to_kg
from .gates import load_sources, load_lms, run_gates, _f
from .templates import render

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BANDS = json.load(open(os.path.join(ROOT, "sources", "age_bands.json")))["bands"]
ABSTENTION_SHARE = 0.15
TAIL_SHARE = 0.10

def sample_age(band: Dict, rng: random.Random) -> int:
    return rng.randint(band["min_days"], band["max_days"])

def _lms_row(age_days: int, sex: str, lms_rows):
    sex_code = 1 if sex == "M" else 2
    agemos = age_days / 30.4375
    cand = [r for r in lms_rows if r["sex"] == sex_code]
    return min(cand, key=lambda r: abs(r["agemos"] - agemos)) if cand else None

def sample_weight_kg(age_days: int, sex: str, rng: random.Random, lms_rows, tail: bool) -> float:
    """Weight from CDC/WHO LMS when available (z in [-2,2], or tails [2,3.5] for 10%); fallback medians otherwise."""
    r = _lms_row(age_days, sex, lms_rows) if lms_rows else None
    if r:
        z = rng.uniform(-2.0, 2.0) if not tail else rng.choice([-1, 1]) * rng.uniform(2.05, 2.5)
        L, M, S = r["L"], r["M"], r["S"]
        x = M * (1 + L * S * z) ** (1 / L) if abs(L) > 1e-9 else M * math.exp(S * z)
        x = min(x, 2.2 * M)
        return round(x, 1 if x >= 10 else 2)
    y = age_days / 365.0
    if age_days < 28: base = 3.4
    elif y < 1: base = 3.4 + 6.0 * y
    elif y < 2: base = 9.5 + 2.5 * (y - 1)
    else: base = 12.0 + 2.3 * (y - 2)
    f = rng.uniform(0.9, 1.1) if not tail else rng.choice([0.75, 1.35])
    x = base * f
    return round(x, 1 if x >= 10 else 2)

def nice_dose(lo: float, hi: float, rng: random.Random) -> float:
    span = hi - lo
    step = 0.5 if span <= 5 else (1.0 if span <= 30 else 5.0)
    if lo < 1: step = 0.1
    n = int(round((hi - lo) / step))
    vals = [round(lo + i * step, 2) for i in range(n + 1)]
    vals = [v for v in vals if lo - 1e-9 <= v <= hi + 1e-9] or [lo]
    return rng.choice(vals)

def make_scenario(sid: str, src: Dict[str, str], band: Dict, complexity: int, rng: random.Random,
                  abstention: bool, tail: bool, lms_rows) -> CanonicalScenario:
    age = sample_age(band, rng)
    sex = rng.choice(["M", "F"])
    wkg = sample_weight_kg(age, sex, rng, lms_rows, tail)
    unit = "kg"; challenges = []
    if tail: challenges.append("weight_tail")
    if complexity == 3 and rng.random() < 0.4:
        unit = "lb"; challenges.append("lb_documentation")
    wval = round(wkg * 2.20462, 1) if unit == "lb" else wkg
    lo, hi = _f(src["dose_min"]), _f(src["dose_max"])
    wnd = nice_dose(lo, hi, rng)
    freqs = [int(x) for x in src["frequency_per_day_options"].split("|") if x.strip()]
    freq = rng.choice(freqs)
    basis = src["dose_basis"]
    dose_unit = "mcg" if basis.startswith("mcg") else "mg"
    if dose_unit == "mcg": challenges.append("mcg_drug")
    if basis.endswith("/day"): challenges.append("per_day_basis")
    s = CanonicalScenario(
        scenario_id=sid, drug=src["drug"], indication=src["indication"], age_days=age, age_band=band["id"],
        sex=sex, current_weight_value=wval, current_weight_unit=unit,
        weight_timestamp="2026-03-10", dose_basis=basis, weight_normalized_dose=wnd, dose_unit=dose_unit,
        frequency_per_day=freq, frequency_text="", route=src["route"], order_status="active",
        order_timestamp="2026-03-10", formulation=(src.get("formulation") or None),
        concentration_mg_per_ml=_f(src.get("concentration_mg_per_ml", "")),
        max_per_dose_mg=_f(src.get("max_per_dose_mg", "")), max_per_day_mg=_f(src.get("max_per_day_mg", "")),
        complexity=complexity, challenges=challenges, generation_method="template",
    )
    if s.max_per_day_mg or s.max_per_dose_mg: s.challenges.append("dose_cap")
    if s.concentration_mg_per_ml: s.challenges.append("concentration_volume")
    if complexity >= 2:
        s.distractor_orders.append(DistractorOrder(drug="cholecalciferol", dose_text="400 units PO daily", status="active", timestamp="2026-03-01") if age < 180 else DistractorOrder(drug="cetirizine", dose_text="2.5 mg PO daily", status="active", timestamp="2026-03-01"))
        s.challenges.append("multiple_meds")
    if complexity == 3 and age >= 14:
        s.prior_weight_value = round(wval * rng.uniform(0.85, 0.95), 1); s.prior_weight_unit = unit
        s.prior_weight_timestamp = "2025-12-01" if age >= 200 else (_dt.date(2026, 3, 10) - _dt.timedelta(days=max(14, min(99, age // 2)))).isoformat(); s.challenges.append("multiple_weights")
        if age < 28: s.birth_weight_kg = round(wkg * 0.95, 2); s.challenges.append("birth_weight")
        if rng.random() < 0.5:
            s.distractor_orders.append(DistractorOrder(drug=src["drug"], dose_text=f"{max(lo*0.5, 0.1):g} {dose_unit}/kg/dose {src['route']} BID", status="discontinued", timestamp=(_dt.date(2026, 3, 10) - _dt.timedelta(days=min(18, max(1, age // 2)))).isoformat()))
            s.challenges.append("discontinued_same_drug")
        if basis.endswith("/day") and rng.random() < 0.5:
            s.challenges.append("derive_per_dose")
    if abstention:
        s.abstention_case = True
        mode = rng.random()
        if complexity == 3 and mode < 0.3:
            s.conflict_fields = ["current_weight_value"]; s.challenges.append("conflict:weight")
        else:
            s.missing_fields = [rng.choice(["current_weight_value", "frequency_per_day"])]
            s.challenges.append("missing:" + s.missing_fields[0])
    expected_exposure(s)
    return s

def build(split: str, sources_path: str, n_drugs: int, variants: int, seed: int, require_verified: bool, out_dir: str, lms_rows) -> None:
    rng = random.Random(seed)
    sources = load_sources(sources_path)
    drugs: List[str] = []
    for r in sources:
        if r["drug"] not in drugs: drugs.append(r["drug"])
    drugs = drugs[:n_drugs]
    rows = [r for r in sources if r["drug"] in drugs]
    if not rows: sys.exit("no source rows")
    scen_path = os.path.join(out_dir, "scenarios.jsonl"); rec_path = os.path.join(out_dir, "records.jsonl")
    rej_path = os.path.join(out_dir, "rejections.log")
    n_scen = n_rec = n_rej = 0
    with open(scen_path, "w") as fs, open(rec_path, "w") as fr, open(rej_path, "w") as fj:
        for src in rows:
            for band in BANDS:
                for cx in (1, 2, 3):
                    for v in range(variants):
                        sid = f"{split}-{src['drug']}-{src['dose_basis'].replace('/', '_')}-{band['id']}-L{cx}-v{v}"
                        abst = rng.random() < ABSTENTION_SHARE
                        tail = (not abst) and rng.random() < TAIL_SHARE
                        s = make_scenario(sid, src, band, cx, rng, abst, tail, lms_rows)
                        errs = validate(s)
                        gates = run_gates(s, sources, lms_rows, require_verified, tail_ok=tail)
                        failed = [g for g in gates if not g[1]]
                        if errs or failed:
                            n_rej += 1; fj.write(json.dumps({"scenario_id": sid, "schema_errors": errs, "gates": gates}) + "\n"); continue
                        fs.write(s.to_json() + "\n"); n_scen += 1
                        note = render(s, rng)
                        fr.write(json.dumps({"record_id": sid + "-r0", "scenario_id": sid, "split": split,
                                             "complexity": cx, "age_band": band["id"], "generation_method": "template",
                                             "abstention_case": s.abstention_case, "text": note}) + "\n"); n_rec += 1
    print(f"[{split}] source_rows={len(rows)} drugs={len(drugs)} scenarios={n_scen} records={n_rec} rejected={n_rej} -> {out_dir}")
    if n_rej: print(f"  rejections logged to {rej_path} (expected: age-restricted drugs in bands outside their label range)")

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dev", action="store_true"); g.add_argument("--test", action="store_true")
    ap.add_argument("--sources", default=os.path.join(ROOT, "sources", "dosing_sources.csv"))
    ap.add_argument("--n-drugs", type=int, default=20)
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--allow-unverified", action="store_true", help="DEV/SMOKE ONLY")
    a = ap.parse_args()
    split = "dev" if a.dev else "test"
    smoke = os.environ.get("F2D_SMOKE") == "1"
    if split == "test" and a.allow_unverified and not smoke: sys.exit("refusing: test set must come from verified sources")
    out_dir = os.path.join(ROOT, "data", split); os.makedirs(out_dir, exist_ok=True)
    if split == "test" and os.path.exists(os.path.join(out_dir, "LOCK.json")): sys.exit("refusing: test set is locked")
    lms = []
    for fn in ("wtageinf.csv", "wtage.csv"):
        pth = os.path.join(ROOT, "sources", fn)
        if os.path.exists(pth): lms += load_lms(pth)
    if not lms:
        if split == "test" and not smoke: sys.exit("refusing: CDC/WHO LMS files missing in sources/ (run python -m sources.fetch_growth)")
        print("WARNING: no LMS files found; weight gate skipped (dev/smoke only)")
    seed = a.seed if a.seed is not None else (1001 if split == "dev" else 2002)
    build(split, a.sources, a.n_drugs, a.variants, seed, require_verified=(split == "test" and not smoke), out_dir=out_dir, lms_rows=lms)
    if split == "test" and smoke:
        open(os.path.join(out_dir, "SMOKE"), "w").write("built from unverified sources for the smoke test only\n")

if __name__ == "__main__": main()
