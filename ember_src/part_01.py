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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QMessageBox,
    QProgressBar,
    QSlider,
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

PRESETS = (
    {
        "id": "visual",
        "title": "Визуал",
        "summary": "Шейдеры, анимации рук в духе Punchy, плащи, листва, частицы, шаги и небо. Мир выглядит живым.",
        "mods": {
            "fabric": (
                "fabric-api", "sodium", "iris", "sodium-extra", "lambdynamiclights", "continuity",
                "punchy", "not-enough-animations", "entity-model-features", "fallingleaves",
                "visuality", "wavey-capes", "presence-footsteps",
            ),
            "quilt": (
                "sodium", "iris", "continuity", "punchy", "not-enough-animations",
                "fallingleaves", "visuality", "wavey-capes",
            ),
            "forge": (
                "embeddium", "oculus", "continuity", "punchy", "entity-model-features",
                "visuality", "effective", "lambdynamiclights", "presence-footsteps",
            ),
            "neoforge": (
                "embeddium", "oculus", "continuity", "punchy", "entity-model-features",
                "visuality", "effective", "lambdynamiclights", "presence-footsteps",
            ),
        },
        "shaders": ("complementary-reimagined",),
    },
    {
        "id": "zombie",
        "title": "Зомби-выживание",
        "summary": "Орды, умные зомби, жажда и могилы. Обычное выживание становится опасным.",
        "mods": {
            "fabric": ("fabric-api", "rottencreatures", "zombie-awareness", "tough-as-nails", "universal-graves"),
            "quilt": ("rottencreatures", "tough-as-nails", "universal-graves"),
            "forge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
            "neoforge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
        },
    },
    {
        "id": "survival",
        "title": "Выживание",
        "summary": "Еда, сезоны, жажда, рюкзак пути, карта и могила, если умрёшь.",
        "mods": {
            "fabric": (
                "fabric-api", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "comforts", "waystones", "appleskin", "jade", "xaeros-minimap", "universal-graves",
            ),
            "quilt": ("farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons", "waystones", "xaeros-minimap"),
            "forge": (
                "cloth-config", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "comforts", "waystones", "appleskin", "jade", "xaeros-minimap", "gravestone-mod",
            ),
            "neoforge": (
                "cloth-config", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "waystones", "appleskin", "jade", "xaeros-minimap", "gravestone-mod",
            ),
        },
    },
    {
        "id": "weapons",
        "title": "Оружие",
        "summary": "Мечи, древковое оружие, перекаты и мушкеты. Бой перестаёт быть ванильным.",
        "mods": {
            "fabric": ("fabric-api", "better-combat", "simply-swords", "spartan-weaponry", "combat-roll", "musket-mod"),
            "quilt": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll"),
            "forge": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll", "musket-mod"),
            "neoforge": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll"),
        },
    },
    {
        "id": "machines",
        "title": "Механизмы и физика",
        "summary": "Create, рельсы, паровозы и физика Valyrien Skies: корабли, дирижабли и механизмы, которые правда двигаются.",
        "mods": {
            "fabric": (
                "fabric-api", "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
            "quilt": ("create", "valkyrien-skies", "clockwork", "eureka"),
            "forge": (
                "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
            "neoforge": (
                "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
        },
    },
    {
        "id": "magic",
        "title": "Магия",
        "summary": "Ботания, заклинания и конфиги, чтобы магия не ломала меню.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "botania"),
            "quilt": ("cloth-config", "botania"),
            "forge": ("cloth-config", "botania", "ars-nouveau"),
            "neoforge": ("cloth-config", "botania", "ars-nouveau"),
        },
    },
)

CURATED = (
    {
        "words": ("шейд", "shader", "iris", "окулус"),
        "title": "Шейдеры",
        "summary": "Картинка с шейдерами без OptiFine: Iris или Oculus плюс быстрый рендер. Пак шейдеров кладётся в shaderpacks.",
        "mods": {
            "fabric": ("sodium", "iris", "fabric-api"),
            "quilt": ("sodium", "iris"),
            "forge": ("embeddium", "oculus"),
            "neoforge": ("embeddium", "oculus"),
        },
        "shaders": ("complementary-reimagined",),
    },
    {
        "words": ("анимац", "animat", "эмф"),
        "title": "Анимации",
        "summary": "Анимации рук, предметов и модели: Not Enough Animations, EMF и ETF.",
        "mods": {
            "fabric": ("fabric-api", "not-enough-animations", "entity-model-features", "entity-texture-features"),
            "quilt": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
            "forge": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
            "neoforge": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
        },
    },
    {
        "words": ("зомби", "zombie", "апокал", "нежить", "орда"),
        "title": "Зомби-выживание",
        "summary": "Орды и умные зомби, тяжёлое выживание и могилы. Уже стоящие моды повторно не качаются.",
        "mods": {
            "fabric": ("fabric-api", "rottencreatures", "zombie-awareness", "tough-as-nails", "universal-graves"),
            "quilt": ("rottencreatures", "tough-as-nails", "universal-graves"),
            "forge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
            "neoforge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
        },
    },
    {
        "words": ("ужас", "хоррор", "horror", "туман"),
        "title": "Хоррор",
        "summary": "Жуткий набор: туман и ощущение, что за тобой следят.",
        "mods": {
            "fabric": ("fabric-api", "from-the-fog"),
            "quilt": ("from-the-fog",),
            "forge": ("from-the-fog",),
            "neoforge": ("from-the-fog",),
        },
    },
    {
        "words": ("оптим", "фпс", "fps", "лаг", "натрий", "sodium", "произв"),
        "title": "Оптимизация",
        "summary": "Сборка для кадров: легче рендер, тики и лишние сущности. Шейдеров нет.",
        "mods": {
            "fabric": ("sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "fabric-api"),
            "quilt": ("sodium", "lithium", "ferrite-core", "immediatelyfast"),
            "forge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
            "neoforge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
        },
    },
    {
        "words": ("маг", "magic", "волшеб", "закл", "ботан"),
        "title": "Магия",
        "summary": "Магический набор: ботания, заклинания и библиотека конфигов.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "botania"),
            "quilt": ("cloth-config", "botania"),
            "forge": ("cloth-config", "botania", "ars-nouveau"),
            "neoforge": ("cloth-config", "botania", "ars-nouveau"),
        },
    },
    {
        "words": ("тех", "tech", "механ", "create", "криэйт", "завод"),
        "title": "Техника",
        "summary": "Небольшая техническая сборка вокруг Create и удобных подсказок.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "create"),
            "quilt": ("cloth-config", "create"),
            "forge": ("cloth-config", "create"),
            "neoforge": ("cloth-config", "create"),
        },
    },
    {
        "words": ("данж", "приключ", "advent", "yung", "пещер"),
        "title": "Данжи",
        "summary": "Больше структур и данжей, плюс карта и подсказки по мобам.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "yungs-better-dungeons", "jade", "xaeros-minimap"),
            "quilt": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
            "forge": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
            "neoforge": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
        },
    },
    {
        "words": ("уют", "декор", "еда", "farm", "дерев"),
        "title": "Уют",
        "summary": "Декор и еда: Farmer's Delight и Supplementaries.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "farmers-delight", "supplementaries"),
            "quilt": ("farmers-delight", "supplementaries"),
            "forge": ("cloth-config", "farmers-delight", "supplementaries"),
            "neoforge": ("cloth-config", "farmers-delight", "supplementaries"),
        },
    },
    {
        "words": ("pvp", "пвп", "мини", "xaero"),
        "title": "PvP",
        "summary": "Лёгкий PvP-набор: карта, яблоки на голоде и оптимизация кадра.",
        "mods": {
            "fabric": ("fabric-api", "sodium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
            "quilt": ("sodium", "appleskin", "xaeros-minimap"),
            "forge": ("embeddium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
            "neoforge": ("embeddium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
        },
    },
)

STYLESHEET = """
* { font-family: "Segoe UI", "Inter", "Arial"; }
QLineEdit, QComboBox {
    background: rgba(255, 255, 255, 0.06);
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 18px;
    selection-background-color: #ff8a2a;
    selection-color: #1a1008;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #ff8a2a; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #1b211c;
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.08);
    selection-background-color: #ff8a2a;
    selection-color: #1a1008;
    outline: none;
}
QLabel#title {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 4px;
    color: #f7f3ec;
}
QLabel#subtitle { color: #c8b7a2; font-size: 12px; }
QLabel#credit { color: #ffb15e; font-size: 11px; font-weight: 700; }
QLabel#section {
    color: #aeb8aa;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#muted { color: #b4bcae; font-size: 11px; }
QLabel#ramValue { color: #ffc27a; font-size: 13px; font-weight: 700; }
QLabel#serverTitle {
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #ffe7c4;
}
QLabel#serverSeason { color: #ffb15e; font-size: 13px; font-weight: 700; }
QFrame#card {
    background-color: rgba(12, 16, 14, 176);
    border: 1px solid rgba(255, 214, 170, 0.16);
    border-radius: 22px;
}
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
}
QSlider::sub-page:horizontal { background: #ff8a2a; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: #ffd7a8;
    border: 2px solid #ff8a2a;
    border-radius: 8px;
}
QProgressBar {
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-radius: 5px;
    min-height: 8px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7a18, stop:1 #ffd7a1);
    border-radius: 5px;
}
QDialog#downloadDialog { background: #121614; }
QListWidget {
    background: rgba(255, 255, 255, 0.04);
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 6px;
    outline: none;
}
QListWidget::item { padding: 7px 8px; border-radius: 8px; }
QListWidget::item:selected { background: #1d4a32; color: #e9fff2; }
QListWidget::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.05);
}
QListWidget::indicator:checked {
    background: #ff8a2a;
    border: 1px solid #ffb15e;
}
QCheckBox { color: #f4f1ea; spacing: 8px; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.05);
}
QCheckBox::indicator:checked { background: #ff8a2a; border: 1px solid #ff8a2a; }
"""


