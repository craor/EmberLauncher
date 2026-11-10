"""Ember — компактный офлайн-лаунчер Minecraft.

Запуск:
    python launcher.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
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

APP_NAME = "Ember"
NICK_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,80}$")
INSTALL_MARKER = ".ember-installed"
MAX_DOWNLOAD_BYTES = 400 * 1024 * 1024
MIN_UPDATE_BYTES = 8 * 1024 * 1024
ALLOWED_HOSTS = frozenset({
    "api.modrinth.com",
    "cdn.modrinth.com",
    "api.cfwidget.com",
    "edge.forgecdn.net",
    "mediafilez.forgecdn.net",
    "bmclapi2.bangbang93.com",
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
})
INSTALLED_ROLE = Qt.ItemDataRole.UserRole + 1
_GAME_VERSION_RE = re.compile(
    r"(?<![\d.])(1\.\d{1,2}(?:\.\d{1,2})?|\d{2}\.\d{1,2}(?:\.\d{1,2})?)(?![\d.])"
)
LOADERS = (
    ("vanilla", "Vanilla"),
    ("fabric", "Fabric"),
    ("forge", "Forge"),
    ("neoforge", "NeoForge"),
    ("quilt", "Quilt"),
    ("optifine", "OptiFine"),
)

JAVA_RUNTIMES = (
    ("java-runtime-epsilon", "Java 25"),
    ("java-runtime-delta", "Java 21"),
    ("java-runtime-gamma", "Java 17"),
    ("jre-legacy", "Java 8"),
)

PACK_VERSIONS = (
    "26.3",
    "1.21.4",
    "1.21.1",
    "1.21",
    "1.20.4",
    "1.20.1",
    "1.20",
    "1.19.4",
    "1.19.2",
    "1.18.2",
    "1.17.1",
    "1.16.5",
    "1.12.2",
)
