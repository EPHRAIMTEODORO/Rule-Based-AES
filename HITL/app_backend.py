"""App-facing job runner for the HITL desktop backend.

This module wraps `process_workbook` in a small in-process job API. A desktop UI
can start a processing job, poll status for progress updates, and fetch the
completed rows plus workbook path when the job finishes.
"""

from __future__ import annotations

import copy
import json
import math
import re
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

try:
    from .hitl_processor import (
        HUMAN_DECISION_FIELDNAMES,
        ProcessingResult,
        process_workbook,
        write_completed_workbook,
    )
except ImportError:  # Allows `python HITL/app_backend.py ...` during local testing.
    from hitl_processor import (
        HUMAN_DECISION_FIELDNAMES,
        ProcessingResult,
        process_workbook,
        write_completed_workbook,
    )


HITL_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = HITL_DIR / "outputs"
JOB_STATUSES = {"queued", "running", "completed", "failed"}
DECISION_FIELDNAMES = set(HUMAN_DECISION_FIELDNAMES)


@dataclass
class AppJob:
    """State for a single app processing job."""

    job_id: str
    input_path: str
    output_path: str
    status: str = "queued"
    progress: dict = field(default_factory=dict)
    result: Optional[dict] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    created_at: str = field(default_factory=lambda: _utc_now())
    updated_at: str = field(default_factory=lambda: _utc_now())

    def public_status(self) -> dict:
        """Return the status payload intended for the UI."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "progress": copy.deepcopy(self.progress),
            "error": self.error,
            "error_type": self.error_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


_JOBS: dict[str, AppJob] = {}
_JOBS_LOCK = threading.RLock()


def _utc_now() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(value: str) -> str:
    """Return a filesystem-friendly name segment."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "uploaded_workbook"


def _json_safe(value: object) -> object:
    """Convert nested values into JSON-safe primitives."""
    try:
        json.dumps(value)
        return value
    except TypeError:
        pass

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _normalize_final_score(value: object) -> object:
    """Normalize a human final score to a 1-6 half-point value."""
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Rater_Final_Score must be a number from 1 to 6.") from exc
    if not math.isfinite(numeric):
        raise ValueError("Rater_Final_Score must be a finite number from 1 to 6.")
    numeric = max(1.0, min(6.0, numeric))
    return round(numeric * 2) / 2


def _normalize_decision_payload(decision: dict) -> dict:
    """Keep only supported human decision fields and normalize score values."""
    normalized = {
        key: value
        for key, value in decision.items()
        if key in DECISION_FIELDNAMES
    }
    if "Rater_Final_Score" in normalized:
        normalized["Rater_Final_Score"] = _normalize_final_score(
            normalized["Rater_Final_Score"]
        )
    if normalized.get("Rater_Final_Score") not in {None, ""}:
        normalized["Decision_Status"] = normalized.get("Decision_Status") or "Finalized"
    elif any(normalized.get(key) for key in DECISION_FIELDNAMES - {"Decision_Status"}):
        normalized["Decision_Status"] = normalized.get("Decision_Status") or "Review"
    else:
        normalized["Decision_Status"] = normalized.get("Decision_Status") or "Pending"
    normalized["Decision_Updated_At"] = _utc_now()
    return _json_safe(normalized)


def _create_output_path(input_path: str, output_dir: Union[str, Path]) -> tuple[str, str]:
    """Create a job ID and a predictable output workbook path."""
    job_id = uuid.uuid4().hex
    source_stem = _safe_filename(Path(input_path).stem)
    job_dir = Path(output_dir) / job_id
    output_path = job_dir / f"{source_stem}_completed.xlsx"
    return job_id, str(output_path)


def _set_job_state(job_id: str, **updates: object) -> None:
    """Apply updates to a job under lock."""
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        for key, value in updates.items():
            setattr(job, key, value)
        job.updated_at = _utc_now()


def _progress_callback(job_id: str):
    """Build a processor progress callback for a job."""

    def callback(event: dict) -> None:
        stage = str(event.get("stage", "running"))
        status = "completed" if stage == "complete" else "running"
        _set_job_state(job_id, status=status, progress=_json_safe(event))

    return callback


