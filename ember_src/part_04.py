

class StageBanner(QWidget):
    """Центральная сцена: картинка, которую выбрал игрок."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(248)
        self.setMaximumHeight(340)
        self._art = stage_pixmap()
        self._version = "Выбери версию"
        self._detail = "Описание появится здесь."

    def set_caption(self, version: str, detail: str) -> None:
        self._version = version or "Нет версии"
        self._detail = detail or ""
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        rect = self.rect().adjusted(2, 2, -3, -3)
        painter.fillRect(rect, QColor("#1A120C"))
        photo = rect.adjusted(6, 6, -6, -6)
        painter.setClipRect(photo)
        if self._art.isNull():
            painter.fillRect(photo, QColor("#3A291C"))
        else:
            scaled = self._art.scaled(
                max(1, photo.width()),
                max(1, photo.height()),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.FastTransformation,
            )
            x = photo.left() + (photo.width() - scaled.width()) // 2
            y = photo.top() + (photo.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        painter.setClipping(False)
        painter.fillRect(photo.left(), photo.bottom() - 52, photo.width(), 52, QColor(43, 31, 23, 220))
        painter.setPen(QColor("#E8873A"))
        painter.setFont(QFont("Pixelify Sans", 14))
        painter.drawText(
            QRectF(photo.left() + 12, photo.bottom() - 48, photo.width() - 24, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._version,
        )
        painter.setPen(QColor("#E7D7B1"))
        painter.setFont(QFont("Alegreya Sans", 10))
        detail = QFontMetrics(painter.font()).elidedText(
            self._detail, Qt.TextElideMode.ElideRight, max(8, photo.width() - 28)
        )
        painter.drawText(
            QRectF(photo.left() + 12, photo.bottom() - 24, photo.width() - 24, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            detail,
        )
        painter.fillRect(rect.left() + 2, rect.top() + 2, 6, 6, QColor("#E8873A"))
        painter.fillRect(rect.right() - 8, rect.top() + 2, 6, 6, QColor("#E8873A"))
        painter.end()


def stage_pixmap() -> QPixmap:
    pixmap = QPixmap()
    path = _bundle_root() / "ember_src" / "stage.b64"
    try:
        encoded = "".join(path.read_text(encoding="ascii").split())
        pixmap.loadFromData(base64.b64decode(encoded), "JPG")
    except (OSError, ValueError):
        return QPixmap()
    return pixmap


class LauncherWindow(GradientWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ember")
        self.setMinimumSize(1180, 720)
        self.resize(1280, 800)
        self.setWindowIcon(load_app_icon())
        self._config = load_config()
        self._server = load_server()
        self._worker: QThread | None = None
        self._proc: subprocess.Popen | None = None
        self._log_file = None
        self._log_path = log_path()
        self._busy = False
        self._plan: dict | None = None
        self._faded = False
        self._update_manual = False
        self._pack_btns: list[EmberButton] = []
        self._version_chips: list[EmberButton] = []
        self._news_worker: QThread | None = None
        self._profile_synced = False

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        side = MaterialFrame("leather", 48)
        side.setObjectName("sideBar")
        side.setFixedWidth(214)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(14, 16, 14, 14)
        side_layout.setSpacing(8)
        brand = QHBoxLayout()
        icon_label = QLabel()
        icon_pixmap = load_app_icon().pixmap(40, 40)
        if icon_pixmap.isNull():
            icon_pixmap = fallback_icon(40)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(40, 40)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        logo = QLabel("EMBER")
        logo.setObjectName("title")
        brand_sub = QLabel(AUTHOR)
        brand_sub.setObjectName("subtitle")
        brand_text.addWidget(logo)
        brand_text.addWidget(brand_sub)
        brand.addWidget(icon_label)
        brand.addLayout(brand_text)
        side_layout.addLayout(brand)
        side_layout.addSpacing(8)

        self.nav_home = EmberButton("Игра", nav=True)
        self.nav_versions = EmberButton("Версии", nav=True)
        self.nav_setup = EmberButton("Установка", nav=True)
        self.nav_news = EmberButton("Новости", nav=True)
        self._nav = (self.nav_home, self.nav_versions, self.nav_setup, self.nav_news)
        self.nav_home.clicked.connect(lambda: self._show_page(0))
        self.nav_versions.clicked.connect(lambda: self._show_page(1))
        self.nav_setup.clicked.connect(lambda: self._show_page(2))
        self.nav_news.clicked.connect(lambda: self._show_page(3))
        for button in self._nav:
            side_layout.addWidget(button)
        side_layout.addStretch(1)
        self.download_stat = QLabel("Скачали лаунчер: …\nОнлайн: укажи адрес сервера")
        self.download_stat.setObjectName("muted")
        self.download_stat.setWordWrap(True)
        self.download_stat.setToolTip(
            "Верхняя строка — сколько раз скачали лаунчер с GitHub. "
            "Нижняя — игроки на твоём сервере Minecraft. Отдельный сайт для счётчика не нужен."
        )
        side_layout.addWidget(self.download_stat)
        self.status_host = QLineEdit(str(self._config.get("status_host") or self._server.get("host") or ""))
        self.status_host.setPlaceholderText("IP сервера, например play.example.com")
        self.status_host.editingFinished.connect(self._ping_server)
        side_layout.addWidget(self.status_host)
        self._download_count: int | None = None
        self._online_line = "Онлайн: укажи адрес сервера"
        side_layout.addWidget(self._section("НИК"))
        self.nick_edit = QComboBox()
        self.nick_edit.setEditable(True)
        self.nick_edit.addItems(self._config.get("accounts") or ["Player"])
        self.nick_edit.setCurrentText(self._config["nickname"])
        if self.nick_edit.lineEdit() is not None:
            self.nick_edit.lineEdit().setMaxLength(16)
            self.nick_edit.lineEdit().setPlaceholderText("Steve")
            self.nick_edit.lineEdit().returnPressed.connect(lambda: self.play())
        self.nick_edit.currentTextChanged.connect(self._sync_chips)
        nick_row = QHBoxLayout()
        self.save_nick_btn = EmberButton("Запомнить")
        self.save_nick_btn.clicked.connect(self.remember_account)
        self.forget_nick_btn = EmberButton("Забыть")
        self.forget_nick_btn.clicked.connect(self.forget_account)
        nick_row.addWidget(self.save_nick_btn)
        nick_row.addWidget(self.forget_nick_btn)
        side_layout.addWidget(self.nick_edit)
        side_layout.addLayout(nick_row)
        self.update_btn = EmberButton("Обновление")
        self.update_btn.clicked.connect(lambda: self.check_for_update(True))
        self.full_btn = EmberButton("Полный экран")
        self.full_btn.clicked.connect(self.toggle_fullscreen)
        side_layout.addWidget(self.update_btn)
        side_layout.addWidget(self.full_btn)
        if self._server.get("credit"):
            credit = QLabel(self._server["credit"])
            credit.setObjectName("credit")
            credit.setWordWrap(True)
            side_layout.addWidget(credit)

        center = MaterialFrame("parchment", 0)
        center.setObjectName("centerCard")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 16, 18, 14)
        center_layout.setSpacing(10)
        home_kicker = QLabel("HOME")
        home_kicker.setObjectName("kicker")
        self.hello = QLabel("ДОБРО ПОЖАЛОВАТЬ")
        self.hello.setObjectName("hello")
        self.hello.setWordWrap(True)
        center_layout.addWidget(home_kicker)
        center_layout.addWidget(self.hello)

        self.pages = QStackedWidget()
        home = QWidget()
        home_layout = QVBoxLayout(home)
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(10)
        self.stage = StageBanner()
        home_layout.addWidget(self.stage)
        home_layout.addWidget(self._section("ЧТО ЗАПУСКАТЬ"))
        self.version_combo = QComboBox()
        self.version_combo.setMaxVisibleItems(14)
        self.version_combo.currentTextChanged.connect(self._apply_profile_target)
        self.version_combo.currentTextChanged.connect(self._sync_chips)
        home_layout.addWidget(self.version_combo)
        self.version_about = QLabel("Здесь будет описание выбранной версии.")
        self.version_about.setObjectName("muted")
        self.version_about.setWordWrap(True)
        home_layout.addWidget(self.version_about)
        other = EmberButton("Скачать другую версию")
        other.clicked.connect(lambda: self._show_page(1))
        home_layout.addWidget(other)
        home_layout.addStretch(1)

        versions = QWidget()
        versions_layout = QVBoxLayout(versions)
        versions_layout.setContentsMargins(0, 4, 0, 0)
        versions_layout.setSpacing(8)
        versions_layout.addWidget(self._section("ВЕРСИЯ"))
        chip_row = QHBoxLayout()
        chip_row.setSpacing(6)
        for label in ("1.21.1", "1.21.4", "1.21.11", "1.20.1", "1.19.2", "26.3"):
            chip = EmberButton(label)
            chip.setShrinkable(True)
            chip.clicked.connect(lambda text=label: self.target_edit.setText(text))
            self._version_chips.append(chip)
            chip_row.addWidget(chip)
        versions_layout.addLayout(chip_row)
        new_line = QHBoxLayout()
        self.target_edit = QLineEdit(self._config["target_version"])
        self.target_edit.setPlaceholderText("с 1.19.2: 1.20.1, 1.21.8, 26.3")
        self.target_edit.textChanged.connect(self._sync_chips)
        self.catalog_btn = EmberButton("Каталог")
        self.catalog_btn.setMinimumWidth(100)
        self.catalog_btn.clicked.connect(self.pick_version)
        new_line.addWidget(self.target_edit, 1)
        new_line.addWidget(self.catalog_btn)
        versions_layout.addLayout(new_line)
        versions_layout.addWidget(self._section("ЗАГРУЗЧИК"))
        self.loader_combo = QComboBox()
        for loader_id, label in LOADERS:
            self.loader_combo.addItem(label, loader_id)
        saved = self.loader_combo.findData(self._config["loader"])
        if saved >= 0:
            self.loader_combo.setCurrentIndex(saved)
        self.loader_combo.currentTextChanged.connect(self._sync_chips)
        versions_layout.addWidget(self.loader_combo)
        self.loader_about = QLabel("")
        self.loader_about.setObjectName("muted")
        self.loader_about.setWordWrap(True)
        versions_layout.addWidget(self.loader_about)
        version_actions = QHBoxLayout()
        self.download_btn = EmberButton("Скачать", primary=True)
        self.download_btn.clicked.connect(self.download_version)
        self.refresh_btn = EmberButton("Обновить список")
        self.refresh_btn.clicked.connect(self.refresh_versions)
        version_actions.addWidget(self.download_btn, 1)
        version_actions.addWidget(self.refresh_btn)
        versions_layout.addLayout(version_actions)
        versions_hint = QLabel(
            "Сначала номер, сразу под ним загрузчик. Моды — с 1.19.2 и новее, на любой номер, не только на кнопки. "
            "Свой запрос пиши справа: животные, военная, магия."
        )
        versions_hint.setObjectName("muted")
        versions_hint.setWordWrap(True)
        versions_layout.addWidget(versions_hint)
        versions_layout.addStretch(1)

        setup = QWidget()
        setup_layout = QVBoxLayout(setup)
        setup_layout.setContentsMargins(0, 4, 0, 0)
        setup_layout.setSpacing(8)
        ram_head = QHBoxLayout()
        ram_head.addWidget(self._section("ПАМЯТЬ"))
        ram_head.addStretch(1)
        self.ram_value = QLabel("")
        self.ram_value.setObjectName("ramValue")
        ram_head.addWidget(self.ram_value)
        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setRange(1, 16)
        self.ram_slider.setValue(int(self._config["ram_gb"]))
        self.ram_slider.valueChanged.connect(self._on_ram_slider)
        setup_layout.addLayout(ram_head)
        setup_layout.addWidget(self.ram_slider)
        self.ram_value.setText(f"{self.ram_slider.value()} ГБ")
        setup_layout.addWidget(self._section("JAVA"))
        java_row = QHBoxLayout()
        self.java_edit = QLineEdit(self._config["java_path"])
        self.java_edit.setPlaceholderText("Пусто — возьму выбранную версию Java")
        self.java_runtime = QComboBox()
        self.java_runtime.setMinimumWidth(118)
        for runtime_id, label in JAVA_RUNTIMES:
            self.java_runtime.addItem(label, runtime_id)
        saved_runtime = self.java_runtime.findData(self._config.get("java_runtime"))
        if saved_runtime >= 0:
            self.java_runtime.setCurrentIndex(saved_runtime)
        self.java_dl_btn = EmberButton("Скачать Java")
        self.java_dl_btn.clicked.connect(self.download_java)
        self.java_btn = EmberButton("Файл")
        self.java_btn.clicked.connect(self.pick_java)
        self.java_auto_btn = EmberButton("Авто")
        self.java_auto_btn.clicked.connect(self.autodetect_java)
        java_row.addWidget(self.java_edit, 1)
        java_row.addWidget(self.java_runtime)
        java_row.addWidget(self.java_dl_btn)
        java_row.addWidget(self.java_btn)
        java_row.addWidget(self.java_auto_btn)
        setup_layout.addLayout(java_row)
        setup_layout.addWidget(self._section("ПАПКА MINECRAFT"))
        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit(self._resolved_minecraft_dir())
        self.pick_dir_btn = EmberButton("Папка")
        self.pick_dir_btn.clicked.connect(self.pick_minecraft_dir)
        self.root_btn = EmberButton("Корень игры")
        self.root_btn.clicked.connect(self.open_game_root)
        self.mods_btn = EmberButton("Моды")
        self.mods_btn.clicked.connect(self.open_mods)
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(self.pick_dir_btn)
        dir_row.addWidget(self.root_btn)
        dir_row.addWidget(self.mods_btn)
        setup_layout.addLayout(dir_row)
        setup_layout.addWidget(self._section("ПОМОЩНИК СБОРОК"))
        helper = QLabel("Нейросеть только понимает фразу. Моды и шейдеры ищет сам лаунчер на Modrinth. Ключ в список настроек не пишется.")
        helper.setObjectName("muted")
        helper.setWordWrap(True)
        setup_layout.addWidget(helper)
        self.llm_provider = QComboBox()
        self.llm_provider.addItem("Без нейросети, готовые подборки", "off")
        self.llm_provider.addItem("Ollama на этом компьютере", "ollama")
        self.llm_provider.addItem("DeepSeek, свой ключ", "deepseek")
        self.llm_provider.addItem("OpenRouter, свой ключ", "openrouter")
        saved_provider = self.llm_provider.findData(self._config.get("llm_provider") or "off")
        if saved_provider >= 0:
            self.llm_provider.setCurrentIndex(saved_provider)
        setup_layout.addWidget(self.llm_provider)
        self.ollama_model = QLineEdit(str(self._config.get("ollama_model") or "qwen2.5:3b"))
        self.ollama_model.setPlaceholderText("Модель Ollama, например qwen2.5:3b или llama3.1:8b")
        setup_layout.addWidget(self.ollama_model)
        self.openrouter_model = QLineEdit(str(self._config.get("openrouter_model") or ""))
        self.openrouter_model.setPlaceholderText("Модель OpenRouter, бесплатные обычно кончаются на :free")
        setup_layout.addWidget(self.openrouter_model)
        key_row = QHBoxLayout()
        self.llm_key = QLineEdit()
        self.llm_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_key.setPlaceholderText("Ключ DeepSeek или OpenRouter, один раз")
        self.save_key_btn = EmberButton("Запомнить ключ")
        self.save_key_btn.clicked.connect(self.save_llm_key)
        key_row.addWidget(self.llm_key, 1)
        key_row.addWidget(self.save_key_btn)
        setup_layout.addLayout(key_row)
        self.optimize_check = QCheckBox("Добавлять оптимизацию, если она есть на эту версию")
        self.optimize_check.setChecked(self._config.get("assistant_optimize") is not False)
        setup_layout.addWidget(self.optimize_check)
        setup_layout.addWidget(self._section("ЗАПУСК"))
        launch_row = QHBoxLayout()
        self.linux_compat = QComboBox()
        for mode, label in (
            ("auto", "Linux: авто"),
            ("x11", "Linux: X11"),
            ("wayland", "Linux: Wayland"),
            ("nvidia", "Linux: NVIDIA"),
            ("mesa", "Linux: Mesa"),
            ("openal", "Linux: звук Pulse"),
        ):
            self.linux_compat.addItem(label, mode)
        saved_compat = self.linux_compat.findData(self._config.get("linux_compat") or "auto")
        if saved_compat >= 0:
            self.linux_compat.setCurrentIndex(saved_compat)
        self.mac_thread = QComboBox()
        for mode, label in (
            ("auto", "Mac: поток авто"),
            ("always", "Mac: главный поток"),
            ("never", "Mac: без флага"),
        ):
            self.mac_thread.addItem(label, mode)
        saved_thread = self.mac_thread.findData(self._config.get("mac_thread") or "auto")
        if saved_thread >= 0:
            self.mac_thread.setCurrentIndex(saved_thread)
        self.gpu_btn = EmberButton("Мощная видеокарта")
        self.gpu_btn.clicked.connect(self.prefer_gpu)
        self.check_files_btn = EmberButton("Проверить файлы")
        self.check_files_btn.clicked.connect(self.check_game_files)
        launch_row.addWidget(self.linux_compat, 1)
        launch_row.addWidget(self.mac_thread, 1)
        launch_row.addWidget(self.gpu_btn)
        launch_row.addWidget(self.check_files_btn)
        setup_layout.addLayout(launch_row)
        setup_layout.addStretch(1)

        news = QWidget()
        news_layout = QVBoxLayout(news)
        news_layout.setContentsMargins(0, 4, 0, 0)
        news_layout.setSpacing(8)
        news_layout.addWidget(self._section("НОВОСТИ"))
        news_hint = QLabel("Релизы Ember с GitHub. Игра отсюда не обновляется — для этого кнопка «Обновление».")
        news_hint.setObjectName("muted")
        news_hint.setWordWrap(True)
        news_layout.addWidget(news_hint)
        news_scroll = QScrollArea()
        news_scroll.setWidgetResizable(True)
        news_scroll.setFrameShape(QFrame.Shape.NoFrame)
        news_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.news_box = QLabel("Открываю новости…")
        self.news_box.setObjectName("newsBody")
        self.news_box.setWordWrap(True)
        self.news_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.news_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.news_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        news_scroll.setWidget(self.news_box)
        news_layout.addWidget(news_scroll, 1)

        self.pages.addWidget(home)
        self.pages.addWidget(versions)
        self.pages.addWidget(setup)
        self.pages.addWidget(news)
        center_layout.addWidget(self.pages, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status = QLabel("Готово.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        center_layout.addWidget(self.progress)
        center_layout.addWidget(self.status)

        footer = MaterialFrame("leather", 24)
        footer.setObjectName("footerBar")
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(10, 8, 8, 8)
        footer_row.setSpacing(8)
        self.footer_version = QLabel("—")
        self.footer_version.setObjectName("chip")
        self.footer_nick = QLabel(self._config["nickname"])
        self.footer_nick.setObjectName("chip")
        self.settings_btn = EmberButton("Настройки")
        self.settings_btn.clicked.connect(lambda: self._show_page(2))
        self.play_btn = EmberButton("Играть", primary=True)
        self.play_btn.setMinimumWidth(190)
        self.play_btn.setMinimumHeight(52)
        self.play_btn.clicked.connect(lambda: self.play())
        footer_row.addWidget(self.footer_version)
        footer_row.addWidget(self.footer_nick)
        footer_row.addWidget(self.settings_btn)
        footer_row.addStretch(1)
        footer_row.addWidget(self.play_btn)
        center_layout.addWidget(footer)

        right = MaterialFrame("mossy", 48)
        right.setObjectName("sidePanel")
        right.setFixedWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 12)
        right_layout.setSpacing(8)
        packs_title = QLabel("СБОРКИ")
        packs_title.setObjectName("kicker")
        self.pack_target = QLabel("Сборка")
        self.pack_target.setObjectName("packTarget")
        self.pack_target.setWordWrap(True)
        packs_hint = QLabel("Напиши, что хочешь: «оптимизация и красивая графика на 1.20.1». Галка — ставить, снятая галка — убрать.")
        packs_hint.setObjectName("muted")
        packs_hint.setWordWrap(True)
        right_layout.addWidget(packs_title)
        right_layout.addWidget(self.pack_target)
        right_layout.addWidget(packs_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body = QWidget()
        body.setObjectName("scrollBody")
        body.setMinimumWidth(0)
        body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 4, 0)
        body_layout.setSpacing(8)
        grid_host = QWidget()
        grid_host.setMinimumWidth(0)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        short_names = {
            "visual": "Визуал",
            "zombie": "Зомби",
            "survival": "Выживание",
            "weapons": "Оружие",
            "machines": "Механизмы",
            "magic": "Магия",
            "optimize": "Оптимизация",
            "vanilla_plus": "Ванильное+",
        }
        for index, pack in enumerate(PRESETS):
            button = EmberButton(short_names.get(pack["id"], pack["title"]))
            button.setShrinkable(True)
            button.setToolTip(pack["summary"])
            button.clicked.connect(lambda preset_id=pack["id"]: self._quick_pack(preset_id))
            self._pack_btns.append(button)
            grid.addWidget(button, index // 2, index % 2)
        body_layout.addWidget(grid_host)
        body_layout.addWidget(self._section("СВОЯ СБОРКА"))
        ask_row = QHBoxLayout()
        self.ask_edit = QLineEdit()
        self.ask_edit.setPlaceholderText("много животных на 1.21.1")
        self.ask_edit.returnPressed.connect(self.ask_pack)
        self.ask_btn = EmberButton("Собрать")
        self.ask_btn.setShrinkable(True)
        self.ask_btn.clicked.connect(self.ask_pack)
        ask_row.addWidget(self.ask_edit, 1)
        ask_row.addWidget(self.ask_btn)
        body_layout.addLayout(ask_row)
        self.plan_label = QLabel("Запрос разберётся сам. Перед установкой будет список: галка значит «будет установлено».")
        self.plan_label.setObjectName("muted")
        self.plan_label.setWordWrap(True)
        body_layout.addWidget(self.plan_label)
        self.mod_list = QListWidget()
        self.mod_list.setMinimumHeight(120)
        self.mod_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.mod_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.mod_list.setItemDelegate(ModListDelegate(self.mod_list))
        body_layout.addWidget(self.mod_list)
        self.install_loader_check = QCheckBox("Поставить загрузчик, если его ещё нет")
        self.install_loader_check.setChecked(True)
        body_layout.addWidget(self.install_loader_check)
        self.install_pack_btn = EmberButton("В папку mods", primary=True)
        self.install_pack_btn.clicked.connect(self.install_pack)
        self.install_pack_btn.setEnabled(False)
        body_layout.addWidget(self.install_pack_btn)
        choice = QHBoxLayout()
        self.drop_mods_btn = EmberButton("Убрать снятые")
        self.drop_mods_btn.setShrinkable(True)
        self.drop_mods_btn.clicked.connect(self.drop_unchecked_mods)
        self.drop_mods_btn.setEnabled(False)
        self.skip_pack_btn = EmberButton("Отмена")
        self.skip_pack_btn.setShrinkable(True)
        self.skip_pack_btn.clicked.connect(self.skip_pack)
        self.skip_pack_btn.setEnabled(False)
        self.rollback_btn = EmberButton("Откатить")
        self.rollback_btn.setShrinkable(True)
        self.rollback_btn.clicked.connect(self.rollback_active_instance)
        self.packs_btn = EmberButton("Все сборки")
        self.packs_btn.setShrinkable(True)
        self.packs_btn.clicked.connect(self.open_pack_menu)
        choice.addWidget(self.drop_mods_btn)
        choice.addWidget(self.skip_pack_btn)
        choice.addWidget(self.rollback_btn)
        choice.addWidget(self.packs_btn)
        body_layout.addLayout(choice)
        scroll.setWidget(body)
        right_layout.addWidget(scroll, 1)

        self.server_card = ServerCard(self._server)
        self.server_card.copy_btn.clicked.connect(self.copy_server)
        self.server_card.join_btn.clicked.connect(lambda: self.play(server=self._server.get("host") or None))
        self.server_card.discord_btn.clicked.connect(lambda: self._open_https(self._server.get("discord") or ""))
        self.server_card.telegram_btn.clicked.connect(lambda: self._open_https(self._server.get("telegram") or ""))
        if self._server.get("host"):
            right_layout.addWidget(self.server_card)
        else:
            self.server_card.hide()

        root.addWidget(side)
        root.addWidget(center, 1)
        root.addWidget(right)
        self._show_page(0)
        self._sync_chips()
        self.refresh_versions()
        reveal_materials(self)

    def showEvent(self, event) -> None:
        reveal_materials(self)
        super().showEvent(event)
        enable_windows_dark_title(int(self.winId()))
        if not self._faded:
            self._faded = True
            screen = QApplication.primaryScreen()
            if screen is not None:
                frame = self.frameGeometry()
                frame.moveCenter(screen.availableGeometry().center())
                self.move(frame.topLeft())
            self.setWindowOpacity(0.0)
            self._fade = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade.setDuration(320)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade.start()
            QTimer.singleShot(450, lambda: self.setWindowOpacity(1.0))
            QTimer.singleShot(1600, lambda: self.check_for_update(False))
            QTimer.singleShot(900, self._ping_server)
        if self._news_worker is None:
            self._load_news()

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self._nav):
            button.setSelected(button_index == index)
        if index == 3 and self._news_worker is None:
            self._load_news()

    def _load_news(self) -> None:
        repo = active_update_repo(self._config) or DEFAULT_UPDATE_REPO
        worker = NewsWorker(repo)
        self._news_worker = worker
        worker.ready.connect(self._on_news)
        worker.failed.connect(self._on_news_failed)
        worker.downloads.connect(self._on_downloads)
        worker.start()

    def _on_news(self, items: object) -> None:
        rows = items if isinstance(items, list) else []
        blocks: list[str] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            blocks.append(f"{item.get('version') or 'Релиз'}   {item.get('date') or ''}\n{item.get('body') or ''}")
        self.news_box.setText("\n\n".join(blocks) if blocks else self._fallback_news())
        self._fit_news()

    def _on_downloads(self, count: int) -> None:
        self._download_count = count
        self._render_stat()

    def _render_stat(self) -> None:
        count = getattr(self, "_download_count", None)
        if count is None:
            first = "Скачали лаунчер: …"
        elif count < 0:
            first = "Скачали лаунчер: нет сети"
        else:
            first = f"Скачали лаунчер: {count}"
        online = getattr(self, "_online_line", "Онлайн: укажи адрес сервера")
        self.download_stat.setText(f"{first}\n{online}")

    def _ping_server(self) -> None:
        host = ""
        field = getattr(self, "status_host", None)
        if field is not None:
            host = field.text().strip()
        if not host:
            host = str(self._server.get("host") or "")
        if not split_server_address(host)[0]:
            self._online_line = "Онлайн: укажи адрес сервера"
            self._render_stat()
            self.persist()
            return
        worker = getattr(self, "_status_worker", None)
        if worker is not None and worker.isRunning():
            return
        self._online_line = "Онлайн: спрашиваю сервер…"
        self._render_stat()
        worker = ServerStatusWorker(host)
        self._status_worker = worker
        worker.ready.connect(self._on_server_status)
        worker.start()
        self.persist()

    def _on_server_status(self, info: object) -> None:
        data = info if isinstance(info, dict) else {}
        if data.get("ok"):
            self._online_line = f"Онлайн: {int(data.get('online') or 0)} из {int(data.get('max') or 0)}"
        else:
            self._online_line = "Сервер не отвечает"
        self._render_stat()

    def _on_news_failed(self, _message: str) -> None:
        self.news_box.setText(self._fallback_news())
        self._fit_news()

    def _fit_news(self) -> None:
        width = max(220, self.news_box.width())
        self.news_box.setMinimumHeight(self.news_box.heightForWidth(width) + 8)

    def _fallback_news(self) -> str:
        return (
            "Релизы GitHub сейчас не открылись. Кнопка «Обновление» слева качает новую сборку лаунчера.\n\n"
            "Игра — профиль, который запускается, и описание этой версии.\n"
            "Версии — номер и загрузчик вместе. Сначала 1.21.1, потом Fabric, Forge или OptiFine, потом «Скачать».\n"
            "Сборки справа идут на эту же пару. Если написать просто 1.21 и файлов нет, берётся 1.21.1."
        )

    def _apply_profile_target(self, *_args: object) -> None:
        version = self.version_combo.currentText().strip()
        if not version:
            return
        release = minecraft_release_from_id(version) or installed_game_version(self.minecraft_dir(), version)
        if release and self.target_edit.text().strip() != release:
            self.target_edit.setText(release)
        low = version.lower()
        loader = "vanilla"
        for key in ("neoforge", "fabric", "quilt", "optifine", "forge"):
            if key in low:
                loader = key
                break
        index = self.loader_combo.findData(loader)
        if index >= 0 and self.loader_combo.currentIndex() != index:
            self.loader_combo.setCurrentIndex(index)

    def _sync_chips(self, *_args: object) -> None:
        nick = self.nickname() or "Player"
        self.hello.setText(f"ДОБРО ПОЖАЛОВАТЬ, {nick}!")
        self.footer_nick.setText(nick)
        version = self.version_combo.currentText().strip()
        target = self.target_edit.text().strip()
        loader_name = self.loader_combo.currentText() or "Vanilla"
        self.loader_about.setText(LOADER_BLURBS.get(self.loader_id(), ""))
        self.pack_target.setText(f"Сборки и скачивание: {target or 'версия не выбрана'} · {loader_name}")
        if not version:
            self.footer_version.setText("нет версии")
            self.stage.set_caption("Нет версии", "Открой «Версии», выбери номер и загрузчик.")
            self.version_about.setText(
                "Пока ничего не установлено. Во вкладке «Версии» выбери номер, например 1.21.1, "
                "сразу под ним загрузчик и нажми «Скачать». Потом вернись сюда и жми «Играть»."
            )
            return
        release = minecraft_release_from_id(version) or installed_game_version(self.minecraft_dir(), version) or version
        low = version.lower()
        if "neoforge" in low:
            profile_loader = "NeoForge"
        elif "fabric" in low:
            profile_loader = "Fabric"
        elif "quilt" in low:
            profile_loader = "Quilt"
        elif "optifine" in low:
            profile_loader = "OptiFine"
        elif "forge" in low:
            profile_loader = "Forge"
        else:
            profile_loader = "Vanilla"
        blurb = VERSION_BLURBS.get(release, "Установленный профиль. Новую игру качай во вкладке «Версии».")
        about = f"{release} · {profile_loader}\n{blurb}\nЗапускается профиль «{version}»."
        if target and release and target != release:
            about += (
                f"\nСборки справа сейчас на {target} · {loader_name}. "
                f"Если моды нужны в этот профиль, поставь {release} во вкладке «Версии»."
            )
        self.footer_version.setText(f"{release} · {profile_loader}")
        self.stage.set_caption(f"{release} · {profile_loader}", blurb)
        self.version_about.setText(about)

    def _mod_loader(self) -> str:
        loader = self.loader_id()
        if loader in ("vanilla", "optifine"):
            loader = "fabric"
            index = self.loader_combo.findData("fabric")
            if index >= 0:
                self.loader_combo.setCurrentIndex(index)
            self._set_status("Для модов нужен Fabric, Forge, NeoForge или Quilt. Взял Fabric — смени во вкладке «Версии», если нужен другой.")
        return loader

    def _pack_version(self, query: str = "") -> str:
        found = minecraft_release_from_id(query) if query else ""
        if found:
            self.target_edit.setText(found)
            return found
        typed = self.target_edit.text().strip()
        if typed:
            return minecraft_release_from_id(typed) or typed
        selected = self.version_combo.currentText().strip()
        detected = installed_game_version(self.minecraft_dir(), selected) if selected else ""
        version = detected or "1.21.1"
        self.target_edit.setText(version)
        return version

    def _quick_pack(self, preset_id: str) -> None:
        if self._busy:
            return
        pack = next((item for item in PRESETS if item["id"] == preset_id), None)
        if pack is None:
            return
        loader = self._mod_loader()
        version = self._pack_version(pack["title"])
        self.ask_edit.setText(pack["title"])
        self.plan_label.setText(f"Собираю «{pack['title']}» для {version} · {loader}…")
        self.mod_list.clear()
        self._plan = None
        self._start_worker(PackWorker(pack["title"], loader, version, pack["id"], ("modrinth", "curseforge")))

    def _resolved_minecraft_dir(self) -> str:
        stored = self._config.get("minecraft_dir") or ""
        return stored or default_minecraft_dir()

    def minecraft_dir(self) -> str:
        typed = self.dir_edit.text().strip().strip('"')
        return typed or default_minecraft_dir()

    def java_runtime_id(self) -> str:
        return str(self.java_runtime.currentData() or "java-runtime-delta")

    def java_path(self) -> str:
        typed = self.java_edit.text().strip().strip('"')
        if typed:
            return typed
        runtime = self.java_runtime_id()
        if minecraft_launcher_lib is not None and runtime:
            try:
                found = minecraft_launcher_lib.runtime.get_executable_path(runtime, self.minecraft_dir())
            except Exception:
                found = None
            if found:
                return found
        return find_best_java(self.minecraft_dir())

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.full_btn.setText("Полный экран")
        else:
            self.showFullScreen()
            self.full_btn.setText("Окно")

    def nickname(self) -> str:
        return self.nick_edit.currentText().strip()

    def saved_accounts(self) -> list[str]:
        found: list[str] = []
        for index in range(self.nick_edit.count()):
            nick = self.nick_edit.itemText(index).strip()
            if NICK_RE.fullmatch(nick) and nick not in found:
                found.append(nick)
        current = self.nickname()
        if NICK_RE.fullmatch(current) and current not in found:
            found.insert(0, current)
        return found[:16]

    def remember_account(self) -> None:
        nick = self.nickname()
        if self._validate_nickname(nick):
            self._set_status(self._validate_nickname(nick))
            return
        if self.nick_edit.findText(nick) < 0:
            self.nick_edit.addItem(nick)
        self.nick_edit.setCurrentText(nick)
        self.persist()
        self._set_status(f"Ник {nick} сохранён на этом компьютере.")

    def forget_account(self) -> None:
        nick = self.nickname()
        index = self.nick_edit.findText(nick)
        if index >= 0:
            self.nick_edit.removeItem(index)
        self.persist()
        self._set_status("Ник убран из списка. Паролей лаунчер не хранит.")

    def _open_https(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            self._set_status("Ссылка сервера не задана.")
            return
        QDesktopServices.openUrl(QUrl(url))

    def loader_id(self) -> str:
        return str(self.loader_combo.currentData() or "vanilla")

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for widget in (
            self.play_btn, self.download_btn, self.pick_dir_btn, self.refresh_btn,
            self.java_btn, self.java_auto_btn, self.java_dl_btn, self.catalog_btn, self.ask_btn,
            self.packs_btn, self.save_nick_btn, self.forget_nick_btn, self.settings_btn,
            self.server_card.join_btn, self.server_card.discord_btn, self.server_card.telegram_btn,
            self.full_btn, self.update_btn, *self._nav, *self._pack_btns, *self._version_chips,
        ):
            widget.setEnabled(not busy)
        self.nick_edit.setEnabled(not busy)
        self.version_combo.setEnabled(not busy)
        self.loader_combo.setEnabled(not busy)
        self.dir_edit.setEnabled(not busy)
        self.java_edit.setEnabled(not busy)
        self.java_runtime.setEnabled(not busy)
        self.target_edit.setEnabled(not busy)
        self.ram_slider.setEnabled(not busy)
        self.ask_edit.setEnabled(not busy)
        self.mod_list.setEnabled(not busy)
        self.install_loader_check.setEnabled(not busy)
        extra = getattr(self, "drop_mods_btn", None)
        if extra is not None and busy:
            extra.setEnabled(False)
        rollback = getattr(self, "rollback_btn", None)
        if rollback is not None:
            rollback.setEnabled(not busy)
        key_button = getattr(self, "save_key_btn", None)
        if key_button is not None:
            key_button.setEnabled(not busy)
        for name in ("gpu_btn", "check_files_btn"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(not busy)
        if busy:
            self.install_pack_btn.setEnabled(False)
            self.skip_pack_btn.setEnabled(False)

    def current_settings(self) -> dict:
        return {
            "nickname": self.nickname(),
            "accounts": self.saved_accounts(),
            "minecraft_dir": self.minecraft_dir(),
            "java_path": self.java_edit.text().strip().strip('"'),
            "java_runtime": self.java_runtime_id(),
            "ram_gb": int(self.ram_slider.value()),
            "last_version": self.version_combo.currentText().strip(),
            "loader": self.loader_id(),
            "target_version": self.target_edit.text().strip(),
            "update_repo": clean_repo(str(self._config.get("update_repo") or "")),
            "llm_provider": str(self.llm_provider.currentData() or "off"),
            "ollama_model": self.ollama_model.text().strip() or "qwen2.5:3b",
            "ollama_url": "http://127.0.0.1:11434",
            "openrouter_model": self.openrouter_model.text().strip() or "meta-llama/llama-3.2-3b-instruct:free",
            "active_instance": str(self._config.get("active_instance") or ""),
            "assistant_optimize": bool(self.optimize_check.isChecked()),
            "ram_auto": self._config.get("ram_auto") is not False,
            "linux_compat": str(self.linux_compat.currentData() or "auto"),
            "mac_thread": str(self.mac_thread.currentData() or "auto"),
            "status_host": self.status_host.text().strip() if getattr(self, "status_host", None) is not None else "",
        }

    def persist(self) -> None:
        self._config = self.current_settings()
        try:
            save_config(self._config)
        except OSError as exc:
            self._set_status(f"Не сохранил настройки: {exc}")

    def closeEvent(self, event) -> None:
        self.persist()
        if self._worker is not None and self._worker.isRunning():
            self._worker.setParent(None)
            _ORPHAN_THREADS.append(self._worker)
            self._worker = None
        if self._news_worker is not None and self._news_worker.isRunning():
            self._news_worker.setParent(None)
            _ORPHAN_THREADS.append(self._news_worker)
            self._news_worker = None
        if self._log_file is not None:
            try:
                self._log_file.close()
            except OSError:
                pass
        super().closeEvent(event)

    def refresh_versions(self) -> None:
        directory = self.minecraft_dir()
        previous = self.version_combo.currentText().strip() or self._config.get("last_version", "")
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        versions = installed_version_ids(directory)
        self.version_combo.addItems(versions)
        if previous:
            index = self.version_combo.findText(previous)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        self.version_combo.blockSignals(False)
        current = self.version_combo.currentText().strip()
        if not self._profile_synced or current != previous:
            self._profile_synced = True
            self._apply_profile_target()
        self._sync_chips()
        if versions:
            self._set_status(f"Установлено версий: {len(versions)}.")
        else:
            self._set_status("Версий нет. Впиши номер и нажми «Скачать».")

    def pick_minecraft_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Папка .minecraft", self.minecraft_dir())
        if not chosen:
            return
        self.dir_edit.setText(chosen)
        self.refresh_versions()
        self.persist()

    def open_game_root(self) -> None:
        open_folder(self.minecraft_dir())

    def open_mods(self) -> None:
        open_folder(os.path.join(self.minecraft_dir(), "mods"))

    def pick_java(self) -> None:
        chosen, _selected = QFileDialog.getOpenFileName(
            self, "Java", os.path.dirname(self.java_edit.text().strip()) or self.minecraft_dir(),
            "Java (javaw.exe java.exe java);;Все файлы (*.*)",
        )
        if chosen:
            self.java_edit.setText(chosen)
            self.persist()

    def autodetect_java(self) -> None:
        detected = find_best_java(self.minecraft_dir())
        if not detected:
            QMessageBox.warning(self, APP_NAME, "Java не найдена. Поставь Java 17+ или скачай версию — подтянется своя.")
            return
        self.java_edit.setText(detected)
        self._set_status("Java подставлена.")
        self.persist()

    def pick_version(self) -> None:
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        dialog = DownloadDialog(self.minecraft_dir(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        version = dialog.chosen_version().strip()
        if version:
            self.target_edit.setText(version)

    def copy_server(self) -> None:
        host = self._server.get("host") or ""
        if not host:
            self._set_status("Сервер не задан.")
            return
        QApplication.clipboard().setText(host)
        self._set_status(f"IP скопирован: {host}")

    def download_version(self) -> None:
        if self._busy:
            return
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        version = self.target_edit.text().strip()
        if not version:
            self._set_status("Впиши версию, например 1.21.1 или 26.3, или открой каталог.")
            return
        self.persist()
        self._start_worker(InstallWorker(self.loader_id(), version, self.minecraft_dir(), self.java_path()))
        names = dict(LOADERS)
        self._set_status(f"Скачиваю {names.get(self.loader_id(), self.loader_id())} {version}…")

    def _start_worker(self, worker: QThread) -> None:
        self._set_busy(True)
        self.progress.setRange(0, 0)
        self._worker = worker
        if isinstance(worker, InstallWorker):
            worker.status.connect(self._set_status)
            worker.maximum.connect(self._on_install_max)
            worker.progress.connect(self._on_install_progress)
            worker.succeeded.connect(self._on_install_done)
            worker.failed.connect(self._on_failed)
        elif isinstance(worker, PackWorker):
            worker.ready.connect(self._on_plan)
            worker.failed.connect(self._on_failed)
        elif isinstance(worker, ModInstallWorker):
            worker.status.connect(self._set_status)
            worker.succeeded.connect(self._on_mods_done)
            worker.failed.connect(self._on_failed)
        elif isinstance(worker, ModRepairWorker):
            worker.status.connect(self._set_status)
            worker.succeeded.connect(self._on_repair_done)
            worker.failed.connect(self._on_repair_failed)
        elif isinstance(worker, JavaWorker):
            worker.status.connect(self._set_status)
            worker.maximum.connect(self._on_install_max)
            worker.progress.connect(self._on_install_progress)
            worker.succeeded.connect(self._on_java_done)
            worker.failed.connect(self._on_failed)
        elif isinstance(worker, FileCheckWorker):
            worker.status.connect(self._set_status)
            worker.succeeded.connect(self._on_files_checked)
            worker.failed.connect(self._on_failed)
        elif isinstance(worker, UpdateCheckWorker):
            worker.ready.connect(self._on_update_info)
            worker.failed.connect(self._on_failed if self._update_manual else self._quiet_update_failed)
        elif isinstance(worker, UpdateDownloadWorker):
            worker.ready.connect(self._on_update_file)
            worker.failed.connect(self._on_failed)
        worker.start()

    def _on_install_max(self, maximum: int) -> None:
        if maximum <= 0:
            self.progress.setRange(0, 0)
            return
        self.progress.setRange(0, maximum)
        self.progress.setValue(0)

    def _on_install_progress(self, value: int) -> None:
        if self.progress.maximum() > 0:
            self.progress.setValue(min(value, self.progress.maximum()))

    def _on_install_done(self, version: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.refresh_versions()
        if version:
            index = self.version_combo.findText(version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
            self._set_status(f"Готово: {version}")
        else:
            self._set_status("Установщик OptiFine открыт. Нажми Install, потом «Обновить».")
        self.persist()

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_status("Ошибка.")
        QMessageBox.critical(self, APP_NAME, message)

    def ask_pack(self) -> None:
        if self._busy:
            return
        query = self.ask_edit.text().strip()
        if len(query) < 2:
            self.plan_label.setText("Напиши любой запрос с версии 1.19.2: животные, военная, данжи. Версию можно прямо в тексте.")
            return
        loader = loader_from_text(query, self.loader_id())
        if loader in ("vanilla", "optifine"):
            loader = "fabric"
        loader_index = self.loader_combo.findData(loader)
        if loader_index >= 0:
            self.loader_combo.setCurrentIndex(loader_index)
        game_version = self._pack_version(query)
        self.plan_label.setText(f"Разбираю запрос и ищу на Modrinth: {game_version} · {loader}…")
        self.mod_list.clear()
        self._plan = None
        self.install_pack_btn.setEnabled(False)
        self.skip_pack_btn.setEnabled(False)
        self.drop_mods_btn.setEnabled(False)
        self._start_worker(PackWorker(query, loader, game_version, assist=True, settings=self.assistant_settings()))

    def check_for_update(self, manual: bool) -> None:
        if self._busy:
            return
        self._update_manual = manual
        repo = active_update_repo(self._config)
        if not repo and manual:
            typed, ok = QInputDialog.getText(
                self,
                "Обновления",
                "Репозиторий GitHub, куда ты выкладываешь релизы.\nНапример: nickname/EmberLauncher",
            )
            if not ok:
                return
            repo = clean_repo(typed)
            if not repo:
                self._set_status("Нужен адрес вида ник/репозиторий.")
                return
            self._config["update_repo"] = repo
            self.persist()
        if not repo:
            return
        self._set_status("Проверяю обновления…")
        self._start_worker(UpdateCheckWorker(repo, APP_VERSION))

    def _quiet_update_failed(self, _message: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        if self.status.text().startswith("Проверяю"):
            self._set_status("Готово.")

    def _on_update_info(self, info: object) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        if not isinstance(info, dict) or not info.get("url"):
            if self._update_manual:
                self._set_status(f"Уже стоит последняя версия {APP_VERSION}.")
            elif self.status.text().startswith("Проверяю"):
                self._set_status("Готово.")
            return
        notes = str(info.get("notes") or "Исправления и улучшения.")
        answer = QMessageBox.question(
            self,
            "Обновление",
            f"Вышла версия {info.get('version')} (сейчас {APP_VERSION}).\n\n{notes}\n\nСкачать и перезапустить?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            self._set_status("Обновление отложено.")
            return
        self._set_status("Качаю обновление…")
        self._start_worker(UpdateDownloadWorker(str(info["url"]), str(info.get("digest") or "")))

    def _on_update_file(self, path: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        try:
            schedule_self_replace(path)
        except Exception as exc:
            self._set_status(str(exc))
            return
        QApplication.instance().quit()

    def open_pack_menu(self) -> None:
        if self._busy:
            return
        dialog = PackMenuDialog(self.target_edit.text().strip(), self.loader_id(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        choice = dialog.choice()
        if not choice:
            return
        self.target_edit.setText(choice["version"])
        loader_index = self.loader_combo.findData(choice["loader"])
        if loader_index >= 0:
            self.loader_combo.setCurrentIndex(loader_index)
        self.ask_edit.setText(choice["title"])
        self.plan_label.setText(f"Собираю «{choice['title']}» для {choice['version']}…")
        self.mod_list.clear()
        self._plan = None
        self._start_worker(PackWorker(
            choice["title"],
            choice["loader"],
            choice["version"],
            choice["id"],
            choice["sources"],
        ))

    def assistant_settings(self) -> dict:
        self.persist()
        return {
            "llm_provider": str(self._config.get("llm_provider") or "off"),
            "ollama_model": str(self._config.get("ollama_model") or ""),
            "ollama_url": "http://127.0.0.1:11434",
            "openrouter_model": str(self._config.get("openrouter_model") or ""),
            "assistant_optimize": self._config.get("assistant_optimize") is not False,
        }

    def save_llm_key(self) -> None:
        provider = str(self.llm_provider.currentData() or "off")
        name = "deepseek" if provider == "deepseek" else "openrouter" if provider == "openrouter" else ""
        if not name:
            self._set_status("Ключ нужен только для DeepSeek или OpenRouter. Ollama работает без ключа.")
            return
        try:
            where = secret_set(name, self.llm_key.text())
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self.llm_key.clear()
        self._set_status(f"Ключ записан: {where}. В настройках и в логе его нет.")

    def _fill_mod_list(self, mods: list) -> None:
        self.mod_list.clear()
        directory = self.minecraft_dir()
        if self._plan and self._plan.get("isolated") and self._plan.get("instance_name"):
            try:
                directory = instance_dir(directory, str(self._plan["instance_name"]))
            except ValueError:
                directory = self.minecraft_dir()
        present = installed_mod_names(directory) if os.path.isdir(directory) else set()
        for mod in mods:
            already = mod_already_installed(mod, present)
            mod["installed"] = already
            source = mod.get("source") or ""
            support = f"{mod.get('support')} · " if mod.get("support") else ""
            library = "библиотека · " if mod.get("library") else ""
            if already:
                item = QListWidgetItem(f"     {support}{library}{mod['title']}  ·  уже в профиле")
                item.setForeground(QColor("#9dffc8"))
                item.setBackground(QColor(16, 42, 30))
            else:
                where = "shaderpacks" if mod.get("folder") == "shaderpacks" else "mods"
                kind = "библиотека" if mod.get("library") else where
                item = QListWidgetItem(f"{support}{mod['title']}  ·  {kind}  ·  {source}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked)
            item.setToolTip(mod.get("blurb") or mod.get("filename") or "")
            item.setData(Qt.ItemDataRole.UserRole, mod.get("slug") or "")
            item.setData(INSTALLED_ROLE, already)
            self.mod_list.addItem(item)

    def _on_plan(self, plan: dict) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        selected = self.version_combo.currentText().strip()
        directory = self.minecraft_dir()
        detected = installed_game_version(directory, selected)
        same_game = bool(selected) and (detected == plan["game_version"] or selected == plan["game_version"])
        has_loader = version_has_loader(selected, plan["loader"]) or version_json_has_loader(directory, selected, plan["loader"])
        plan["install_loader"] = not (same_game and has_loader)
        if plan["install_loader"]:
            note = (
                f" Загрузчика {plan['loader']} на {plan['game_version']} в выбранной версии не видно. "
                "Галка ниже поставит его на эту же версию."
            )
        else:
            note = f" Моды встанут в {plan['game_version']} без переустановки игры."
        self._plan = plan
        if plan.get("game_version"):
            self.target_edit.setText(str(plan["game_version"]))
        self._fill_mod_list(plan.get("mods") or [])
        installed_count = sum(1 for mod in plan.get("mods") or [] if mod.get("installed"))
        if installed_count:
            note += f" Уже лежащие в профиле: {installed_count}. Их заново не качаю."
        where = "Отдельный профиль." if plan.get("isolated") else "Обычная папка mods."
        self.plan_label.setText(
            f"Будет установлено · {plan['title']} · {plan['loader']} · {plan['game_version']}\n"
            f"{plan['summary']}{note} {where} Сними галку и нажми «Убрать снятые», если мод не нужен."
        )
        self.install_loader_check.setChecked(bool(plan["install_loader"]))
        self.install_pack_btn.setText("Установить всё" if plan.get("isolated") else "В папку mods")
        self.install_pack_btn.setEnabled(True)
        self.skip_pack_btn.setEnabled(True)
        self.drop_mods_btn.setEnabled(True)
        self._set_status(f"Список для {plan['game_version']} готов. Ничего не скачано, пока не нажмёшь установку.")

    def skip_pack(self) -> None:
        self._plan = None
        self.mod_list.clear()
        self.install_pack_btn.setEnabled(False)
        self.skip_pack_btn.setEnabled(False)
        self.drop_mods_btn.setEnabled(False)
        self.plan_label.setText("Отмена. Ничего не ставил.")
        self._set_status("Сборку отменил.")

    def drop_unchecked_mods(self) -> None:
        if not self._plan:
            return
        keep: list[dict] = []
        for index in range(self.mod_list.count()):
            item = self.mod_list.item(index)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            slug = str(item.data(Qt.ItemDataRole.UserRole) or "")
            match = next((mod for mod in self._plan.get("mods") or [] if str(mod.get("slug") or "") == slug), None)
            if match is not None:
                keep.append(match)
        self._plan["mods"] = keep
        self._fill_mod_list(keep)
        self._set_status(f"В списке осталось {len(keep)}. Это и будет установлено.")

    def rollback_active_instance(self) -> None:
        name = str(self._config.get("active_instance") or "")
        if not name:
            self._set_status("Активного профиля нет, откатывать нечего.")
            return
        try:
            source = rollback_instance(self.minecraft_dir(), name)
        except (OSError, RuntimeError, ValueError) as exc:
            self._set_status(str(exc))
            return
        self._set_status("Вернул профиль из бэкапа " + os.path.basename(source) + ".")

    def _checked_mods(self, mods: list) -> list:
        wanted: set[str] = set()
        for index in range(self.mod_list.count()):
            item = self.mod_list.item(index)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                wanted.add(str(item.data(Qt.ItemDataRole.UserRole) or ""))
        if not wanted and not self.mod_list.count():
            return list(mods)
        return [mod for mod in mods if str(mod.get("slug") or "") in wanted]

    def install_pack(self) -> None:
        if self._busy or not self._plan:
            return
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        plan = dict(self._plan)
        if plan.get("isolated"):
            for index in range(self.mod_list.count()):
                item = self.mod_list.item(index)
                if item is not None:
                    item.setCheckState(Qt.CheckState.Checked)
        chosen = self._checked_mods(list(self._plan.get("mods") or []))
        fresh = [mod for mod in chosen if not mod.get("installed")]
        if not chosen:
            self._set_status("Отметь хотя бы один мод.")
            return
        if not fresh:
            self._set_status("Зелёные моды уже стоят, заново их не качаю.")
            self.plan_label.setText("Новых модов не выбрано. Зелёная галка значит, что файл уже лежит в mods.")
            return
        plan["mods"] = fresh
        install_loader = bool(self._plan.get("install_loader")) and self.install_loader_check.isChecked()
        self.install_pack_btn.setEnabled(False)
        self.skip_pack_btn.setEnabled(False)
        self._start_worker(ModInstallWorker(plan, self.minecraft_dir(), self.java_path(), install_loader))

    def download_java(self) -> None:
        if self._busy:
            return
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        runtime = self.java_runtime_id()
        label = self.java_runtime.currentText()
        self.persist()
        self._start_worker(JavaWorker(runtime, self.minecraft_dir()))
        self._set_status(f"Скачиваю {label}…")

    def _on_java_done(self, path: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        if path:
            self.java_edit.setText(path)
            self._set_status(f"Java готова: {path}")
        else:
            self._set_status("Java скачана, но java.exe не нашёлся. Нажми «Авто».")
        self.persist()

    def _on_mods_done(self, payload: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._plan = None
        version, _sep, note = (payload or "").partition("\n")
        instance_name = ""
        if "__instance__=" in note:
            note, _mark, instance_name = note.rpartition("__instance__=")
            instance_name = instance_slug(instance_name.strip())
            self._config["active_instance"] = instance_name
        self.refresh_versions()
        if version:
            index = self.version_combo.findText(version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        if note.strip():
            self.plan_label.setText(note.strip())
            self._set_status(note.strip())
        else:
            self.plan_label.setText("Моды лежат в папке mods. Шейдеры, если были, в shaderpacks.")
            self._set_status("Сборка установлена.")
        self.persist()

    def _on_repair_done(self, note: str) -> None:
        self._repair_note = (note or "").strip()
        self._set_busy(False)
        self._launch_prepared(getattr(self, "_pending_server", None))

    def _on_repair_failed(self, _message: str) -> None:
        self._repair_note = ""
        self._set_busy(False)
        self._launch_prepared(getattr(self, "_pending_server", None))

    def _validate_nickname(self, nickname: str) -> str:
        if NICK_RE.fullmatch(nickname):
            return ""
        return "Ник: 3–16 символов, латиница, цифры и _."

    def _on_ram_slider(self, value: int) -> None:
        self.ram_value.setText(f"{int(value)} ГБ")
        if getattr(self, "_ram_hold", False):
            return
        self._config["ram_auto"] = False

    def prefer_gpu(self) -> None:
        java = self.java_path() or find_best_java(self.minecraft_dir())
        self._set_status(prefer_discrete_gpu(java))

    def check_game_files(self) -> None:
        if self._busy:
            return
        version = self.version_combo.currentText().strip()
        if not version:
            self._set_status("Сначала выбери установленную версию.")
            return
        self._start_worker(FileCheckWorker(self.minecraft_dir(), version))
        self._set_status("Сверяю файлы игры…")

    def _on_files_checked(self, note: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._set_status(note)

    def play(self, server: str | None = None) -> None:
        if self._busy:
            return
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        if self._proc is not None and self._proc.poll() is None:
            QMessageBox.information(self, APP_NAME, "Minecraft уже запущен.")
            return
        nickname = self.nickname()
        nick_error = self._validate_nickname(nickname)
        if nick_error:
            self._set_status(nick_error)
            self.nick_edit.setFocus()
            return
        version = self.version_combo.currentText().strip()
        if not version:
            self._set_status("Нет установленной версии. Сначала скачай её.")
            return
        directory = self.minecraft_dir()
        version_json = os.path.join(directory, "versions", version, version + ".json")
        if not os.path.isfile(version_json):
            self._set_status("Файлы версии не найдены.")
            return
        java_path = self.java_path()
        if self.java_edit.text().strip() and not os.path.isfile(java_path):
            self._set_status("Файл Java не найден.")
            return
        self.persist()
        loader = infer_loader(version)
        game = installed_game_version(directory, version) or minecraft_release_from_id(version)
        mods_dir = os.path.join(directory, "mods")
        has_jars = os.path.isdir(mods_dir) and any(name.lower().endswith(".jar") for name in os.listdir(mods_dir))
        if has_jars and loader and game:
            self._pending_server = server
            self._repair_note = ""
            self._start_worker(ModRepairWorker(directory, loader, game))
            self._set_status("Проверяю библиотеки модов…")
            return
        self._launch_prepared(server)

    def _launch_prepared(self, server: str | None = None) -> None:
        if minecraft_launcher_lib is None:
            self._missing_library()
            return
        if self._proc is not None and self._proc.poll() is None:
            QMessageBox.information(self, APP_NAME, "Minecraft уже запущен.")
            return
        nickname = self.nickname()
        version = self.version_combo.currentText().strip()
        directory = self.minecraft_dir()
        java_path = self.java_path()
        player_uuid = offline_player_uuid(nickname)
        token = "0"
        options: dict = {
            "username": nickname,
            "uuid": player_uuid,
            "token": token,
            "launcherName": APP_NAME,
            "launcherVersion": APP_VERSION,
        }
        if server:
            options["server"] = server
            options["port"] = "25565"
        if java_path:
            options["executablePath"] = java_path
        else:
            detected = find_best_java(directory)
            if detected:
                options["defaultExecutablePath"] = detected
        instance_name = str(self._config.get("active_instance") or "")
        game_dir = directory
        if instance_name:
            try:
                folder = instance_dir(directory, instance_name)
                meta_path = os.path.join(folder, "instance.json")
                meta = {}
                if os.path.isfile(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as handle:
                        loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        meta = loaded
                wanted = str(meta.get("version_id") or "")
                game = str(meta.get("game_version") or "")
                same = version == wanted or version == game or (game and version.endswith("-" + game))
                if os.path.isdir(folder) and same:
                    options["gameDirectory"] = folder
                    game_dir = folder
                elif os.path.isdir(folder):
                    self._set_status("Эта версия не из профиля сборки. Запускаю обычную папку игры.")
            except (OSError, ValueError, json.JSONDecodeError):
                self._set_status("Профиль сборки не прочитался. Запускаю обычную папку.")
        game_version = installed_game_version(directory, version) or minecraft_release_from_id(version)
        self._launch_dir = game_dir
        self._launch_game = game_version
        pack_note = ""
        try:
            disabled_packs = disable_incompatible_packs(game_dir, game_version)
        except Exception:
            disabled_packs = []
        if disabled_packs:
            names = ", ".join(item.split(" ", 1)[0] for item in disabled_packs[:4])
            pack_note = f"Отключил ресурспаки не для этой версии: {names}."
        if self._config.get("ram_auto") is not False:
            want = suggested_ram_gb(count_mods(game_dir))
            if want != int(self.ram_slider.value()):
                self._ram_hold = True
                self.ram_slider.setValue(want)
                self._ram_hold = False
        java_candidate = java_path or find_best_java(directory)
        try:
            _component, needed_major = java_requirement(directory, version)
        except Exception:
            needed_major = 0
        if java_candidate and needed_major:
            running_major = java_major_version(java_candidate)
            if running_major and running_major < needed_major:
                self._set_status(
                    f"Для этой игры нужна Java {needed_major}, сейчас {running_major}. "
                    "Во вкладке «Установка» скачай её и нажми «Играть»."
                )
                return
        try:
            command = minecraft_launcher_lib.command.get_minecraft_command(version, directory, options)
        except VersionNotFound:
            self._set_status("Версия не найдена.")
            return
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        command = scrub_launch_command(command, nickname, player_uuid, token)
        command = apply_ram(command, int(self.ram_slider.value()))
        command = prefer_javaw(command)
        if command and not os.path.isfile(command[0]):
            replacement = java_path or find_best_java(directory)
            if not replacement:
                self._set_status("Java не найдена. Нажми «Авто».")
                return
            command[0] = replacement
        command = prepare_mac_game_command(
            command,
            thread_mode=str(self._config.get("mac_thread") or "auto"),
        )
        command = prepare_native_command(command)
        unlock_downloaded_java(command[0] if command else "", directory, version)
        try:
            self._log_file = open(self._log_path, "a", encoding="utf-8", errors="replace")
            self._log_file.write(
                f"\n--- {datetime.now().isoformat(timespec='seconds')} version={version} "
                f"user={nickname} ram={self.ram_slider.value()}G server={server or '-'}\n"
            )
            self._log_file.flush()
            popen_kwargs: dict = {
                "cwd": directory,
                "stdout": self._log_file,
                "stderr": subprocess.STDOUT,
                "stdin": subprocess.DEVNULL,
                "env": game_process_env(str(self._config.get("linux_compat") or "auto")),
            }
            if os.name == "nt":
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 0
                popen_kwargs["startupinfo"] = startup
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                self._proc = subprocess.Popen(command, **popen_kwargs)
            elif sys.platform == "darwin":
                bundle = write_mac_game_bundle(command, directory, self._log_path)
                self._log_file.write(f"mac-app={bundle}\n")
                self._log_file.flush()
                self._proc = subprocess.Popen(
                    ["open", "-n", "-W", bundle],
                    cwd=directory,
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                popen_kwargs["start_new_session"] = True
                self._proc = subprocess.Popen(command, **popen_kwargs)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        where = f" на {server}" if server else ""
        note = " ".join(part for part in (getattr(self, "_repair_note", "") or "", pack_note) if part)
        launched = f"Minecraft {version} запущен{where}."
        self._set_status((note + " " + launched).strip() if note else launched)
        self._crash_checks = 0
        QTimer.singleShot(1500, self._check_process)

    def _check_process(self) -> None:
        if self._proc is None:
            return
        code = self._proc.poll()
        if code is None:
            self._crash_checks = getattr(self, "_crash_checks", 0) + 1
            if self._crash_checks < 12:
                QTimer.singleShot(1500, self._check_process)
            return
        if mac_minecraft_alive():
            self._proc = None
            return
        try:
            if self._log_file and not self._log_file.closed:
                self._log_file.write(f"\n[ember] process exit {code}\n")
                self._log_file.flush()
        except OSError:
            pass
        game_dir = getattr(self, "_launch_dir", None) or self.minecraft_dir()
        kind = ""
        try:
            kind = crash_fix_kind(game_dir, self._log_path)
        except Exception:
            kind = ""
        extra = ""
        if kind == "pack":
            try:
                names = disable_incompatible_packs(game_dir, getattr(self, "_launch_game", "") or "")
            except Exception:
                names = []
            extra = (
                " Отключил ресурспаки: " + ", ".join(item.split(" ", 1)[0] for item in names[:4]) + "."
                if names else
                " Ресурспаки уже проверил."
            )
        elif kind == "shader":
            try:
                extra = " " + disable_shader_pack(game_dir)
            except Exception:
                extra = ""
        elif kind == "java":
            try:
                _component, major = java_requirement(self.minecraft_dir(), self.version_combo.currentText().strip())
            except Exception:
                major = 0
            if major:
                extra = f" Нужна Java {major}. Скачай её во вкладке «Установка»."
        elif kind == "ram":
            want = suggested_ram_gb(max(count_mods(game_dir), 40))
            self._ram_hold = True
            self.ram_slider.setValue(max(int(self.ram_slider.value()), want))
            self._ram_hold = False
            self._config["ram_auto"] = True
            extra = f" Поднял память до {self.ram_slider.value()} ГБ. Нажми «Играть» ещё раз."
        message, _disabled = startup_failure(game_dir, self._log_path)
        text = (message + extra).strip()
        self._set_status(text[:240])
        QMessageBox.warning(self, APP_NAME, text)

    def _missing_library(self) -> None:
        QMessageBox.critical(
            self, APP_NAME,
            "Не установлен minecraft-launcher-lib.\npip install -r requirements.txt\n\n" + str(_MLL_IMPORT_ERROR or ""),
        )
