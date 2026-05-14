from __future__ import annotations

import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, StringVar, Tk, ttk, messagebox

# ---------------------------------------------------------------------------
# Bootstrap: add the repo src/ directory so the package is importable even
# when paper-forensics has not been installed via pip install -e .
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from paper_forensics.app_server import build_review_server, find_available_port
except Exception as _import_err:  # noqa: BLE001
    # Show a readable error in a dialog before the window disappears.
    _root = Tk()
    _root.withdraw()
    messagebox.showerror(
        "paper-forensics — startup error",
        f"Could not load paper-forensics:\n\n{_import_err}\n\n"
        "Make sure the repo folder structure is intact and that Jinja2 is "
        "installed (pip install jinja2).",
    )
    sys.exit(1)


HOST = "127.0.0.1"
PREFERRED_PORT = 8765


class LauncherApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("paper-forensics launcher")
        self.root.geometry("540x240")
        self.root.minsize(520, 220)

        self.repo_root = Path(__file__).resolve().parent
        self.output_root = self.repo_root / "outputs" / "app_runs"
        default_corpus = self.repo_root / "examples" / "corpus"
        self.corpus_path = default_corpus if default_corpus.exists() else None

        self.server = None
        self.server_thread = None
        self.server_url = None

        self.status_var = StringVar(value="Starting local review app…")
        self.url_var = StringVar(value="")
        self.corpus_var = StringVar(
            value=f"Corpus: {self.corpus_path}" if self.corpus_path else "Corpus: not configured"
        )

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(50, self.start_server)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill=BOTH, expand=True)

        title = ttk.Label(frame, text="paper-forensics", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            frame,
            text="No terminal required. This window keeps the local review app running while you attach a .tex file and click Analyze in your browser.",
            wraplength=480,
            justify=LEFT,
        )
        subtitle.pack(anchor="w", pady=(8, 14))

        status = ttk.Label(frame, textvariable=self.status_var, wraplength=480, justify=LEFT)
        status.pack(anchor="w")

        corpus = ttk.Label(frame, textvariable=self.corpus_var, wraplength=480, justify=LEFT)
        corpus.pack(anchor="w", pady=(8, 0))

        url = ttk.Label(frame, textvariable=self.url_var, foreground="#2a5a8a", wraplength=480, justify=LEFT)
        url.pack(anchor="w", pady=(8, 0))

        hint = ttk.Label(
            frame,
            text="Workflow: 1. Browser opens automatically. 2. Click Choose File. 3. Select your TeX file or project archive. 4. Click Analyze.",
            wraplength=480,
            justify=LEFT,
        )
        hint.pack(anchor="w", pady=(16, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(18, 0))

        self.open_button = ttk.Button(buttons, text="Open Browser", command=self.open_browser, state="disabled")
        self.open_button.pack(side=LEFT)

        close_button = ttk.Button(buttons, text="Stop App", command=self.close)
        close_button.pack(side=RIGHT)

    def start_server(self) -> None:
        try:
            port = find_available_port(HOST, PREFERRED_PORT)
            self.server_url = f"http://{HOST}:{port}"
            self.server = build_review_server(
                host=HOST,
                port=port,
                corpus_path=self.corpus_path,
                output_root=self.output_root,
            )
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.status_var.set("Local review app is running.")
            self.url_var.set(f"Open review workspace: {self.server_url}")
            self.open_button.config(state="normal")
            self.root.after(250, self.open_browser)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("paper-forensics", f"Unable to start the local review app.\n\n{exc}")
            self.close()

    def open_browser(self) -> None:
        if self.server_url:
            webbrowser.open(self.server_url, new=2)

    def close(self) -> None:
        try:
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    LauncherApp().run()
