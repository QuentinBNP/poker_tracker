from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from app_info import APP_NAME


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        APP_NAME,
        "--paths",
        str(project_root),
        str(project_root / "main.py"),
    ]
    subprocess.run(command, cwd=project_root, check=True)


if __name__ == "__main__":
    main()