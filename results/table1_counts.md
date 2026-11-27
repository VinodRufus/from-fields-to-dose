## Table 1. Test-set characteristics (locked 3 October 2026; one record per scenario)

Lock digests: records 492d7ca22097..., scenarios 432be74fe65c..., repeat subset f1012bdcb01f...

| Characteristic | Non-abstention records | Abstention records | All records |
|---|---|---|---|
| Records | 304 | 57 | 361 |
| Neonate (0 to 27 days) | 13 | 3 | 16 |
| Infant (28 to 365 days) | 58 | 14 | 72 |
| Toddler and young child (366 to 2190 days) | 89 | 20 | 109 |
| School-age child (2191 to 4380 days) | 88 | 14 | 102 |
| Adolescent (4381 to 6574 days) | 56 | 6 | 62 |
| Complexity level 1 | 101 | 20 | 121 |
| Complexity level 2 | 100 | 20 | 120 |
| Complexity level 3 | 103 | 17 | 120 |
| Template-generated note | 189 | 57 | 246 |
| Paraphrased by qwen2.5:14b (audited) | 115 | 0 | 115 |
| Dosing basis mg/kg/day | 196 | 35 | 231 |
| Dosing basis mg/kg/dose | 89 | 17 | 106 |
| Dosing basis mcg/kg/day | 11 | 2 | 13 |
| Dosing basis mcg/kg/dose | 8 | 3 | 11 |
| In the 108-record repeat subset (runs 2 and 3) | 91 | 17 | 108 |

Abstention cases by missing element:
- conflict only: 5
- current_weight_value: 25
- frequency_per_day: 27
- with a weight conflict flagged: 5

Challenge tags over all 361 scenarios (a scenario can carry several):
- concentration_volume: 353
- per_day_basis: 244
- multiple_meds: 240
- dose_cap: 188
- multiple_weights: 120
- lb_documentation: 57
- discontinued_same_drug: 57
- derive_per_dose: 44
- weight_tail: 30
- missing:frequency_per_day: 27
- missing:current_weight_value: 25
- mcg_drug: 24
- conflict:weight: 5
- birth_weight: 4

Drugs represented (20) with record counts:
acetaminophen 10, amoxicillin 18, amoxicillin-clavulanate 17, ampicillin 24, azithromycin 22, cefdinir 17, ceftriaxone 24, cephalexin 16, clindamycin 26, dexamethasone 29, digoxin 5, famotidine 17, fentanyl 11, fluconazole 18, gentamicin 48, ibuprofen 4, levothyroxine 8, midazolam 8, ondansetron 21, prednisolone 18

Distinct drugs: 20. Scenarios with a maximum in the order: 188.

## Figure 1 flow counts

- Scenarios generated and locked: 361 (one record each; 304 non-abstention, 57 abstention)
- Repeat subset: 108 records
- Scored files: 30 (10 model-workflow cells, runs ['run1', 'run2', 'run3'])
  - gpt-5.5-2026-04-23 B: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - gpt-5.5-2026-04-23 C: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - claude-sonnet-5 B: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - claude-sonnet-5 C: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - gemini-3.1-pro-preview B: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - gemini-3.1-pro-preview C: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - deepseek-v4-pro B: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 1 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - deepseek-v4-pro C: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - llama3.1:8b B: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
  - llama3.1:8b C: run1: 361 records (304 non-abstention), 0 malformed; run2: 108 records (91 non-abstention), 0 malformed; run3: 108 records (91 non-abstention), 0 malformed
- Total scored outputs: 5770 (4860 non-abstention; 1 malformed, all in repeat runs)
- Run 1 non-abstention outputs entering the primary analysis: 3040 (10 cells x 304)
