from __future__ import annotations

import argparse
from pathlib import Path

from paper_forensics.app_server import serve_review_app
from paper_forensics.audit import run_audit
from paper_forensics.config import AuditConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-forensics", description="TeX-first sentence-level manuscript review.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit a TeX paper.")
    audit_parser.add_argument("input_path", type=Path, help="Path to the main .tex file.")
    audit_parser.add_argument("--corpus", type=Path, default=None, help="Folder containing local literature files.")
    audit_parser.add_argument("--output", type=Path, default=Path("outputs/latest"), help="Output folder.")
    audit_parser.add_argument("--max-matches", type=int, default=3, help="Number of top plagiarism matches to keep.")
    audit_parser.add_argument(
        "--min-sentence-chars",
        type=int,
        default=25,
        help="Discard short sentence fragments below this character count.",
    )

    app_parser = subparsers.add_parser("app", help="Launch the local review application.")
    app_parser.add_argument("--corpus", type=Path, default=None, help="Folder containing local literature files.")
    app_parser.add_argument("--output-root", type=Path, default=Path("outputs/app_runs"), help="Artifact root folder.")
    app_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    app_parser.add_argument("--port", type=int, default=8765, help="Port for the local review app.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "audit":
        config = AuditConfig(
            corpus_path=args.corpus,
            output_dir=args.output,
            max_matches=args.max_matches,
            min_sentence_chars=args.min_sentence_chars,
        )
        result = run_audit(args.input_path, config)
        print("Audit complete.")
        for label, path in result.generated_files.items():
            print(f"{label}: {path}")
    elif args.command == "app":
        serve_review_app(
            host=args.host,
            port=args.port,
            corpus_path=args.corpus,
            output_root=args.output_root,
        )


if __name__ == "__main__":
    main()
