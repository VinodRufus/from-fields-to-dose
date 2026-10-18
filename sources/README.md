# Sources

## dosing_sources.csv (you fill this; one row per drug x dose pattern)
Columns:
drug, rxnorm_ingredient, indication, route, formulation, concentration_mg_per_ml,
dose_basis (mg/kg/dose|mg/kg/day|mcg/kg/dose|mcg/kg/day), dose_min, dose_max,
frequency_per_day_options (e.g. "2|3|4"), max_per_dose_mg, max_per_day_mg,
age_min_days, age_max_days, source_type (FDA_label|WHO|open_formulary),
source_id (DailyMed set id / document id), source_version, retrieval_date,
notes, verified (true|false)

`dosing_sources.example.csv` contains DEMO rows with `verified=false`. They exist
only so the smoke test runs. Replace with verified rows before building the test set.

## CDC / WHO growth references (download; check license before committing)
- `wtageinf.csv`  weight-for-age, birth to 36 months (CDC LMS file)
- `wtage.csv`     weight-for-age, 2 to 20 years (CDC LMS file)
Columns expected: Sex (1=male, 2=female), Agemos, L, M, S.
Verify the current CDC download path before use (it was reorganized in 2024-25).

## age_bands.json
NICHD pediatric terminology bands. Marked [verify]; confirm boundaries and the
citation before registration.
