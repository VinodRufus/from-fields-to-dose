"""Rebuild the row-level evidence packet (results/packet/02_row_level) from the committed run-1 raw and scored files.

Three files, each as .txt (human-readable) and .jsonl (one row per record, model and workflow): stale_weight (the five
abstention notes on which every frontier model supplied a prior-visit weight as current), maximum_dose (the five Level 3
notes whose weight-based product exceeds a maximum stated in the order; the fifth, prednisolone adolescent v0, was
identified by tools/max_check.py after the first packet build) and neonatal_rounding (the one locked record whose printed
amount is more than 10 percent from the exact product). For every record the note text and scenario fields come from the
locked data files (verified against LOCK.json), and for every model and workflow the parsed output comes from the raw file
and the scored row from the scored file. Nothing is typed in.

The first packet build (release v1.0.2) was made before the Gemini 3.1 Pro runs were scored, so its Gemini scored rows
were empty; this script fills them from the committed scored files and otherwise reproduces the earlier files.

Usage (from the repository root): python -m tools.packet_rows
"""
from __future__ import annotations
import glob, hashlib, json, os, sys

OUT = os.path.join("results", "packet", "02_row_level")
MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro-preview", "gpt-5.5-2026-04-23", "llama3.1:8b"]  # alphabetical, as in the first packet build
SETS = {
    "stale_weight": [
        "test-clindamycin-mg_kg_day-infant-L3-v0-r0",
        "test-gentamicin-mg_kg_day-school_age-L3-v1-r0",
        "test-dexamethasone-mg_kg_day-toddler-L3-v1-r0",
        "test-dexamethasone-mg_kg_day-school_age-L3-v1-r0",
        "test-dexamethasone-mg_kg_day-adolescent-L3-v0-r0",
    ],
    "maximum_dose": [
        "test-amoxicillin-mg_kg_day-school_age-L3-v1-r0",
        "test-ceftriaxone-mg_kg_day-adolescent-L3-v1-r0",
        "test-prednisolone-mg_kg_day-school_age-L3-v1-r0",
        "test-prednisolone-mg_kg_day-adolescent-L3-v1-r0",
        "test-prednisolone-mg_kg_day-adolescent-L3-v0-r0",
    ],
    "neonatal_rounding": ["test-dexamethasone-mg_kg_day-neonate-L1-v0-r0"],
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def load_runs():
    """Return {(model, workflow): ({record_id: raw_row}, {record_id: scored_row})} for run 1."""
    runs = {}
    for f in sorted(glob.glob("results/raw_test_*_run1.jsonl")):
        L = [json.loads(l) for l in open(f)]
        cfg = L[0]["_config"]
        key = (cfg["model"]["id"], cfg["workflow"])
        raw = {}
        for x in L[1:]:
            if "record_id" in x:
                raw[x["record_id"]] = x  # last attempt per record, as the scorer keeps it
        sf = f.replace("raw_test_", "scored_test_")
        S = [json.loads(l) for l in open(sf)] if os.path.exists(sf) else []
        scored = {x["record_id"]: x for x in S[1:] if "record_id" in x}
        runs[key] = (raw, scored)
    return runs


def main():
    lock = json.load(open("data/test/LOCK.json"))
    for name, key in (("records.jsonl", "records_sha256"), ("scenarios.jsonl", "scenarios_sha256")):
        if sha256(os.path.join("data/test", name)) != lock[key]:
            sys.exit(f"STOP: data/test/{name} does not match LOCK.json")
    R = {json.loads(l)["record_id"]: json.loads(l) for l in open("data/test/records.jsonl")}
    S = {json.loads(l)["scenario_id"]: json.loads(l) for l in open("data/test/scenarios.jsonl")}
    runs = load_runs()
    missing = [(m, w) for m in MODELS for w in ("B", "C") if (m, w) not in runs]
    if missing:
        sys.exit(f"STOP: run-1 files missing for {missing}")
    os.makedirs(OUT, exist_ok=True)
    for name, ids in SETS.items():
        txt, rows = [], []
        for rid in ids:
            rec = R[rid]; sc = S[rec["scenario_id"]]
            txt.append("=" * 100)
            txt.append(f"RECORD {rid}")
            txt.append("--- NOTE ---")
            txt.append(rec["text"])
            txt.append("--- SCENARIO ---")
            for k in sorted(sc):
                txt.append(f"  {k}: {sc[k]}")
            for m in MODELS:
                for w in ("B", "C"):
                    raw, scored = runs[(m, w)]
                    parsed = (raw.get(rid) or {}).get("parsed") or {}
                    srow = scored.get(rid) or {}
                    txt.append(f"--- {m} workflow {w} ---")
                    txt.append(f"  parsed: {json.dumps(parsed)}")
                    txt.append(f"  scored: {json.dumps(srow)}")
                    rows.append({"record_id": rid, "model": m, "workflow": w, "note": rec["text"], "scenario": sc, "parsed": parsed, "scored": srow})
        open(os.path.join(OUT, name + ".txt"), "w").write("\n".join(txt) + "\n")
        with open(os.path.join(OUT, name + ".jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        empty = sum(1 for r in rows if not r["scored"])
        print(f"{name}: {len(ids)} records, {len(rows)} rows, {empty} rows without a scored entry")


if __name__ == "__main__":
    main()
