"""eyewright tray - one windowless process: supervisor + tray + Decide dialog.

    pythonw supervisor/tray.py          # normal (tray icon, owns the supervisor)
    python  supervisor/tray.py --check  # headless self-check, no GUI, no model call

Reuses ``svcwatch.watch_one`` for the keep-alive loop, so the tray owns the
supervisor: one process, one startup entry, live health in the tooltip.

Threading contract (the wrinkle):
  - Tk owns the main thread (hidden root + ``after`` pump).
  - pystray runs on a worker thread; its menu callbacks only put on ``_events``.
  - Decisions run on another worker; results come back through ``_events``.
No widget is ever touched off the Tk thread.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir():
    # The venv's pythonw is console-subsystem (uv ships a copy of python.exe), so
    # launching it from the Startup shortcut always allocates a terminal - hiding
    # it after the fact is unreliable. Run with a GUI-subsystem pythonw instead;
    # this keeps pystray/Pillow importable from the venv without a console.
    sys.path.insert(0, str(VENV_SITE))
sys.path.insert(0, str(ROOT))   # import eyewright from the source checkout
sys.path.insert(0, str(HERE))   # import svcwatch

import svcwatch as svc  # noqa: E402

LOG_DIR = HERE / "logs"
PID_FILE = HERE / "tray.pid"
CONFIG = Path(os.environ.get("EYEWRIGHT_GATE", ROOT / "examples" / "gate.json"))
SERVICES = Path(os.environ.get("EYEWRIGHT_SERVICES", HERE / "services.json"))

STATE_CAP = 1_000_000   # total chars handed to the model
FILE_CAP = 200_000      # per-file cap
DEFAULT_QUESTION = "Is this acceptable?"

_events: "queue.Queue[tuple]" = queue.Queue()


def _hide_console() -> None:
    """Hide the console window the venv's ``pythonw`` shim still allocates.

    uv's ``.venv/Scripts/pythonw.exe`` is console-subsystem (unlike the base
    interpreter's GUI ``pythonw.exe``), so starting the tray from a GUI shortcut
    pops a terminal at logon. Hide it; a logon entry must leave no stray window.
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "tray.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _excepthook(exc, val, tb) -> None:
    log("".join(traceback.format_exception(exc, val, tb)))


def _title(health: dict) -> str:
    """Tray tooltip: 'eyewright - ready', or which service is down.

    The tooltip is the only thing a user reads without opening a window, so it
    says 'ready' rather than listing services that are up.
    """
    down = [n for n, v in health.items() if not v]
    if down:
        return "eyewright - " + ", ".join(down) + " down"
    return "eyewright - " + ("ready" if health else "no services")


def build_state(text: str, files, folders) -> str:
    """Assemble the state string: free text + text files + folder listings.

    Pure (no Tk, no network) so it is directly testable. Text-only and capped;
    truncation is announced inline so the model is never silently fed a stub.
    """
    parts = []
    if text.strip():
        parts.append(text.strip())
    budget = STATE_CAP
    for raw in files:
        p = Path(raw)
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            body = f"<unreadable: {e}>"
        if len(body) > FILE_CAP:
            body = body[:FILE_CAP] + f"\n<truncated at {FILE_CAP} chars>"
        chunk = f"--- file: {p.name} ---\n{body}"
        if len(chunk) > budget:
            parts.append(f"--- file: {p.name} ---\n<truncated: state budget reached>")
            continue
        budget -= len(chunk)
        parts.append(chunk)
    for raw in folders:
        d = Path(raw)
        try:
            names = sorted(x.name for x in d.iterdir())
        except OSError as e:
            names = [f"<unreadable: {e}>"]
        chunk = (
            f"--- folder: {d.name} ({len(names)} entries) ---\n"
            + "\n".join(f"- {n}" for n in names)
        )
        parts.append(chunk[:budget])
        budget -= min(len(chunk), budget)
    return "\n\n".join(parts)


def decide(text, files, folders, question, engine):
    """Call eyewright in-process. Runs on a worker thread, never the Tk thread."""
    from eyewright import ask

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    state = build_state(text, files, folders)
    return ask(cfg, state, question, engine=engine)


