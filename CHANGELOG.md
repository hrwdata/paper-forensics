# Changelog

All notable changes to paper-forensics are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- `Open Paper Forensics.cmd` double-click launcher (Windows) — starts the local review app with no terminal required.
- `launch_paper_forensics.pyw` Tkinter GUI launcher used by the `.cmd` entry point.
- `LICENSE` file (MIT).
- AI-assisted tell evidence summaries, category counts, and richer sentence-level export fields in `audit.json`, `audit.csv`, and `report.html`.

### Changed
- Upload size capped at 50 MB; requests exceeding the limit receive a 413 response before the body is read.
- Job failure errors are no longer forwarded verbatim to the client; details are logged server-side only.
- `serve_review_app` prints a console warning when binding to a non-localhost interface.
- `pyproject.toml`: author corrected; `pytest-cov>=4.0` added to dev extras.
- Review UI wording now describes the AI component as heuristic AI-assisted tell review rather than a definitive detector.
- Review UI font uses **Inter** with `ui-sans-serif, system-ui` fallbacks.

---

## [0.1.0] — 2026-04-20

### Added
- Initial release.
- Sentence-level plagiarism risk scoring against a local TeX corpus (TF-IDF vector similarity + lexical overlap + rare-phrase overlap).
- Sentence-level AI-rhetoric risk scoring (phrase patterns, semantic thinness, style-shift, smoothness, heuristic classifier).
- `paper-forensics audit` CLI: writes `audit.json`, `audit.csv`, and `report.html`.
- `paper-forensics app` CLI: starts a local HTTP server for upload-and-review workflow.
- Three-pane review workspace (outline, document, inspector).
- Archive upload support: `.zip`, `.tar`, `.tar.gz`, `.tgz`.
- Auto-detection of `main.tex` inside uploaded project archives.
- Safe archive extraction with path-traversal checks.
