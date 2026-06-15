# AES Human Review Prototype UI

This is a React/Vite prototype for the hybrid AES workflow:

1. A user submits an essay.
2. The backend provides linguistic feature analysis and LLM rubric evaluation.
3. The UI compares the feature baseline score against the LLM score.
4. A human reviewer makes the final scoring decision.

The prototype is designed as a future Tauri desktop app frontend. For now, it runs as a local Vite app.

## Data Source

The UI uses generated placeholder JSON from the project Excel files:

- `../NewAes/ELAT_DATA/full_sample_aes_features_with_grammar_llm_improved.xlsx`
- `../NewAes/ELAT_DATA/essays.xlsx`

The generator joins both files by `essay_id` and writes:

- `src/data/aesCases.json`

Run this whenever the Excel files change:

```powershell
npm run generate:data
```

Current limitation: the workbook does not yet include a dedicated feature-only prediction column. The UI currently uses the spreadsheet `score` column as a temporary `Feature baseline` for the agreement comparison.

## Run Locally

```powershell
cd prototype-ui
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Build check:

```powershell
npm run build
```

## Reviewer Navigation

The left sidebar is an essay review queue.

Users can:

- Search by essay ID or prompt name.
- Filter the queue by `All`, `Needs`, `Aligned`, or `Done`.
- Click any essay in the queue.
- Use previous and next arrow buttons in the top bar.
- See progress such as `Essay 4 of 443`.

The default queue order prioritizes cases that need human attention:

1. Larger feature-vs-LLM agreement gaps.
2. Cases marked `Needs review`.
3. Remaining aligned cases.

## Main UI Areas

### Essay

Shows the raw essay text from `essays.xlsx`, plus prompt, group, and word count context.

### Scores and Measures

Shows:

- Feature baseline score
- LLM overall score
- Agreement gap
- Linguistic feature measures
- LLM rubric scores
- LLM justification text

The agreement threshold is currently set in `src/main.tsx`:

```ts
const agreementThreshold = 1;
```

### Final Human Decision

The human reviewer can set:

- Final score
- Confidence
- Decision route
- Rationale

Submitting a decision marks the essay as `Completed` in the current browser session.

## State Behavior

Reviewer decisions are stored in React state by `essayId`. This means edits persist while moving between essays during the same session, but they are not yet saved to disk or a backend.

For the later Tauri version, this state should move behind a backend command or local database table.

## Useful Files

- `src/main.tsx` - main prototype interface and state logic
- `src/styles.css` - UI layout and styling
- `src/data/aesCases.json` - generated placeholder data
- `scripts/export_prototype_fixture.py` - Excel-to-JSON fixture generator

## Future Improvements

- Replace the temporary `score` baseline with a true feature-only predicted score.
- Save reviewer decisions through Tauri commands.
- Add reviewer login or rater ID.
- Add keyboard shortcuts for next/previous essay.
- Add export of final human decisions to CSV or Excel.
- Load cases on demand instead of bundling the full JSON fixture.
