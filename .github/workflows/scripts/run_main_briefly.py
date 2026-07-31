from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUN_TIMEOUT_SECONDS = 10
TERMINATION_TIMEOUT_SECONDS = 5


def main() -> None:
    process = subprocess.Popen([sys.executable, "src/main.py"], cwd=PROJECT_ROOT)

    try:
        exit_code = process.wait(timeout=RUN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _stop_process(process)
        print("main.py started successfully")
        return

    if exit_code != 0:
        raise SystemExit(f"main.py exited early with code {exit_code}")

    print("main.py started and exited cleanly")


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()

    try:
        process.wait(timeout=TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


if __name__ == "__main__":
    main()