"""Scoring (Protocol Section 12-13): Levels 1-4, abstention, automatic error coding.
Usage: python -m scoring.score --raw results/raw_dev_C_FAKE_x.jsonl [--tol 0.10 --tol-sens 0.20]"""
from __future__ import annotations
import argparse, json, os, sys, hashlib
from typing import Dict, Any, Optional, List
from generator.calculator import to_kg, reconstruct, relative_deviation

ROOT = os.path.join(os.path.dirname(__file__), "..")
REQUIRED = ["drug", "current_weight_kg", "dose_basis", "weight_normalized_dose", "dose_unit", "dose_per_admin_mg", "frequency_per_day", "route"]
NUM_TOL = 0.01   # Level 1 numeric tolerance after normalization (1% relative)

def num_eq(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None: return a is None and b is None
    if b == 0: return abs(a) < 1e-9
    return abs(a - b) / abs(b) <= NUM_TOL

def norm_route(r: Optional[str]) -> Optional[str]:
    if r is None: return None
    r = r.strip().lower()
    return {"po": "oral", "by mouth": "oral", "oral": "oral", "iv": "iv", "intravenous": "iv", "im": "im"}.get(r, r)

def truth_fields(s: Dict[str, Any]) -> Dict[str, Any]:
    miss = set(s.get("missing_fields", [])) | set(s.get("conflict_fields", []))
    return {
        "drug": s["drug"],
        "current_weight_kg": None if "current_weight_value" in miss else round(to_kg(s["current_weight_value"], s["current_weight_unit"]), 6),
        "dose_basis": s["dose_basis"], "weight_normalized_dose": s["weight_normalized_dose"], "dose_unit": s["dose_unit"],
        "dose_per_admin_mg": s.get("expected_dose_per_admin_mg"),
        "frequency_per_day": None if "frequency_per_day" in miss else s["frequency_per_day"],
        "route": norm_route(s["route"]),
    }

def field_correct(name: str, got: Any, truth: Any) -> bool:
    if name in ("drug",): return (got or "").strip().lower() == (truth or "").strip().lower()
    if name == "route": return norm_route(got) == truth
    if name in ("dose_basis", "dose_unit"): return got == truth
    if name == "frequency_per_day": return got == truth
    return num_eq(got, truth)

def auto_code(p: Dict[str, Any], s: Dict[str, Any], t: Dict[str, Any]) -> List[str]:
    """Rule-based error classes that can be determined from output vs canonical (Protocol 13)."""
    codes = []
    miss = set(s.get("missing_fields", []))
    conf = set(s.get("conflict_fields", []))
    w = p.get("current_weight_kg")
    if "current_weight_value" in conf:
        if w is not None: codes.append("conflict_resolved_without_flag:weight")
    elif "current_weight_value" in miss:
        if w is not None: codes.append("unsupported_value_hallucination:weight")
    else:
        if w is None: codes.append("extraction:weight_missing")
        elif not num_eq(w, t["current_weight_kg"]):
            if s["current_weight_unit"] == "lb" and num_eq(w, s["current_weight_value"]): codes.append("weight_unit")
            elif s.get("prior_weight_value") is not None and num_eq(w, to_kg(s["prior_weight_value"], s["prior_weight_unit"])): codes.append("weight_selection")
            elif s.get("birth_weight_kg") is not None and num_eq(w, s["birth_weight_kg"]): codes.append("weight_selection:birth_weight")
            else: codes.append("extraction:weight_wrong")
    if p.get("dose_basis") != t["dose_basis"]:
        if p.get("dose_basis") and t["dose_basis"] and p["dose_basis"].split("/")[0] == t["dose_basis"].split("/")[0]: codes.append("dose_basis")
        elif p.get("dose_basis") == "fixed": codes.append("adult_fixed_dose_assumption")
        else: codes.append("normalization:dose_basis")
    if p.get("dose_unit") != t["dose_unit"]: codes.append("unit_scale")
    if "frequency_per_day" in miss:
        if p.get("frequency_per_day") is not None: codes.append("unsupported_value_hallucination:frequency")
    elif p.get("frequency_per_day") != t["frequency_per_day"]: codes.append("frequency")
    if norm_route(p.get("route")) != t["route"]: codes.append("route")
    if not field_correct("weight_normalized_dose", p.get("weight_normalized_dose"), t["weight_normalized_dose"]):
        if s.get("concentration_mg_per_ml") and num_eq(p.get("weight_normalized_dose"), s["concentration_mg_per_ml"]): codes.append("strength_vs_dose")
        else: codes.append("extraction:dose_wrong")
    if (s.get("max_per_day_mg") or s.get("max_per_dose_mg")) and (p.get("max_per_day_mg") is None and p.get("max_per_dose_mg") is None) and not field_correct("dose_per_admin_mg", p.get("dose_per_admin_mg"), t["dose_per_admin_mg"]):
        codes.append("dose_cap")
    return codes

def score_record(rec: Dict[str, Any], s: Dict[str, Any], workflow: str, tol: float, tol_sens: float) -> Dict[str, Any]:
    p = rec.get("parsed") or {}
    if not isinstance(p, dict): p = {}
    p = {k: (v if (k == "insufficient_information" and isinstance(v, list)) or isinstance(v, (int, float, str)) or v is None else None) for k, v in p.items()}
    if not isinstance(p.get("insufficient_information"), list): p["insufficient_information"] = []
    t = truth_fields(s)
    abst = bool(s.get("abstention_case"))
    miss = set(s.get("missing_fields", [])) | set(s.get("conflict_fields", []))
    out: Dict[str, Any] = {"record_id": rec["record_id"], "scenario_id": s["scenario_id"], "workflow": workflow,
                           "run_id": rec.get("run_id"), "age_band": s["age_band"], "complexity": s["complexity"], "abstention_case": abst,
                           "conflict_case": bool(s.get("conflict_fields")), "challenges": s.get("challenges", []),
                           "generation_method": rec.get("generation_method"), "malformed": rec.get("parsed") is None}
    if rec.get("parsed") is None:
        out.update({"fields": {}, "field_acc": 0.0, "complete_regimen": False, "dosing_consistent": False,
                    "dose_consequential": True, "codes": ["malformed_output"]})
        return out
    req = [k for k in REQUIRED if not (k == "dose_per_admin_mg" and "derive_per_dose" in (s.get("challenges") or []))]
    fields = {k: field_correct(k, p.get(k), t[k]) for k in req}
    out["fields"] = fields
    out["field_acc"] = sum(fields.values()) / len(fields)
    out["complete_regimen"] = all(fields.values())
    out["codes"] = auto_code(p, s, t)
    if abst:
        flagged = set(p.get("insufficient_information") or [])
        expect = {"current_weight_kg" if f == "current_weight_value" else f for f in miss}
        out["appropriate_abstention"] = expect.issubset(flagged) and all(p.get(f) is None for f in expect)
        out["unnecessary_abstention"] = bool(flagged - expect)
        out["hallucinated"] = any(p.get(f) is not None for f in expect)
        out["dosing_consistent"] = None; out["dose_consequential"] = None
        return out
    # Level 3/4
    if workflow == "C":
        try:
            rc = reconstruct(p.get("current_weight_kg"), p.get("dose_basis"), p.get("weight_normalized_dose"), p.get("dose_unit"),
                             p.get("frequency_per_day"), p.get("max_per_dose_mg"), p.get("max_per_day_mg"), p.get("concentration_mg_per_ml"))
            obs_dose, obs_day = rc["mg_per_kg_per_dose"], rc["mg_per_kg_per_day"]
        except Exception:
            obs_dose, obs_day = None, None
    else:
        obs_dose, obs_day = p.get("mg_per_kg_per_dose"), p.get("mg_per_kg_per_day")
    exp_dose, exp_day = s.get("expected_mg_per_kg_per_dose"), s.get("expected_mg_per_kg_per_day")
    dev_dose, dev_day = relative_deviation(obs_dose, exp_dose), relative_deviation(obs_day, exp_day)
    devs = [d for d in (dev_dose, dev_day) if d is not None]
    worst = max(devs) if devs else None
    out.update({"obs_mg_per_kg_per_dose": obs_dose, "obs_mg_per_kg_per_day": obs_day,
                "dev_dose": dev_dose, "dev_day": dev_day,
                "dosing_consistent": (worst is not None and worst <= tol),
                "dose_consequential": (worst is None or worst > tol),
                "dose_consequential_sens": (worst is None or worst > tol_sens),
                "exceeds_labeled_max": bool(s.get("max_per_day_mg") and obs_day is not None and obs_day * to_kg(s["current_weight_value"], s["current_weight_unit"]) > s["max_per_day_mg"] * 1.001)})
    if out["complete_regimen"] and not out["dosing_consistent"]: out["codes"].append("arithmetic_inconsistency")
    out["primary_endpoint"] = out["complete_regimen"] and out["dosing_consistent"]
    return out

def check_lock(split: str) -> None:
    if split != "test": return
    lock = json.load(open(os.path.join(ROOT, "data", "test", "LOCK.json")))
    from tools.lock_testset import hash_file, hash_scoring
    if hash_file(os.path.join(ROOT, "data", "test", "records.jsonl")) != lock["records_sha256"]: sys.exit("refusing: test records hash mismatch")
    if hash_scoring() != lock["scoring_sha256"]: sys.exit("refusing: scoring code or prompts changed since lock (record a deviation and re-lock only with justification)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, nargs="+")
    ap.add_argument("--tol", type=float, default=0.10)
    ap.add_argument("--tol-sens", type=float, default=0.20)
    a = ap.parse_args()
    for raw in a.raw:
        score_file(raw, a.tol, a.tol_sens)

def score_file(raw_path: str, tol: float, tol_sens: float):
    a = type("A", (), {"raw": raw_path, "tol": tol, "tol_sens": tol_sens})()
    lines = [json.loads(l) for l in open(a.raw)]
    cfg = lines[0]["_config"]; rows = [x for x in lines[1:] if "record_id" in x]
    # keep the last attempt per record (resumed runs may contain an earlier failed line)
    last = {}
    for x in rows: last[x["record_id"]] = x
    rows = list(last.values())
    split, workflow = cfg["split"], cfg["workflow"]
    check_lock(split)
    scen = {json.loads(l)["scenario_id"]: json.loads(l) for l in open(os.path.join(ROOT, "data", split, "scenarios.jsonl"))}
    gm = {json.loads(l)["record_id"]: json.loads(l).get("generation_method", "template") for l in open(os.path.join(ROOT, "data", split, "records.jsonl"))}
    for r in rows: r["generation_method"] = gm.get(r["record_id"])
    out_path = a.raw.replace("raw_", "scored_")
    with open(out_path, "w") as f:
        f.write(json.dumps({"_config": cfg, "tol": a.tol, "tol_sens": a.tol_sens}) + "\n")
        for r in rows:
            f.write(json.dumps(score_record(r, scen[r["scenario_id"]], workflow, a.tol, a.tol_sens)) + "\n")
    print("wrote", out_path)

if __name__ == "__main__": main()
