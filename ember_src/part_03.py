

class EmberButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, text: str, primary: bool = False, parent: QWidget | None = None, *, nav: bool = False) -> None:
        super().__init__(parent)
        self._text = text
        self._primary = primary
        self._nav = nav
        self._shrink = False
        self._selected = False
        self._hover = 0.0
        self._pressed = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42 if nav else (46 if primary else 34))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        weight = QFont.Weight.Bold if primary or nav else QFont.Weight.DemiBold
        self.setFont(QFont("Segoe UI", 12 if primary else 10, weight))
        if nav:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setShrinkable(self, shrink: bool = True) -> None:
        self._shrink = bool(shrink)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setSelected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.update()

    def setText(self, text: str) -> None:
        self._text = text
        self.update()

    def sizeHint(self) -> QSize:
        if self._nav:
            return QSize(180, 42)
        width = QFontMetrics(self.font()).horizontalAdvance(self._text) + 28
        return QSize(max(width, 84), 46 if self._primary else 34)

    def minimumSizeHint(self) -> QSize:
        if self._shrink:
            return QSize(48, 46 if self._primary else 34)
        return self.sizeHint()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        if not enabled:
            self._animate_to(0.0)
        self.update()

    def _on_anim(self, value: object) -> None:
        self._hover = float(value)
        self.update()

    def _animate_to(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event) -> None:
        if self.isEnabled():
            self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._pressed = False
        self._animate_to(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if (
            self.isEnabled()
            and was_pressed
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._nav:
            self._paint_nav(painter)
            painter.end()
            return
        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.width() <= 4 or rect.height() <= 4:
            painter.end()
            return
        radius = 14 if self._primary else 10
        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), radius, radius)
        if self._primary:
            left = lerp_color(QColor("#e26412"), QColor("#ff9a3d"), self._hover)
            right = lerp_color(QColor("#ffb15e"), QColor("#ffe1b0"), self._hover)
            if self._pressed and self.isEnabled():
                left, right = left.darker(112), right.darker(112)
            if not self.isEnabled():
                left, right = QColor("#3a332c"), QColor("#51483e")
            gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.topRight()))
            gradient.setColorAt(0.0, left)
            gradient.setColorAt(1.0, right)
            painter.fillPath(path, gradient)
            text_color = QColor("#1a1008") if self.isEnabled() else QColor("#b1a69a")
        else:
            fill = lerp_color(QColor(255, 255, 255, 16), QColor(255, 255, 255, 42), self._hover)
            border = lerp_color(QColor(255, 255, 255, 36), QColor(255, 176, 90, 210), self._hover)
            text_color = QColor("#f4f1ea") if self.isEnabled() else QColor(255, 255, 255, 90)
            if not self.isEnabled():
                fill = QColor(255, 255, 255, 10)
                border = QColor(255, 255, 255, 18)
            painter.fillPath(path, fill)
            painter.setPen(QPen(border, 1.3))
            painter.drawPath(path)
        painter.setPen(text_color)
        painter.setFont(self.font())
        shown = QFontMetrics(self.font()).elidedText(
            self._text, Qt.TextElideMode.ElideRight, max(8, rect.width() - 16)
        )
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, shown)
        painter.end()

    def _paint_nav(self, painter: QPainter) -> None:
        rect = QRectF(self.rect().adjusted(2, 2, -2, -2))
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        if self._selected:
            fill = QColor(255, 138, 42, 78 + int(40 * self._hover))
            border = QColor(255, 186, 110, 210)
        elif self._hover > 0:
            fill = QColor(255, 255, 255, int(28 * self._hover))
            border = QColor(255, 176, 90, int(140 * self._hover))
        else:
            fill = QColor(0, 0, 0, 0)
            border = QColor(0, 0, 0, 0)
        painter.fillPath(path, fill)
        if border.alpha() > 0:
            painter.setPen(QPen(border, 1.2))
            painter.drawPath(path)
        icon = QRectF(rect.left() + 12, rect.center().y() - 7, 14, 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ff8a2a") if self._selected else QColor(255, 214, 170, 160))
        painter.drawRoundedRect(icon, 4, 4)
        painter.setPen(QColor("#fff6ec") if self._selected else QColor("#e6d8c8"))
        painter.setFont(self.font())
        painter.drawText(
            QRectF(icon.right() + 10, rect.top(), rect.width() - 40, rect.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )


class InstallWorker(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    maximum = pyqtSignal(int)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, loader_id: str, version: str, directory: str, java_path: str) -> None:
        super().__init__()
        self.loader_id = loader_id
        self.version = version
        self.directory = directory
        self.java_path = java_path

    def run(self) -> None:
        def set_status(text: str) -> None:
            self.status.emit(translate_status(str(text)))

        def set_progress(value: int) -> None:
            try:
                self.progress.emit(int(value))
            except (TypeError, ValueError):
                return

        def set_max(value: int) -> None:
            try:
                self.maximum.emit(max(0, int(value)))
            except (TypeError, ValueError):
                self.maximum.emit(0)

        callback = {"setStatus": set_status, "setProgress": set_progress, "setMax": set_max}
        try:
            os.makedirs(self.directory, exist_ok=True)
            if self.loader_id == "vanilla":
                minecraft_launcher_lib.install.install_minecraft_version(self.version, self.directory, callback=callback)
                self.succeeded.emit(self.version)
                return
            if self.loader_id == "optifine":
                launch_optifine_installer(self.version, self.directory, self.java_path, set_status)
                self.succeeded.emit("")
                return
            if not hasattr(minecraft_launcher_lib, "mod_loader"):
                raise RuntimeError("Нужен minecraft-launcher-lib 8 или новее.")
            loader = minecraft_launcher_lib.mod_loader.get_mod_loader(self.loader_id)
            installed = loader.install(
                self.version,
                self.directory,
                callback=callback,
                java=self.java_path or "java",
            )
            self.succeeded.emit(str(installed))
        except Exception as exc:
            self.failed.emit(str(exc))


class VersionListWorker(QThread):
    ready = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, directory: str) -> None:
        super().__init__()
        self.directory = directory

    def run(self) -> None:
        try:
            os.makedirs(self.directory, exist_ok=True)
            versions = minecraft_launcher_lib.utils.get_available_versions(self.directory)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.ready.emit(list(versions))


class PackWorker(QThread):
    ready = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        query: str,
        loader: str,
        game_version: str,
        preset_id: str = "",
        sources: tuple[str, ...] = ("modrinth", "curseforge"),
    ) -> None:
        super().__init__()
        self.query = query
        self.loader = loader
        self.game_version = game_version
        self.preset_id = preset_id
        self.sources = sources

    def run(self) -> None:
        try:
            plan = build_pack(
                self.query,
                self.loader,
                self.game_version,
                preset_id=self.preset_id,
                sources=self.sources,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.ready.emit(plan)


class NewsWorker(QThread):
    ready = pyqtSignal(list)
    failed = pyqtSignal(str)
    downloads = pyqtSignal(int)

    def __init__(self, repo: str) -> None:
        super().__init__()
        self.repo = repo

    def run(self) -> None:
        try:
            notes = github_release_notes(self.repo)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.ready.emit(notes)
        try:
            self.downloads.emit(github_download_total(self.repo))
        except Exception:
            self.downloads.emit(-1)


class UpdateCheckWorker(QThread):
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, repo: str, current: str) -> None:
        super().__init__()
        self.repo = repo
        self.current = current

    def run(self) -> None:
        try:
            info = github_update(self.repo, self.current)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.ready.emit(info or {})


