from __future__ import annotations

import cgi
import io
import json
import logging
import sys
import tarfile
import threading
import uuid
import zipfile
from dataclasses import dataclass, field
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from typing import Any

_log = logging.getLogger(__name__)

# Maximum accepted upload size (bytes). Reject larger files before reading body.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

from paper_forensics.audit import run_audit
from paper_forensics.config import AuditConfig
from paper_forensics.report.html_report import render_review_workspace
from paper_forensics.report.review_payload import build_review_payload
from paper_forensics.scoring.schemas import portable_path


SUPPORTED_UPLOAD_SUFFIXES = (
    ".tex",
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
)


@dataclass
class ReviewJob:
    job_id: str
    upload_name: str
    status: str = "queued"
    stage: str = "preparing"
    progress: float = 0.05
    message: str = "Preparing upload"
    error: str | None = None
    review_payload: dict[str, Any] | None = None
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    work_dir: Path | None = None


class ReviewAppState:
    def __init__(self, corpus_path: Path | None, output_root: Path) -> None:
        self.corpus_path = corpus_path
        self.output_root = output_root
        self.jobs: dict[str, ReviewJob] = {}
        self.lock = threading.Lock()

    def create_job(self, upload_name: str) -> ReviewJob:
        job = ReviewJob(job_id=uuid.uuid4().hex[:12], upload_name=upload_name)
        with self.lock:
            self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> ReviewJob | None:
        with self.lock:
            return self.jobs.get(job_id)


def build_review_server(host: str, port: int, corpus_path: Path | None, output_root: Path) -> ThreadingHTTPServer:
    state = ReviewAppState(corpus_path=corpus_path, output_root=output_root)
    handler = partial(ReviewAppHandler, state=state)
    return ThreadingHTTPServer((host, port), handler)


def serve_review_app(host: str, port: int, corpus_path: Path | None, output_root: Path) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"WARNING: paper-forensics is binding to {host!r} (non-localhost). "
            "Ensure the network environment is trusted before proceeding.",
            file=sys.stderr,
        )
    server = build_review_server(host=host, port=port, corpus_path=corpus_path, output_root=output_root)
    print(f"paper-forensics app listening at http://{host}:{port}")
    if corpus_path:
        print(f"corpus: {corpus_path}")
    print(f"artifacts: {output_root.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down paper-forensics app.")
    finally:
        server.server_close()


