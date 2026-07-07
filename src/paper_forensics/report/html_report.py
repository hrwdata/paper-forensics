from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paper_forensics.report.review_payload import build_review_payload
from paper_forensics.scoring.schemas import AuditResult


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
ASSET_DIR = Path(__file__).resolve().parent / "assets"


def write_html_report(result: AuditResult, path: Path) -> None:
    html = render_review_workspace(
        initial_payload=build_review_payload(result),
        app_mode=False,
        app_config={
            "mode": "report",
            "page_title": "paper-forensics review report",
        },
    )
    path.write_text(html, encoding="utf-8")


def render_review_workspace(
    initial_payload: dict[str, Any] | None,
    app_mode: bool,
    app_config: dict[str, Any] | None = None,
) -> str:
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("review.html")
    return template.render(
        review_css=_asset_text("review_app.css"),
        review_js=_asset_text("review_app.js"),
        initial_payload_json=json.dumps(initial_payload),
        app_config_json=json.dumps(app_config or {}),
        app_mode=app_mode,
    )


def _asset_text(filename: str) -> str:
    return (ASSET_DIR / filename).read_text(encoding="utf-8")
