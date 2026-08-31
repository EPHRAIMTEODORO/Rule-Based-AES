"""Smoke test for the HITL app backend job API."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from HITL import get_job_result, get_job_status, start_job  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate the desktop UI calling the HITL app backend."
    )
    parser.add_argument("--input", default="HITL/Essays.xlsx")
    parser.add_argument("--output-dir", default="HITL/outputs")
    parser.add_argument("--essay-id-column", default="id")
    parser.add_argument("--prompt-column", default="Topic")
    parser.add_argument("--text-column", default="Essay")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--no-start-ollama", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    job_id = start_job(
        input_path=args.input,
        output_dir=args.output_dir,
        essay_id_column=args.essay_id_column,
        prompt_column=args.prompt_column,
        text_column=args.text_column,
        limit=args.limit,
        start_ollama=not args.no_start_ollama,
        quiet=True,
    )
    print(f"started job: {job_id}", flush=True)

    while True:
        status = get_job_status(job_id)
        progress = status.get("progress", {})
        message = progress.get("message", status["status"])
        print(f"{status['status']}: {message}", flush=True)

        if status["status"] == "completed":
            result = get_job_result(job_id)
            print(f"output: {result['output_path']}", flush=True)
            print(f"rows: {result['rows_processed']}", flush=True)
            print(f"columns: {len(result['columns'])}", flush=True)
            return

        if status["status"] == "failed":
            raise SystemExit(status.get("error") or "Job failed.")

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
