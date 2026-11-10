#!/usr/bin/env python3
"""Собирает лаунчер под текущую систему. server.json намеренно не вшивается."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    subprocess.check_call([sys.executable, str(ROOT / "make_icon.py")], cwd=ROOT)
    sep = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "EmberLauncher",
        "--icon",
        "icon.ico",
        "--add-data",
        f"icon.ico{sep}.",
        "--add-data",
        f"icon.png{sep}.",
        "--collect-all",
        "minecraft_launcher_lib",
        "--collect-all",
        "PyQt6",
        "launcher.py",
    ]
    subprocess.check_call(command, cwd=ROOT)
    dist = ROOT / "dist"
    if sys.platform == "darwin":
        app = dist / "EmberLauncher.app"
        archive = dist / "EmberLauncher-macOS.zip"
        subprocess.check_call(["ditto", "-c", "-k", "--keepParent", str(app), str(archive)])
        print(archive)
        return
    if os.name == "nt":
        print(dist / "EmberLauncher.exe")
        return
    binary = dist / "EmberLauncher"
    renamed = dist / "EmberLauncher-linux"
    shutil.copy2(binary, renamed)
    renamed.chmod(0o755)
    print(renamed)


if __name__ == "__main__":
    main()
