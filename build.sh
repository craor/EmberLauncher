#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt "pyinstaller>=6.0"
python3 build_release.py
