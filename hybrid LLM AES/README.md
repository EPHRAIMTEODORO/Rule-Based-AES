# Hybrid LLM AES

This folder contains a hybrid Automated Essay Scoring approach that combines the
existing rule-based AES feature extractor with local Llama 3 rubric judgments.

The original `aes_feature_extractor.py` is not modified. The hybrid script
imports it, adds LLM-based rubric features, and writes a new CSV with both sets
of columns.

## Design Goal

The current rule-based AES script captures measurable language features, but it
cannot reliably judge semantic and discourse-level qualities such as whether an
essay is clearly organized, fully developed, relevant to the prompt, or easily
understood by a native reader.

The hybrid design separates the work:

```text
Rule-based code: observable linguistic features
LLM: rubric judgments requiring semantic interpretation
Hybrid model: later calibration against human rater scores
```

## Handled By Code

The existing rule-based extractor handles features that can be measured
directly and transparently:

- `word_count`
- `sentence_count`
- `mean_sentence_length`
- `avg_word_freq`
- `mtld`
- `awl_ratio`
- `clause_density`
- `dependency_depth`
- `noun_complexity`
- `connective_density`
- `lexical_overlap`
- `grammar_errors_per_100`

The hybrid script also computes:

- `paragraph_count`

These features are output with the `aes_` prefix, using the same convention as
the original extractor.

## Handled By The LLM

Llama 3 handles rubric traits that require semantic judgment:

- `organization`
- `paragraph_development`
- `supporting_detail`
- `abstract_elaboration`
- `prompt_control`
- `comprehensibility`
- `grammar_meaning_impact`
- `llm_recommended_score`
- `justification`

These values are output with the `llm_` prefix.

The prompt includes Level 4, Level 5, and Level 6 anchor essays. Llama 3 uses
these anchors to calibrate its rubric judgments against concrete examples of
the expected organization, development, detail, control, and comprehensibility
at each level.

The LLM should not replace the rule-based extractor. It should add missing
rubric information that the feature extractor cannot measure well.

## Why Grammar Is Split

The rule-based code counts grammar-related matches using LanguageTool. That is a
surface-level feature.

The LLM judges `grammar_meaning_impact`, which asks whether grammar errors
interfere with meaning. This avoids making the LLM duplicate the exact same job
as the rule-based grammar feature.

## Rubric Anchors

The LLM prompt includes three full anchor essays:

- Level 4 anchor: partially organized, generally understandable, but limited in
  cohesion and development.
- Level 5 anchor: clearly organized with concrete support, but less controlled
  and less abstractly developed than Level 6.
- Level 6 anchor: clearly organized, fully developed, detailed, and easy for
  native readers unfamiliar with learner writing to understand.

These anchors are used only for calibration. The model is instructed not to copy
anchor language into its justification and not to reward an essay just because
it shares the same topic as an anchor.

## Expected Local Model

This project assumes Llama 3 is available locally through Ollama.

Check that Ollama can see the model:

```bash
ollama list
```

Run Llama 3 once if needed:

```bash
ollama run llama3:8b
```

## Usage

From the repository root:

```bash
python "hybrid LLM AES/hybrid_llm_aes.py" \
  --input language_features_sample_cleaned_scored.csv \
  --output hybrid_llm_results.csv \
  --text-column text_clean \
  --essay-id-column essay_id \
  --prompt-column prompt_id \
  --model llama3:8b
```

For a quick test on only a few essays:

```bash
python "hybrid LLM AES/hybrid_llm_aes.py" \
  --input language_features_sample_cleaned_scored.csv \
  --output hybrid_llm_results_sample.csv \
  --text-column text_clean \
  --essay-id-column essay_id \
  --prompt-column prompt_id \
  --model llama3:8b \
  --limit 5
```

## Output Columns

The output CSV preserves the original input columns and appends:

- `aes_*` rule-based features
- `llm_*` rubric features

Example LLM columns:

```text
llm_organization
llm_paragraph_development
llm_supporting_detail
llm_abstract_elaboration
llm_prompt_control
llm_comprehensibility
llm_grammar_meaning_impact
llm_recommended_score
llm_justification
```

## Result Column Dictionary

### Original Input Columns

These columns come from the source spreadsheet or CSV and are preserved when
present:

- `essay_id`: Unique essay identifier.
- `prompt_id`: Essay topic or writing prompt identifier.
- `Group`: Existing grouping/category column from the dataset.
- `word_count`: Original word count column from the dataset, if provided.
- `score`: Human rater score. This is the target score used for evaluation.
- `text_clean`: Cleaned student essay text.

### Rule-Based `aes_*` Columns

These columns are produced by the original rule-based feature extractor:

- `aes_score`: Rule-based AES score on a 0-100 scale.
- `aes_paragraph_count`: Paragraph count computed from visible paragraph breaks.
- `aes_word_count`: Number of alphabetic word tokens detected by spaCy.
- `aes_sentence_count`: Number of sentences detected by spaCy.
- `aes_mean_sentence_length`: Average number of words per sentence.
- `aes_avg_word_freq`: Average Zipf word frequency. Lower values usually suggest
  rarer or more advanced vocabulary.
