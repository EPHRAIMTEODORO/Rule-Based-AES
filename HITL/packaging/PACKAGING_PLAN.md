# HITL Offline Desktop Packaging Plan

## Goal

Build a download-and-open desktop app that runs entirely on the user's laptop.
The user should not need to manually install Python, Python packages, Java,
Ollama, Llama 3, spaCy data, or NLTK data.

Current local app shape:

```text
desktop shell
-> local UI from HITL/ui/index.html
-> local HTTP bridge from HITL/local_api_server.py
-> job API from HITL/app_backend.py
-> workbook processor from HITL/hitl_processor.py
-> hybrid scorer from HITL/hybrid_llm_aes.py
-> local Ollama API using llama3:8b
```

## Recommended First Packaging Target

Use Electron with a Python backend sidecar for the first distributable
prototype.

Reasons:

- The UI is already HTML, CSS, and JavaScript.
- The backend is already Python.
- The local API boundary is already stable.
- Electron can launch the Python sidecar and load `http://127.0.0.1:<port>/`.
- This keeps the packaging experiment focused on bundling runtimes and assets,
  not rewriting the app.

Later, if app size becomes the main constraint, evaluate Tauri plus the same
Python sidecar or a native Python window with pywebview.

## Offline Runtime Assets

The installer/app bundle must include or provision these assets locally:

```text
Python 3.9+ runtime
Python package environment
spaCy model: en_core_web_sm
NLTK data: punkt, punkt_tab
Java runtime for LanguageTool
Ollama executable or equivalent local model runtime
Llama model: llama3:8b or packaged replacement
HITL source files
HITL/ui/index.html
HITL/Essays.xlsx sample workbook
data/awl_word_forms.json
uploads and outputs runtime folders
license notices for third-party packages and model weights
```

## Distribution Decision Points

### Model Runtime

Current runtime:

```text
Ollama server at 127.0.0.1:11434
model name: llama3:8b
```

Packaging options:

1. Bundle Ollama and preloaded model files.
   - Best match with current code.
   - Largest app bundle.
   - Requires platform-specific model storage setup.

2. First-run local model installer.
   - Smaller initial installer.
   - Not fully offline unless the installer media includes the model.
   - Still avoids manual user commands.

3. Replace Ollama with an embedded inference runtime.
   - Potentially cleaner packaged app.
   - Requires adapting `call_ollama_chat`.
   - Good later option if Ollama packaging becomes awkward.

For the next prototype, keep Ollama as the runtime and make the app launcher
set a private model directory such as:

```text
<app data>/models/ollama
```

### Grammar Runtime

Current grammar feature:

```text
language-tool-python + Java
```

Packaging options:

1. Bundle a Java runtime.
   - Best match with current code.
   - Adds app size and platform-specific work.

2. Replace LanguageTool with a bundled pure-Python grammar approximation.
   - Smaller and simpler.
   - Less accurate grammar error density.

3. Make grammar density optional and show degraded preflight status.
   - Fastest fallback.
   - Not ideal for final scoring consistency.

For consistency with current scoring, bundle Java for now.

## Build Phases

### Phase 1: Local App Bundle Skeleton

Create an Electron shell that:

- launches bundled Python backend
- waits for `GET /health`
- opens the local UI
- shuts down backend on app close
- stores uploads/outputs in app data, not inside read-only app resources

### Phase 2: Runtime Freezing

Create a bundled Python environment containing:

- `spacy`
- `wordfreq`
- `lexical-diversity`
- `language-tool-python`
- `nltk`
- `openpyxl`
- `en_core_web_sm`
- NLTK `punkt` and `punkt_tab`
- project `data/awl_word_forms.json`
- `HITL` source files

### Phase 3: Local Model Packaging

Package local inference:

- include Ollama executable per platform
- include model files for `llama3:8b` or approved replacement
- set model storage path at app launch
- start the local model server silently
- confirm `GET /preflight` reports the model as available

### Phase 4: Installer and Permissions

Build platform installers:

- macOS `.dmg` or signed `.pkg`
- Windows installer
- optional Linux AppImage/deb later

Installer must handle:

- app data directory creation
- executable permissions
- bundled model placement
- license/notice files
- no internet dependency during first scoring run

### Phase 5: End-to-End Offline Test

On a clean device or VM with internet disabled:

1. Install the app.
2. Open the app.
3. Verify readiness panel reports ready.
4. Click sample job.
5. Upload a user workbook matching `HITL/Essays.xlsx`.
6. Confirm records render in the UI.
7. Download completed workbook.
8. Reopen app and confirm previous runtime folders are still writable.

## Required App Launcher Behavior

The packaged desktop shell should:

- choose a free local API port or reserve `8765`
- launch the Python local API server
- set runtime paths through environment variables
- keep all file writes in app data directories
- open the UI only after `/health` responds
- poll `/preflight` and surface missing assets
- stop the Python backend on app exit

## Backend Changes Still Needed For Packaging

- Make upload/output directories configurable by environment variable.
- Make `HITL/Essays.xlsx` path configurable for bundled resources.
- Make the API port configurable and pass it to the UI.
- Add a backend shutdown endpoint for the desktop shell.
- Add process-level logging to an app data log file.
- Add model-runtime configuration for a bundled Ollama directory.
- Add preflight fields for app bundle paths and disk space.

## Packaging Risks

- App size will be large if bundling Llama 3 8B.
- Model redistribution and license notices need review before release.
- LanguageTool requires Java, increasing bundle complexity.
- Local model scoring can be slow on low-memory laptops.
- Some systems may block localhost servers unless the app is signed/notarized.
- LLM output can occasionally be malformed despite JSON mode; retry handling
  should be improved before release.

## Definition Of Packaging-Ready

The app is packaging-ready when this command reports ready on a clean test
machine without using the internet:

```bash
python "HITL/preflight.py" --json
```

and the served UI can complete:

```text
/sample-job
-> /jobs/<job_id>
-> /jobs/<job_id>/result
-> /jobs/<job_id>/download
```
