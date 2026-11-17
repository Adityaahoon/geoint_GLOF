"""Lightweight background-job runner with persistent, reproducible processing logs.

Each job is recorded in `processing_jobs` with its parameters, progress, log lines,
result and errors. A thread pool is sufficient for a single-node research deployment;
swap for Celery/RQ for multi-node use.
"""
from __future__ import annotations

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

from .database import SessionLocal
from .models import ProcessingJob

logger = logging.getLogger("glacioguard.jobs")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gg-job")


class JobContext:
    """Passed to job functions so they can report progress and log messages."""

    def __init__(self, job_id: int):
        self.job_id = job_id

    def _update(self, **fields: Any) -> None:
        db = SessionLocal()
        try:
            job = db.get(ProcessingJob, self.job_id)
            if job is None:
                return
            for k, v in fields.items():
                setattr(job, k, v)
            db.commit()
        finally:
            db.close()

    def log(self, message: str, progress: float | None = None) -> None:
        logger.info("[job %s] %s", self.job_id, message)
        db = SessionLocal()
        try:
            job = db.get(ProcessingJob, self.job_id)
            if job is None:
                return
            stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            job.log = (job.log or "") + f"{stamp} {message}\n"
            if progress is not None:
                job.progress = float(max(0.0, min(1.0, progress)))
            db.commit()
        finally:
            db.close()


def create_job(job_type: str, parameters: dict | None = None) -> int:
    db = SessionLocal()
    try:
        job = ProcessingJob(job_type=job_type, parameters=parameters or {}, status="queued", log="")
        db.add(job)
        db.commit()
        return job.id
    finally:
        db.close()


def run_job(job_id: int, fn: Callable[[JobContext], dict | None]) -> None:
    ctx = JobContext(job_id)
    ctx._update(status="running", started_at=datetime.utcnow())
    try:
        result = fn(ctx)
        ctx._update(status="completed", progress=1.0, result=result or {}, finished_at=datetime.utcnow())
    except Exception as exc:  # noqa: BLE001 - we persist every failure
        logger.exception("Job %s failed", job_id)
        ctx.log(f"ERROR: {exc}")
        ctx._update(status="failed", error=f"{exc}\n{traceback.format_exc()}", finished_at=datetime.utcnow())


def submit(job_type: str, fn: Callable[[JobContext], dict | None], parameters: dict | None = None,
           synchronous: bool = False) -> int:
    job_id = create_job(job_type, parameters)
    if synchronous:
        run_job(job_id, fn)
    else:
        _executor.submit(run_job, job_id, fn)
    return job_id