# The tray sits on the taskbar, whose theme is `SystemUsesLightTheme` — light
# glyphs on a dark bar, dark glyphs on a light one.
SCLERA_ON_DARK = "#e6edf3"
SCLERA_ON_LIGHT = "#1f2328"


def _sclera() -> str:
    """Glyph tone for the current taskbar theme (re-read every health poll)."""
    if os.name != "nt":
        return SCLERA_ON_DARK
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as k:
            light, _ = winreg.QueryValueEx(k, "SystemUsesLightTheme")
        return SCLERA_ON_LIGHT if light else SCLERA_ON_DARK
    except Exception:
        return SCLERA_ON_DARK


def _eye(color: str, sclera: str = SCLERA_ON_DARK):
    """Tray icon: an eye outlined and irised in the health colour.

    Tray icons here are light glyphs, so the sclera stays the theme's glyph tone
    and the health colour goes on the **outline and iris**. An iris alone was a
    ~5 px dot at 16 px and the colour was unreadable; the outline restores enough
    coloured area without filling the whole almond (which read as a green blob
    and put colour on ~4x more area than any neighbour).

    Eyelashes were tested and dropped: at 16 px three strokes over the lid read
    as antennae.

    Drawn instead of shipped as a PNG so the health colour *is* the icon, and at
    4x then downsampled because Windows does not anti-alias a 64 px source on the
    way down to the 16 px tray size (``SM_CXSMICON`` at 96 DPI).
    """
    import math

    from PIL import Image, ImageDraw

    s, n = 4, 64  # supersample factor, arc segments
    c = 64 * s / 2
    w, h, r = 31 * s, 20 * s, 12 * s
    upper = [(c - w + 2 * w * i / n, c - h * math.sin(math.pi * i / n)) for i in range(n + 1)]
    lower = [(c - w + 2 * w * i / n, c + h * math.sin(math.pi * i / n)) for i in range(n - 1, 0, -1)]
    img = Image.new("RGBA", (64 * s, 64 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon(upper + lower, fill=sclera, outline=color, width=4 * s)
    d.ellipse((c - r, c - r, c + r, c + r), fill=color)
    return img.resize((64, 64), Image.LANCZOS)


class App:
    def __init__(self, root, services, icon):
        self.root = root
        self.services = services
        self.icon = icon
        self.stop = threading.Event()
        self.files: list[str] = []
        self.folders: list[str] = []
        self.result_widget = None
        self.decide_button = None

    # ---- supervisor -----------------------------------------------------
    def start_supervisor(self) -> None:
        poll = float(self.services.get("poll_seconds", 15))
        for name, entry in self.services["services"].items():
            if not entry.get("enabled", True):
                continue
            threading.Thread(
                target=svc.watch_one,
                args=(name, entry, self.stop, poll),
                daemon=True,
            ).start()
            log(f"supervising {name}")

    def health(self) -> dict[str, bool]:
        return {
            name: svc.healthy(entry.get("health"))
            for name, entry in self.services["services"].items()
            if entry.get("enabled", True)
        }

    def health_loop(self) -> None:
        while not self.stop.is_set():
            try:
                h = self.health()
                ok = all(h.values()) if h else True
                self.icon.icon = _eye("#3fb950" if ok else "#d29922", _sclera())
                self.icon.title = _title(h)
            except Exception:
                log(traceback.format_exc())
            self.stop.wait(15)

    # ---- UI pump --------------------------------------------------------
    def pump(self) -> None:
        try:
            while True:
                kind, payload = _events.get_nowait()
                if kind == "decide":
                    self.open_decide()
                elif kind == "status":
                    self.show_status()
                elif kind == "start":
                    threading.Thread(
                        target=svc.cmd_once, args=(self.services,), daemon=True
                    ).start()
                elif kind == "logs":
                    os.startfile(LOG_DIR)
                elif kind == "result":
                    self.show_result(payload)
                elif kind == "quit":
                    self.stop.set()
                    self.icon.stop()
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def show_status(self) -> None:
        from tkinter import messagebox

        h = self.health()
        body = "\n".join(f"{n:<14} {'up' if v else 'DOWN'}" for n, v in h.items())
        messagebox.showinfo("eyewright status", body or "no services enabled")

    # ---- Decide window --------------------------------------------------
    def open_decide(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, scrolledtext, ttk

        if self.result_widget is not None and self.result_widget.winfo_exists():
            self.result_widget.master.deiconify()
            self.result_widget.master.lift()
            return

        win = tk.Toplevel(self.root)
        win.title("eyewright - Decide")
        win.geometry("640x720")
        win.columnconfigure(0, weight=1)

        picked = tk.Listbox(win, height=5)
        picked.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(2, 4))

        def add(kind: str) -> None:
            if kind == "files":
                paths = filedialog.askopenfilenames(parent=win)
                for p in paths:
                    self.files.append(p)
                    picked.insert("end", f"file: {p}")
            else:
                p = filedialog.askdirectory(parent=win)
                if p:
                    self.folders.append(p)
                    picked.insert("end", f"dir:  {p}")

        def remove() -> None:
            for idx in reversed(picked.curselection()):
                label = picked.get(idx)
                (self.files if label.startswith("file:") else self.folders).pop(idx)
                picked.delete(idx)

        bar = tk.Frame(win)
        bar.grid(row=2, column=0, columnspan=2, sticky="w", padx=10)
        tk.Button(bar, text="Add files...", command=lambda: add("files")).pack(side="left")
        tk.Button(bar, text="Add folder...", command=lambda: add("folders")).pack(side="left", padx=6)
        tk.Button(bar, text="Remove", command=remove).pack(side="left")

        tk.Label(win, text="Text").grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))
        text = scrolledtext.ScrolledText(win, height=7, wrap="word")
        text.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10)

        tk.Label(win, text="Question").grid(row=5, column=0, sticky="w", padx=10, pady=(10, 0))
        question = tk.Entry(win)
        question.insert(0, DEFAULT_QUESTION)
        question.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10)

        row = tk.Frame(win)
        row.grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        tk.Label(row, text="Engine").pack(side="left")
        engine = ttk.Combobox(
            row, values=["auto", "typed", "generative"], state="readonly", width=12
        )
        engine.set("auto")
        engine.pack(side="left", padx=6)
        decide_btn = tk.Button(row, text="Decide")
        decide_btn.pack(side="left", padx=10)
        status = tk.Label(row, text="", fg="#8b949e")
        status.pack(side="left")

        tk.Label(win, text="Result").grid(row=8, column=0, sticky="w", padx=10)
        result = scrolledtext.ScrolledText(win, height=12, wrap="word", state="disabled")
        result.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        win.rowconfigure(4, weight=1)
        win.rowconfigure(9, weight=2)

        self.result_widget, self.decide_button = result, decide_btn
        self._status = status
        self._text = text
        self._question = question
        self._engine = engine

        def submit() -> None:
            if not (text.get("1.0", "end").strip() or self.files or self.folders):
                from tkinter import messagebox

                messagebox.showwarning("eyewright", "Add text, a file, or a folder first.")
                return
            decide_btn.configure(state="disabled", text="Deciding...")
            status.configure(text="asking eyewright...")
            payload = (
                text.get("1.0", "end").strip(),
                list(self.files),
                list(self.folders),
                question.get().strip() or DEFAULT_QUESTION,
                engine.get(),
            )

            def work() -> None:
                try:
                    res = decide(*payload)
                except Exception as e:
                    log(traceback.format_exc())
                    res = {"error": str(e)}
                _events.put(("result", res))

            threading.Thread(target=work, daemon=True).start()

        decide_btn.configure(command=submit)

    def show_result(self, res) -> None:
        if self.result_widget is None or not self.result_widget.winfo_exists():
            return
        if "error" in res:
            head = f"ERROR: {res['error']}"
        else:
            ans = res.get("answer")
            conf = res.get("confidence")
            head = f"{ans}" + (f"   (confidence {conf})" if conf is not None else "")
            if res.get("fallback"):
                head += f"   [{res['fallback']}]"
        self.result_widget.configure(state="normal")
        self.result_widget.delete("1.0", "end")
        self.result_widget.insert("end", head + "\n\n" + json.dumps(res, indent=2, ensure_ascii=False))
        self.result_widget.configure(state="disabled")
        if self.decide_button is not None:
            self.decide_button.configure(state="normal", text="Decide")
        if getattr(self, "_status", None) is not None:
            self._status.configure(text="")


