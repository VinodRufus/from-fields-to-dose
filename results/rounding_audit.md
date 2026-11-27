## Rounding audit of the printed per-dose amount (tools/rounding_audit.py)

Scenarios with a printed amount: 304 (304 non-abstention, 0 abstention cases whose missing element is not needed for the amount).

### Non-abstention scenarios (304)

- Printed amount more than 1 percent from the exact product: 56; more than 10 percent: 1.
- Exact product more than 1 percent from the printed amount (fails Level 2 if written): 55; more than 10 percent: 1.
- Of those more than 1 percent (printed vs exact): by dose unit {'mg': 53, 'mcg': 3}; by complexity {1: 18, 2: 17, 3: 21}.

### All scenarios with a printed amount

- Printed amount more than 1 percent from the exact product: 56; more than 10 percent: 1.
- Exact product more than 1 percent from the printed amount (fails Level 2 if written): 55; more than 10 percent: 1.
- Of those more than 1 percent (printed vs exact): by dose unit {'mg': 53, 'mcg': 3}; by complexity {1: 18, 2: 17, 3: 21}.

### Records where the printed amount is more than 1 percent from the exact product (non-abstention)

| Scenario | Level | Drug | Printed mg | Exact mg | Printed vs exact | Exact vs printed |
|---|---|---|---|---|---|---|
| test-dexamethasone-mg_kg_day-neonate-L1-v0 | 1 | dexamethasone | 0.02 | 0.0226 | 0.115 | 0.130 |
| test-dexamethasone-mg_kg_day-infant-L1-v0 | 1 | dexamethasone | 0.06 | 0.057133 | 0.050 | 0.048 |
| test-dexamethasone-mg_kg_day-toddler-L2-v1 | 2 | dexamethasone | 0.13 | 0.125333 | 0.037 | 0.036 |
| test-ondansetron-mg_kg_dose-infant-L1-v1 | 1 | ondansetron | 1.1 | 1.14 | 0.035 | 0.036 |
| test-ondansetron-mg_kg_dose-adolescent-L2-v0 | 2 | ondansetron | 12.0 | 11.64 | 0.031 | 0.030 |
| test-gentamicin-mg_kg_dose-infant-L1-v0 | 1 | gentamicin | 16.0 | 15.525 | 0.031 | 0.030 |
| test-prednisolone-mg_kg_day-school_age-L2-v1 | 2 | prednisolone | 16.0 | 16.5 | 0.030 | 0.031 |
| test-dexamethasone-mg_kg_day-neonate-L3-v0 | 3 | dexamethasone | 0.09 | 0.0928 | 0.030 | 0.031 |
| test-gentamicin-mg_kg_dose-infant-L1-v1 | 1 | gentamicin | 15.0 | 14.58 | 0.029 | 0.028 |
| test-dexamethasone-mg_kg_day-toddler-L1-v1 | 1 | dexamethasone | 1.6 | 1.64267 | 0.026 | 0.027 |
| test-prednisolone-mg_kg_day-toddler-L2-v1 | 2 | prednisolone | 12.0 | 11.7 | 0.026 | 0.025 |
| test-famotidine-mg_kg_dose-toddler-L3-v0 | 3 | famotidine | 12.0 | 11.7027 | 0.025 | 0.025 |
| test-gentamicin-mg_kg_dose-infant-L2-v0 | 2 | gentamicin | 12.0 | 12.3 | 0.024 | 0.025 |
| test-dexamethasone-mg_kg_day-toddler-L2-v0 | 2 | dexamethasone | 0.08 | 0.082 | 0.024 | 0.025 |
| test-gentamicin-mg_kg_dose-infant-L2-v1 | 2 | gentamicin | 19.0 | 18.55 | 0.024 | 0.024 |
| test-gentamicin-mg_kg_day-infant-L3-v0 | 3 | gentamicin | 19.0 | 19.4567 | 0.023 | 0.024 |
| test-clindamycin-mg_kg_day-neonate-L2-v1 | 2 | clindamycin | 10.0 | 10.24 | 0.023 | 0.024 |
| test-dexamethasone-mg_kg_day-school_age-L1-v0 | 1 | dexamethasone | 0.14 | 0.143333 | 0.023 | 0.024 |
| test-famotidine-mg_kg_dose-school_age-L2-v0 | 2 | famotidine | 17.0 | 17.4 | 0.023 | 0.024 |
| test-gentamicin-mg_kg_day-infant-L1-v1 | 1 | gentamicin | 21.0 | 20.5333 | 0.023 | 0.022 |
| test-famotidine-mg_kg_dose-school_age-L1-v0 | 1 | famotidine | 16.0 | 15.65 | 0.022 | 0.022 |
| test-prednisolone-mg_kg_day-school_age-L3-v0 | 3 | prednisolone | 21.0 | 20.5477 | 0.022 | 0.022 |
| test-prednisolone-mg_kg_day-adolescent-L1-v0 | 1 | prednisolone | 24.0 | 23.5 | 0.021 | 0.021 |
| test-famotidine-mg_kg_dose-adolescent-L2-v0 | 2 | famotidine | 22.0 | 21.55 | 0.021 | 0.020 |
| test-clindamycin-mg_kg_day-infant-L1-v0 | 1 | clindamycin | 22.0 | 22.44 | 0.020 | 0.020 |
| test-gentamicin-mg_kg_day-toddler-L3-v0 | 3 | gentamicin | 24.0 | 24.4486 | 0.018 | 0.019 |
| test-ondansetron-mg_kg_dose-adolescent-L1-v0 | 1 | ondansetron | 11.0 | 11.205 | 0.018 | 0.019 |
| test-ondansetron-mg_kg_dose-infant-L3-v0 | 3 | ondansetron | 1.6 | 1.5717 | 0.018 | 0.018 |
| test-gentamicin-mg_kg_day-infant-L2-v1 | 2 | gentamicin | 14.0 | 14.24 | 0.017 | 0.017 |
| test-ondansetron-mg_kg_dose-toddler-L3-v1 | 3 | ondansetron | 1.9 | 1.9323 | 0.017 | 0.017 |
| test-gentamicin-mg_kg_day-infant-L2-v0 | 2 | gentamicin | 21.0 | 20.675 | 0.016 | 0.015 |
| test-clindamycin-mg_kg_day-neonate-L3-v0 | 3 | clindamycin | 14.0 | 14.2201 | 0.015 | 0.016 |
| test-clindamycin-mg_kg_day-infant-L3-v1 | 3 | clindamycin | 22.0 | 21.6704 | 0.015 | 0.015 |
| test-gentamicin-mg_kg_day-toddler-L1-v1 | 1 | gentamicin | 27.0 | 26.6 | 0.015 | 0.015 |
| test-gentamicin-mg_kg_dose-toddler-L3-v1 | 3 | gentamicin | 27.0 | 27.4 | 0.015 | 0.015 |
| test-dexamethasone-mg_kg_day-school_age-L2-v0 | 2 | dexamethasone | 3.0 | 3.04333 | 0.014 | 0.014 |
| test-gentamicin-mg_kg_day-toddler-L3-v1 | 3 | gentamicin | 31.0 | 30.5667 | 0.014 | 0.014 |
| test-fentanyl-mcg_kg_dose-toddler-L3-v1 | 3 | fentanyl | 0.028 | 0.0284 | 0.014 | 0.014 |
| test-gentamicin-mg_kg_dose-toddler-L3-v0 | 3 | gentamicin | 33.0 | 32.5453 | 0.014 | 0.014 |
| test-dexamethasone-mg_kg_day-adolescent-L1-v0 | 1 | dexamethasone | 3.0 | 3.0415 | 0.014 | 0.014 |
| test-dexamethasone-mg_kg_day-infant-L3-v1 | 3 | dexamethasone | 0.3 | 0.296045 | 0.013 | 0.013 |
| test-ondansetron-mg_kg_dose-infant-L3-v1 | 3 | ondansetron | 1.5 | 1.4805 | 0.013 | 0.013 |
| test-dexamethasone-mg_kg_day-infant-L2-v1 | 2 | dexamethasone | 0.21 | 0.2073 | 0.013 | 0.013 |
| test-dexamethasone-mg_kg_day-neonate-L1-v1 | 1 | dexamethasone | 0.27 | 0.273533 | 0.013 | 0.013 |
| test-famotidine-mg_kg_dose-school_age-L1-v1 | 1 | famotidine | 23.0 | 23.3 | 0.013 | 0.013 |
| test-dexamethasone-mg_kg_day-adolescent-L3-v1 | 3 | dexamethasone | 2.8 | 2.76467 | 0.013 | 0.013 |
| test-levothyroxine-mcg_kg_day-neonate-L3-v0 | 3 | levothyroxine | 0.04 | 0.0405 | 0.012 | 0.013 |
| test-ondansetron-mg_kg_dose-school_age-L1-v1 | 1 | ondansetron | 3.4 | 3.36 | 0.012 | 0.012 |
| test-fentanyl-mcg_kg_dose-toddler-L3-v0 | 3 | fentanyl | 0.044 | 0.0435 | 0.011 | 0.011 |
| test-ondansetron-mg_kg_dose-toddler-L1-v0 | 1 | ondansetron | 4.3 | 4.35 | 0.011 | 0.012 |
| test-dexamethasone-mg_kg_day-adolescent-L2-v1 | 2 | dexamethasone | 2.1 | 2.124 | 0.011 | 0.011 |
| test-clindamycin-mg_kg_day-infant-L2-v1 | 2 | clindamycin | 41.0 | 40.5533 | 0.011 | 0.011 |
| test-ondansetron-mg_kg_dose-school_age-L3-v1 | 3 | ondansetron | 2.7 | 2.73 | 0.011 | 0.011 |
| test-ondansetron-mg_kg_dose-school_age-L3-v0 | 3 | ondansetron | 3.8 | 3.84 | 0.010 | 0.011 |
| test-dexamethasone-mg_kg_day-infant-L3-v0 | 3 | dexamethasone | 0.4 | 0.404151 | 0.010 | 0.010 |
| test-dexamethasone-mg_kg_day-neonate-L2-v0 | 2 | dexamethasone | 0.02 | 0.0198 | 0.010 | 0.010 |
