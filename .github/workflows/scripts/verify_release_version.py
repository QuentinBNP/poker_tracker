from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_release_version.py <release-tag>")

    release_tag = sys.argv[1]
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        project_version = tomllib.load(pyproject_file)["project"]["version"]

    expected_tag = f"v{project_version}"
    if release_tag != expected_tag:
        raise SystemExit(
            f"Release tag {release_tag!r} must match project version {expected_tag!r}."
        )

    print(f"Release tag matches project version: {release_tag}")


if __name__ == "__main__":
    main()