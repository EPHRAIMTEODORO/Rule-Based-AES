# Research results and documentation verification

Audit date: October 19, 2026, Pacific/Honolulu. This report evaluates saved
predictions and inspects source behavior. It does not report a new Llama scoring
run, clean-machine installer test, or human-subject study.

## 1. Provenance of the reproduced experiment

Input artifact:
`hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv`

SHA-256:
`a0a73435708bb4dfeaed90b5d424bc2b9e2929ce22c4168ec839e0a6623216d8`

The file has **41 scored essays**, no duplicate texts under whitespace/case
normalization, and historical half-point LLM grades. Its human reference column
is `score`. This audit cannot establish the exact generation-time prompt,
model digest, runtime configuration, anchor selection process, or rater protocol
from that CSV alone. The present HITL source requests and normalizes integer
grades; do not label these saved metrics as newly measured 0.1.3 performance.

| Human reference score | Essay count |
| --- | ---: |
| 1 | 1 |
| 2 | 1 |
| 2.5 | 3 |
| 3 | 5 |
| 3.5 | 6 |
| 4 | 5 |
| 4.5 | 5 |
| 5 | 5 |
| 5.5 | 5 |
| 6 | 5 |

| Prompt/topic | Essay count |
| --- | ---: |
| Reducing Stress | 29 |
| University Living | 6 |
| Mandatory Attendance | 4 |
| Study Abroad | 1 |
| Technology | 1 |

Reducing Stress represents about 71% of the sample. A random essay split
therefore measures a different question from generalization to a new prompt.

None of the current HITL Level 4/5/6 anchors exactly matches a text in this CSV
after whitespace/case normalization. This narrow check does not rule out
near-duplicates, data reuse during prompt development, or other leakage.

## 2. Reproduced direct-prediction metrics

Command, from the repository root:

```powershell
.venv/Scripts/python.exe "hybrid LLM AES/evaluate_hybrid_results.py" --input "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" --score-column score --prediction aes_score:aes-0-100 --prediction llm_recommended_score
```

| Prediction | n | Pearson r | MAE | Agreement within 0.25 | Agreement within 0.5 | QWK |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Manual AES, scaled to 1–6 | 41 | 0.52226 | 1.03878 | 0.21951 | 0.31707 | 0.24673 |
| Historical LLM recommendation | 41 | 0.77802 | 0.57317 | 0.34146 | 0.68293 | 0.73558 |

The AES scale conversion is `1 + (aes_score / 100) × 5`.

Metric interpretation:

- **Pearson r:** linear association between predictions and human scores.
  Higher is better, but it is not percentage accuracy.
- **MAE:** mean absolute grade-point error. Lower is better.
- **“Exact agreement” in this script:** absolute difference ≤0.25, calculated
  on unrounded predictions. This is not literal equality for a continuous model.
- **“Adjacent agreement” in this script:** difference ≤0.5. Do not describe it
  as the common “within one whole grade” convention.
- **QWK in the historical script:** labels from 1 to 6 in half-point steps;
  predictions and references are rounded to half points using Python `round`.
  Larger disagreements receive quadratic penalties.

The LLM has lower absolute error and stronger association/agreement than the
manual baseline on this saved sample. This is a preliminary artifact-based
comparison, not proof of general validity or superiority on independent data.

## 3. Holdout and repeated cross-validation

Command:

```powershell
.venv/Scripts/python.exe "hybrid LLM AES/validate_hybrid_model.py" --input "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" --score-column score --prompt-column prompt_id --folds 5 --repeats 20
```

Defaults: seed 42, test fraction 0.25, Ridge alpha 10. Missing features are
imputed with training means; standardization is fitted on training data.
Models are trained within each split/fold and predictions clipped to 1–6.
Feature-column availability is selected across the loaded dataset; there is no
nested hyperparameter search. The script uses standard-library linear algebra.

### Single 10-essay holdout

| System | Pearson r | MAE | QWK |
| --- | ---: | ---: | ---: |
| Manual AES scaled | 0.18338 | 1.07120 | 0.07455 |
| Direct LLM | 0.87346 | 0.35000 | 0.81481 |
| Ridge: AES features | 0.88366 | 0.49339 | 0.77855 |
| Ridge: LLM traits | 0.89017 | 0.48222 | 0.71698 |
| Ridge: AES + LLM score | 0.92378 | 0.41091 | 0.84848 |
| Ridge: AES + LLM traits | 0.90929 | 0.41785 | 0.84848 |

A single ten-essay test set is too small to treat as a stable estimate. Report
it separately from full-sample or repeated-CV results.

### Mean metrics over twenty repeated five-fold evaluations

| System | Reported n | Pearson r | MAE | QWK |
| --- | ---: | ---: | ---: | ---: |
| Manual AES scaled | 820 | 0.52226 | 1.03878 | 0.24673 |
| Direct LLM | 820 | 0.77802 | 0.57317 | 0.73558 |
| Ridge: AES features | 820 | 0.73388 | 0.61977 | 0.69401 |
| Ridge: LLM traits | 820 | 0.76396 | 0.64398 | 0.72829 |
| Ridge: AES + LLM score | 820 | 0.76473 | 0.60533 | 0.73273 |
| Ridge: AES + LLM traits | 820 | 0.76503 | 0.61700 | 0.74476 |

Each repetition pools out-of-fold predictions for all 41 rows, computes
metrics, and contributes to the average. `820 = 41 × 20` counts repeated
prediction appearances; there are still **41 unique essay records**, and
independence by writer has not been established. Direct
scores are not retrained, so their repeated metrics remain their full-sample
metrics. They are not new independent model evaluations on each repetition.