def _run_job(job_id: str, processor_kwargs: dict) -> None:
    """Run one workbook processing job in a background thread."""
    _set_job_state(
        job_id,
        status="running",
        progress={"stage": "starting", "message": "Starting job"},
    )

    try:
        result: ProcessingResult = process_workbook(
            **processor_kwargs,
            progress_callback=_progress_callback(job_id),
        )
    except Exception as exc:
        _set_job_state(
            job_id,
            status="failed",
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
            progress={"stage": "failed", "message": str(exc)},
        )
        return

    result_payload = _json_safe(result.to_dict())
    _set_job_state(
        job_id,
        status="completed",
        result=result_payload,
        progress={
            "stage": "complete",
            "message": "Completed workbook is ready",
            "rows_processed": result.rows_processed,
            "output_path": result.output_path,
        },
    )


def start_job(
    input_path: str,
    output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
    essay_id_column: Optional[str] = "Student ID",
    prompt_column: Optional[str] = "Topic",
    text_column: Optional[str] = "Essay",
    sheet_name: Optional[str] = None,
    model: str = "llama3:8b",
    ollama_url: str = "http://127.0.0.1:11434/api/chat",
    ollama_command: str = "ollama",
    ollama_startup_timeout: float = 30.0,
    start_ollama: bool = True,
    temperature: float = 0.0,
    timeout: int = 180,
    limit: Optional[int] = None,
    delay_seconds: float = 0.0,
    quiet: bool = True,
) -> str:
    """Start processing an uploaded workbook and return a job ID."""
    job_id, output_path = _create_output_path(input_path, output_dir)
    job = AppJob(job_id=job_id, input_path=str(input_path), output_path=output_path)

    with _JOBS_LOCK:
        _JOBS[job_id] = job

    processor_kwargs = {
        "input_path": input_path,
        "output_path": output_path,
        "essay_id_column": essay_id_column,
        "prompt_column": prompt_column,
        "text_column": text_column,
        "sheet_name": sheet_name,
        "model": model,
        "ollama_url": ollama_url,
        "ollama_command": ollama_command,
        "ollama_startup_timeout": ollama_startup_timeout,
        "start_ollama": start_ollama,
        "temperature": temperature,
        "timeout": timeout,
        "limit": limit,
        "delay_seconds": delay_seconds,
        "quiet": quiet,
    }
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, processor_kwargs),
        name=f"hitl-job-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return job_id


def get_job_status(job_id: str) -> dict:
    """Return current job status for UI polling."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job ID: {job_id}")
        return job.public_status()


def get_job_result(job_id: str) -> dict:
    """Return completed job result with rows and output workbook path."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job ID: {job_id}")
        if job.status == "failed":
            raise RuntimeError(job.error or "Job failed.")
        if job.status != "completed" or job.result is None:
            raise RuntimeError(f"Job is not complete. Current status: {job.status}")
        return copy.deepcopy(job.result)


def update_job_decision(job_id: str, row_index: int, decision: dict) -> dict:
    """Update one human rater decision and rewrite the completed workbook."""
    if row_index < 0:
        raise IndexError("row_index must be zero or greater.")

    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job ID: {job_id}")
        if job.status == "failed":
            raise RuntimeError(job.error or "Job failed.")
        if job.status != "completed" or job.result is None:
            raise RuntimeError(f"Job is not complete. Current status: {job.status}")

        result = copy.deepcopy(job.result)
        records = result.get("records", [])
        columns = result.get("columns", [])
        if row_index >= len(records):
            raise IndexError(f"row_index {row_index} is outside the result rows.")

        normalized_decision = _normalize_decision_payload(decision)
        records[row_index].update(normalized_decision)
        for fieldname in HUMAN_DECISION_FIELDNAMES:
            if fieldname not in columns:
                columns.append(fieldname)

        result["records"] = records
        result["columns"] = columns
        write_completed_workbook(job.output_path, columns, records)

        job.result = _json_safe(result)
        job.updated_at = _utc_now()
        return copy.deepcopy(records[row_index])


def list_jobs() -> list[dict]:
    """Return public status for all known jobs."""
    with _JOBS_LOCK:
        return [job.public_status() for job in _JOBS.values()]


def clear_job(job_id: str) -> None:
    """Remove a completed or failed job from the in-memory registry."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job ID: {job_id}")
        if job.status not in {"completed", "failed"}:
            raise RuntimeError(f"Cannot clear a job while it is {job.status}.")
        del _JOBS[job_id]
