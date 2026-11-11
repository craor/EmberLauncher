#!/usr/bin/env python3
"""Собирает лаунчер под текущую систему. server.json намеренно не вшивается."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_MACHO_MAGIC = {
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
}


def _is_macho(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) in _MACHO_MAGIC
    except OSError:
        return False


def _sign_mac_app(app: Path) -> None:
    binaries = [path for path in app.rglob("*") if path.is_file() and not path.is_symlink() and _is_macho(path)]
    binaries.sort(key=lambda path: len(path.parts), reverse=True)
    for path in binaries:
        subprocess.check_call(["codesign", "--force", "--sign", "-", str(path)], cwd=ROOT)
    subprocess.check_call(["codesign", "--force", "--sign", "-", str(app)], cwd=ROOT)
    subprocess.check_call(["codesign", "--verify", "--deep", "--strict", str(app)], cwd=ROOT)


def _create_dmg(staging: Path, archive: Path) -> None:
    """hdiutil на раннере иногда отвечает Resource busy сразу после codesign."""
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(4):
        subprocess.run(["hdiutil", "detach", "/Volumes/Ember"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if archive.exists():
            archive.unlink()
        try:
            subprocess.check_call(
                [
                    "hdiutil",
                    "create",
                    "-volname",
                    "Ember",
                    "-srcfolder",
                    str(staging),
                    "-ov",
                    "-format",
                    "UDZO",
                    str(archive),
                ],
                cwd=ROOT,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            time.sleep(3 + attempt * 2)
    if last_error is not None:
        raise last_error


def _write_mac_dmg(app: Path, dist: Path) -> Path:
    staging = dist / "dmg-root"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    subprocess.check_call(["ditto", str(app), str(staging / "EmberLauncher.app")])
    (staging / "Как открыть.txt").write_text(
        "Ember для Mac с чипом Apple (M1 и новее). На Intel не запустится.\n"
        "\n"
        "1. Если в «Программах» уже есть старый EmberLauncher — замени его.\n"
        "2. Перетащи EmberLauncher в «Программы».\n"
        "3. Открой «Программы», нажми EmberLauncher правой кнопкой и выбери «Открыть».\n"
        "4. Если система пишет про неизвестного разработчика — ещё раз «Открыть».\n"
        "5. Первый запуск спросит папку. Ярлык Ember появится на рабочем столе.\n"
        "\n"
        "Не запускай программу прямо из этого окна: macOS прячет такие файлы, и окно не появляется.\n"
        "Сборка без сертификата Apple.\n",
        encoding="utf-8",
    )
    _sign_mac_app(staging / "EmberLauncher.app")
    # Сначала zip: его ищет лаунчер до 1.8.6. Потом dmg, он на раннере иногда занят.
    zipped = dist / "EmberLauncher-macOS.zip"
    if zipped.exists():
        zipped.unlink()
    subprocess.check_call(
        ["ditto", "-c", "-k", "--keepParent", str(staging / "EmberLauncher.app"), str(zipped)],
        cwd=ROOT,
    )
    archive = dist / "EmberLauncher-macOS.dmg"
    _create_dmg(staging, archive)
    shutil.rmtree(staging)
    return archive


def main() -> None:
    subprocess.check_call([sys.executable, str(ROOT / "make_icon.py")], cwd=ROOT)
    sep = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "EmberLauncher",
    ]
    if sys.platform == "darwin":
        # --onefile на Mac прыгает в Dock и сразу умирает: система не пускает
        # распакованный внутренний файл. Папка .app этого не делает.
        # --collect-all PyQt6 ломает сборку: симлинки framework уже существуют.
        command.extend(["--icon", "icon.icns", "--osx-bundle-identifier", "ember.launcher"])
    else:
        command.append("--onefile")
        if os.name == "nt":
            command.extend(["--icon", "icon.ico"])
    command.extend([
        "--add-data",
        f"icon.ico{sep}.",
        "--add-data",
        f"icon.png{sep}.",
        "--add-data",
        f"ember_src{sep}ember_src",
        "--collect-all",
        "minecraft_launcher_lib",
    ])
    if sys.platform != "darwin":
        command.extend(["--collect-all", "PyQt6"])
    command.append("launcher.py")
    subprocess.check_call(command, cwd=ROOT)
    dist = ROOT / "dist"
    if sys.platform == "darwin":
        print(_write_mac_dmg(dist / "EmberLauncher.app", dist))
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