class ReviewAppHandler(BaseHTTPRequestHandler):
    server_version = "paper-forensics/0.1"

    def __init__(self, *args: Any, state: ReviewAppState, **kwargs: Any) -> None:
        self.state = state
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            self._serve_shell()
            return
        if self.path == "/health":
            self._write_json({"status": "ok"})
            return
        if self.path.startswith("/api/jobs/"):
            suffix = self.path[len("/api/jobs/") :]
            if "/artifacts/" in suffix:
                job_id, _, kind = suffix.partition("/artifacts/")
                self._serve_artifact(job_id, kind)
                return
            self._serve_job_status(suffix.split("/", 1)[0])
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/jobs":
            self._create_job()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _serve_shell(self) -> None:
        html = render_review_workspace(
            initial_payload=None,
            app_mode=True,
            app_config={
                "mode": "app",
                "page_title": "paper-forensics review app",
                "create_job_endpoint": "/api/jobs",
                "job_status_prefix": "/api/jobs/",
                "corpus_label": f"Corpus: {self.state.corpus_path}" if self.state.corpus_path else "Corpus not configured",
            },
        )
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _create_job(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
        if content_length > MAX_UPLOAD_BYTES:
            self._write_json(
                {"error": f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB size limit."},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        manuscript = form["manuscript"] if "manuscript" in form else None
        if manuscript is None or not getattr(manuscript, "filename", ""):
            self._write_json({"error": "No manuscript file was provided."}, status=HTTPStatus.BAD_REQUEST)
            return

        upload_name = Path(manuscript.filename).name
        if not _is_supported_upload(upload_name):
            self._write_json(
                {"error": "Unsupported upload type. Accepted formats are .tex, .zip, .tar, .tgz, and .tar.gz."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        upload_bytes = manuscript.file.read()
        job = self.state.create_job(upload_name)
        worker = threading.Thread(
            target=_run_review_job,
            args=(self.state, job.job_id, upload_name, upload_bytes),
            daemon=True,
        )
        worker.start()
        self._write_json({"job_id": job.job_id, "status": job.status, "message": job.message}, status=HTTPStatus.ACCEPTED)

    def _serve_job_status(self, job_id: str) -> None:
        job = self.state.get_job(job_id)
        if not job:
            self._write_json({"error": "Unknown job."}, status=HTTPStatus.NOT_FOUND)
            return
        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress,
            "message": job.message,
            "error": job.error,
        }
        if job.review_payload:
            payload["review_payload"] = job.review_payload
        self._write_json(payload)

    def _serve_artifact(self, job_id: str, kind: str) -> None:
        job = self.state.get_job(job_id)
        if not job or kind not in job.artifact_paths:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = job.artifact_paths[kind]
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = {
            "json": "application/json; charset=utf-8",
            "csv": "text/csv; charset=utf-8",
            "html": "text/html; charset=utf-8",
        }.get(kind, "application/octet-stream")
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(body)

    def _write_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _run_review_job(state: ReviewAppState, job_id: str, upload_name: str, upload_bytes: bytes) -> None:
    job = state.get_job(job_id)
    if not job:
        return

    try:
        work_dir = state.output_root / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        job.work_dir = work_dir

        _update_job(job, status="running", stage="preparing", progress=0.12, message="Preparing upload")
        manuscript_root, main_tex_path = prepare_uploaded_project(upload_name, upload_bytes, work_dir / "input")

        _update_job(job, stage="resolving", progress=0.32, message=f"Resolved manuscript at {main_tex_path.name}")
        output_dir = work_dir / "artifacts"
        config = AuditConfig(corpus_path=state.corpus_path, output_dir=output_dir)

        _update_job(job, stage="analyzing", progress=0.72, message="Running sentence-level audit")
        result = run_audit(main_tex_path, config)
        job.artifact_paths = {kind: Path(path) for kind, path in result.generated_files.items()}
        result.generated_files = {
            kind: f"/api/jobs/{job.job_id}/artifacts/{kind}"
            for kind in job.artifact_paths
        }

        _update_job(job, stage="finalizing", progress=0.92, message="Preparing review workspace")
        review_payload = build_review_payload(result)
        review_payload["document"]["upload_root"] = portable_path(manuscript_root)
        review_payload["document"]["main_tex"] = portable_path(main_tex_path)
        job.review_payload = review_payload

        _update_job(job, status="completed", stage="finalizing", progress=1.0, message="Review workspace ready")
    except Exception as exc:  # noqa: BLE001
        _log.exception("Job %s failed", job_id)
        _update_job(
            job,
            status="failed",
            stage="finalizing",
            progress=1.0,
            error="Analysis could not be completed. Review the server logs for details.",
            message="Analysis failed",
        )


def _update_job(
    job: ReviewJob,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: float | None = None,
    message: str | None = None,
    error: str | None = None,
) -> None:
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if message is not None:
        job.message = message
    if error is not None:
        job.error = error


def prepare_uploaded_project(upload_name: str, upload_bytes: bytes, target_dir: Path) -> tuple[Path, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    upload_path = target_dir / Path(upload_name).name
    upload_path.write_bytes(upload_bytes)

    lowered = upload_path.name.lower()
    if lowered.endswith(".tex"):
        return upload_path.parent, upload_path

    project_dir = target_dir / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    if lowered.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(upload_bytes)) as archive:
            _safe_extract_zip(archive, project_dir)
    elif lowered.endswith(".tar") or lowered.endswith(".tgz") or lowered.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(upload_bytes), mode=_tar_mode(lowered)) as archive:
            _safe_extract_tar(archive, project_dir)
    else:
        raise ValueError("Unsupported upload type.")

    main_tex = detect_main_tex(project_dir)
    return project_dir, main_tex


def detect_main_tex(project_dir: Path) -> Path:
    candidates = sorted(project_dir.rglob("*.tex"))
    if not candidates:
        raise ValueError("No .tex file was found in the uploaded project.")

    def score(path: Path) -> tuple[int, int, int, str]:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        has_document = int("\\begin{document}" in text)
        preferred_name = int(path.name.lower() == "main.tex")
        depth = -len(path.relative_to(project_dir).parts)
        return (preferred_name, has_document, depth, str(path))

    return max(candidates, key=score)


def _is_supported_upload(filename: str) -> bool:
    lowered = filename.lower()
    return any(lowered.endswith(suffix) for suffix in SUPPORTED_UPLOAD_SUFFIXES)


def _tar_mode(filename: str) -> str:
    return "r:gz" if filename.endswith(".gz") or filename.endswith(".tgz") else "r:"


def _safe_extract_zip(archive: zipfile.ZipFile, target_dir: Path) -> None:
    for member in archive.infolist():
        destination = (target_dir / member.filename).resolve()
        if not _is_within(destination, target_dir):
            raise ValueError("Archive contains unsafe paths.")
        archive.extract(member, target_dir)


def _safe_extract_tar(archive: tarfile.TarFile, target_dir: Path) -> None:
    for member in archive.getmembers():
        destination = (target_dir / member.name).resolve()
        if not _is_within(destination, target_dir):
            raise ValueError("Archive contains unsafe paths.")
    archive.extractall(target_dir)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def find_available_port(host: str, preferred_port: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, preferred_port))
            return preferred_port
        except OSError:
            probe.bind((host, 0))
            return int(probe.getsockname()[1])
