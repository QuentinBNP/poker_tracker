from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from app_info import APP_NAME

    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    assets_dir = build_dir / "windows-assets"

    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)

    subprocess.run(
        [sys.executable, str(project_root / "scripts" / "build_windows_assets.py")],
        cwd=project_root,
        check=True,
    )

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
        "--icon",
        str(assets_dir / "MyPokerTracker.ico"),
        "--version-file",
        str(assets_dir / "version_info.txt"),
        "--paths",
        str(project_root),
        str(project_root / "main.py"),
    ]
    subprocess.run(command, cwd=project_root, check=True)


if __name__ == "__main__":
    main()