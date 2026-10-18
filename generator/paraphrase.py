"""Controlled paraphrase of template records by the GENERATOR model (Protocol 7.1), with a
fact-preservation check (Protocol 3.3 step 2). Records that fail the check keep the template text.
Usage: python -m generator.paraphrase --split dev [--fraction 0.5] [--fake]
Abstention and conflict records are never paraphrased (their missing/conflicting facts must stay exactly as built)."""
from __future__ import annotations
import argparse, json, os, random, re, sys, time
from typing import Dict, Any, List
from harness.common import ROOT, load_config, call_model, ModelError
from .templates import FREQ_TEXT, ROUTE_TEXT, fmt_dose

PROMPT = """Rewrite the clinical note below in a different documentation style (for example a different clinician's voice, different sentence order, or a different note format). Rules:
- Keep EVERY number, unit, date, medication name, frequency, and route exactly as given. Do not round, convert, add, or remove any value.
- Do not add any new clinical facts, weights, doses, or medications.
- Keep the same meaning for order status (active, discontinued, prior).
- Keep it the same length within 30 percent. Output only the rewritten note, no commentary.

Note:
<<<
{text}
>>>"""

def _nums_in(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", text)

def facts_preserved(s: Dict[str, Any], new_text: str) -> List[str]:
    """Return list of missing facts (empty = ok)."""
    t = new_text.lower(); missing = []
    def has(x): return x.lower() in t
    if not has(s["drug"]): missing.append("drug")
    if "current_weight_value" not in s.get("missing_fields", []):
        if f"{s['current_weight_value']:g}" not in new_text: missing.append("weight_value")
        if not has(s["current_weight_unit"]): missing.append("weight_unit")
    if f"{s['weight_normalized_dose']:g}" not in new_text: missing.append("weight_normalized_dose")
    if not has(f"{s['dose_unit']}/kg"): missing.append("dose_unit_per_kg")
    if "frequency_per_day" not in s.get("missing_fields", []):
        syn = [x.lower() for x in FREQ_TEXT.get(s["frequency_per_day"], [])]
        syn += {1: ["every 24 hours", "once a day", "q.d.", "qd"], 2: ["every 12 hours", "twice a day", "b.i.d."],
                3: ["every 8 hours", "three times a day", "t.i.d."], 4: ["every 6 hours", "four times a day", "q.i.d."], 6: ["every 4 hours"]}.get(s["frequency_per_day"], [])
        if not any(x in t for x in syn): missing.append("frequency")
    rsyn = [x.lower() for x in ROUTE_TEXT.get(s["route"], [s["route"]])] + [s["route"].lower()]
    if not any(re.search(r"\b" + re.escape(x) + r"\b", t) for x in rsyn): missing.append("route")
    if s.get("expected_dose_per_admin_mg") is not None and "derive_per_dose" not in s.get("challenges", []):
        if fmt_dose(s["expected_dose_per_admin_mg"], s["dose_unit"]).split()[0] not in new_text: missing.append("per_dose_value")
    if s.get("concentration_mg_per_ml") and f"{s['concentration_mg_per_ml']:g}" not in new_text: missing.append("concentration")
    if s.get("max_per_day_mg") and f"{s['max_per_day_mg']:g}" not in new_text: missing.append("max_per_day")
    if s.get("prior_weight_value") is not None and f"{s['prior_weight_value']:g}" not in new_text: missing.append("prior_weight")
    # no new numbers that look like weights/doses were introduced
    orig_nums = set(_nums_in(s.get("_template_text", "")))
    new_nums = set(_nums_in(new_text))
    extra = [n for n in new_nums - orig_nums if n not in ("1", "2", "3", "4", "5", "6", "8", "12", "24")]
    if extra: missing.append("new_numbers:" + ",".join(sorted(extra)[:5]))
    return missing

def fake_paraphrase(text: str, rng: random.Random) -> str:
    swaps = [("Weight:", "Wt:"), ("Medication order", "Order"), ("Assessment/Plan", "A/P"), ("presenting for", "seen for"), ("Today's weight", "Current weight")]
    for a, b in swaps:
        if rng.random() < 0.7: text = text.replace(a, b)
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--fraction", type=float, default=0.5, help="share of eligible records to paraphrase")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--seed", type=int, default=99)
    a = ap.parse_args()
    cfg = load_config(); gen = cfg.get("generator") or {}
    if not a.fake and not gen.get("id"): sys.exit("config/models.yaml: generator.id is empty")
    d = os.path.join(ROOT, "data", a.split)
    if os.path.exists(os.path.join(d, "LOCK.json")): sys.exit("refusing: split is locked")
    scen = {json.loads(l)["scenario_id"]: json.loads(l) for l in open(os.path.join(d, "scenarios.jsonl"))}
    recs = [json.loads(l) for l in open(os.path.join(d, "records.jsonl"))]
    rng = random.Random(a.seed); n_try = n_ok = n_fail = 0; log = []
    for r in recs:
        s = scen[r["scenario_id"]]
        if r.get("generation_method", "template") != "template": continue
        if s.get("abstention_case") or rng.random() > a.fraction: continue
        n_try += 1
        s["_template_text"] = r["text"]
        try:
            new = fake_paraphrase(r["text"], rng) if a.fake else call_model(gen, "You rewrite clinical notes without changing any fact.", PROMPT.format(text=r["text"]), want_json=False).strip()
        except ModelError as e:
            log.append({"record_id": r["record_id"], "status": "error", "detail": str(e)}); n_fail += 1; continue
        missing = facts_preserved(s, new)
        if missing:
            log.append({"record_id": r["record_id"], "status": "rejected", "missing": missing}); n_fail += 1; continue
        r["text"] = new; r["generation_method"] = "paraphrase:" + (gen.get("id") if not a.fake else "FAKE"); n_ok += 1
        log.append({"record_id": r["record_id"], "status": "ok"})
    with open(os.path.join(d, "records.jsonl"), "w") as f:
        for r in recs: f.write(json.dumps(r) + "\n")
    with open(os.path.join(d, "paraphrase.log"), "w") as f:
        for x in log: f.write(json.dumps(x) + "\n")
    print(f"[{a.split}] paraphrase attempted={n_try} accepted={n_ok} rejected_or_error={n_fail} (rejections keep template text; see paraphrase.log)")

if __name__ == "__main__": main()
