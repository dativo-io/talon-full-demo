#!/usr/bin/env python3
"""Run a command with a wall-clock timeout and terminate its process group."""

from __future__ import annotations

import os
import signal
import subprocess
import sys


def terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate the complete child process group, escalating after five seconds."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run-with-timeout.py SECONDS COMMAND [ARG ...]", file=sys.stderr)
        return 2

    try:
        timeout = int(sys.argv[1])
    except ValueError:
        print(f"invalid timeout: {sys.argv[1]}", file=sys.stderr)
        return 2
    if timeout <= 0:
        print("timeout must be positive", file=sys.stderr)
        return 2

    command = sys.argv[2:]
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(
            f"ERROR: command exceeded {timeout}s; terminating process group",
            file=sys.stderr,
        )
        terminate_group(process)
        return 124
    except KeyboardInterrupt:
        print("Cancelled; terminating child process group", file=sys.stderr)
        terminate_group(process)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
