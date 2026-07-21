"""
Session-wide plumbing for the Playwright E2E suite under tests/e2e.

The frontend is a CRA static bundle, so instead of a dev server we build it
once and serve the `build/` directory over plain HTTP. That server is shared
by every test (it's read-only from the browser's point of view -- all NPC/API
data comes from Playwright route mocks, not from this server), which is what
makes the whole suite safe to run with `pytest -n auto`.

Coordinating a single shared server across pytest-xdist workers is the tricky
part: worker processes are forked *after* the controlling process finishes
`pytest_configure`, so the controlling process is the only one guaranteed to
run before any worker exists. We start the server there and write its URL to
a well-known temp file; workers (which have `config.workerinput` set) just
read it back. `pytest_unconfigure` on the controlling process tears the
server down after all workers have finished.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from tests.e2e.mock_constants import STATE_FILE

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
BUILD_DIR = FRONTEND_DIR / "build"


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception as exc:  # noqa: BLE001 - retry loop, re-raised below
            last_err = exc
            time.sleep(0.5)
    raise RuntimeError(f"Frontend static server at {url} never came up: {last_err}")


def _build_frontend() -> None:
    if (BUILD_DIR / "index.html").exists() and os.environ.get("E2E_FORCE_REBUILD") != "1":
        return
    # Invoke react-scripts directly via node rather than `npm run build`:
    # this repo's frontend/node_modules/.bin shims are POSIX symlinks with
    # no .cmd/.ps1 wrapper, so npm (a Windows-native launcher here) can't
    # resolve `react-scripts` through the normal PATH shim lookup.
    subprocess.run(
        ["node", str(FRONTEND_DIR / "node_modules" / "react-scripts" / "bin" / "react-scripts.js"), "build"],
        cwd=str(FRONTEND_DIR),
        check=True,
    )


def _start_static_server() -> dict:
    _build_frontend()
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=str(BUILD_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    _wait_until_up(base_url)
    return {"pid": proc.pid, "port": port, "base_url": base_url}


def pytest_configure(config):
    if hasattr(config, "workerinput"):
        # Running inside an xdist worker: the controlling process already
        # started the server before any worker was spawned.
        return
    info = _start_static_server()
    STATE_FILE.write_text(json.dumps(info))
    config._e2e_server_info = info


def pytest_unconfigure(config):
    if hasattr(config, "workerinput"):
        return
    info = getattr(config, "_e2e_server_info", None)
    if info is None:
        return
    try:
        os.kill(info["pid"], signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    STATE_FILE.unlink(missing_ok=True)