The full-feature Ridge hybrid's QWK exceeds direct LLM QWK by about **0.00918**,
but its MAE is worse by **0.04383**, and its correlation is lower. The script
does not provide confidence intervals or significance tests; do not claim a
reliable across-metric improvement.

Prompt-grouped validation is available via `--group-column prompt_id`. The
five highly imbalanced prompt groups, including two singleton groups, limit
interpretation. Grouped validation is a useful sensitivity analysis, not a
remedy for the small sample or for unknown generation-time leakage.

## 4. Evaluation-script differences that change QWK

The repository contains two different metric implementations:

| Script | QWK rounding and labels | AES QWK on the same CSV | LLM QWK |
| --- | --- | ---: | ---: |
| `hybrid LLM AES/evaluate_hybrid_results.py` | Half-point rounding; 0.5 labels | 0.24673 | 0.73558 |
| `HITL/evaluate_hybrid_results.py` | Half-up integer rounding; 1.0 labels | 0.32418 | 0.73535 |

Both produce the same displayed r, MAE, and tolerance-agreement values here,
because those calculations still use the original unrounded CSV values. The
HITL evaluation command does not simulate the complete current desktop
normalization path; only its QWK rounding differs in this comparison.

For a paper or presentation, name the evaluator and rounding convention. For
new experiments, settle a single scoring/rounding policy before comparing
systems, including how half-point human references relate to whole-grade
placement. Do not silently mix QWK values from the two scripts.

## 5. Different dataset sizes in this repository

Counts below are nonblank data rows, not worksheet `max_row` values:

| File | Nonblank data rows | Scope |
| --- | ---: | --- |
| Historical hybrid results CSV | 41 | Reproduced scoring/validation metrics |
| `HITL/Essays.xlsx` | 10 | Packaged sample, headers `id`, `Topic`, `Essay` |
| `Essays_V2.xlsx` | 10 | Default-header upload sample; worksheet dimensions include many empty rows |
| `NewAes/ELAT_DATA/essays.xlsx` | 443 | Separate research input workbook |
| `NewAes/ELAT_DATA/full_sample_aes_features_with_grammar_llm_improved.xlsx` | 443 | Separate five-trait batch output workbook |

The sample API processes only the first essay of its ten-row workbook. The
larger batch workbook's presence is not evidence that the 41-essay metrics
apply to 443 essays, or that every output in the larger workbook is valid.

## 6. Verification completed for this documentation

1. Read the current desktop launcher, renderer, API, job backend, workbook
   processor, feature extractor, rubric prompt, packaging configuration, and
   research evaluator/validator.
2. Recomputed historical direct metrics, the default holdout, and repeated
   five-fold validation. Results reproduce the earlier recorded metrics.
3. Ran the HITL evaluator on the same CSV and verified the QWK convention
   difference shown above.
4. Counted actual nonblank workbook rows and confirmed the AWL JSON contains
   3,111 unique forms.
5. Ran the existing regression suites in the repository virtual environment:

```powershell
.venv/Scripts/python.exe -m unittest test_aes_feature_extractor HITL.test_human_decision_workflow HITL.test_runtime_recovery -v
```

Result: **37 tests passed**. They cover grammar fallback/output handling,
missing-component score normalization, pending decisions, integer grades,
model interruption budgets, runtime ownership, API diagnostics, and error/progress
handling. Model calls in the recovery suite are mocked. These tests do not
measure real LLM accuracy, full renderer behavior, or clean-machine packaging.

The initial test attempt with the system Python failed because that interpreter
lacked `language_tool_python` and `openpyxl`. The existing `.venv` supplied the
dependencies and completed the tests. No dependency installation was needed.

Recorded local environment:

| Package/runtime | Version inspected |
| --- | --- |
| System Python | 3.12.10 |
| spaCy in `.venv` | 3.8.14 |
| `en_core_web_sm` | 3.8.0 |
| wordfreq | 3.1.1 |
| lexical-diversity | 0.1.1 |
| language-tool-python | 3.4.0 |
| NLTK | 3.9.4 |
| openpyxl | 3.1.5 |
| setuptools | 80.10.2 |
| Electron in package lockfile | 32.3.3 |
| electron-builder in package lockfile | 25.1.8 |

This is a partial environment record for the documentation audit, not a full
reconstruction of the environment that generated the historical predictions.

## 7. A stronger validation study

Before making a deployment-accuracy claim:

1. Freeze source commit, model digest/quantization, Ollama version, prompt and
   anchor hashes, context/generation settings, dependencies, and hardware.
2. Establish trained independent human raters, inter-rater agreement,
   adjudication, and a clearly defined target grade/placement policy.
3. Use a larger independent dataset; separate anchors, prompt-development data,
   calibration/training rows, and final test rows. Group by writer if writers
   contribute multiple essays, and test new-prompt generalization.
4. Regenerate current whole-grade predictions with valid full task prompts and
   paragraph formatting. Track missing features, model/schema failures, and
   repeated-run stability.
5. Report r, MAE, grade confusion matrices, clearly defined exact/within-one
   agreement, one specified QWK convention, and placement-category errors.
6. Compare a majority/mean baseline, manual AES, direct LLM, feature-only
   learned models, learned hybrid models, and the final human-assisted process.
7. Add essay-level uncertainty intervals and paired comparisons. Repeated CV
   appearances must not be treated as independent observations.
8. Measure human-only versus assisted review: final agreement with independent
   reference ratings, time per essay, overrides, mismatch usefulness, subgroup
   performance, and anchoring effects.

The historical artifact supports preliminary evidence for useful LLM rubric
judgments. It does not yet establish educational validity, fairness, or the
incremental benefit of human assistance.
