# From Fields to Dose

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23448179.svg)](https://doi.org/10.5281/zenodo.23448179)

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
runner), scoring/ (four-level scorer, codebook), analysis/ (registered analysis and additions outside the lock), tools/
(audits, tables and the figure scripts in tools/figures/), tests/, data/test/ (locked split), data/dev/ (development
split and its realism audit), protocol/ (Protocol v1.0, lock hashes, deviations log), results/ (raw and scored outputs,
analysis outputs, manual coding, supplementary tables, evidence packet), docs/ (official documents and figures).

## Reproduce the headline tables

```
python -m scoring.score --raw 'results/raw_test_*.jsonl'
python -m analysis.analyze --scored 'results/scored_test_*_run1.jsonl'
python -m analysis.pairwise --scored 'results/scored_test_*_run1.jsonl'
python -m analysis.sensitivity_text_rule
python -m tools.admin_amount --scored 'results/scored_test_*_run1.jsonl'
python -m tools.by_stratum --scored 'results/scored_test_*_run1.jsonl'
python -m tools.max_check
python -m tools.h4_classes
python -m tools.rounding_audit
python -m tools.run_times
python -m tools.packet_rows
```

The nine manuscript figures are drawn from the committed files by the scripts in tools/figures/ (PNG, PDF and SVG in
docs/figures/, plus an editable PowerPoint from tools/figures/build_pptx.py).

No provider keys are needed to score or analyse; keys are needed only to re-run models (see SETUP_GUIDE.md).

## Status

All five registered models have complete results (first runs on 361 records and three runs on the 108-record repeat subset).
The unassisted manual error coding (results/manual_codes.jsonl) and its re-coding check (results/manual_codes_recode.jsonl)
are complete and summarised in results/h4_classes.txt. Release v1.0.3 adds, relative to v1.0.2: the manual coding and
re-code files; the Level 3 rule sensitivity (analysis/sensitivity_text_rule.py); the H4 class, rounding-audit, run-time
and Table 1 scripts with their outputs; the rebuilt row-level evidence packet (Gemini 3.1 Pro scored rows filled, fifth
maximum-dose note added); the figure scripts and figures; and the deviations rows of 14 to 26 November 2026. The
documents in docs/ are the v1.0.2 versions and describe the coding as pending; the manuscript supersedes them.

## Licences

Code: MIT (LICENSE). Synthetic data, protocol, outputs and documents: CC BY 4.0 (LICENSE-DATA). Cite with CITATION.cff.

## Archival release

This repository is archived on Zenodo. Concept DOI for all versions: https://doi.org/10.5281/zenodo.23448179.
Version DOI for release v1.0.2: https://doi.org/10.5281/zenodo.23448180. Version DOI for release v1.0.3: see the Zenodo
record linked from the concept DOI. Pre-registration DOI (OSF): 10.17605/OSF.IO/3P9EY.
