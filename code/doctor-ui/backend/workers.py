"""Start and talk to doctor workers (`worker.py`), one per benchmark.

A worker is a long-lived subprocess in the benchmark's own Python environment. Calls to one
worker are serialized with a lock; different benchmarks run in parallel.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
WORKER = HERE / "worker.py"


class WorkerError(RuntimeError):
    def __init__(self, message: str, trace: str = ""):
        super().__init__(message)
        self.trace = trace


class WorkerClient:
    def __init__(
        self,
        python: list[str],
        cwd: Path,
        doctor: Path,
        adapter: str,
        sys_path: list[str] | None = None,
        kwargs: dict | None = None,
        env: dict | None = None,
    ):
        self.python, self.cwd, self.doctor = python, Path(cwd), Path(doctor)
        self.adapter, self.sys_path, self.kwargs = adapter, sys_path or [], kwargs or {}
        self.env = env or {}
        self.lock = threading.Lock()
        self.proc: Optional[subprocess.Popen] = None
        self.next_id = 0
        self.info: dict = {}
        self.stderr_tail: list[str] = []

    # --- lifecycle -----------------------------------------------------------------------

    def start(self) -> dict:
        cmd = [*self.python, str(WORKER), "--doctor", str(self.doctor)]
        for p in self.sys_path:
            cmd += ["--sys-path", p]
        env = {**os.environ, **self.env, "PYTHONUNBUFFERED": "1"}
        env.pop("VIRTUAL_ENV", None)  # let `uv run --project` pick the benchmark's env
        self.proc = subprocess.Popen(
            cmd,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        first = self._read_line()
        if not first.get("ready"):
            raise WorkerError(f"worker did not start: {first}")
        self.info = self._call("init", {"adapter": self.adapter, "kwargs": self.kwargs})
        return self.info

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self.stderr_tail = (self.stderr_tail + [line.rstrip()])[-40:]

    # --- calls ---------------------------------------------------------------------------

    def call(self, op: str, args: dict | None = None, progress: Callable | None = None):
        with self.lock:
            if not self.alive():
                self.start()
            return self._call(op, args or {}, progress)

    def _call(self, op: str, args: dict, progress: Callable | None = None):
        self.next_id += 1
        rid = self.next_id
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps({"id": rid, "op": op, "args": args}) + "\n")
        self.proc.stdin.flush()
        while True:
            msg = self._read_line()
            if msg.get("id") != rid:
                continue
            if "progress" in msg:
                if progress:
                    progress(*msg["progress"])
                continue
            if msg.get("ok"):
                return msg.get("result")
            raise WorkerError(msg.get("error", "worker error"), msg.get("trace", ""))

    def _read_line(self) -> dict:
        assert self.proc and self.proc.stdout
        while True:
            line = self.proc.stdout.readline()
            if not line:
                tail = "\n".join(self.stderr_tail[-15:])
                self.proc = None
                raise WorkerError(f"worker exited. Last output:\n{tail}")
            line = line.strip()
            if not line.startswith("{"):
                continue  # stray output from the benchmark
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
