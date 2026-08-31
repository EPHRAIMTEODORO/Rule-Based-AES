"""Offline readiness checks for the HITL desktop app."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "llama3:8b"
REQUIRED_PACKAGES = [
    ("spacy", "spacy"),
    ("wordfreq", "wordfreq"),
    ("lexical-diversity", "lexical_diversity"),
    ("language-tool-python", "language_tool_python"),
    ("nltk", "nltk"),
    ("openpyxl", "openpyxl"),
]


@dataclass
class PreflightCheck:
    """One readiness check result."""

    name: str
    ok: bool
    status: str
    message: str
    detail: Optional[str] = None


@dataclass
class PreflightResult:
    """Complete readiness result for the desktop app."""

    ready: bool
    status: str
    checks: list[PreflightCheck]

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        payload = asdict(self)
        payload["summary"] = {
            "passed": sum(1 for check in self.checks if check.ok),
            "failed": sum(1 for check in self.checks if not check.ok),
            "total": len(self.checks),
        }
        return payload


def _check(name: str, ok: bool, message: str, detail: Optional[str] = None) -> PreflightCheck:
    """Build a normalized check result."""
    return PreflightCheck(
        name=name,
        ok=ok,
        status="ok" if ok else "missing",
        message=message,
        detail=detail,
    )


def _import_package(import_name: str) -> tuple[bool, Optional[str]]:
    """Return whether a Python package imports successfully."""
    try:
        __import__(import_name)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, None


def _check_python_version() -> PreflightCheck:
    """Check supported Python version."""
    version = sys.version_info
    ok = version >= (3, 9)
    readable = f"{version.major}.{version.minor}.{version.micro}"
    return _check(
        "python_version",
        ok,
        f"Python {readable}" if ok else f"Python {readable}; Python 3.9+ is required",
    )


def _check_python_packages() -> list[PreflightCheck]:
    """Check required Python packages."""
    checks = []
    for package_name, import_name in REQUIRED_PACKAGES:
        ok, detail = _import_package(import_name)
        checks.append(
            _check(
                f"python_package:{package_name}",
                ok,
                f"{package_name} is available" if ok else f"{package_name} is missing",
                detail,
            )
        )
    return checks


def _check_spacy_model() -> PreflightCheck:
    """Check that the packaged spaCy English model is available."""
    try:
        import spacy

        spacy.load("en_core_web_sm")
    except Exception as exc:
        return _check(
            "spacy_model:en_core_web_sm",
            False,
            "spaCy model en_core_web_sm is missing",
            f"{type(exc).__name__}: {exc}",
        )
    return _check("spacy_model:en_core_web_sm", True, "spaCy model en_core_web_sm is available")


def _check_nltk_resource(resource_name: str) -> PreflightCheck:
    """Check a required NLTK resource."""
    try:
        import nltk

        location = nltk.data.find(resource_name)
    except Exception as exc:
        return _check(
            f"nltk_resource:{resource_name}",
            False,
            f"NLTK resource {resource_name} is missing",
            f"{type(exc).__name__}: {exc}",
        )
    return _check(
        f"nltk_resource:{resource_name}",
        True,
        f"NLTK resource {resource_name} is available",
        str(location),
    )


def _check_java() -> PreflightCheck:
    """Check Java availability for LanguageTool."""
    java_path = shutil.which("java")
    if not java_path:
        return _check("java", False, "Java is missing; LanguageTool needs Java")

    try:
        completed = subprocess.run(
            [java_path, "-version"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return _check(
            "java",
            False,
            "Java could not be executed",
            f"{type(exc).__name__}: {exc}",
        )

    detail = completed.stderr.strip().splitlines()[0] if completed.stderr else java_path
    return _check("java", completed.returncode == 0, "Java is available", detail)


def _check_path_exists(name: str, path: Path, label: str) -> PreflightCheck:
    """Check that an expected local asset exists."""
    return _check(
        name,
        path.exists(),
        f"{label} exists" if path.exists() else f"{label} is missing",
        str(path),
    )


def _check_writable_dir(name: str, path: Path) -> PreflightCheck:
    """Check that a runtime folder is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
    except Exception as exc:
        return _check(
            name,
            False,
            f"{path} is not writable",
            f"{type(exc).__name__}: {exc}",
        )
    return _check(name, True, f"{path} is writable", str(path))