class UpdateDownloadWorker(QThread):
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, digest: str) -> None:
        super().__init__()
        self.url = url
        self.digest = digest

    def run(self) -> None:
        dest = os.path.join(tempfile.gettempdir(), "EmberLauncher-update.exe")
        try:
            http_download(self.url, dest, timeout=300)
            verify_update_file(dest, self.digest)
        except Exception as exc:
            try:
                os.remove(dest)
            except OSError:
                pass
            self.failed.emit(str(exc))
            return
        self.ready.emit(dest)


class ModInstallWorker(QThread):
    status = pyqtSignal(str)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, plan: dict, directory: str, java_path: str, install_loader: bool) -> None:
        super().__init__()
        self.plan = plan
        self.directory = directory
        self.java_path = java_path
        self.install_loader = install_loader

    def run(self) -> None:
        installed_version = ""
        try:
            if self.install_loader:
                self.status.emit(f"Ставлю {self.plan['loader']} {self.plan['game_version']}")
                if not hasattr(minecraft_launcher_lib, "mod_loader"):
                    raise RuntimeError("Нужен minecraft-launcher-lib 8 или новее.")
                loader = minecraft_launcher_lib.mod_loader.get_mod_loader(self.plan["loader"])

                def set_status(text: str) -> None:
                    self.status.emit(translate_status(str(text)))

                installed_version = str(loader.install(
                    self.plan["game_version"],
                    self.directory,
                    callback={"setStatus": set_status, "setProgress": lambda _v: None, "setMax": lambda _v: None},
                    java=self.java_path or "java",
                ))
            for index, mod in enumerate(self.plan["mods"], start=1):
                if mod.get("installed"):
                    self.status.emit(f"Уже стоит: {mod['title']}")
                    continue
                folder = os.path.join(self.directory, mod["folder"])
                os.makedirs(folder, exist_ok=True)
                dest = os.path.join(folder, mod["filename"])
                self.status.emit(f"Качаю {index}/{len(self.plan['mods'])}: {mod['title']}")
                if not os.path.isfile(dest):
                    http_download(mod["url"], dest)
            note = ""
            try:
                note = finish_mod_folder(
                    self.directory,
                    str(self.plan.get("loader") or ""),
                    str(self.plan.get("game_version") or ""),
                    status=lambda text: self.status.emit(text),
                )
            except Exception:
                note = ""
            self.succeeded.emit(installed_version + ("\n" + note if note else ""))
        except Exception as exc:
            self.failed.emit(str(exc))


