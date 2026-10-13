# Windows Handoff For HITL Desktop Packaging

This handoff is for building and testing the HITL Academic Writing Scorer
desktop app on Windows. For the Mac build planned on the other laptop, use
[`MAC_HANDOFF.md`](MAC_HANDOFF.md); runtime binaries and Python sidecars must
be built on the target operating system and architecture.

## Current State

The repo on `main` already includes:

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
- `Essays_V2.xlsx` as a small upload workbook for Windows testing

The Windows production handoff has been verified with a bundled Python sidecar,
Windows Ollama runtime, local `llama3:8b` model store, private Java runtime,
offline startup, workbook processing, and upgrade-over-existing-install.

The shared launcher also has platform paths for macOS ARM64 and x64. Build the
Mac sidecar and runtime assets on the Mac laptop itself; do not copy Windows
executables or a Windows PyInstaller sidecar into a Mac build.

Continue the Mac work with [`MAC_HANDOFF.md`](MAC_HANDOFF.md).

The current Mac target checklist is:

- bundled PyInstaller backend sidecar
- bundled Ollama runtime and companion files
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

## Pull The Latest Work First

On the Windows machine, start from the latest `main` branch. If the repo has
not been cloned yet:

```powershell
git clone https://github.com/EPHRAIMTEODORO/Rule-Based-AES.git
cd Rule-Based-AES
git checkout main
git pull origin main
```

If the repo already exists:

```powershell
cd "C:\Path\To\Rule-Based-AES"
git checkout main
git pull origin main
git status
```

Before building, confirm these files exist:

```powershell
Test-Path HITL\WINDOWS_HANDOFF.md
Test-Path HITL\desktop\package.json
Test-Path HITL\desktop\scripts\build-python-sidecar.cjs
Test-Path HITL\desktop\scripts\prepare-runtime-assets.cjs
Test-Path Essays_V2.xlsx
```

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

The Electron build output is written to:

```text
HITL/desktop/dist/
```

The tested offline Windows handoff is a three-file bundle in the ignored
`HITL/desktop/dist/installer-files/` folder:

```text
7za.exe
HITL Academic Writing Scorer Setup 0.1.1.exe
hitl-app.7z
```

Keep these files together. The small setup executable extracts the large
payload and can replace the standard per-user install at
`%LOCALAPPDATA%\Programs\hitl-academic-writing-scorer-desktop`.

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
python -m pip install -r ..\packaging\requirements-desktop-build.txt
```

Then install the runtime Python packages used by the HITL backend. If a
requirements file has been added by the time you work on Windows, use it.
Otherwise install the packages directly:

```powershell
python -m pip install spacy wordfreq lexical-diversity language-tool-python nltk openpyxl pyinstaller
python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
```

If those versions do not match the local Python/spaCy version, adjust the
spaCy model version to match the installed spaCy major/minor version.

Also confirm that the backend can import the project modules before packaging:

```powershell
cd ..
python -m py_compile local_api_server.py app_backend.py hitl_processor.py preflight.py hybrid_llm_aes.py
cd desktop
```

## Prepare Windows Runtime Assets

Install Ollama for Windows on the build machine and pull the model once on that
machine:

```powershell
ollama pull llama3:8b
ollama list
```

Install or unzip a Windows JRE. The build should point to the JRE root folder
that contains `bin\java.exe`.

Then copy Windows runtime assets into ignored packaging folders:

```powershell
npm run prepare:runtimes -- --include-models --java-home "C:\Path\To\JRE"
```

After this command, inspect:

```powershell
Test-Path runtime-assets\ollama\win32-x64\ollama.exe
Test-Path runtime-assets\ollama-models\blobs
Test-Path runtime-assets\ollama-models\manifests
Test-Path runtime-assets\jre\win32-x64\bin\java.exe
```

If `runtime-assets\ollama\win32-x64\ollama.exe` exists but inference fails,
check whether Ollama for Windows needs companion runtime files copied alongside
`ollama.exe`, similar to the Mac build requiring `llama-server` and dynamic
libraries.

## Build Steps

Build the Windows Python sidecar:

```powershell
npm run build:backend
```

Confirm the sidecar exists:

```powershell
Test-Path backend-dist\hitl-api\hitl-api.exe
```

Create the Windows installable:

```powershell
npm run dist:win
```

Expected output:

```text
HITL\desktop\dist\
```

The Electron build produces the application payload. The handoff wrapper is
assembled from that payload and written as:

```text
HITL\desktop\dist\installer-files\HITL Academic Writing Scorer Setup 0.1.1.exe
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
9. Upload `Essays_V2.xlsx` and confirm the review dashboard renders.
10. Save a human decision and confirm the completed Excel output is rewritten.
11. Install the generated `.exe` on a different Windows user profile or VM.
12. Disable internet and confirm the installed app still starts and scores.
13. Run the same setup over an existing install and confirm it replaces the
    application without deleting `%APPDATA%` model or user-output data.

## Known Cautions

- Build Windows artifacts on Windows. Do not rely on Mac cross-compilation for
  PyInstaller or bundled runtimes.
- The app will be very large because `llama3:8b` is several GB.
- The app still needs proper Windows code signing before smooth external
  distribution.
- Check license/notice requirements before sharing outside the research team.
- The first launch may take time while bundled Ollama model files are copied
  into app data.
- The generated installer may be unsigned. Windows SmartScreen warnings are
  expected until proper code signing is configured.