def _ollama_tags_url(ollama_url: str) -> str:
    """Convert an Ollama chat API URL into the local tags URL."""
    parsed_url = urllib.parse.urlparse(ollama_url)
    return urllib.parse.urlunparse(parsed_url._replace(path="/api/tags", query=""))


def _check_ollama_executable(ollama_command: str) -> PreflightCheck:
    """Check that the Ollama executable can be found."""
    found = shutil.which(ollama_command)
    return _check(
        "ollama_executable",
        found is not None,
        f"Ollama executable found at {found}" if found else f"Ollama executable not found: {ollama_command}",
        found,
    )


def _read_ollama_tags(ollama_url: str, timeout_seconds: float) -> tuple[bool, Optional[dict], Optional[str]]:
    """Read local Ollama model tags."""
    request = urllib.request.Request(_ollama_tags_url(ollama_url), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return True, json.loads(response.read().decode("utf-8")), None
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def _check_ollama_server(ollama_url: str, timeout_seconds: float) -> PreflightCheck:
    """Check whether the local Ollama API is reachable."""
    ok, _, detail = _read_ollama_tags(ollama_url, timeout_seconds)
    return _check(
        "ollama_server",
        ok,
        "Ollama local API is reachable" if ok else "Ollama local API is not reachable",
        _ollama_tags_url(ollama_url) if ok else detail,
    )


def _check_ollama_model(
    model: str,
    ollama_url: str,
    timeout_seconds: float,
) -> PreflightCheck:
    """Check whether the required local Ollama model is available."""
    ok, payload, detail = _read_ollama_tags(ollama_url, timeout_seconds)
    if not ok or payload is None:
        return _check(
            "ollama_model",
            False,
            f"Cannot confirm local model {model}; Ollama API is unavailable",
            detail,
        )

    model_names = {
        str(item.get("name", ""))
        for item in payload.get("models", [])
        if isinstance(item, dict)
    }
    found = model in model_names
    return _check(
        "ollama_model",
        found,
        f"Local model {model} is available" if found else f"Local model {model} is missing",
        ", ".join(sorted(model_names)) if model_names else "No local Ollama models reported",
    )


def run_preflight(
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    ollama_command: str = "ollama",
    timeout_seconds: float = 2.0,
) -> PreflightResult:
    """Run all offline readiness checks."""
    checks: list[PreflightCheck] = [
        _check_python_version(),
        *_check_python_packages(),
        _check_spacy_model(),
        _check_nltk_resource("tokenizers/punkt"),
        _check_nltk_resource("tokenizers/punkt_tab"),
        _check_java(),
        _check_path_exists("sample_workbook", THIS_DIR / "Essays.xlsx", "Sample workbook"),
        _check_path_exists("awl_data", PROJECT_DIR / "data" / "awl_word_forms.json", "AWL data"),
        _check_writable_dir("uploads_writable", THIS_DIR / "uploads"),
        _check_writable_dir("outputs_writable", THIS_DIR / "outputs"),
        _check_ollama_executable(ollama_command),
        _check_ollama_server(ollama_url, timeout_seconds),
        _check_ollama_model(model, ollama_url, timeout_seconds),
    ]
    ready = all(check.ok for check in checks)
    status = "ready" if ready else "not_ready"
    return PreflightResult(ready=ready, status=status, checks=checks)


def _parse_args() -> argparse.Namespace:
    """Parse preflight CLI options."""
    parser = argparse.ArgumentParser(description="Run HITL offline readiness checks.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-command", default="ollama")
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def main() -> None:
    """Run preflight from the command line."""
    args = _parse_args()
    result = run_preflight(
        model=args.model,
        ollama_url=args.ollama_url,
        ollama_command=args.ollama_command,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2), flush=True)
        return

    print(f"HITL preflight: {result.status}", flush=True)
    for check in result.checks:
        marker = "OK" if check.ok else "MISSING"
        print(f"[{marker}] {check.name}: {check.message}", flush=True)
    raise SystemExit(0 if result.ready else 1)


if __name__ == "__main__":
    main()
