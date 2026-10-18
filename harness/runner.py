"""Model runner (Protocol Sections 10-11). API only, pinned ids, resumable, full config logged.
Usage:
  python -m harness.runner --split dev  --workflow C --limit 20            # prompt development
  python -m harness.runner --split test --workflow C --run-id run1          # primary run
  python -m harness.runner --split test --workflow B --run-id run1
  python -m harness.runner --split test --workflow C --run-id run2 --subset data/test/repeat_subset.txt
  --model <id> restricts to one configured model. --fake uses a deterministic fake model (smoke tests only).
Re-running the same command resumes: records already in the output file are skipped."""
from __future__ import annotations
import argparse, json, os, sys, time, random, hashlib
from typing import Dict, Any, Set
from .common import ROOT, load_config, check_generator_exclusion, call_model, extract_json, ModelError

def fake_model(scenario: Dict[str, Any], workflow: str, rng: random.Random) -> Dict[str, Any]:
    from generator.calculator import to_kg, reconstruct
    miss = set(scenario.get("missing_fields", [])) | set(scenario.get("conflict_fields", []))
    out = {"drug": scenario["drug"],
           "current_weight_kg": None if "current_weight_value" in miss else round(to_kg(scenario["current_weight_value"], scenario["current_weight_unit"]), 3),
           "dose_basis": scenario["dose_basis"], "weight_normalized_dose": scenario["weight_normalized_dose"],
           "dose_unit": scenario["dose_unit"], "frequency_per_day": None if "frequency_per_day" in miss else scenario["frequency_per_day"],
           "route": scenario["route"], "concentration_mg_per_ml": scenario.get("concentration_mg_per_ml"),
           "max_per_dose_mg": scenario.get("max_per_dose_mg"), "max_per_day_mg": scenario.get("max_per_day_mg"),
           "insufficient_information": sorted({"current_weight_kg" if f == "current_weight_value" else f for f in miss})}
    r = rng.random()
    if r < 0.10 and out["frequency_per_day"] == 3: out["frequency_per_day"] = 4
    elif r < 0.18 and out["dose_basis"].endswith("/day"): out["dose_basis"] = out["dose_basis"].replace("/day", "/dose")
    elif r < 0.24 and scenario["current_weight_unit"] == "lb": out["current_weight_kg"] = scenario["current_weight_value"]
    elif r < 0.28 and scenario.get("prior_weight_value") is not None: out["current_weight_kg"] = round(to_kg(scenario["prior_weight_value"], scenario["prior_weight_unit"]), 3)
    elif r < 0.32 and out["current_weight_kg"] is None: out["current_weight_kg"] = 12.0; out["insufficient_information"] = []
    if out["current_weight_kg"] and out["frequency_per_day"]:
        rc = reconstruct(out["current_weight_kg"], out["dose_basis"], out["weight_normalized_dose"], out["dose_unit"], out["frequency_per_day"], out["max_per_dose_mg"], out["max_per_day_mg"], out["concentration_mg_per_ml"])
        out["dose_per_admin_mg"] = rc["dose_per_admin_mg"]; out["volume_ml"] = rc["volume_ml"]
        if workflow == "B": out["mg_per_kg_per_dose"] = rc["mg_per_kg_per_dose"]; out["mg_per_kg_per_day"] = rc["mg_per_kg_per_day"]
    else:
        out["dose_per_admin_mg"] = None; out["volume_ml"] = None
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--workflow", required=True, choices=["B", "C"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--run-id", default="run1")
    ap.add_argument("--model", default=None)
    ap.add_argument("--subset", default=None, help="file with record_ids, one per line (repeat runs)")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls (quota pacing)")
    a = ap.parse_args()
    cfg = load_config(); check_generator_exclusion(cfg)
    data_dir = os.path.join(ROOT, "data", a.split)
    if a.split == "test" and not os.path.exists(os.path.join(data_dir, "LOCK.json")):
        sys.exit("refusing: test set is not locked (run: python -m tools.lock_testset)")
    if a.split == "test" and os.path.exists(os.path.join(data_dir, "SMOKE")) and not a.fake:
        sys.exit("refusing: data/test was built in smoke mode from unverified sources; rebuild it from verified sources")
    scen = {}
    for l in open(os.path.join(data_dir, "scenarios.jsonl")):
        d = json.loads(l); scen[d["scenario_id"]] = d
    recs = [json.loads(l) for l in open(os.path.join(data_dir, "records.jsonl"))]
    if a.subset:
        keep = {x.strip() for x in open(a.subset) if x.strip()}
        recs = [r for r in recs if r["record_id"] in keep]
    if a.limit: recs = recs[: a.limit]
    system = open(os.path.join(ROOT, "harness", "prompts", "system.txt")).read()
    task = open(os.path.join(ROOT, "harness", "prompts", f"task_{a.workflow}.txt")).read()
    models = [{"id": "FAKE", "provider": "fake", "family": "fake"}] if a.fake else [m for m in cfg["models"] if m.get("id") and (a.model is None or m["id"] == a.model)]
    if not models: sys.exit("no models configured in config/models.yaml")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    rng = random.Random(7)
    for m in models:
        safe = str(m["id"]).replace("/", "_").replace(":", "_")
        out_path = os.path.join(ROOT, "results", f"raw_{a.split}_{a.workflow}_{safe}_{a.run_id}.jsonl")
        done: Set[str] = set()
        if os.path.exists(out_path):
            for l in open(out_path):
                try:
                    d = json.loads(l)
                    if "record_id" in d and d.get("parsed") is not None: done.add(d["record_id"])
                except Exception: pass
        cfg_rec = {"model": {k: v for k, v in m.items() if k != "api_key"}, "workflow": a.workflow, "split": a.split, "run_id": a.run_id,
                   "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "subset": a.subset,
                   "system_prompt_sha256": hashlib.sha256(system.encode()).hexdigest(), "task_prompt_sha256": hashlib.sha256(task.encode()).hexdigest()}
        todo = [r for r in recs if r["record_id"] not in done]
        print(f"[{m['id']}] {a.split} wf={a.workflow} run={a.run_id}: {len(done)} done, {len(todo)} to do -> {out_path}")
        n_ok = n_err = 0; cost_note = []
        with open(out_path, "a") as f:
            if not done: f.write(json.dumps({"_config": cfg_rec}) + "\n")
            for i, r in enumerate(todo, 1):
                s = scen[r["scenario_id"]]
                user = task.format(drug=s["drug"], record=r["text"])
                t0 = time.time(); raw = None; parsed = None; err = None; retries = 0
                if a.fake:
                    parsed = fake_model(s, a.workflow, rng); raw = json.dumps(parsed)
                else:
                    for attempt in range(2):
                        try:
                            raw = call_model(m, system, user, want_json=True)
                            parsed = extract_json(raw)
                            if parsed is not None: break
                            retries += 1; user = user + "\n\nYour previous output was not valid JSON. Return only the JSON object."
                        except ModelError as e:
                            err = str(e); break
                rec = {"record_id": r["record_id"], "scenario_id": r["scenario_id"], "workflow": a.workflow, "run_id": a.run_id,
                       "raw": raw, "parsed": parsed, "error": err, "retries": retries, "latency_s": round(time.time() - t0, 3),
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
                f.write(json.dumps(rec) + "\n"); f.flush()
                if parsed is not None: n_ok += 1
                else: n_err += 1
                if i % 25 == 0 or i == len(todo): print(f"  {i}/{len(todo)} ok={n_ok} err={n_err}")
                if err and any(t in err.lower() for t in ("quota", "rate limit", "402", "credit", "billing", "prepayment")):
                    print("  stopping on quota/rate-limit error; rerun the same command later to resume"); break
                if a.sleep: time.sleep(a.sleep)
        print(f"[{m['id']}] finished: ok={n_ok} err={n_err}")

if __name__ == "__main__": main()
