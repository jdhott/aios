#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path

LOCK_PATH = Path(os.environ.get("AIOS_RUNTIME_LOCK_PATH", str(Path.home() / "LocalProjects/aios/.aios_runtime.lock")))
STALE_AFTER_SECONDS = int(os.environ.get("AIOS_RUNTIME_LOCK_STALE_SECONDS", "1800"))

def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def _read_lock():
    try:
        text = LOCK_PATH.read_text().strip()
        parts = dict(
            p.split("=", 1) for p in text.splitlines()
            if "=" in p
        )
        return int(parts.get("pid", "0")), float(parts.get("time", "0"))
    except Exception:
        return 0, 0.0

def acquire_lock() -> bool:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()

    if LOCK_PATH.exists():
        pid, started = _read_lock()
        age = now - started if started else 999999
        if _pid_running(pid) and age < STALE_AFTER_SECONDS:
            print(f"[Runtime Lock] Another AIOS run is active; skipping this run. pid={pid} age_seconds={int(age)}")
            return False
        print(f"[Runtime Lock] Removing stale lock. pid={pid} age_seconds={int(age)}")
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        f.write(f"pid={os.getpid()}\\n")
        f.write(f"time={now}\\n")
    print(f"[Runtime Lock] Acquired lock: {LOCK_PATH}")
    return True

def release_lock() -> None:
    try:
        pid, _ = _read_lock()
        if pid == os.getpid():
            LOCK_PATH.unlink()
            print(f"[Runtime Lock] Released lock: {LOCK_PATH}")
    except FileNotFoundError:
        pass

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: aios_runtime_lock.py <command> [args...]", file=sys.stderr)
        return 2

    if not acquire_lock():
        return 0

    try:
        proc = subprocess.run(sys.argv[1:])
        return proc.returncode
    finally:
        release_lock()

if __name__ == "__main__":
    raise SystemExit(main())
