# From Fields to Dose: setup and run guide (copy-paste, step by step)

Everything runs on your own Mac with your own API keys. Nothing touches an employer account, machine, or dataset.
Blocks are numbered; run them in order; each block is short enough to paste into zsh without mangling.
Expected effort: Phase 1 is manual label reading (about 5 hours). Everything else is mostly waiting for API calls.

Protocol v1 is the source of truth (protocol/Protocol_v1_From_Fields_to_Dose.docx). Section numbers below refer to it.

---------------------------------------------------------------------------------------------------
## BLOCK 0. Unzip, create a virtual environment, run the tests and the smoke test (10 minutes)

```
cd ~/Documents
unzip -o ~/Downloads/fields-to-dose-v2.zip
cd ~/Documents/f2d
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m tools.smoke
```

Expected: `25 passed`, then a results table and `SMOKE TEST PASSED`. The smoke test uses fake drugs and a fake
model; it proves the pipeline, nothing else. If `python3` is older than 3.10, install a current Python first.

Every later block assumes you are in `~/Documents/f2d` with the venv active:
```
cd ~/Documents/f2d && source .venv/bin/activate
```

---------------------------------------------------------------------------------------------------
## BLOCK 1. Keys and model identifiers (15 minutes)

```
cp .env.example .env
open -e .env
```
Fill the keys you have (OpenAI, Anthropic, Gemini, DeepSeek, Groq). Save and close. Then:
```
open -e config/models.yaml
```
Put the exact pinned model ids you used in the flagship run manifest into the `id:` fields. Rules the runner enforces:
- the generator/auditor family (default Qwen on Ollama) must differ from every evaluated model family;
- API access only; no web interfaces.
If you do not have Ollama, install it and pull the generator model:
```
brew install ollama
ollama serve &
ollama pull qwen2.5:14b
```
(On a Mac with 16 GB RAM use `qwen2.5:7b` and change the two ids in models.yaml.) Add `OLLAMA_KEY=ollama` to `.env`.

Check that every configured model answers:
```
python -m tools.ping_models
```
Expected: one `OK` line per model with a short JSON reply. Fix any `FAIL` before continuing.

---------------------------------------------------------------------------------------------------
## BLOCK 2. Phase 1: dosing sources with provenance (Protocol Sections 4 and 5) — the manual part

Pull the FDA labels for the 21 candidate drugs (openFDA; same SPL corpus as DailyMed):
```
python -m sources.fetch_labels
open sources/labels/index.csv
```
For each drug, open the label file(s) under `sources/labels/<drug>/`, read `DOSAGE_AND_ADMINISTRATION` and
`PEDIATRIC_USE`, and fill one row per drug and dose pattern in `sources/dosing_sources.csv`:
```
cp sources/dosing_sources.template.csv sources/dosing_sources.csv
open sources/dosing_sources.csv
```
Columns to fill from the label: `dose_min`, `dose_max` (in the units of `dose_basis`), `frequency_per_day_options`
(e.g. `2|3`), `max_per_dose_mg`, `max_per_day_mg` (blank if none), `age_min_days`, `age_max_days`,
`concentration_mg_per_ml` (from DOSAGE FORMS AND STRENGTHS), `source_id` (the SET_ID from the label file),
`source_version`, `retrieval_date`, and set `verified` to `true` only after you have read the label text yourself.
Delete any row the label does not support (the protocol says exclude, never improvise). Keep at least 15 drugs and
check the composition rule in Protocol Section 5 (3 mcg drugs, 5 with caps, 3 oral liquids, 4 parenteral).

Validate the table:
```
python -m sources.check_sources
```
Expected: `OK` with counts per composition rule. Fix anything it reports.

Growth references (Section 6):
```
python -m sources.fetch_growth
ls -la sources/wtageinf.csv sources/wtage.csv
```
If a download fails, the script prints where to get the file by hand. Record which files you used, and the date, in
`protocol/DEVIATIONS.md`.

---------------------------------------------------------------------------------------------------
## BLOCK 3. Phase 2a: development set (Section 9). Prompts are tuned here and nowhere else.

```
python -m generator.build_corpus --dev --variants 1
python -m generator.paraphrase --split dev --fraction 0.5
python -m generator.audit --split dev
python -m generator.show_flagged --split dev
```
Read the flagged records. Fix a template in `generator/templates.py` if a flag reveals a real problem, or remove
records with `python -m tools.remove_records --split dev --ids <record_id> ...`. Re-run the three commands if you
changed a template.

Run the two workflows on the dev set with every configured model (a few dollars):
```
python -m harness.runner --split dev --workflow C --limit 60
python -m harness.runner --split dev --workflow B --limit 60
python -m scoring.score --raw results/raw_dev_*.jsonl
python -m analysis.analyze --scored 'results/scored_dev_*.jsonl'
```
Look at the error codes. If malformed outputs are common for a model, adjust `harness/prompts/system.txt` wording or
the output contract, then rerun the dev commands. Do not look at test data during this step (none exists yet).

---------------------------------------------------------------------------------------------------
## BLOCK 4. Phase 2b: build, audit, and LOCK the test set (Sections 7, 8, 9, 14)

