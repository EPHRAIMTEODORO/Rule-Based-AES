# HITL Hybrid LLM AES

This folder contains the human-in-the-loop version of the hybrid Automated
Essay Scoring approach. It combines the existing rule-based AES feature
extractor with local Llama 3 rubric judgments and emits columns that can be
pasted or imported into the `01_Raw_Inputs` sheet of the HITL academic writing
template.

The original `aes_feature_extractor.py` is not modified. The HITL script imports
it, adds LLM-based rubric features, adds the missing template lexical fields,
and writes a new CSV with both the original hybrid columns and workbook-ready
aliases.

For the desktop app, use `app_backend.py`. It exposes an app-facing job API:
`start_job(...)`, `get_job_status(...)`, and `get_job_result(...)`. Under the
hood, it calls `process_workbook(...)`, writes a completed Excel workbook, and
returns structured row records for the UI.

The HITL prototype is designed for local/offline desktop use. The UI uses no
external scripts, fonts, or APIs. The local HTTP bridge binds to `127.0.0.1` by
default, stores uploaded workbooks under `HITL/uploads/`, writes completed
workbooks under `HITL/outputs/`, and calls only the local Ollama API at
`127.0.0.1:11434`.

Use `preflight.py` to check whether the device has all local runtime pieces
needed for offline scoring:

```bash
python "HITL/preflight.py"
```

For JSON output:

```bash
python "HITL/preflight.py" --json
```

Packaging notes live in `HITL/packaging/`:

```text
PACKAGING_PLAN.md
runtime_manifest.json
```

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
- `type_token_ratio`
- `avg_word_length`

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

The HITL script starts the Ollama server automatically when it runs. If the
model has not been downloaded yet, run Llama 3 once first:

```bash
ollama run llama3:8b
```

To disable automatic server startup, pass `--no-start-ollama`.

## Usage

From the repository root:

```bash
python "HITL/hybrid_llm_aes.py" \
  --input language_features_sample_cleaned_scored.csv \
  --output hitl_hybrid_llm_results.csv \
  --text-column text_clean \
  --essay-id-column essay_id \
  --prompt-column prompt_id \
  --model llama3:8b
```

For the desktop-app backend contract:

```python
from HITL import get_job_result, get_job_status, start_job, update_job_decision

job_id = start_job(
    input_path="HITL/Essays.xlsx",
    essay_id_column="id",
    prompt_column="Topic",
    text_column="Essay",
)

status = get_job_status(job_id)
result = get_job_result(job_id)  # call after status["status"] == "completed"
rows_for_ui = result["records"]
completed_workbook = result["output_path"]

updated_row = update_job_decision(
    job_id,
    row_index=0,
    decision={
        "Rater_Final_Score": 4.5,
        "Rater_Final_Placement": "Advanced II",
        "Rater_Action": "Override score",
        "Admissions_Decision": "Follow up",
        "Reason_Notes": "Human rater found stronger organization than the model.",
    },
)
```

Completed workbooks are written under `HITL/outputs/<job_id>/` by default.

For direct Python use without the job runner, call `process_workbook(...)` from
`hitl_processor.py`.

For a command-line smoke test of the workbook processor:

```bash
python "HITL/hitl_processor.py" \
  --input "HITL/Essays.xlsx" \
  --output "HITL/completed_scores.xlsx" \
  --limit 1
```

For a smoke test of the app-facing job API:

```bash
python "HITL/smoke_test_app_backend.py" \
  --input "HITL/Essays.xlsx" \
  --limit 1
```

For browser-style prototype UIs, run the local HTTP API:

```bash
python "HITL/local_api_server.py"
```

The default server listens on `http://127.0.0.1:8765` and serves the prototype
UI at that same address.

Endpoint contract:

```text
GET  /health
GET  /preflight
POST /jobs                 multipart/form-data with file=<uploaded .xlsx>
POST /jobs                 application/json with input_path=<local .xlsx path>
POST /sample-job           runs the packaged HITL/Essays.xlsx sample
GET  /jobs/<job_id>
GET  /jobs/<job_id>/result
POST /jobs/<job_id>/decision
GET  /jobs/<job_id>/download
```

Minimal upload flow:

```javascript
const form = new FormData();
form.append("file", selectedFile);
form.append("essay_id_column", "id");
form.append("prompt_column", "Topic");
form.append("text_column", "Essay");

const created = await fetch("http://127.0.0.1:8765/jobs", {
  method: "POST",
  body: form,
}).then((response) => response.json());

const status = await fetch(`http://127.0.0.1:8765${created.status_url}`)
  .then((response) => response.json());

const result = await fetch(`http://127.0.0.1:8765${created.result_url}`)
  .then((response) => response.json());

const rowsForUi = result.records;
```

Minimal human-review save:

```javascript
await fetch(`http://127.0.0.1:8765${created.status_url}/decision`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    row_index: 0,
    decision: {
      Rater_Final_Score: "4.5",
      Rater_Final_Placement: "Advanced II",
      Rater_Action: "Override score",
      Admissions_Decision: "Follow up",
      Reason_Notes: "Human rater found stronger organization than the model.",
    },
  }),
});
```

Decision saves update the in-memory job result and rewrite the generated Excel
workbook. The human-facing columns are:

```text
Rater_Final_Score
Rater_Final_Placement
Rater_Action
Decision_Status
Admissions_Decision
Reason_Notes
Decision_Updated_At
```

The included UI in `HITL/ui/index.html` uses this same flow: upload workbook,
poll status, show a review dashboard, let the rater move through one essay at a
time, save final decisions, and expose the completed workbook download link.
Its sample button calls `/sample-job`, so packaged app users do not need to know
where the sample workbook lives on disk.

For a quick test on only a few essays:

```bash
python "HITL/hybrid_llm_aes.py" \
  --input language_features_sample_cleaned_scored.csv \
  --output hitl_hybrid_llm_results_sample.csv \
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

### HITL Template Columns

The HITL script also writes these workbook-facing columns:

```text
Essay_ID
Essay_Text
LLM_Organization_Coherence
LLM_Supporting_Detail
LLM_Paragraph_Development
LLM_Comprehensibility
LLM_Prompt_Fulfillment
Word_Count
Sentence_Count
Paragraph_Count
Grammar_Errors_per_100
Type_Token_Ratio
Avg_Word_Length
AWL_Ratio
```

The main field mapping is:

```text
LLM_Prompt_Fulfillment <- llm_prompt_control
Type_Token_Ratio       <- aes_type_token_ratio
Avg_Word_Length        <- aes_avg_word_length
AWL_Ratio              <- aes_awl_ratio
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
