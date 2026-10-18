# Error codebook (Protocol Section 13)

Automatic classes (assigned by scoring/score.py from output vs canonical): weight_selection, weight_unit, unit_scale,
dose_basis, frequency, route, strength_vs_dose, dose_cap, adult_fixed_dose_assumption, unsupported_value_hallucination,
conflict_resolved_without_flag, arithmetic_inconsistency, malformed_output, extraction:* (value wrong, no finer class).

Manual classes for residual `extraction:*` errors (one per error; choose the earliest failing stage):
- E1 extraction: a value present in the note was copied wrongly or omitted.
- E2 normalization: the right value was found but represented wrongly (unit string, abbreviation, decimal).
- E3 association: a correct value was attached to the wrong medication, order, or weight.
- E4 temporal: a discontinued or historical value was treated as current.
- E5 volume_vs_dose: administration volume confused with medication amount.
- E6 other: anything else; write one line.

Procedure: errors are presented in random order without the model name. Code from the note and the output only.
Do not look up which model produced it. After two weeks, re-code a 10 percent sample; report agreement.
