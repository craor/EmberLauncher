"""Ember — компактный офлайн-лаунчер Minecraft.

Запуск:
    python launcher.py
"""

from __future__ import annotations

import base64
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
    "26.2",
    "26.1",
    "1.21.11",
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

VERSION_BLURBS = {
    "26.3": "Wilderness Bound: осиновый лес, заброшенные лагеря, подушки и соломенные кровати. Нужна Java 25.",
    "26.2": "Chaos Cubed: серные пещеры и новый дроп 2026 года. Нужна Java 25.",
    "26.1": "Tiny Takeover: новые модели детёнышей. Первая Java-версия с номером 26 и Java 25.",
    "1.21.11": "Последняя игра со старыми номерами. Модов меньше, чем на 1.21.1.",
    "1.21.4": "The Garden Awakens. Моды есть, но самый полный набор всё ещё на 1.21.1.",
    "1.21.1": "Лучшая 1.21 для сборок: Fabric, Forge и NeoForge, шейдеры и техника.",
    "1.21": "Самый первый релиз 1.21. Если модов мало, бери 1.21.1 — это та же линия.",
    "1.20.4": "Поздняя 1.20. Моды ставятся, но выбор меньше, чем на 1.20.1.",
    "1.20.1": "Классика модов: Create, магия, оружие, Forge и Fabric.",
    "1.20": "Начало 1.20. Для модов удобнее 1.20.1.",
    "1.19.4": "Поздняя 1.19. Моды есть и на Fabric, и на Forge.",
    "1.19.2": "Wild Update. Много готовых сборок выживания.",
    "1.18.2": "Пещеры и скалы. Хорошая база для выживания с модами.",
    "1.17.1": "Короткий переходный релиз. Модов меньше, чем на 1.18.2 и 1.16.5.",
    "1.16.5": "Старый Forge. Большие моды, обычно хватает Java 8.",
    "1.12.2": "Очень старые моды. Нужна Java 8, новые загрузчики сюда не встанут.",
}

LOADER_BLURBS = {
    "vanilla": "Чистая игра, без модов. Сборки справа на ваниль не ставятся.",
    "fabric": "Удобный загрузчик для сборок: шейдеры Iris, Sodium и лёгкие моды.",
    "forge": "Большие моды: Create, магия, оружие. На свежих версиях чаще нужен NeoForge.",
    "neoforge": "Новый Forge. Для 1.21 и 26.x обычно он, а не старый Forge.",
    "quilt": "Родственник Fabric. Модов меньше, чем у Fabric.",
    "optifine": "Свои шейдеры и графика. Большие моды Fabric и Forge с ним не мешаются.",
}

