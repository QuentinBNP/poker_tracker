from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    subprocess.run(
        [sys.executable, str(project_root / "scripts" / "build_windows_exe.py")],
        cwd=project_root,
        check=True,
    )

    installer_script = project_root / "build" / "windows-assets" / "MyPokerTracker.iss"
    subprocess.run(["iscc", str(installer_script)], cwd=project_root, check=True)


if __name__ == "__main__":
    main()