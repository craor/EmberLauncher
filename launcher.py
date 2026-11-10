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
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "1.8.7"
USER_AGENT = "EmberLauncher/1.8.7"
AUTHOR = "craor"
DEFAULT_UPDATE_REPO = "craor/EmberLauncher"


def _bundle_root() -> pathlib.Path:
    if getattr(sys, "frozen", False):
        return pathlib.Path(getattr(sys, "_MEIPASS"))
    return pathlib.Path(__file__).resolve().parent


def _load_program() -> None:
    folder = _bundle_root() / "ember_src"
    parts = sorted(folder.glob("part_*.py"))
    if not parts:
        raise RuntimeError("Не найдены файлы ember_src")
    source = "".join(part.read_text(encoding="utf-8") for part in parts)
    exec(compile(source, "ember_src/launcher.py", "exec"), globals())


_load_program()