class ModRepairWorker(QThread):
    status = pyqtSignal(str)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, directory: str, loader: str, game_version: str) -> None:
        super().__init__()
        self.directory = directory
        self.loader = loader
        self.game_version = game_version

    def run(self) -> None:
        try:
            note = finish_mod_folder(
                self.directory,
                self.loader,
                self.game_version,
                status=lambda text: self.status.emit(text),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(note or "")


class JavaWorker(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    maximum = pyqtSignal(int)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, runtime: str, directory: str) -> None:
        super().__init__()
        self.runtime = runtime
        self.directory = directory

    def run(self) -> None:
        def set_status(text: str) -> None:
            self.status.emit(translate_status(str(text)))

        def set_progress(value: int) -> None:
            try:
                self.progress.emit(int(value))
            except (TypeError, ValueError):
                return

        def set_max(value: int) -> None:
            try:
                self.maximum.emit(max(0, int(value)))
            except (TypeError, ValueError):
                self.maximum.emit(0)

        try:
            os.makedirs(self.directory, exist_ok=True)
            minecraft_launcher_lib.runtime.install_jvm_runtime(
                self.runtime,
                self.directory,
                callback={"setStatus": set_status, "setProgress": set_progress, "setMax": set_max},
            )
            path = minecraft_launcher_lib.runtime.get_executable_path(self.runtime, self.directory) or ""
            self.succeeded.emit(path)
        except Exception as exc:
            self.failed.emit(str(exc))


class DownloadDialog(QDialog):
    def __init__(self, minecraft_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadDialog")
        self.setWindowTitle("Версия Minecraft")
        self.setModal(True)
        self.resize(460, 520)
        self._versions: list[dict] = []
        self._chosen = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск, например 1.21")
        self.search.textChanged.connect(self._refill)
        layout.addWidget(self.search)
        self.snapshots = QCheckBox("Снапшоты")
        self.snapshots.toggled.connect(self._refill)
        layout.addWidget(self.snapshots)
        self.version_list = QListWidget()
        self.version_list.itemDoubleClicked.connect(lambda _item: self._accept_current())
        layout.addWidget(self.version_list, 1)
        self.manual = QLineEdit()
        self.manual.setPlaceholderText("Или id вручную, например 1.20.1")
        layout.addWidget(self.manual)
        self.fetch_status = QLabel("Получаю список…")
        self.fetch_status.setObjectName("muted")
        self.fetch_status.setWordWrap(True)
        layout.addWidget(self.fetch_status)
        row = QHBoxLayout()
        cancel = EmberButton("Отмена")
        cancel.clicked.connect(self.reject)
        pick = EmberButton("Выбрать", primary=True)
        pick.clicked.connect(self._accept_current)
        row.addWidget(cancel)
        row.addWidget(pick, 1)
        layout.addLayout(row)
        self._worker = VersionListWorker(minecraft_dir)
        self._worker.ready.connect(self._on_versions)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def chosen_version(self) -> str:
        return self._chosen

    def _on_versions(self, versions: list) -> None:
        self._versions = [item for item in versions if isinstance(item, dict) and item.get("id")]
        self.fetch_status.setText(f"Версий: {len(self._versions)}")
        self._refill()

    def _on_failed(self, message: str) -> None:
        self.fetch_status.setText("Список не загрузился. Впиши id вручную.\n" + message)

    def _refill(self) -> None:
        query = self.search.text().strip().lower()
        show_snapshots = self.snapshots.isChecked()
        self.version_list.clear()
        for entry in self._versions:
            version_type = str(entry.get("type", ""))
            version_id = str(entry.get("id", ""))
            if version_type == "snapshot" and not show_snapshots:
                continue
            if version_type not in ("release", "snapshot"):
                continue
            if query and query not in version_id.lower():
                continue
            item = QListWidgetItem(f"{version_id}   {version_type}")
            item.setData(Qt.ItemDataRole.UserRole, version_id)
            self.version_list.addItem(item)

    def _accept_current(self) -> None:
        manual = self.manual.text().strip()
        if manual:
            self._chosen = manual
            self.accept()
            return
        current = self.version_list.currentItem()
        if current is None:
            self.fetch_status.setText("Выбери версию или впиши id.")
            return
        self._chosen = str(current.data(Qt.ItemDataRole.UserRole) or "")
        if self._chosen:
            self.accept()

    def closeEvent(self, event) -> None:
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.setParent(None)
            _ORPHAN_THREADS.append(worker)
        super().closeEvent(event)


class GradientWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._t = 0.0
        rng = random.Random(3)
        self._embers = [
            {
                "x": rng.random(),
                "y": rng.random(),
                "s": rng.uniform(1.1, 2.8),
                "v": rng.uniform(0.08, 0.22),
                "a": rng.randint(50, 150),
                "drift": rng.uniform(-0.03, 0.03),
            }
            for _ in range(32)
        ]
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._advance)
        self._clock.start(33)
        self._trail: list[dict] = []
        self.setMouseTracking(True)

    def _advance(self) -> None:
        self._t += 0.033
        for ember in self._embers:
            ember["y"] -= ember["v"] * 0.02
            ember["x"] += ember["drift"] * 0.02
            if ember["y"] < -0.04:
                ember["y"] = 1.04
                ember["x"] = random.random()
            ember["x"] = ember["x"] % 1.0
        local = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(local):
            x = float(local.x())
            y = float(local.y())
            last = self._trail[-1] if self._trail else None
            if last is None or abs(last["x"] - x) > 3 or abs(last["y"] - y) > 3:
                self._trail.append({"x": x, "y": y, "life": 1.0})
        for point in self._trail:
            point["life"] -= 0.035
        if len(self._trail) > 42:
            self._trail = self._trail[-42:]
        self._trail = [point for point in self._trail if point["life"] > 0]
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = float(self.width())
        height = float(self.height())
        shift = 0.5 + 0.5 * math.sin(self._t * 0.45)
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor(10, 16, 14))
        gradient.setColorAt(0.42 + 0.08 * shift, QColor(24, 16, 12))
        gradient.setColorAt(1.0, QColor(34, 13, 8))
        painter.fillRect(self.rect(), gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        glow_x = width * (0.2 + 0.55 * (0.5 + 0.5 * math.sin(self._t * 0.25)))
        glow = QPainterPath()
        glow.addEllipse(QPointF(glow_x, height * 0.18), width * 0.34, height * 0.28)
        painter.fillPath(glow, QColor(255, 120, 40, 26))
        for ember in self._embers:
            painter.setBrush(QColor(255, 156, 70, int(ember["a"])))
            painter.drawEllipse(QPointF(ember["x"] * width, ember["y"] * height), ember["s"], ember["s"])
        for point in self._trail:
            life = float(point["life"])
            radius = 4 + 16 * (1.0 - life)
            painter.setBrush(QColor(255, 90, 24, int(70 * life)))
            painter.drawEllipse(QPointF(point["x"], point["y"]), radius, radius)
            painter.setBrush(QColor(255, 186, 90, int(190 * life)))
            painter.drawEllipse(QPointF(point["x"], point["y"]), 1.6 + 2.4 * life, 1.6 + 2.4 * life)
        painter.end()


class ModListDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        super().paint(painter, option, index)
        if not index.data(INSTALLED_ROLE):
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(option.rect.left() + 8, option.rect.center().y() - 7, 15, 15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(61, 220, 132))
        painter.drawRoundedRect(box, 4, 4)
        painter.setPen(QPen(QColor("#06210f"), 2))
        mark = QPainterPath()
        mark.moveTo(box.left() + 3, box.center().y())
        mark.lineTo(box.left() + 6, box.bottom() - 3.5)
        mark.lineTo(box.right() - 3, box.top() + 4)
        painter.drawPath(mark)
        painter.restore()


class ServerCard(QWidget):
    def __init__(self, info: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._info = info
        self.setMinimumWidth(248)
        self.setMaximumWidth(280)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(6)
        kicker = QLabel("СЕРВЕР")
        kicker.setObjectName("section")
        title = QLabel(info.get("name") or "Сервер")
        title.setObjectName("serverTitle")
        season = QLabel(info.get("season") or "")
        season.setObjectName("serverSeason")
        body = QLabel(info.get("about") or "")
        body.setObjectName("muted")
        body.setWordWrap(True)
        ip = QLabel(info.get("host") or "")
        ip.setObjectName("serverTitle")
        ip.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(kicker)
        layout.addWidget(title)
        if info.get("season"):
            layout.addWidget(season)
        if info.get("about"):
            layout.addWidget(body)
        layout.addSpacing(8)
        layout.addWidget(ip)
        layout.addStretch(1)
        links = QHBoxLayout()
        self.discord_btn = EmberButton("Discord")
        self.telegram_btn = EmberButton("Telegram")
        if not info.get("discord"):
            self.discord_btn.hide()
        if not info.get("telegram"):
            self.telegram_btn.hide()
        links.addWidget(self.discord_btn)
        links.addWidget(self.telegram_btn)
        if info.get("discord") or info.get("telegram"):
            layout.addLayout(links)
        self.copy_btn = EmberButton("Копировать IP")
        self.join_btn = EmberButton("Зайти", primary=True)
        layout.addWidget(self.copy_btn)
        layout.addWidget(self.join_btn)
        if info.get("credit"):
            credit = QLabel(info["credit"])
            credit.setObjectName("credit")
            credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(credit)

    def _tick(self) -> None:
        self._phase += 0.07
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect().adjusted(1, 1, -2, -2))
        path = QPainterPath()
        path.addRoundedRect(rect, 22, 22)
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, QColor(28, 16, 12, 230))
        fill.setColorAt(1.0, QColor(14, 16, 14, 235))
        painter.fillPath(path, fill)
        alpha = 110 + int(90 * (0.5 + 0.5 * math.sin(self._phase)))
        painter.setPen(QPen(QColor(255, 150, 60, alpha), 1.6))
        painter.drawPath(path)
        pulse = QPainterPath()
        pulse.addEllipse(QPointF(rect.center().x(), rect.top() + 28), 70 + 8 * math.sin(self._phase), 26)
        painter.fillPath(pulse, QColor(255, 120, 40, 28))
        painter.end()


