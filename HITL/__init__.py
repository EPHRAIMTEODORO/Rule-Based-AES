"""HITL backend package for desktop-app integration."""

from .app_backend import (
    clear_job,
    get_job_result,
    get_job_status,
    list_jobs,
    start_job,
    update_job_decision,
)
from .hitl_processor import ProcessingResult, process_workbook
from .preflight import PreflightResult, run_preflight

__all__ = [
    "PreflightResult",
    "ProcessingResult",
    "clear_job",
    "get_job_result",
    "get_job_status",
    "list_jobs",
    "process_workbook",
    "run_preflight",
    "start_job",
    "update_job_decision",
]
