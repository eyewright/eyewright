"""svcwatch - a tiny keep-alive supervisor for local model services.

Reads ``supervisor/services.json`` and keeps each enabled service running: probes
its health URL, starts it (detached) when down, restarts with backoff, and logs.
The descriptor is deliberately generic so ctxd's Model Router (M3 adapter family)
can adopt the same contract later.

    uv run python supervisor/svcwatch.py --status
    uv run python supervisor/svcwatch.py --once        # start anything down, exit
    uv run python supervisor/svcwatch.py               # watch (default)

Logs: ``supervisor/logs/svcwatch.log`` and one log per service.
"""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "services.json"
LOG_DIR = HERE / "logs"
PID_FILE = HERE / "svcwatch.pid"


def healthy(url, timeout=3.0):
    if not url:
        return True
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


def _pid_alive(pid):
    if os.name == "nt":
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "svcwatch.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def start(name, svc):
    cwd = os.path.expanduser(os.path.expandvars(svc.get("cwd") or str(HERE)))
    env = dict(os.environ)
    env.update(svc.get("env") or {})
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logf = LOG_DIR / Path(svc.get("log") or f"{name}.log").name
    fh = open(logf, "a", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
    proc = subprocess.Popen(svc["cmd"], cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, creationflags=flags)
    log(f"started {name} (pid {proc.pid}) -> {logf}")
    return proc


def wait_healthy(url, proc, grace_s, poll=3.0):
    """Wait up to grace_s for health. Returns early if the process exits."""
    deadline = time.time() + grace_s
    while time.time() < deadline:
        if healthy(url):
            return True
        if proc is not None and proc.poll() is not None:
            return False
        time.sleep(poll)
    return healthy(url)


def watch_one(name, svc, stop, default_poll):
    url = svc.get("health")
    restart = svc.get("restart") or {}
    backoffs = restart.get("backoff_s") or [5, 15, 60, 300]
    grace = float(restart.get("startup_grace_s") or svc.get("startup_grace_s") or 60)
    poll = float(restart.get("poll_seconds") or svc.get("poll_seconds") or default_poll)
    proc = None
    fail = 0
    while not stop.is_set():
        if healthy(url):
            fail = 0
            stop.wait(poll)
            continue
        # Down, or a just-started child that has not bound yet: give it grace
        # before acting, so we never stack duplicate instances on the port.
        if proc is not None and proc.poll() is None and wait_healthy(url, proc, grace):
            fail = 0
            continue
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        fail += 1
        log(f"{name} down ({url}) - start #{fail}")
        proc = start(name, svc)
        if wait_healthy(url, proc, grace):
            fail = 0
            log(f"{name} healthy")
            continue
        stop.wait(backoffs[min(fail - 1, len(backoffs) - 1)])


def cmd_status(config):
    ok = True
    for name, svc in config["services"].items():
        if not svc.get("enabled", True):
            print(f"{name:<14} disabled")
            continue
        up = healthy(svc.get("health"))
        ok = ok and up
        print(f"{name:<14} {'up' if up else 'DOWN':<5} {svc.get('health')}")
    return 0 if ok else 1


def cmd_once(config):
    for name, svc in config["services"].items():
        if not svc.get("enabled", True):
            continue
        if healthy(svc.get("health")):
            log(f"{name} already healthy")
            continue
        log(f"{name} down - starting")
        start(name, svc)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--name")
    args = ap.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))

    if args.status:
        return cmd_status(config)
    if args.once:
        return cmd_once(config)

    if PID_FILE.exists():
        try:
            old = int(PID_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            old = 0
        if old and old != os.getpid() and _pid_alive(old):
            log(f"another svcwatch is running (pid {old}); exiting")
            return 0
        try:
            PID_FILE.unlink()  # stale
        except OSError:
            pass
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    stop = threading.Event()
    try:
        threads = []
        for name, svc in config["services"].items():
            if not svc.get("enabled", True) or (args.name and name != args.name):
                continue
            t = threading.Thread(target=watch_one,
                                 args=(name, svc, stop, float(config.get("poll_seconds", 15))),
                                 daemon=True)
            t.start()
            threads.append(t)
        if not threads:
            log("no enabled services")
            return 0
        log(f"watching {len(threads)} service(s): {', '.join(t.name for t in threads)}")
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopping")
    finally:
        stop.set()
        try:
            PID_FILE.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())