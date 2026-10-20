# Windows Handoff For HITL Desktop Packaging

The next Windows release is **0.1.3**. It adds guarded LanguageTool output parsing, bounded local-model recovery,
backend-owned Ollama lifecycle, runtime provenance, and an explicit inference test.

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

The source fixes are on `main`. Pull `main` immediately before building so the
new installer includes the latest backend and scoring code.

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
git log -1 --oneline
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
`HITL/desktop/dist/release-0.1.3/installer-files/` folder:

```text
7za.exe
HITL Academic Writing Scorer Setup 0.1.3.exe
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

The package version in `HITL\desktop\package.json` should report `0.1.3`
before building. If an older `dist` folder is present, keep the generated
0.1.3 files together and do not mix them with an older installer bundle.

Expected output:

```text
HITL\desktop\dist\
```

The Electron build produces the application payload. The handoff wrapper is
assembled from that payload and written as:

```text
HITL\desktop\dist\release-0.1.3\installer-files\HITL Academic Writing Scorer Setup 0.1.3.exe
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

## Runtime Recovery In 0.1.3

The Electron launcher selects a fresh private Ollama port and passes
`--managed-ollama` to the backend. The backend owns the bundled server and can
restart it if interrupted; it never kills a separately installed Ollama service.
An explicit `HITL_OLLAMA_URL` selects an external endpoint instead.

Interrupted generation has at most two recovery attempts within the existing
per-essay timeout. Only the current essay is retried, preserving completed rows
in the current job. Missing-model and rejected-request errors are not retried
as runner interruptions. Full failure tracebacks are written to the backend log.

LanguageTool checks reject missing, failed, and malformed subprocess output
before parsing. When both grammar methods fail, the grammar metric remains
unavailable and is excluded from the weighted score. It is not treated as zero
errors.

The setup panel labels the existing checks as Availability. `Test Scoring`
performs a deliberate local inference request, separately from `/preflight`,
and is unavailable during workbook processing. The panel also identifies the
app version and whether the active Ollama endpoint is managed or external.

Windows Ollama auto-updates can kill every `ollama.exe`/`llama-server.exe`
process by executable name, including bundled copies in other directories.
Private ports alone do not prevent this. Recovery tests must terminate only
isolated test PIDs, never every process with those names.

Release-specific build configuration, checksums, and verification results are
kept in the ignored `HITL/desktop/dist/release-0.1.3/` directory. The Windows
handoff uses Electron's directory target and the existing three-file setup
wrapper, avoiding the standalone NSIS payload-size limit. The release config
includes the complete model blob and omits redundant model chunks.

## Local 0.1.3 Verification (2026-10-16)

- All 37 unit/API regression tests passed.
- The frozen Windows backend processed all 30 rows of
  `Essays_system_check.xlsx`, preserving student order and valid rubric scores.
- An isolated runner termination during essay 2 and an isolated server/runner
  termination during essay 3 both recovered automatically. Progress retained
  the one and two already completed rows respectively.
- Grammar metrics were available for 28 rows. The other two rows completed
  with grammar unavailable, without the `.find()` exception.
- Saving a human decision, downloading the completed workbook, reopening all
  30 rows, and graceful backend shutdown passed.
- The three-file installer archive passed its integrity check and its SHA-256
  checksums are saved in the release directory.
- Upgrading this laptop to 0.1.3 preserved all 25 original model/runtime files
  byte for byte. The installed backend passed availability 20/20 and a real
  inference probe using its bundled Ollama 0.33.2 on a private endpoint.
- Installed application/backend hashes match the tested release; Desktop and
  Start Menu shortcuts point to the upgraded installation.

The visual check was completed on 2026-10-17 after Windows was unlocked. The
installed app shows version 0.1.3, availability 20/20, successful Test Scoring,
and all 30 review rows with the saved first-row final score 4 / EIL 1.

That check found an additional UI bug: `numericValue()` converts empty
strings and null values to zero. Unavailable grammar is therefore labelled
Clean, and a blank pending final score is displayed as 1 with a Finalized
preview. The stored record remains blank and Pending until a decision is
saved. These display cases still need correction; the focused installed-UI
checks in `verification-2026-10-17/ui-missing-value-tests.json` reproduce them.

A clean account/VM installation and physically disconnected network test remain
unverified. The frozen integration test used unreachable HTTP/HTTPS proxies
with loopback exceptions and cloud disabled.

During this run Windows temporarily stopped enumerating the NVIDIA GPU and
execution paused for approximately 31 minutes. The runner recovery completed
on CPU; the server recovery rediscovered the restored NVIDIA GPU. These
observations and the successful final report are retained under the release's
`verification/` folder.

## Installed-Binary Retest (2026-10-17)

All 37 unit/API tests passed again. A fresh isolated run using the installed
0.1.3 binaries completed all 30 essays in approximately 13 minutes 38 seconds.
Both deliberate runner/server interruptions recovered, 28 rows had grammar
metrics, and the two unavailable-grammar rows completed safely. Saving a human
decision, download/reopening, and graceful shutdown passed again. A fresh
visible Test Scoring check also succeeded in the installed Electron app.

Results are in `dist/release-0.1.3/verification-2026-10-17/TEST_RESULTS.md`.
The two additional missing-value UI checks fail as documented above; these
findings do not change the successful original crash-recovery results.