- `aes_mtld`: Measure of textual lexical diversity. Higher values suggest more
  varied vocabulary.
- `aes_awl_ratio`: Ratio of essay words found in the Academic Word List.
- `aes_clause_density`: Approximate clause frequency using dependency labels.
- `aes_dependency_depth`: Average syntactic dependency depth.
- `aes_noun_complexity`: Average number of syntactic children attached to noun
  tokens.
- `aes_connective_density`: Cohesive/connective devices per 100 words.
- `aes_lexical_overlap`: Average word-set overlap between adjacent sentences.
- `aes_grammar_errors_per_100`: LanguageTool grammar matches per 100 words.

### LLM `llm_*` Columns

These columns are produced by local Llama 3 using the ESL placement rubric:

- `llm_organization`: How clearly the essay is organized and whether ideas are
  logically arranged.
- `llm_paragraph_development`: Whether the essay has enough paragraphs and
  whether those paragraphs are actually developed, not just present.
- `llm_supporting_detail`: Quality and concreteness of examples, reasons, and
  supporting details.
- `llm_abstract_elaboration`: Whether the essay goes beyond simple concrete
  details into more general explanation, reasoning, or reflection.
- `llm_prompt_control`: How well the essay stays on topic and responds to the
  assigned prompt.
- `llm_comprehensibility`: How understandable the essay would be to native
  readers who are not used to learner writing.
- `llm_grammar_meaning_impact`: Whether grammar and vocabulary errors interfere
  with meaning. This is different from counting grammar errors.
- `llm_recommended_score`: Llama 3's recommended placement score on the human
  1-6 scale, allowing half-points.
- `llm_justification`: Short evidence-based explanation for the LLM rubric
  scores.

LLM trait scores use integer values from 1 to 6:

```text
1 = very limited
2 = weak
3 = developing
4 = generally understandable / partially controlled
5 = strong but not top-level
6 = clearly top-level
```

## Evaluate Results

After running the hybrid extractor, compare prediction columns against the
human score:

```bash
python "hybrid LLM AES/evaluate_hybrid_results.py" \
  --input hybrid_llm_results.csv \
  --score-column score \
  --prediction aes_score:aes-0-100 \
  --prediction llm_recommended_score
```

`aes_score` is scaled from the rule-based 0-100 range into the human 1-6 range
for evaluation. `llm_recommended_score` is already expected to be on the
human 1-6 placement scale.

## Validate Results

Use the validation script to check whether the result is likely to hold up
outside the current sample:

```bash
python "hybrid LLM AES/validate_hybrid_model.py" \
  --input "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" \
  --score-column score \
  --prompt-column prompt_id \
  --folds 5 \
  --repeats 20
```

This prints:

- full-sample metrics for direct score columns
- one deterministic held-out train/test split
- repeated 5-fold cross-validation for direct scores and learned Ridge models

For a stricter prompt-transfer check, keep essays from the same prompt together
in validation folds:

```bash
python "hybrid LLM AES/validate_hybrid_model.py" \
  --input "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" \
  --score-column score \
  --prompt-column prompt_id \
  --group-column prompt_id \
  --folds 5 \
  --repeats 20
```

Interpret grouped prompt validation cautiously in the current dataset because
the prompts are highly imbalanced: most essays are from `Reducing Stress`, while
some prompts have only one essay.

Validation model names:

- `aes_score_scaled`: rule-based `aes_score`, converted from 0-100 into the
  human 1-6 score range.
- `llm_recommended_score`: direct Llama 3 score on the human 1-6 scale.
- `ridge_aes_features`: learned Ridge regression using only `aes_*` feature
  columns, excluding the final `aes_score`.
- `ridge_llm_traits`: learned Ridge regression using LLM rubric trait columns,
  excluding `llm_recommended_score` and `llm_justification`.
- `ridge_aes_plus_llm_score`: learned Ridge regression using rule-based
  `aes_*` feature columns plus `llm_recommended_score`.
- `ridge_hybrid_features`: learned Ridge regression using both rule-based
  `aes_*` features and LLM rubric trait columns.

The Ridge implementation is intentionally standard-library only, so the script
does not require scikit-learn.

## Research Evaluation Plan

After generating LLM features, compare three systems against the human score:

1. Rule-based AES only
2. LLM rubric score only
3. Hybrid rule-based + LLM features

Recommended metrics:

- correlation with human score
- mean absolute error
- exact agreement
- adjacent agreement
- quadratic weighted kappa

The research claim should be conservative:

> The rule-based AES captures observable linguistic features, while the LLM
> captures semantic and discourse-level rubric features. A calibrated hybrid
> model may improve agreement with human raters while preserving
> interpretability.
