# Current Work Summary

This repo contains a rule-based Automated Essay Scoring (AES) feature extractor
and a separate hybrid LLM AES workflow that uses local Llama 3 through Ollama.

This summary exists so another Codex session on another device can quickly pick
up the project context.

## Repository State

The original rule-based extractor remains unchanged:

- `aes_feature_extractor.py`

The hybrid work is isolated in:

- `hybrid LLM AES/`

Recent commits:

- `6856321 Add hybrid LLM AES pipeline`
- `857af19 Add LLM rubric anchor essays`

## Main Goal

The original rule-based AES score aligned with human raters only moderately.
The current project direction is a hybrid approach:

```text
rule-based AES features + LLM rubric features -> better prediction of human score
```

The rule-based script handles measurable linguistic features. The LLM handles
semantic and discourse-level judgments that the feature extractor cannot judge
well.

## What Code Handles

The existing rule-based extractor handles:

- word count
- sentence count
- mean sentence length
- average word frequency
- MTLD lexical diversity
- Academic Word List ratio
- clause density
- dependency depth
- noun complexity
- connective density
- lexical overlap
- grammar errors per 100 words

The hybrid script also computes paragraph count.

## What Llama 3 Handles

The LLM produces these rubric fields:

- `llm_organization`
- `llm_paragraph_development`
- `llm_supporting_detail`
- `llm_abstract_elaboration`
- `llm_prompt_control`
- `llm_comprehensibility`
- `llm_grammar_meaning_impact`
- `llm_recommended_score`
- `llm_justification`

The LLM is not intended to replace the rule-based extractor. It adds rubric
features that require semantic judgment.

## Rubric Anchors

The LLM prompt now includes full Level 4, Level 5, and Level 6 anchor essays.
These anchors are stored in:

- `hybrid LLM AES/llm_rubric_prompt.py`

The anchors are used to calibrate Llama 3's scores. The prompt tells the model
to compare the target essay against the anchors for organization, development,
detail, prompt control, and comprehensibility.

## Important Files

- `hybrid LLM AES/README.md`: explains the hybrid approach and all result
  columns.
- `hybrid LLM AES/hybrid_llm_aes.py`: runs the rule-based extractor and local
  Llama 3 scorer.
- `hybrid LLM AES/llm_rubric_prompt.py`: contains the LLM prompt, rubric, and
  Level 4/5/6 anchor essays.
- `hybrid LLM AES/evaluate_hybrid_results.py`: evaluates prediction columns
  against the human `score` column.
- `hybrid LLM AES/Language_Features_Sample_cleaned.xlsx`: input workbook used
  for the latest hybrid run.
- `hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv`:
  generated hybrid result file.

## Local Model

The local model used on the first device was:

```bash
llama3:8b
```

Check Ollama on another device with:

```bash
ollama list
```

If needed, start/download the model:

```bash
ollama run llama3:8b
```

## Run Hybrid Scoring

From the repo root:

```bash
python3 "hybrid LLM AES/hybrid_llm_aes.py" \
  --input "hybrid LLM AES/Language_Features_Sample_cleaned.xlsx" \
  --output "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" \
  --text-column text_clean \
  --essay-id-column essay_id \
  --prompt-column prompt_id \
  --sheet Cleaned_Data \
  --model llama3:8b
```

For a quick test:

```bash
python3 "hybrid LLM AES/hybrid_llm_aes.py" \
  --input "hybrid LLM AES/Language_Features_Sample_cleaned.xlsx" \
  --output "hybrid LLM AES/hybrid_llm_results_sample.csv" \
  --text-column text_clean \
  --essay-id-column essay_id \
  --prompt-column prompt_id \
  --sheet Cleaned_Data \
  --model llama3:8b \
  --limit 1
```

## Evaluate Results

Compare rule-based and LLM scores against human scores:

```bash
python3 "hybrid LLM AES/evaluate_hybrid_results.py" \
  --input "hybrid LLM AES/Language_Features_Sample_cleaned_hybrid_llm_results.csv" \
  --score-column score \
  --prediction aes_score:aes-0-100 \
  --prediction llm_recommended_score
```

The latest full run on 41 essays produced:

```text
aes_score:              r = 0.52226, MAE = 1.03878, QWK = 0.24673
llm_recommended_score:  r = 0.77802, MAE = 0.57317, QWK = 0.73558
```

## Next Likely Steps

Possible next tasks:

- Rerun the full hybrid scorer after the new Level 4/5/6 anchors and compare
  metrics to the previous run.
- Add a learned hybrid model that combines `aes_*` and `llm_*` columns.
- Add cross-validation because the current dataset is small.
- Decide whether generated result CSV files should stay in git or be treated as
  local artifacts.

