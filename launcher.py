"""Ember — компактный офлайн-лаунчер Minecraft.

Запуск:
    python launcher.py

Код программы лежит в ember_src/part_*.py и выполняется в этом модуле.
Версию меняй здесь: от неё зависит автообновление.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime


def _arm_crash_log() -> None:
    """Пишет падение до появления окна. На Mac лог: ~/Library/Logs/EmberLauncher/crash.log."""
    try:
        if sys.platform == "darwin":
            folder = pathlib.Path.home() / "Library" / "Logs" / "EmberLauncher"
        elif os.name == "nt":
            folder = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "EmberLauncher"
        else:
            folder = pathlib.Path.home() / ".cache" / "EmberLauncher"
        folder.mkdir(parents=True, exist_ok=True)
        handle = open(folder / "crash.log", "w", encoding="utf-8")
        handle.write("start\n")
        handle.flush()
        import faulthandler
        faulthandler.enable(handle, all_threads=True)

        def hook(exc_type, exc, tb) -> None:
            handle.write("".join(traceback.format_exception(exc_type, exc, tb)))
            handle.flush()
            sys.__excepthook__(exc_type, exc, tb)

        sys.excepthook = hook
    except Exception:
        return


_arm_crash_log()


def _bundle_root() -> pathlib.Path:
    if getattr(sys, "frozen", False):
        return pathlib.Path(getattr(sys, "_MEIPASS"))
    return pathlib.Path(__file__).resolve().parent


def _install_ca_bundle() -> None:
    """python.org и PyInstaller на Mac не знают системные сертификаты, и любой https падает."""
    import ssl

    def usable(path: str) -> bool:
        try:
            return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 20_000
        except OSError:
            return False

    candidates: list[str] = []
    bundled = _bundle_root() / "cacert.pem"
    if usable(str(bundled)):
        candidates.append(str(bundled))
    try:
        import certifi

        located = certifi.where()
        if usable(located) and located not in candidates:
            candidates.append(located)
    except Exception:
        pass
    if sys.platform == "darwin":
        exported = pathlib.Path(tempfile.gettempdir()) / "ember-ca" / "macos.pem"
        try:
            if not usable(str(exported)):
                exported.parent.mkdir(exist_ok=True)
                chunks: list[bytes] = []
                for keychain in (
                    "/System/Library/Keychains/SystemRootCertificates.keychain",
                    "/Library/Keychains/System.keychain",
                ):
                    if not os.path.isfile(keychain):
                        continue
                    chunks.append(subprocess.check_output(
                        ["/usr/bin/security", "find-certificate", "-a", "-p", keychain],
                        timeout=30,
                    ))
                if chunks:
                    exported.write_bytes(b"\n".join(chunks))
        except Exception:
            pass
        if usable(str(exported)):
            candidates.append(str(exported))
    for cafile in candidates:
        try:
            ssl.create_default_context(cafile=cafile)
        except Exception:
            continue
        os.environ["SSL_CERT_FILE"] = cafile
        os.environ["REQUESTS_CA_BUNDLE"] = cafile
        os.environ["CURL_CA_BUNDLE"] = cafile

        def context(path: str = cafile) -> ssl.SSLContext:
            return ssl.create_default_context(cafile=path)

        ssl._create_default_https_context = context  # type: ignore[attr-defined]
        try:
            urllib.request.install_opener(
                urllib.request.build_opener(urllib.request.HTTPSHandler(context=context()))
            )
        except Exception:
            continue
        return


_install_ca_bundle()

try:
    import minecraft_launcher_lib
    from minecraft_launcher_lib.exceptions import UnsupportedVersion, VersionNotFound
except ImportError as import_error:
    minecraft_launcher_lib = None
    VersionNotFound = Exception
    UnsupportedVersion = Exception
    _MLL_IMPORT_ERROR = import_error
else:
    _MLL_IMPORT_ERROR = None

from PyQt6.QtCore import (
    QEasingCurve,
    QByteArray,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "1.9.0"
USER_AGENT = "EmberLauncher/1.9.0"
AUTHOR = "craor"
DEFAULT_UPDATE_REPO = "craor/EmberLauncher"


def _load_program() -> None:
    folder = _bundle_root() / "ember_src"
    parts = sorted(folder.glob("part_*.py"))
    if not parts:
        raise RuntimeError("Не найдены файлы ember_src")
    source = "".join(part.read_text(encoding="utf-8") for part in parts)
    exec(compile(source, "ember_src/launcher.py", "exec"), globals())


_load_program()
