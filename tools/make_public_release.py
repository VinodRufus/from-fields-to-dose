"""Build the public release directory from the working repository (allow-list copy; see System Architecture, Section 7).

Copies only listed paths into ../from-fields-to-dose-public (fresh directory, no git history), writes README, licences and
CITATION.cff, runs a secret pattern scan, and prints a summary. It never touches the working repository.

Usage (from the working repository root): python -m tools.make_public_release [--out ../from-fields-to-dose-public]
"""
import argparse, fnmatch, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOW_DIRS = ["config", "sources", "generator", "harness", "scoring", "analysis", "tools", "tests", "data/test", "data/dev", "protocol", "docs", "results/packet", "results/export"]
ALLOW_FILES = ["SETUP_GUIDE.md", "README.md", "requirements.txt", "pyproject.toml", ".gitignore"]
RESULT_GLOBS = ["raw_test_*.jsonl", "scored_test_*.jsonl", "*.csv", "analysis_*.txt", "per_drug_run1.txt", "admin_amount_run1.txt", "by_stratum_run1.txt", "manual_codes*.jsonl", "h4_classes.txt", "rounding_audit.md", "run_times.md", "table1_counts.md"]
# Files cited in the paper that the exclusion patterns would otherwise drop (a record-id list and a 15-line diff; no secrets).
ALLOW_EXTRA = ["data/test/removals.log", "results/logs/analyze_malformed_as_failure.diff"]
EXCLUDE_ANY = ["__pycache__", ".DS_Store", ".env", ".venv", "archive", "logs", "backup", "*.pyc", "*.log", "secret*"]
SECRET_PATTERNS = [r"sk-[A-Za-z0-9_\-]{16,}", r"sk-ant-[A-Za-z0-9_\-]{16,}", r"AIza[0-9A-Za-z_\-]{30,}", r"xai-[A-Za-z0-9]{16,}", r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}", r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"]

README = """# From Fields to Dose

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
"""

LICENSE_MIT = """MIT License

Copyright (c) 2026 Vinod Rufus Motani

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

LICENSE_DATA = """The synthetic data (data/), the protocol (protocol/), the model outputs and analysis outputs (results/) and the
documents and figures (docs/) in this repository are licensed under the Creative Commons Attribution 4.0 International
License (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/

Attribution: Vinod Rufus Motani, From Fields to Dose: Evaluating Large Language Models for Weight-Based Pediatric
Medication Extraction and Dosing Consistency. Registration DOI 10.17605/OSF.IO/3P9EY. ORCID 0009-0005-3459-0859.

The synthetic records contain no real patient data. FDA label excerpts in sources/labels are public-domain US government
works; WHO and CDC growth reference tables are redistributed under their own terms.
"""

CITATION = """cff-version: 1.2.0
message: "If you use this benchmark, its data or its code, please cite it as below."
title: "From Fields to Dose: Evaluating Large Language Models for Weight-Based Pediatric Medication Extraction and Dosing Consistency"
authors:
  - family-names: Motani
    given-names: Vinod Rufus
    orcid: "https://orcid.org/0009-0005-3459-0859"
doi: "10.5281/zenodo.23448179"
version: "1.0.3"
identifiers:
  - type: doi
    value: 10.5281/zenodo.23448179
    description: "Zenodo concept DOI, resolving to the latest archived release"
  - type: doi
    value: 10.5281/zenodo.23448180
    description: "Zenodo archive of release v1.0.2"
  - type: doi
    value: 10.17605/OSF.IO/3P9EY
    description: "Pre-registration on the Open Science Framework"
repository-code: "https://github.com/VinodRufus/from-fields-to-dose"
license: MIT
type: software
"""


def excluded(path):
    parts = path.replace("\\", "/").split("/")
    return any(fnmatch.fnmatch(p, pat) for p in parts for pat in EXCLUDE_ANY)


def copy_tree(src, dst):
    n = 0
    for dp, dns, fns in os.walk(src):
        rel = os.path.relpath(dp, ROOT)
        if excluded(rel):
            dns[:] = []
            continue
        dns[:] = [d for d in dns if not excluded(os.path.join(rel, d))]
        for fn in fns:
            rp = os.path.join(rel, fn)
            if excluded(rp):
                continue
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            shutil.copy2(os.path.join(dp, fn), os.path.join(dst, rp)); n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "..", "from-fields-to-dose-public"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    total = 0
    for d in ALLOW_DIRS:
        src = os.path.join(ROOT, d)
        if os.path.isdir(src):
            total += copy_tree(src, out)
    for f in ALLOW_FILES:
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(out, f)); total += 1
    for f in ALLOW_EXTRA:
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(out, f)), exist_ok=True)
            shutil.copy2(src, os.path.join(out, f)); total += 1
        else:
            print(f"WARNING: cited file not found in the working repository: {f}")
    rdir = os.path.join(ROOT, "results")
    os.makedirs(os.path.join(out, "results"), exist_ok=True)
    for fn in sorted(os.listdir(rdir)):
        p = os.path.join(rdir, fn)
        if os.path.isfile(p) and any(fnmatch.fnmatch(fn, g) for g in RESULT_GLOBS) and not excluded(fn):
            shutil.copy2(p, os.path.join(out, "results", fn)); total += 1
    open(os.path.join(out, "README.md"), "w").write(README)
    open(os.path.join(out, "LICENSE"), "w").write(LICENSE_MIT)
    open(os.path.join(out, "LICENSE-DATA"), "w").write(LICENSE_DATA)
    open(os.path.join(out, "CITATION.cff"), "w").write(CITATION)
    open(os.path.join(out, ".gitignore"), "w").write(".env\n.venv/\n__pycache__/\n*.pyc\n.DS_Store\n")
    total += 5
    # secret scan over the release directory
    hits = []
    for dp, dns, fns in os.walk(out):
        for fn in fns:
            p = os.path.join(dp, fn)
            if fn.endswith((".png", ".pdf", ".docx", ".zip")):
                continue
            try:
                txt = open(p, "r", errors="ignore").read()
            except Exception:
                continue
            for pat in SECRET_PATTERNS:
                for m in re.finditer(pat, txt):
                    hits.append((os.path.relpath(p, out), m.group(0)[:12] + "..."))
    print(f"release directory: {out}\nfiles copied: {total}")
    if hits:
        print("SECRET SCAN: possible secrets found, do not push:")
        for h in hits[:40]:
            print("  ", h)
        sys.exit(2)
    print("secret scan: clean")


if __name__ == "__main__":
    main()
