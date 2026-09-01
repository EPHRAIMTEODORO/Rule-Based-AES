"""Local HTTP API for the HITL desktop-app prototype.

This server is intentionally small and dependency-free. It lets a desktop UI
upload a workbook, start a background HITL scoring job, poll job status, read
JSON results, and download the completed workbook.
"""

from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import shutil
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from HITL import (  # noqa: E402
    get_job_result,
    get_job_status,
    run_preflight,
    start_job,
    update_job_decision,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
UPLOAD_DIR = THIS_DIR / "uploads"
OUTPUT_DIR = THIS_DIR / "outputs"
UI_INDEX = THIS_DIR / "ui" / "index.html"
SAMPLE_WORKBOOK = THIS_DIR / "Essays.xlsx"
ALLOWED_EXTENSIONS = {".xlsx"}
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "null",
}


def _origin(handler: BaseHTTPRequestHandler) -> str:
    """Return a local-only CORS origin for prototype desktop shells."""
    origin = handler.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        return origin
    return f"http://{handler.headers.get('Host', '127.0.0.1:8765')}"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    """Write a JSON response."""
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", _origin(handler))
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _error_response(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    """Write a consistent error response."""
    _json_response(handler, status, {"error": message})


def _status_with_urls(status: dict) -> dict:
    """Attach endpoint URLs to a job status payload."""
    job_id = status["job_id"]
    return {
        **status,
        "status_url": f"/jobs/{job_id}",
        "result_url": f"/jobs/{job_id}/result",
        "download_url": f"/jobs/{job_id}/download",
    }


def _safe_upload_name(filename: str) -> str:
    """Return a safe uploaded workbook filename."""
    source_name = Path(filename).name
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in Path(source_name).stem)
    suffix = Path(source_name).suffix.lower()
    return f"{stem or 'upload'}{suffix}"


def _save_uploaded_file(form: cgi.FieldStorage) -> str:
    """Save the uploaded workbook and return its path."""
    upload = form["file"] if "file" in form else None
    if isinstance(upload, list):
        upload = upload[0] if upload else None
    if upload is None or not getattr(upload, "filename", ""):
        raise ValueError("Upload request must include a file field named `file`.")

    filename = _safe_upload_name(upload.filename)
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .xlsx uploads are supported.")

    upload_id = uuid.uuid4().hex
    upload_dir = UPLOAD_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / filename
    with upload_path.open("wb") as output_file:
        shutil.copyfileobj(upload.file, output_file)
    return str(upload_path)


def _field_value(form: cgi.FieldStorage, field_name: str, default: object = None) -> object:
    """Read a scalar form field."""
    if field_name not in form:
        return default
    return form.getfirst(field_name, default)


def _optional_int(value: object) -> Optional[int]:
    """Convert a value to int when present."""
    if value in {None, ""}:
        return None
    return int(str(value))


class HITLRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the local HITL API."""

    server_version = "HITLLocalAPI/0.1"

    def log_message(self, format: str, *args: object) -> None:
        """Silence default request logs; the desktop UI owns user-facing status."""

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight for local browser-based prototypes."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", _origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.split("/") if part]

        try:
            if parsed.path in {"/", "/index.html"}:
                self._send_ui_index()
                return

            if parsed.path == "/health":
                _json_response(self, HTTPStatus.OK, {"status": "ok"})
                return

            if parsed.path == "/preflight":
                _json_response(self, HTTPStatus.OK, run_preflight().to_dict())
                return

            if len(path_parts) == 2 and path_parts[0] == "jobs":
                status = _status_with_urls(get_job_status(path_parts[1]))
                _json_response(self, HTTPStatus.OK, status)
                return

            if len(path_parts) == 3 and path_parts[0] == "jobs" and path_parts[2] == "result":
                result = get_job_result(path_parts[1])
                _json_response(self, HTTPStatus.OK, result)
                return

            if len(path_parts) == 3 and path_parts[0] == "jobs" and path_parts[2] == "download":
                self._send_completed_workbook(path_parts[1])
                return
        except KeyError as exc:
            _error_response(self, HTTPStatus.NOT_FOUND, str(exc))
            return
        except RuntimeError as exc:
            _error_response(self, HTTPStatus.CONFLICT, str(exc))
            return

        _error_response(self, HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def _send_ui_index(self) -> None:
        """Serve the prototype UI."""
        if not UI_INDEX.exists():
            _error_response(self, HTTPStatus.NOT_FOUND, "Prototype UI file was not found.")
            return

        body = UI_INDEX.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        """Route POST requests."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.split("/") if part]

        try:
            if parsed.path == "/sample-job":
                self._create_sample_job()
                return

            if len(path_parts) == 3 and path_parts[0] == "jobs" and path_parts[2] == "decision":
                self._update_job_decision(path_parts[1])
                return

            if parsed.path != "/jobs":
                _error_response(self, HTTPStatus.NOT_FOUND, "Unknown endpoint.")
                return

            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                self._create_job_from_upload()
                return
            if content_type.startswith("application/json"):
                self._create_job_from_json()
                return
        except ValueError as exc:
            _error_response(self, HTTPStatus.BAD_REQUEST, str(exc))
            return
        except KeyError as exc:
            _error_response(self, HTTPStatus.NOT_FOUND, str(exc))
            return
        except (IndexError, RuntimeError) as exc:
            _error_response(self, HTTPStatus.CONFLICT, str(exc))
            return

        _error_response(
            self,
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "Use multipart/form-data with a `file` field or application/json.",
        )

    def _json_payload(self) -> dict:
        """Read a JSON request body."""
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def _update_job_decision(self, job_id: str) -> None:
        """Update a human decision for one completed result row."""
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            raise ValueError("Decision updates must use application/json.")

        payload = self._json_payload()
        if "row_index" not in payload:
            raise ValueError("Decision update must include row_index.")
        decision = payload.get("decision")
        if not isinstance(decision, dict):
            raise ValueError("Decision update must include a decision object.")

        record = update_job_decision(job_id, int(payload["row_index"]), decision)
        _json_response(self, HTTPStatus.OK, {"record": record})

    def _create_sample_job(self) -> None:
        """Create a job from the packaged sample workbook."""
        if not SAMPLE_WORKBOOK.exists():
            _error_response(self, HTTPStatus.NOT_FOUND, "Sample workbook was not found.")
            return

        job_id = start_job(
            input_path=str(SAMPLE_WORKBOOK),
            output_dir=OUTPUT_DIR,
            essay_id_column="id",
            prompt_column="Topic",
            text_column="Essay",
            model="llama3:8b",
            start_ollama=True,
            limit=1,
        )
        status = _status_with_urls(get_job_status(job_id))
        _json_response(self, HTTPStatus.ACCEPTED, status)

    def _create_job_from_upload(self) -> None:
        """Create a job from a multipart workbook upload."""
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        input_path = _save_uploaded_file(form)
        job_id = start_job(
            input_path=input_path,
            output_dir=OUTPUT_DIR,
            essay_id_column=str(_field_value(form, "essay_id_column", "Student ID")),
            prompt_column=str(_field_value(form, "prompt_column", "Topic")),
            text_column=str(_field_value(form, "text_column", "Essay")),
            sheet_name=_field_value(form, "sheet_name") or None,
            model=str(_field_value(form, "model", "llama3:8b")),
            start_ollama=str(_field_value(form, "start_ollama", "true")).lower() != "false",
            limit=_optional_int(_field_value(form, "limit")),
        )
        status = _status_with_urls(get_job_status(job_id))
        _json_response(self, HTTPStatus.ACCEPTED, status)

    def _create_job_from_json(self) -> None:
        """Create a job from an already-local workbook path."""
        payload = self._json_payload()
        input_path = payload.get("input_path")
        if not input_path:
            raise ValueError("JSON request must include `input_path`.")
        if Path(input_path).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Only .xlsx inputs are supported.")
        if not Path(input_path).exists():
            raise ValueError(f"Input workbook does not exist: {input_path}")

        job_id = start_job(
            input_path=str(input_path),
            output_dir=payload.get("output_dir", str(OUTPUT_DIR)),
            essay_id_column=payload.get("essay_id_column", "Student ID"),
            prompt_column=payload.get("prompt_column", "Topic"),
            text_column=payload.get("text_column", "Essay"),
            sheet_name=payload.get("sheet_name") or None,
            model=payload.get("model", "llama3:8b"),
            start_ollama=payload.get("start_ollama", True) is not False,
            limit=payload.get("limit"),
        )
        status = _status_with_urls(get_job_status(job_id))
        _json_response(self, HTTPStatus.ACCEPTED, status)

    def _send_completed_workbook(self, job_id: str) -> None:
        """Stream a completed workbook to the UI."""
        result = get_job_result(job_id)
        output_path = Path(result["output_path"])
        if not output_path.exists():
            _error_response(self, HTTPStatus.NOT_FOUND, "Completed workbook file was not found.")
            return

        content_type = mimetypes.guess_type(output_path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(output_path.stat().st_size))
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{output_path.name}"',
        )
        self.end_headers()
        with output_path.open("rb") as input_file:
            shutil.copyfileobj(input_file, self.wfile)


def _parse_args() -> argparse.Namespace:
    """Parse server options."""
    parser = argparse.ArgumentParser(description="Run the local HITL API server.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    """Run the local HTTP API server."""
    args = _parse_args()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), HITLRequestHandler)
    print(f"HITL local API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHITL local API stopped.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
