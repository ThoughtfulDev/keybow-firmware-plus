#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_dir"
PYTHONPATH=editor exec "${PYTHON:-python3}" -m keybow_editor.server