```
python -m generator.build_corpus --test --variants 2
python -m generator.paraphrase --split test --fraction 0.5
python -m generator.audit --split test
python -m generator.show_flagged --split test
```
Fix or remove flagged records exactly as in BLOCK 3 (`--split test`). Then the blinded self-audit (Section 3.3 step 5):
```
python -m tools.self_audit --split test --fraction 0.10
```
It shows 10 percent of records one at a time with the canonical values hidden; you type what the note says; it
reports the correction rate and writes `data/test/self_audit.jsonl`. Fix any real generator error it reveals and
rebuild (BLOCK 4 from the top). When clean:
```
python -m tools.make_repeat_subset --split test
python -m tools.lock_testset
```
Copy the printed hashes into the OSF registration (BLOCK 5). From now on `data/test/` is frozen; the scorer refuses
to run if the records, prompts, or scoring code change.

---------------------------------------------------------------------------------------------------
## BLOCK 5. Register on OSF (30 minutes, before any evaluated model touches the test set)

1. Resolve the `[verify]` and `[decide]` items in Protocol v1 (age-band citation, 10 percent tolerance source, final
   model list, budget ceiling). Save as Protocol v1.0 final.
2. osf.io -> Create new project "From Fields to Dose" -> Registrations -> New registration -> "Open-Ended Registration".
3. Upload the protocol PDF, `config/models.yaml` (keys are not in it), and a text file containing the LOCK.json hashes.
4. Submit. Record the OSF URL in `protocol/README.md`.

---------------------------------------------------------------------------------------------------
## BLOCK 6. Phase 4: the runs (Section 10, 11, 15). Resumable; rerun the same command after any interruption.

Primary runs, both workflows, all models:
```
python -m harness.runner --split test --workflow C --run-id run1
python -m harness.runner --split test --workflow B --run-id run1
```
Repeat runs on the stratified subset (stability):
```
python -m harness.runner --split test --workflow C --run-id run2 --subset data/test/repeat_subset.txt
python -m harness.runner --split test --workflow C --run-id run3 --subset data/test/repeat_subset.txt
python -m harness.runner --split test --workflow B --run-id run2 --subset data/test/repeat_subset.txt
python -m harness.runner --split test --workflow B --run-id run3 --subset data/test/repeat_subset.txt
```
Notes:
- One model at a time: add `--model "<id>"` to any command.
- Gemini free tier is about 250 requests per day. Either enable billing on the Gemini key or run Gemini with
  `--sleep 2` across several days; the runner resumes where it stopped.
- Volume: roughly 500 test records x 2 workflows + 300 repeat calls per model. Budget: under 40 dollars per frontier model.
- Workflow A (rules baseline, Section 11) is time-boxed to two days. If you want it: `python -m harness.rules_baseline --split test`
  and score its output like any other raw file. If you skip it, note that in DEVIATIONS.md.

---------------------------------------------------------------------------------------------------
## BLOCK 7. Phase 5: score, analyze, code errors (Sections 12, 13, 16)

```
python -m scoring.score --raw results/raw_test_*.jsonl
python -m analysis.analyze --scored 'results/scored_test_*_run1.jsonl' | tee results/analysis_primary.txt
```
Stability, per model (replace MODEL with the id as it appears in the file names):
```
python -m analysis.stability --scored results/scored_test_C_MODEL_run1.jsonl results/scored_test_C_MODEL_run2.jsonl results/scored_test_C_MODEL_run3.jsonl | tee -a results/analysis_stability.txt
```
Manual error coding of residual errors (Section 13), blinded to model identity:
```
python -m tools.code_errors --scored 'results/scored_test_*_run1.jsonl'
```
It presents each uncoded error in random order without the model name; you type a class from the list; the codebook
is in `scoring/codebook.md`. After two weeks, re-code a 10 percent sample for intra-rater agreement:
```
python -m tools.code_errors --recode 0.10
```

---------------------------------------------------------------------------------------------------
## BLOCK 8. Package and hand off (Section 17)

```
python -m tools.export_results
```
This writes `results/export/` with: `summary.json` (every number the paper and the article will quote), the tables as
CSV, the run manifest (model ids, dates, settings, prompt hashes, cost), LOCK.json, DEVIATIONS.md, and a sanitized copy
of the configuration. Zip that folder and send it to me together with `results/analysis_primary.txt` and
`results/analysis_stability.txt`. I will write the results section of the paper, the replacement "Current Stage"
section for the article, and the fourth quote, and nothing else in either document changes.

Public release (after acceptance): create `VinodRufus/fields-to-dose-benchmark` the same way as the flagship repo
(private first, secret scan, then public). License: MIT for code, CC BY 4.0 for data (Section 17).

---------------------------------------------------------------------------------------------------
## Troubleshooting

- `refusing: test set is not locked` -> run BLOCK 4 to the end.
- `refusing: scoring code or prompts changed since lock` -> you edited a prompt or scorer after lock. Revert the edit,
  or record a deviation and re-lock with `rm data/test/LOCK.json && python -m tools.lock_testset` (the new hash must go
  into an OSF update).
- `refusing: evaluated model ... shares family with the generator` -> change the generator to a different family.
- A model returns prose instead of JSON -> the runner retries once with a repair message; persistent failures are
  scored as malformed and reported.
- Quota errors -> the runner stops and tells you; rerun the same command later.
