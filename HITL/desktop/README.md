# HITL Electron Desktop Shell

This is the Phase 1 desktop wrapper for the HITL Academic Writing Scorer.

It starts the local Python API server, waits for `/health`, opens the existing
dashboard UI, stores uploads and outputs in Electron's app-data directory, and
shuts the backend down when the app exits.

## Development Run

Install desktop dependencies once:

```bash
cd HITL/desktop
npm install
```

Run the desktop shell:

```bash
npm start
```

By default the launcher uses `python3` on macOS/Linux and `python` on Windows.
To point it at a virtual environment:

```bash
HITL_PYTHON=/absolute/path/to/python npm start
```

After `npm run build:backend` has created `backend-dist/hitl-api/`, `npm start`
uses the frozen backend executable instead of the Python script fallback.

The launcher creates writable app-data folders for uploads, outputs, logs, and
Ollama model storage. It also passes the selected model/runtime settings to the
backend before the UI opens.

## Build The Python Sidecar

Install the Python packaging tool once for the selected Python runtime:

```bash
python3 -m pip install -r ../packaging/requirements-desktop-build.txt
```

Then freeze the backend:

```bash
npm run build:backend
```

This writes an ignored build artifact to:

```text
HITL/desktop/backend-dist/hitl-api/
```

The sidecar includes the HITL Python backend, required Python packages, the
sample workbook, UI file, AWL data, and bundled NLTK resources. It does not yet
include Java, Ollama, or the Llama model.

## Runtime Asset Folders

Optional bundled runtimes should be placed under:

```text
HITL/desktop/runtime-assets/ollama/
HITL/desktop/runtime-assets/ollama-models/
HITL/desktop/runtime-assets/jre/
```

Platform-specific executables can use subfolders such as:

```text
runtime-assets/ollama/darwin-arm64/ollama
runtime-assets/ollama/darwin-x64/ollama
runtime-assets/ollama/win32-x64/ollama.exe
runtime-assets/ollama/linux-x64/ollama
runtime-assets/jre/darwin-arm64/bin/java
runtime-assets/jre/win32-x64/bin/java.exe
```

Prepare the current machine's Ollama executable:

```bash
npm run prepare:runtimes
```

Prepare the Ollama executable and copy the local Ollama model store into the
ignored packaging folder:

```bash
npm run prepare:runtimes -- --include-models
```

That model-store copy can be several GB. It is intentionally ignored by git.

Prepare a private Java runtime when you have a JRE folder selected:

```bash
npm run prepare:runtimes -- --java-home /absolute/path/to/jre
```

At startup the Electron shell:

- prefers `HITL_BACKEND_EXECUTABLE` when provided
- prefers `HITL_OLLAMA_COMMAND` when provided
- prefers `HITL_JAVA_HOME` when provided
- otherwise checks the bundled runtime asset folders
- sets `OLLAMA_MODELS` to the app-data model directory
- chooses a local Ollama port and sets `OLLAMA_HOST`
- copies bundled `ollama-models` resources into app data when present

## Packaging Commands

These commands create OS-specific builds from the same Electron codebase:

```bash
npm run dist:with-backend
npm run dist:mac
npm run dist:win
npm run dist:linux
```

Use `npm run dist:with-backend` when you want the package command to rebuild the
Python sidecar first. The current app still does not bundle Java, Ollama, or the
Llama model. Those are the next packaging phase.
