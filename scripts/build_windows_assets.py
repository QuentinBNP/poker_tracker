from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from app_info import (
        APP_AUTHOR,
        APP_COMPANY,
        APP_DESCRIPTION,
        APP_ICON_PATH,
        APP_NAME,
        APP_VERSION,
    )

    assets_dir = project_root / "build" / "windows-assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    icon_path = assets_dir / "MyPokerTracker.ico"
    version_info_path = assets_dir / "version_info.txt"
    installer_script_path = assets_dir / "MyPokerTracker.iss"

    shutil.copy2(APP_ICON_PATH, icon_path)
    version_info_path.write_text(
        _version_file_content(
            app_author=APP_AUTHOR,
            app_company=APP_COMPANY,
            app_description=APP_DESCRIPTION,
            app_name=APP_NAME,
            app_version=APP_VERSION,
        ),
        encoding="utf-8",
    )
    installer_script_path.write_text(
        _installer_script_content(
            project_root=project_root,
            app_company=APP_COMPANY,
            app_name=APP_NAME,
            app_version=APP_VERSION,
        ),
        encoding="utf-8",
    )


def _version_file_content(
    *,
    app_author: str,
    app_company: str,
    app_description: str,
    app_name: str,
    app_version: str,
) -> str:
    version_tuple = _version_tuple(app_version)
    version_commas = ", ".join(str(part) for part in version_tuple)
    version_dots = ".".join(str(part) for part in version_tuple)

    return f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_commas}),
    prodvers=({version_commas}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{app_company}'),
          StringStruct('FileDescription', '{app_description}'),
          StringStruct('FileVersion', '{version_dots}'),
          StringStruct('InternalName', '{app_name}'),
          StringStruct('OriginalFilename', '{app_name}.exe'),
          StringStruct('ProductName', '{app_name}'),
          StringStruct('ProductVersion', '{version_dots}'),
          StringStruct('LegalCopyright', 'Copyright (c) {app_author}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)'''


def _installer_script_content(
    *,
    project_root: Path,
    app_company: str,
    app_name: str,
    app_version: str,
) -> str:
  dist_dir = (project_root / "dist" / app_name).as_posix()
  icon_path = (
    project_root / "build" / "windows-assets" / "MyPokerTracker.ico"
  ).as_posix()
  output_dir = (project_root / "dist" / "installer").as_posix()
  app_id = f"{{{{{app_name}}}}}"
  task_line = (
    'Name: "desktopicon"; Description: "Create a desktop shortcut"; '
    'GroupDescription: "Additional icons:"; Flags: unchecked'
  )
  run_line = (
    'Filename: "{app}\\{#MyAppExeName}"; '
    'Description: "Launch {#MyAppName}"; '
    'Flags: nowait postinstall skipifsilent'
  )

  return f'''#define MyAppName "{app_name}"
#define MyAppVersion "{app_version}"
#define MyAppPublisher "{app_company}"
#define MyAppExeName "{app_name}.exe"

[Setup]
AppId={app_id}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir={output_dir}
OutputBaseFilename={app_name}-Setup-{app_version}
SetupIconFile={icon_path}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
{task_line}

[Files]
Source: "{dist_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\Uninstall {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
{run_line}
'''


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")[:4]]
    while len(parts) < 4:
        parts.append(0)
    return (parts[0], parts[1], parts[2], parts[3])


if __name__ == "__main__":
    main()