from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

APP_NAME = "MyPokerTracker"
APP_SLUG = "mypokertracker"
APP_COMPANY = "Quentin Bonopera"
APP_AUTHOR = "Quentin Bonopera"
APP_DESCRIPTION = "MyPokerTracker Winamax desktop application"
APP_ICON_NAME = "MyPokerTracker.ico"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ICON_PATH = PROJECT_ROOT / "assets" / APP_ICON_NAME


def _get_app_version() -> str:
	pyproject_path = PROJECT_ROOT / "pyproject.toml"
	if pyproject_path.exists():
		with pyproject_path.open("rb") as pyproject_file:
			return str(tomllib.load(pyproject_file)["project"]["version"])

	return version("mypokertracker")


APP_VERSION = _get_app_version()