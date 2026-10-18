"""Workflow A: rules-based extractor (regex + small grammar) followed by the deterministic calculator (Protocol 11).
Time-boxed secondary arm. Usage: python -m harness.rules_baseline --split test [--run-id run1]
Writes results/raw_<split>_C_RULES_<run>.jsonl in the same format as the model runner (scored as workflow C)."""
import argparse, json, os, re, time
from harness.common import ROOT
from generator.calculator import LB_PER_KG
FREQ = [(r"\b(q4h|every 4 hours)\b", 6), (r"\b(qid|q6h|four times daily|every 6 hours)\b", 4), (r"\b(tid|q8h|three times daily|every 8 hours)\b", 3),
        (r"\b(bid|q12h|twice daily|every 12 hours)\b", 2), (r"\b(once daily|daily|q24h)\b", 1)]
def extract(text: str, drug: str):
    t = text; low = t.lower(); out = {"drug": drug if drug.lower() in low else None, "insufficient_information": []}
    # weights: prefer "Today's weight"/"Wt"/"Weight:" lines; take the LAST current-weight mention, ignore 'prior'/'birth'
    w = None
    for m in re.finditer(r"(?i)(today's weight|current weight|wt|weight)[^\n.;]*?(\d+(?:\.\d+)?)\s*(kg|lb)", t):
        ctx = t[max(0, m.start()-15):m.end()].lower()
        if "prior" in ctx or "birth" in ctx or "intake" in ctx or "recorded as" in ctx: continue
        v, u = float(m.group(2)), m.group(3).lower(); w = v / LB_PER_KG if u == "lb" else v
    if w is None: out["insufficient_information"].append("current_weight_kg")
    out["current_weight_kg"] = round(w, 3) if w else None
    # target drug order line: find the drug followed by a dose per kg
    m = None
    for cand in re.finditer(re.escape(drug) + r"\s+(\d+(?:\.\d+)?)\s*(mg|mcg)/kg/(dose|day)", t, re.I):
        after = t[cand.end(): cand.end() + 90].lower(); before = t[max(0, cand.start() - 25): cand.start()].lower()
        if "discontinued" in after or "previously" in before: continue
        m = cand
    if m:
        out["weight_normalized_dose"] = float(m.group(1)); out["dose_unit"] = m.group(2).lower(); out["dose_basis"] = f"{m.group(2).lower()}/kg/{m.group(3).lower()}"
        tail = t[m.end(): m.end() + 160].lower()
    else:
        out["weight_normalized_dose"] = None; out["dose_unit"] = None; out["dose_basis"] = None; tail = low
    f = None
    for pat, n in FREQ:
        if re.search(pat, tail): f = n; break
    if f is None: out["insufficient_information"].append("frequency_per_day")
    out["frequency_per_day"] = f
    out["route"] = "oral" if re.search(r"\b(po|by mouth|oral)\b", tail) else ("IV" if re.search(r"\b(iv|intravenous)\b", tail) else ("IM" if re.search(r"\bim\b", tail) else None))
    mc = re.search(r"(\d+(?:\.\d+)?)\s*mg/mL", t, re.I); out["concentration_mg_per_ml"] = float(mc.group(1)) if mc else None
    md = re.search(r"not to exceed\s+(\d+(?:\.\d+)?)\s*mg/day", t, re.I); out["max_per_day_mg"] = float(md.group(1)) if md else None
    mp = re.search(r"max\s+(\d+(?:\.\d+)?)\s*(mg|mcg)/dose", t, re.I); out["max_per_dose_mg"] = (float(mp.group(1)) / (1000 if mp.group(2).lower() == "mcg" else 1)) if mp else None
    pd = re.search(r"\((\d+(?:\.\d+)?)\s*(mg|mcg) per dose", t, re.I)
    out["dose_per_admin_mg"] = (float(pd.group(1)) / (1000 if pd.group(2).lower() == "mcg" else 1)) if pd else None
    if out["dose_per_admin_mg"] is None and w and out.get("weight_normalized_dose") and f:
        from generator.calculator import reconstruct
        try:
            rc = reconstruct(w, out["dose_basis"], out["weight_normalized_dose"], out["dose_unit"], f, out["max_per_dose_mg"], out["max_per_day_mg"], out["concentration_mg_per_ml"])
            out["dose_per_admin_mg"] = rc["dose_per_admin_mg"]
        except Exception: pass
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); ap.add_argument("--run-id", default="run1"); a = ap.parse_args()
    d = os.path.join(ROOT, "data", a.split)
    scen = {json.loads(l)["scenario_id"]: json.loads(l) for l in open(os.path.join(d, "scenarios.jsonl"))}
    recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
    out = os.path.join(ROOT, "results", f"raw_{a.split}_C_RULES_{a.run_id}.jsonl")
    with open(out, "w") as f:
        f.write(json.dumps({"_config": {"model": {"id": "RULES", "provider": "rules", "family": "rules"}, "workflow": "C", "split": a.split, "run_id": a.run_id, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "subset": None}}) + "\n")
        for r in recs:
            p = extract(r["text"], scen[r["scenario_id"]]["drug"])
            f.write(json.dumps({"record_id": r["record_id"], "scenario_id": r["scenario_id"], "workflow": "C", "run_id": a.run_id, "raw": json.dumps(p), "parsed": p, "error": None, "retries": 0, "latency_s": 0.0}) + "\n")
    print("wrote", out)
if __name__ == "__main__": main()