def _menu():
    import pystray

    return pystray.Menu(
        pystray.MenuItem("Decide...", lambda i, it: _events.put(("decide", None)), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Status", lambda i, it: _events.put(("status", None))),
        pystray.MenuItem("Start services", lambda i, it: _events.put(("start", None))),
        pystray.MenuItem("Open logs", lambda i, it: _events.put(("logs", None))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda i, it: _events.put(("quit", None))),
    )


def _claim_pid() -> bool:
    if PID_FILE.exists():
        try:
            old = int(PID_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            old = 0
        if old and old != os.getpid() and svc._pid_alive(old):
            log(f"another tray is running (pid {old}); exiting")
            return False
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def check() -> int:
    """Headless self-check: state assembly + config. No GUI, no model call."""
    import tempfile

    tmp = Path(tempfile.gettempdir()) / "eyewright-tray-check.txt"
    tmp.write_text("check-body", encoding="utf-8")
    state = build_state("free text", [tmp], [HERE])
    assert "free text" in state
    assert "--- file: eyewright-tray-check.txt ---" in state and "check-body" in state
    assert "--- folder: supervisor (" in state
    gate = json.loads(CONFIG.read_text(encoding="utf-8"))
    services = json.loads(SERVICES.read_text(encoding="utf-8"))
    assert gate.get("primary") and gate.get("generative", {}).get("model")
    assert services.get("services")

    def near(px, rgb, tol=4):
        return all(abs(a - b) <= tol for a, b in zip(px[:3], rgb))

    up, down = _eye("#3fb950"), _eye("#d29922")
    assert up.size == (64, 64)
    assert up.getpixel((2, 2))[3] == 0                  # transparent corner, not a square
    assert up.getpixel((32, 32))[:3] == (63, 185, 80)    # iris carries the health colour
    assert near(up.getpixel((4, 32)), (63, 185, 80))     # so does the outline
    assert up.getpixel((13, 32))[:3] == (230, 237, 243)  # sclera on a dark taskbar
    assert down.getpixel((32, 32))[:3] == (210, 153, 34)

    # Theme switch: on a light taskbar the glyph must go dark, or it vanishes.
    assert near(_eye("#3fb950", SCLERA_ON_LIGHT).getpixel((13, 32)), (31, 35, 40))
    assert _sclera() in (SCLERA_ON_DARK, SCLERA_ON_LIGHT)

    assert _title({"laya-serve": True}) == "eyewright - ready"
    assert _title({"laya-serve": False, "ollama": True}) == "eyewright - laya-serve down"
    assert _title({}) == "eyewright - no services"

    print(
        f"ok: state assembly + configs ({CONFIG.name}, {SERVICES.name}) + tray eye; "
        f"generative={gate['generative']['model']}"
    )
    return 0


def main() -> int:
    _hide_console()

    import tkinter as tk

    import pystray

    if not _claim_pid():
        return 0
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    sys.stderr = open(LOG_DIR / "tray.log", "a", encoding="utf-8", buffering=1)
    sys.excepthook = _excepthook

    services = json.loads(SERVICES.read_text(encoding="utf-8"))
    root = tk.Tk()
    root.withdraw()
    icon = pystray.Icon("eyewright", _eye("#8b949e", _sclera()), "eyewright", _menu())
    app = App(root, services, icon)

    app.start_supervisor()
    threading.Thread(target=icon.run, daemon=True).start()
    threading.Thread(target=app.health_loop, daemon=True).start()
    root.after(100, app.pump)
    try:
        root.mainloop()
    finally:
        app.stop.set()
        try:
            PID_FILE.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(check() if "--check" in sys.argv else main())
