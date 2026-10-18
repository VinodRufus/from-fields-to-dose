# From Fields to Dose

Evaluating Large Language Models for Weight-Based Pediatric Medication Extraction and Dosing Consistency.

A pre-registered, solo, synthetic-data benchmark. Author record: https://orcid.org/0009-0005-3459-0859.
Registration: https://osf.io/3p9ey (DOI 10.17605/OSF.IO/3P9EY). Project: https://osf.io/uajs3.

## Verification chain

1. The test set and the scoring code were hashed before any evaluated model saw a test record: data/test/LOCK.json carries
   SHA-256 of records.jsonl, scenarios.jsonl and repeat_subset.txt, and a combined hash over scoring/score.py,
   generator/calculator.py, the three prompt files, harness/output_schema.json and analysis/analyze.py
   (tools/lock_testset.py, function hash_scoring). The same hashes are in protocol/LOCK_hashes.txt and in the registration.
2. Recompute: `shasum -a 256 data/test/records.jsonl data/test/scenarios.jsonl data/test/repeat_subset.txt` and
   `python3 -c "from tools.lock_testset import hash_scoring; print(hash_scoring())"`.
3. Every change after registration is a dated row in protocol/DEVIATIONS.md.
4. Every number in the documents comes from a committed script run on committed files; results/packet holds the
   row-level evidence behind each headline count.

## Layout

config/ (model identifiers; environment-variable names only), sources/ (dosing table from FDA labels, growth references,
age bands), generator/ (synthetic record generation and the deterministic calculator), harness/ (prompts, output schema,
runner), scoring/ (four-level scorer, codebook), analysis/ (registered analysis and additions outside the lock), tools/,
tests/, data/test/ (locked split), data/dev/ (development split), protocol/ (Protocol v1.0, lock hashes, deviations log),
results/ (raw and scored outputs, analysis outputs, supplementary tables, evidence packet), docs/ (official documents and figures).

## Reproduce the headline tables

```
python -m scoring.score --raw 'results/raw_test_*.jsonl'
python -m analysis.analyze --scored 'results/scored_test_*_run1.jsonl'
python -m analysis.pairwise --scored 'results/scored_test_*_run1.jsonl'
python -m tools.admin_amount --scored 'results/scored_test_*_run1.jsonl'
python -m tools.by_stratum --scored 'results/scored_test_*_run1.jsonl'
python -m tools.max_check
```

No provider keys are needed to score or analyse; keys are needed only to re-run models (see SETUP_GUIDE.md).

## Status

All five registered models have complete results (first runs on 361 records and three runs on the 108-record repeat subset).
Unassisted manual error coding, the re-coding check and the TRIPOD-LLM checklist are pending and are stated as pending in docs/.

## Licences

Code: MIT (LICENSE). Synthetic data, protocol, outputs and documents: CC BY 4.0 (LICENSE-DATA). Cite with CITATION.cff.
