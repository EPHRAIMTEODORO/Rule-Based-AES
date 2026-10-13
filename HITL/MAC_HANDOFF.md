# macOS Handoff For HITL Desktop Packaging

This handoff covers building the offline HITL Academic Writing Scorer app on
the Mac laptop. Build the sidecar and native runtime assets on the Mac that
will produce the release. Do not cross-copy Windows executables, Java files,
Ollama files, or PyInstaller output into this build.

## Pull The Latest Work

From Terminal:

```bash
git clone https://github.com/EPHRAIMTEODORO/Rule-Based-AES.git
cd Rule-Based-AES
git checkout main
git pull origin main
```

If the repo already exists:

```bash
cd /path/to/Rule-Based-AES
git checkout main
git pull origin main
git status
```

The shared Electron launcher supports both Apple Silicon and Intel paths:

```bash
uname -m
node -p "process.platform + '-' + process.arch"
```

Use an Apple Silicon build for `arm64` and an Intel build for `x64`. Build
native Python and Ollama assets on the matching architecture.

## Build Machine Setup

Install Node.js/npm, Python 3.9 or newer, a JRE, and Ollama on the build Mac.
Use a dedicated Python environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r HITL/packaging/requirements-desktop-build.txt
python -m pip install spacy wordfreq lexical-diversity language-tool-python nltk openpyxl pyinstaller
```

Install the spaCy model matching the installed spaCy version, then verify the
backend imports:

```bash
python -m py_compile HITL/local_api_server.py HITL/app_backend.py HITL/hitl_processor.py HITL/preflight.py HITL/hybrid_llm_aes.py
```

Install or select a private JRE whose root contains `bin/java`. With a JDK or
JRE installed through a standard macOS location, this usually finds Java:

```bash
/usr/libexec/java_home -V
export HITL_JAVA_HOME="$(/usr/libexec/java_home)"
"$HITL_JAVA_HOME/bin/java" -version
```

## Prepare Native Runtime Assets

Start Ollama on the build Mac and pull the model once:

```bash
ollama pull llama3:8b
ollama list
```

From `HITL/desktop`, install the JavaScript dependencies and prepare the
current Mac's runtime assets:

```bash
cd HITL/desktop
npm install
npm run prepare:runtimes -- --include-models --java-home "$HITL_JAVA_HOME"
```

Confirm the platform-specific folders match the machine architecture:

```bash
test -x runtime-assets/ollama/darwin-*/ollama
test -x runtime-assets/jre/darwin-*/bin/java
test -d runtime-assets/ollama-models/manifests
test -d runtime-assets/ollama-models/blobs
```

The model store can be several GB. These runtime folders are ignored by Git
and must be present locally when the package is built.

## Build The Mac App

Build the Python sidecar first, then create the macOS package:

```bash
npm run build:backend
test -x backend-dist/hitl-api/hitl-api
npm run dist:mac
```

The expected artifacts are under `HITL/desktop/dist/`, normally including a
`.dmg` and a platform-specific unpacked app directory. Keep generated DMGs,
runtime assets, model files, and sidecar output out of Git.

## Verification Checklist

On the build Mac:

1. Confirm the backend sidecar exists and is executable.
2. Confirm the `darwin-arm64` or `darwin-x64` Ollama runtime exists.
3. Confirm the matching private Java runtime exists.
4. Confirm the model manifests and blobs exist.
5. Run `npm run dist:mac` without missing-resource warnings.
6. Verify the DMG with `hdiutil verify "dist/<generated-file>.dmg"`.
7. Install the app from the DMG into `/Applications` or a test user account.
8. Disable internet before launching the installed app.
9. Confirm `/health` and `/preflight` report ready.
10. Confirm preflight reports Java, Ollama, and `llama3:8b` as available.
11. Use the sample job, then upload `Essays_V2.xlsx`.
12. Save a human decision and confirm the completed workbook downloads.
13. Reopen the app and confirm the app-data folders remain writable.

For a local API smoke check while the app is running:

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/preflight
```

## macOS Notes

- Unsigned builds may trigger Gatekeeper. Test the exact release flow on a
  clean user account before distribution and document any required security
  approval.
- Build on Apple Silicon for Apple Silicon and on Intel for Intel unless a
  deliberate universal build is configured and tested.
- The first launch may take time while the bundled model store is copied into
  the user's app-data directory.
- The app writes uploads, outputs, logs, and model storage to writable app data,
  not inside the read-only `.app` bundle.
- Review licenses and notices for the model, Ollama, Java, LanguageTool, and
  Python packages before sharing the DMG outside the research team.
