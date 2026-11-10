

class StageBanner(QWidget):
    """Центральная сцена: закат и блочные фигурки, без чужих скинов."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMaximumHeight(260)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addStretch(1)
        card = QFrame()
        card.setObjectName("hubCard")
        card.setFixedWidth(230)
        column = QVBoxLayout(card)
        column.setContentsMargins(14, 12, 14, 12)
        kicker = QLabel("EMBER")
        kicker.setObjectName("kicker")
        self.caption = QLabel("Выбери версию")
        self.caption.setObjectName("hubTitle")
        self.caption.setWordWrap(True)
        self.detail = QLabel("Потом жми «Играть». Сборки справа.")
        self.detail.setObjectName("hubBody")
        self.detail.setWordWrap(True)
        column.addWidget(kicker)
        column.addWidget(self.caption)
        column.addWidget(self.detail)
        column.addStretch(1)
        layout.addWidget(card)

    def set_caption(self, version: str, loader: str) -> None:
        self.caption.setText(version or "Нет версии")
        self.detail.setText(f"{loader or 'Vanilla'}. Сборки — на правой панели.")

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect().adjusted(1, 1, -2, -2))
        clip = QPainterPath()
        clip.addRoundedRect(rect, 18, 18)
        painter.setClipPath(clip)
        sky = QLinearGradient(rect.topLeft(), rect.bottomRight())
        sky.setColorAt(0.0, QColor(16, 36, 58))
        sky.setColorAt(0.45, QColor(48, 28, 22))
        sky.setColorAt(1.0, QColor(255, 112, 32))
        painter.fillPath(clip, sky)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 196, 110, 230))
        painter.drawEllipse(QPointF(rect.right() - 86, rect.top() + 48), 34, 34)
        painter.setBrush(QColor(255, 140, 50, 50))
        painter.drawEllipse(QPointF(rect.right() - 86, rect.top() + 48), 58, 58)
        ground_top = rect.bottom() - 58
        painter.setBrush(QColor(46, 92, 42))
        painter.drawRect(QRectF(rect.left(), ground_top, rect.width(), 58))
        painter.setBrush(QColor(62, 122, 48))
        painter.drawRect(QRectF(rect.left(), ground_top, rect.width(), 10))
        self._block_player(painter, rect.left() + 78, ground_top, QColor("#3f8fd2"), QColor("#c48a56"), QColor("#24356f"))
        self._block_player(painter, rect.left() + 168, ground_top, QColor("#e07a32"), QColor("#e8c07a"), QColor("#5a4632"))
        self._creeper(painter, rect.left() + 250, ground_top)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 186, 110, 90), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 18, 18)
        painter.end()

    def _block_player(self, painter: QPainter, x: float, ground: float, shirt: QColor, skin: QColor, pants: QColor) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pants)
        painter.drawRect(QRectF(x + 6, ground - 28, 10, 28))
        painter.drawRect(QRectF(x + 20, ground - 28, 10, 28))
        painter.setBrush(shirt)
        painter.drawRect(QRectF(x + 4, ground - 58, 28, 30))
        painter.setBrush(skin)
        painter.drawRect(QRectF(x - 4, ground - 50, 8, 22))
        painter.drawRect(QRectF(x + 32, ground - 50, 8, 22))
        painter.drawRect(QRectF(x + 6, ground - 78, 24, 22))
        painter.setBrush(QColor(20, 16, 14))
        painter.drawRect(QRectF(x + 9, ground - 72, 18, 6))

    def _creeper(self, painter: QPainter, x: float, ground: float) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#3f9a45"))
        painter.drawRect(QRectF(x + 6, ground - 22, 8, 22))
        painter.drawRect(QRectF(x + 22, ground - 22, 8, 22))
        painter.drawRect(QRectF(x, ground - 62, 36, 42))
        painter.setBrush(QColor("#163218"))
        painter.drawRect(QRectF(x + 8, ground - 52, 6, 8))
        painter.drawRect(QRectF(x + 22, ground - 52, 6, 8))
        painter.drawRect(QRectF(x + 14, ground - 40, 8, 10))


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

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        side = QFrame()
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
        self._nav = (self.nav_home, self.nav_versions, self.nav_setup)
        self.nav_home.clicked.connect(lambda: self._show_page(0))
        self.nav_versions.clicked.connect(lambda: self._show_page(1))
        self.nav_setup.clicked.connect(lambda: self._show_page(2))
        for button in self._nav:
            side_layout.addWidget(button)
        side_layout.addStretch(1)
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

        center = QFrame()
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
        pick_row = QHBoxLayout()
        play_col = QVBoxLayout()
        play_col.addWidget(self._section("ЧТО ЗАПУСКАТЬ"))
        self.version_combo = QComboBox()
        self.version_combo.setMaxVisibleItems(14)
        self.version_combo.currentTextChanged.connect(self._sync_chips)
        play_col.addWidget(self.version_combo)
        loader_col = QVBoxLayout()
        loader_col.addWidget(self._section("ЗАГРУЗЧИК"))
        self.loader_combo = QComboBox()
        for loader_id, label in LOADERS:
            self.loader_combo.addItem(label, loader_id)
        saved = self.loader_combo.findData(self._config["loader"])
        if saved >= 0:
            self.loader_combo.setCurrentIndex(saved)
        self.loader_combo.currentTextChanged.connect(self._sync_chips)
        loader_col.addWidget(self.loader_combo)
        pick_row.addLayout(play_col, 1)
        pick_row.addLayout(loader_col, 1)
        home_layout.addLayout(pick_row)
        recent = EmberButton("Последние версии")
        recent.clicked.connect(lambda: self._show_page(1))
        home_layout.addWidget(recent)
        home_layout.addStretch(1)

        versions = QWidget()
        versions_layout = QVBoxLayout(versions)
        versions_layout.setContentsMargins(0, 4, 0, 0)
        versions_layout.setSpacing(8)
        versions_layout.addWidget(self._section("НОВАЯ ВЕРСИЯ"))
        new_line = QHBoxLayout()
        self.target_edit = QLineEdit(self._config["target_version"])
        self.target_edit.setPlaceholderText("26.3 или 1.21.1")
        self.catalog_btn = EmberButton("Каталог")
        self.catalog_btn.setMinimumWidth(100)
        self.catalog_btn.clicked.connect(self.pick_version)
        new_line.addWidget(self.target_edit, 1)
        new_line.addWidget(self.catalog_btn)
        versions_layout.addLayout(new_line)
        version_actions = QHBoxLayout()
        self.download_btn = EmberButton("Скачать", primary=True)
        self.download_btn.clicked.connect(self.download_version)
        self.refresh_btn = EmberButton("Обновить список")
        self.refresh_btn.clicked.connect(self.refresh_versions)
        version_actions.addWidget(self.download_btn, 1)
        version_actions.addWidget(self.refresh_btn)
        versions_layout.addLayout(version_actions)
        versions_hint = QLabel("Скачанная версия появится в списке на экране «Игра». Сборку для неё собирай справа.")
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
        self.ram_slider.valueChanged.connect(lambda value: self.ram_value.setText(f"{int(value)} ГБ"))
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
        setup_layout.addStretch(1)

        self.pages.addWidget(home)
        self.pages.addWidget(versions)
        self.pages.addWidget(setup)
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

        footer = QFrame()
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

        right = QFrame()
        right.setObjectName("sidePanel")
        right.setFixedWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 12)
        right_layout.setSpacing(8)
        packs_title = QLabel("СБОРКИ")
        packs_title.setObjectName("kicker")
        packs_hint = QLabel("Готовые наборы. Жми карточку — моды найдутся сами.")
        packs_hint.setObjectName("muted")
        packs_hint.setWordWrap(True)
        right_layout.addWidget(packs_title)
        right_layout.addWidget(packs_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("scrollBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 4, 0)
        body_layout.setSpacing(8)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        short_names = {
            "visual": "Визуал",
            "zombie": "Зомби",
            "survival": "Выживание",
            "weapons": "Оружие",
            "machines": "Механизмы",
            "magic": "Магия",
        }
        for index, pack in enumerate(PRESETS):
            button = EmberButton(short_names.get(pack["id"], pack["title"]))
            button.setToolTip(pack["summary"])
            button.clicked.connect(lambda preset_id=pack["id"]: self._quick_pack(preset_id))
            self._pack_btns.append(button)
            grid.addWidget(button, index // 2, index % 2)
        body_layout.addWidget(grid_host)
        body_layout.addWidget(self._section("СВОЯ СБОРКА"))
        ask_row = QHBoxLayout()
        self.ask_edit = QLineEdit()
        self.ask_edit.setPlaceholderText("зомби выживание на 26.3")
        self.ask_edit.returnPressed.connect(self.ask_pack)
        self.ask_btn = EmberButton("Собрать")
        self.ask_btn.clicked.connect(self.ask_pack)
        ask_row.addWidget(self.ask_edit, 1)
        ask_row.addWidget(self.ask_btn)
        body_layout.addLayout(ask_row)
        self.plan_label = QLabel("Зелёная галка значит, что мод уже стоит. Источники: Modrinth и CurseForge.")
        self.plan_label.setObjectName("muted")
        self.plan_label.setWordWrap(True)
        body_layout.addWidget(self.plan_label)
        self.mod_list = QListWidget()
        self.mod_list.setMinimumHeight(150)
        self.mod_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.mod_list.setItemDelegate(ModListDelegate(self.mod_list))
        body_layout.addWidget(self.mod_list)
        self.install_loader_check = QCheckBox("Если загрузчика нет — поставить его на эту же версию")
        self.install_loader_check.setChecked(True)
        body_layout.addWidget(self.install_loader_check)
        choice = QHBoxLayout()
        self.skip_pack_btn = EmberButton("Не ставить")
        self.skip_pack_btn.clicked.connect(self.skip_pack)
        self.skip_pack_btn.setEnabled(False)
        self.install_pack_btn = EmberButton("В mods", primary=True)
        self.install_pack_btn.clicked.connect(self.install_pack)
        self.install_pack_btn.setEnabled(False)
        self.packs_btn = EmberButton("Все сборки")
        self.packs_btn.clicked.connect(self.open_pack_menu)
        choice.addWidget(self.skip_pack_btn)
        choice.addWidget(self.packs_btn)
        choice.addWidget(self.install_pack_btn, 1)
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

    def showEvent(self, event) -> None:
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

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self._nav):
            button.setSelected(button_index == index)

    def _sync_chips(self, *_args: object) -> None:
        nick = self.nickname() or "Player"
        self.hello.setText(f"ДОБРО ПОЖАЛОВАТЬ, {nick}!")
        self.footer_nick.setText(nick)
        version = self.version_combo.currentText().strip() or "нет версии"
        self.footer_version.setText(version)
        self.stage.set_caption(version, self.loader_combo.currentText())

    def _quick_pack(self, preset_id: str) -> None:
        if self._busy:
            return
        pack = next((item for item in PRESETS if item["id"] == preset_id), None)
        if pack is None:
            return
        loader = self.loader_id()
        if loader in ("vanilla", "optifine"):
            loader = "fabric"
            index = self.loader_combo.findData("fabric")
            if index >= 0:
                self.loader_combo.setCurrentIndex(index)
        selected = self.version_combo.currentText().strip()
        version = resolve_pack_version(pack["title"], self.target_edit.text(), selected, self.minecraft_dir())
        self.target_edit.setText(version)
        self.ask_edit.setText(pack["title"])
        self.plan_label.setText(f"Собираю «{pack['title']}» для {version}…")
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
            self.full_btn, self.update_btn, *self._nav, *self._pack_btns,
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
            self._set_status("Впиши версию, например 26.3 или 1.20.1, или открой каталог.")
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
        elif isinstance(worker, JavaWorker):
            worker.status.connect(self._set_status)
            worker.maximum.connect(self._on_install_max)
            worker.progress.connect(self._on_install_progress)
            worker.succeeded.connect(self._on_java_done)
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
            self.plan_label.setText("Напиши, что хочешь: анимации, шейдеры, данжи, оптимизация. Версию можно прямо в тексте.")
            return
        loader = loader_from_text(query, self.loader_id())
        loader_index = self.loader_combo.findData(loader)
        if loader_index >= 0:
            self.loader_combo.setCurrentIndex(loader_index)
        if minecraft_release_from_id(query):
            self.target_edit.setText(minecraft_release_from_id(query))
        selected = self.version_combo.currentText().strip()
        game_version = resolve_pack_version(query, self.target_edit.text(), selected, self.minecraft_dir())
        self.target_edit.setText(game_version)
        self.plan_label.setText(f"Смотрю Modrinth и CurseForge для {game_version}…")
        self.mod_list.clear()
        self._plan = None
        self._start_worker(PackWorker(query, loader, game_version))

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

    def _fill_mod_list(self, mods: list) -> None:
        self.mod_list.clear()
        present = installed_mod_names(self.minecraft_dir())
        for mod in mods:
            where = "shaderpacks" if mod.get("folder") == "shaderpacks" else "mods"
            already = mod_already_installed(mod, present)
            mod["installed"] = already
            source = mod.get("source") or ""
            if already:
                item = QListWidgetItem(f"     {mod['title']}  ·  уже установлен")
                item.setForeground(QColor("#9dffc8"))
                item.setBackground(QColor(16, 42, 30))
            else:
                item = QListWidgetItem(f"{mod['title']}  ·  {where}  ·  {source}")
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
                "Галка ниже поставит его на эту же версию, не на 1.21.1."
            )
        else:
            note = f" Моды встанут в {plan['game_version']} без переустановки игры."
        self._plan = plan
        self._fill_mod_list(plan.get("mods") or [])
        installed_count = sum(1 for mod in plan.get("mods") or [] if mod.get("installed"))
        if installed_count:
            note += f" Зелёным отмечено уже установленное: {installed_count}. Их заново не качаю."
        self.plan_label.setText(f"{plan['title']} · {plan['loader']} · {plan['game_version']}\n{plan['summary']}{note}")
        self.install_loader_check.setChecked(bool(plan["install_loader"]))
        self.install_pack_btn.setEnabled(True)
        self.skip_pack_btn.setEnabled(True)
        self._set_status(f"Сборка для {plan['game_version']}. Сними лишние галки и нажми «В mods».")

    def skip_pack(self) -> None:
        self._plan = None
        self.mod_list.clear()
        self.install_pack_btn.setEnabled(False)
        self.skip_pack_btn.setEnabled(False)
        self.plan_label.setText("Ок, ничего не ставил.")
        self._set_status("Сборку пропустил.")

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

    def _on_mods_done(self, version: str) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._plan = None
        self.refresh_versions()
        if version:
            index = self.version_combo.findText(version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        self.plan_label.setText("Моды лежат в папке mods. Шейдеры, если были, в shaderpacks.")
        self._set_status("Сборка установлена.")
        self.persist()

    def _validate_nickname(self, nickname: str) -> str:
        if NICK_RE.fullmatch(nickname):
            return ""
        return "Ник: 3–16 символов, латиница, цифры и _."

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
        try:
            self._log_file = open(self._log_path, "a", encoding="utf-8", errors="replace")
            self._log_file.write(
                f"\n--- {datetime.now().isoformat(timespec='seconds')} version={version} "
                f"user={nickname} ram={self.ram_slider.value()}G server={server or '-'}\n"
            )
            self._log_file.flush()
            popen_kwargs: dict = {"cwd": directory, "stdout": self._log_file, "stderr": subprocess.STDOUT}
            if os.name == "nt":
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 0
                popen_kwargs["startupinfo"] = startup
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            self._proc = subprocess.Popen(command, **popen_kwargs)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        where = f" на {server}" if server else ""
        self._set_status(f"Minecraft {version} запущен{where}.")
        QTimer.singleShot(1500, self._check_process)

    def _check_process(self) -> None:
        if self._proc is None or self._proc.poll() is None:
            return
        self._set_status(f"Игра сразу закрылась (код {self._proc.returncode}). Лог: {self._log_path}")
        QMessageBox.warning(self, APP_NAME, "Minecraft закрылся сразу после старта.\n" + self._log_path)

    def _missing_library(self) -> None:
        QMessageBox.critical(
            self, APP_NAME,
            "Не установлен minecraft-launcher-lib.\npip install -r requirements.txt\n\n" + str(_MLL_IMPORT_ERROR or ""),
        )
