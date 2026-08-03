from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_build_assets_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_windows_assets.py"
    spec = importlib.util.spec_from_file_location("build_windows_assets", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_shortcuts_use_versioned_icon_file() -> None:
    build_assets = _load_build_assets_module()

    script = build_assets._installer_script_content(
        project_root=Path("C:/project"),
        app_company="Example Company",
        app_name="MyPokerTracker",
        app_version="0.2.1",
    )

    assert 'DestDir: "{app}"; DestName: "MyPokerTracker-0.2.1.ico"' in script
    assert script.count('IconFilename: "{app}\\MyPokerTracker-0.2.1.ico"') == 2
    assert "{{app}}" not in script