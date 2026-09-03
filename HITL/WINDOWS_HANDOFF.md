# Windows Handoff For HITL Desktop Packaging

This handoff is for continuing the HITL Academic Writing Scorer desktop build
on a Windows machine.

## Current State

The Mac-side repo already includes:

- Electron desktop shell in `HITL/desktop`
- local UI served from `HITL/ui/index.html`
- Python local API server in `HITL/local_api_server.py`
- background workbook job API in `HITL/app_backend.py`
- workbook processing in `HITL/hitl_processor.py`
- hybrid scoring through `HITL/hybrid_llm_aes.py`
- PyInstaller sidecar builder in `HITL/desktop/scripts/build-python-sidecar.cjs`
- runtime asset preparer in `HITL/desktop/scripts/prepare-runtime-assets.cjs`
- packaging notes in `HITL/packaging/PACKAGING_PLAN.md`
- machine-readable packaging checklist in `HITL/packaging/runtime_manifest.json`

The Mac ARM build was verified with:

- bundled PyInstaller backend sidecar
- bundled Ollama runtime
- copied local `llama3:8b` Ollama model store
- bundled Java runtime
- successful local Ollama inference from the copied model store
- successful macOS DMG creation and `hdiutil verify`

## Important Git Note

Large runtime artifacts are intentionally ignored by git:

- `HITL/desktop/node_modules/`
- `HITL/desktop/backend-build/`
- `HITL/desktop/backend-dist/hitl-api/`
- `HITL/desktop/runtime-assets/ollama/<platform>/`
- `HITL/desktop/runtime-assets/ollama-models/`
- `HITL/desktop/runtime-assets/jre/<platform>/`
- `HITL/desktop/dist/`

Do not commit generated installers, copied model stores, Java runtimes, Ollama
binaries, or `node_modules`.

## Windows Goal

Create a Windows build that a tester can install/open without manually
installing Python, Python packages, Java, Ollama, or `llama3:8b`.

Expected Windows runtime layout:

```text
HITL/desktop/backend-dist/hitl-api/hitl-api.exe
HITL/desktop/runtime-assets/ollama/win32-x64/ollama.exe
HITL/desktop/runtime-assets/ollama-models/blobs/
HITL/desktop/runtime-assets/ollama-models/manifests/
HITL/desktop/runtime-assets/jre/win32-x64/bin/java.exe
```

## Setup On Windows

Use PowerShell from the repo root:

```powershell
cd HITL\desktop
npm install
```

Install Python dependencies needed by the sidecar build. Prefer a dedicated
virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r ..\requirements.txt
python -m pip install -r ..\packaging\requirements-desktop-build.txt
```

If the repo does not have `HITL\requirements.txt`, inspect the existing Python
imports and install the same packages used on Mac: `spacy`, `wordfreq`,
`lexical-diversity`, `language-tool-python`, `nltk`, `openpyxl`,
`en_core_web_sm`, and any package required by `aes_feature_extractor.py`.

## Build Steps

Build the Windows Python sidecar:

```powershell
npm run build:backend
```

Prepare Windows runtime assets:

```powershell
npm run prepare:runtimes -- --include-models --java-home "C:\Path\To\JRE"
```

Then create the Windows installer:

```powershell
npm run dist:win
```

Expected output:

```text
HITL\desktop\dist\
```

## Verification Checklist

Before calling the Windows build ready:

1. Confirm `HITL\desktop\backend-dist\hitl-api\hitl-api.exe` exists.
2. Confirm `HITL\desktop\runtime-assets\ollama\win32-x64\ollama.exe` exists.
3. Confirm `HITL\desktop\runtime-assets\ollama-models\manifests\` exists.
4. Confirm `HITL\desktop\runtime-assets\ollama-models\blobs\` exists.
5. Confirm `HITL\desktop\runtime-assets\jre\win32-x64\bin\java.exe` exists.
6. Run the packaged backend `/health` and `/preflight` locally.
7. Run one small local Ollama inference using the copied model store.
8. Launch the Electron app and process the sample workbook.
9. Upload a normal `.xlsx` workbook and confirm the review dashboard renders.
10. Save a human decision and confirm the completed Excel output is rewritten.

## Known Cautions

- Build Windows artifacts on Windows. Do not rely on Mac cross-compilation for
  PyInstaller or bundled runtimes.
- The app will be very large because `llama3:8b` is several GB.
- The app still needs proper Windows code signing before smooth external
  distribution.
- Check license/notice requirements before sharing outside the research team.
- The first launch may take time while bundled Ollama model files are copied
  into app data.