class PackMenuDialog(QDialog):
    def __init__(self, version: str, loader: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadDialog")
        self.setWindowTitle("Сборки")
        self.setModal(True)
        self.resize(760, 500)
        self._choice: dict | None = None
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        self.pack_list = QListWidget()
        for pack in PRESETS:
            item = QListWidgetItem(pack["title"])
            item.setData(Qt.ItemDataRole.UserRole, pack["id"])
            item.setToolTip(pack["summary"])
            self.pack_list.addItem(item)
        self.pack_list.currentRowChanged.connect(self._show_pack)
        root.addWidget(self.pack_list, 2)
        side = QVBoxLayout()
        self.desc = QLabel("Выбери сборку слева, версию и нажми «Собрать эту».")
        self.desc.setObjectName("muted")
        self.desc.setWordWrap(True)
        self.version_box = QComboBox()
        self.version_box.setEditable(True)
        self.version_box.addItems(PACK_VERSIONS)
        typed = (version or "").strip()
        if typed:
            if self.version_box.findText(typed) < 0:
                self.version_box.insertItem(0, typed)
            self.version_box.setCurrentText(typed)
        self.loader_box = QComboBox()
        for loader_id, label in LOADERS:
            if loader_id not in ("optifine", "vanilla"):
                self.loader_box.addItem(label, loader_id)
        picked = loader if loader not in ("optifine", "vanilla") else "fabric"
        index = self.loader_box.findData(picked)
        if index >= 0:
            self.loader_box.setCurrentIndex(index)
        self.modrinth_box = QCheckBox("Modrinth")
        self.modrinth_box.setChecked(True)
        self.curse_box = QCheckBox("CurseForge")
        self.curse_box.setChecked(True)
        go = EmberButton("Собрать эту", primary=True)
        go.clicked.connect(self._accept_pack)
        side.addWidget(self.desc, 1)
        side.addWidget(QLabel("ВЕРСИЯ"))
        side.addWidget(self.version_box)
        side.addWidget(QLabel("ЗАГРУЗЧИК"))
        side.addWidget(self.loader_box)
        checks = QHBoxLayout()
        checks.addWidget(self.modrinth_box)
        checks.addWidget(self.curse_box)
        side.addLayout(checks)
        side.addWidget(go)
        root.addLayout(side, 3)
        if self.pack_list.count():
            self.pack_list.setCurrentRow(0)

    def _current_pack(self) -> dict | None:
        item = self.pack_list.currentItem()
        if item is None:
            return None
        preset_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        return next((pack for pack in PRESETS if pack["id"] == preset_id), None)

    def _show_pack(self, _row: int) -> None:
        pack = self._current_pack()
        if not pack:
            return
        self.desc.setText(
            pack["title"] + "\n\n" + pack["summary"]
            + "\n\nСначала ищется файл на Modrinth. Если на этой версии его нет, берётся CurseForge. "
            "Если написать просто 1.21, а файлов нет, возьмётся ближайшая 1.21.x, где моды есть."
        )

    def _accept_pack(self) -> None:
        pack = self._current_pack()
        if not pack:
            self.desc.setText("Выбери сборку.")
            return
        sources: list[str] = []
        if self.modrinth_box.isChecked():
            sources.append("modrinth")
        if self.curse_box.isChecked():
            sources.append("curseforge")
        if not sources:
            self.desc.setText("Отметь хотя бы один источник.")
            return
        version = self.version_box.currentText().strip()
        if not version:
            self.desc.setText("Выбери версию.")
            return
        self._choice = {
            "id": pack["id"],
            "title": pack["title"],
            "version": version,
            "loader": str(self.loader_box.currentData() or "fabric"),
            "sources": tuple(sources),
        }
        self.accept()

    def choice(self) -> dict | None:
        return self._choice
