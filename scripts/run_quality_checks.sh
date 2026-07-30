#!/usr/bin/env sh

set -eu

PROJECT_ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)

if [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/venv/Scripts/python.exe" ]; then
    PYTHON_BIN="$PROJECT_ROOT/venv/Scripts/python.exe"
elif [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
else
    PYTHON_BIN=python
fi

cd "$PROJECT_ROOT"

"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m mypy .