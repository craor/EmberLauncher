

import time


def paint_glass_sheen(painter: QPainter, rect, radius: float, strength: float = 0.7) -> None:
    """Скользящий блик и светлая кромка, как у жидкого стекла."""
    if rect.width() <= 4 or rect.height() <= 4:
        return
    phase = (time.monotonic() % 4.8) / 4.8
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(rect), radius, radius)
    painter.setClipPath(clip)
    span = float(rect.width() + rect.height())
    start_x = rect.left() - rect.width() * 0.55 + span * phase
    shine = QLinearGradient(start_x, rect.top(), start_x + rect.width() * 0.42, rect.bottom())
    alpha = int(78 * max(0.2, min(1.0, strength)))
    shine.setColorAt(0.0, QColor(255, 255, 255, 0))
    shine.setColorAt(0.46, QColor(255, 255, 255, alpha))
    shine.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shine)
    painter.drawRect(rect)
    lip = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + max(10.0, rect.height() * 0.42))
    lip.setColorAt(0.0, QColor(255, 255, 255, int(120 * strength)))
    lip.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(lip)
    painter.drawRect(rect)
    painter.restore()


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
        self._glow = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42 if nav else (46 if primary else 34))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        weight = QFont.Weight.Bold if primary or nav else QFont.Weight.DemiBold
        family = "Alegreya Sans"
        self.setFont(QFont(family, 11 if primary else 10, weight))
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

    def setPulse(self, enabled: bool = True) -> None:
        previous = getattr(self, "_glow_anim", None)
        if previous is not None:
            previous.stop()
        if not enabled:
            self._glow = 0.0
            self.update()
            return
        glow = QVariantAnimation(self)
        glow.setDuration(1500)
        glow.setStartValue(0.0)
        glow.setEndValue(1.0)
        glow.setLoopCount(-1)
        glow.setEasingCurve(QEasingCurve.Type.InOutSine)
        glow.valueChanged.connect(self._set_glow)
        self._glow_anim = glow
        glow.start()

    def _set_glow(self, value: object) -> None:
        self._glow = float(value)
        self.update()

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._nav:
            self._paint_nav(painter)
            painter.end()
            return
        rect = self.rect().adjusted(2, 2, -3, -3)
        if rect.width() <= 8 or rect.height() <= 8:
            painter.end()
            return
        if self._pressed and self.isEnabled():
            rect = rect.adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        if self._primary:
            face = lerp_color(QColor("#5B4BFF"), QColor("#7A6CFF"), self._hover)
            ink = QColor("#FFFFFF") if self.isEnabled() else QColor("#D9D6F5")
        else:
            face = lerp_color(QColor(255, 255, 255, 214), QColor(255, 255, 255, 245), self._hover)
            ink = QColor("#1B2430") if self.isEnabled() else QColor("#9AA3AE")
        if not self.isEnabled() and not self._primary:
            face = QColor(255, 255, 255, 140)
        painter.setPen(Qt.PenStyle.NoPen)
        glow = float(getattr(self, "_glow", 0.0) or 0.0)
        if self._primary and glow:
            wave = 1.0 - abs((glow * 2.0) - 1.0)
            painter.setBrush(QColor(91, 75, 255, int(28 + 64 * wave)))
            painter.drawRoundedRect(rect.adjusted(-3, -2, 4, 6), radius + 4, radius + 4)
        painter.setBrush(QColor(27, 36, 48, 28))
        painter.drawRoundedRect(rect.adjusted(0, 3, 0, 1), radius, radius)
        painter.setBrush(face)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
        painter.drawRoundedRect(rect, radius, radius)
        paint_glass_sheen(painter, rect, radius, 0.42 if self._primary else 0.7)
        painter.setPen(ink)
        painter.setFont(self.font())
        shown = QFontMetrics(self.font()).elidedText(
            self._text, Qt.TextElideMode.ElideRight, max(8, rect.width() - 20)
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, shown)
        painter.end()

    def _paint_nav(self, painter: QPainter) -> None:
        rect = self.rect().adjusted(2, 4, -2, -4)
        radius = rect.height() / 2
        if self._selected:
            face = QColor(255, 255, 255, 236)
            ink = QColor("#1B2430")
        elif self._hover > 0:
            face = QColor(255, 255, 255, int(150 + 70 * self._hover))
            ink = QColor("#1B2430")
        else:
            face = QColor(255, 255, 255, 90)
            ink = QColor("#3C4654")
        if not self.isEnabled():
            face = QColor(255, 255, 255, 60)
            ink = QColor("#9AA3AE")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(face)
        painter.drawRoundedRect(rect, radius, radius)
        paint_glass_sheen(painter, rect, radius, 0.55 if self._selected else 0.28)
        dot = QColor("#5B4BFF") if self._selected else QColor("#C5CDD6")
        painter.setBrush(dot)
        painter.drawEllipse(rect.left() + 12, rect.center().y() - 4, 8, 8)
        painter.setPen(ink)
        painter.setFont(self.font())
        painter.drawText(
            QRectF(rect.left() + 28, rect.top(), rect.width() - 36, rect.height()),
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
            patch_minecraft_downloads()
            os.makedirs(self.directory, exist_ok=True)
            if self.loader_id == "vanilla":
                minecraft_launcher_lib.install.install_minecraft_version(self.version, self.directory, callback=callback)
                self.succeeded.emit(self.version)
                return
            if self.loader_id == "optifine":
                minecraft_launcher_lib.install.install_minecraft_version(self.version, self.directory, callback=callback)
                java = java_for_loader(self.directory, self.version, self.java_path)
                if not java:
                    raise RuntimeError(
                        "Java не найдена. Открой «Установка», нажми «Скачать Java» и скачай OptiFine ещё раз."
                    )
                launch_optifine_installer(self.version, self.directory, java, set_status)
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
            self.failed.emit(explain_install_error(exc))


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
            self.failed.emit(network_error(exc))
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
        assist: bool = False,
        settings: dict | None = None,
    ) -> None:
        super().__init__()
        self.query = query
        self.loader = loader
        self.game_version = game_version
        self.preset_id = preset_id
        self.sources = sources
        self.assist = assist
        self.settings = dict(settings or {})

    def run(self) -> None:
        try:
            if self.assist:
                plan = assist_build(self.query, self.loader, self.game_version, self.settings)
            else:
                plan = build_pack(
                    self.query,
                    self.loader,
                    self.game_version,
                    preset_id=self.preset_id,
                    sources=self.sources,
                )
        except Exception as exc:
            self.failed.emit(network_error(exc))
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
            self.failed.emit(network_error(exc))
        else:
            self.ready.emit(notes)
        try:
            self.downloads.emit(github_download_total(self.repo))
        except Exception:
            self.downloads.emit(-1)


class ServerStatusWorker(QThread):
    ready = pyqtSignal(object)

    def __init__(self, address: str) -> None:
        super().__init__()
        self.address = address

    def run(self) -> None:
        self.ready.emit(query_server_status(self.address))


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
            self.failed.emit(network_error(exc))
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
        dest = os.path.join(tempfile.gettempdir(), "ember-update-" + release_filename())
        try:
            http_download(self.url, dest, timeout=300)
            verify_update_file(dest, self.digest)
        except Exception as exc:
            try:
                os.remove(dest)
            except OSError:
                pass
            self.failed.emit(network_error(exc))
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
            root = self.directory
            instance_name = str(self.plan.get("instance_name") or "") if self.plan.get("isolated") else ""
            if instance_name:
                root = prepare_instance(self.directory, instance_name)
                backup_instance(root)
                self.status.emit("Сделал бэкап профиля, основная папка mods не трогается.")
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
            shader_file = ""
            for index, mod in enumerate(self.plan["mods"], start=1):
                if mod.get("installed"):
                    self.status.emit(f"Уже стоит: {mod['title']}")
                    continue
                folder_name = "shaderpacks" if mod.get("folder") == "shaderpacks" else "mods"
                folder = os.path.join(root, folder_name)
                os.makedirs(folder, exist_ok=True)
                filename = safe_filename(str(mod.get("filename") or ""))
                if not filename:
                    raise RuntimeError(f"У «{mod.get('title') or 'мода'}» плохое имя файла.")
                dest = os.path.join(folder, filename)
                self.status.emit(f"Качаю {index}/{len(self.plan['mods'])}: {mod['title']}")
                if not os.path.isfile(dest):
                    http_download(mod["url"], dest)
                verify_mod_file(dest, mod)
                if folder_name == "shaderpacks":
                    shader_file = filename
            if instance_name and shader_file:
                write_shader_choice(root, shader_file)
                self.status.emit("Прописал шейдерпак в настройках Iris и Oculus.")
            note = ""
            try:
                note = finish_mod_folder(
                    root,
                    str(self.plan.get("loader") or ""),
                    str(self.plan.get("game_version") or ""),
                    status=lambda text: self.status.emit(text),
                )
            except Exception:
                note = ""
            if instance_name:
                write_instance_meta(root, self.plan, installed_version)
                note = (note + " " if note else "") + "Сборка лежит в отдельном профиле. Основная игра не изменена."
                self.succeeded.emit(installed_version + ("\n" + note if note else "") + "\n__instance__=" + os.path.basename(root))
                return
            self.succeeded.emit(installed_version + ("\n" + note if note else ""))
        except Exception as exc:
            self.failed.emit(network_error(exc))


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
            self.failed.emit(network_error(exc))
            return
        self.succeeded.emit(note or "")


class FileCheckWorker(QThread):
    status = pyqtSignal(str)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, directory: str, version_id: str) -> None:
        super().__init__()
        self.directory = directory
        self.version_id = version_id

    def run(self) -> None:
        try:
            self.status.emit("Сверяю клиент и библиотеки…")
            bad = mismatched_game_files(self.directory, self.version_id)
        except Exception as exc:
            self.failed.emit(network_error(exc))
            return
        if not bad:
            self.succeeded.emit("Файлы клиента и библиотек совпадают с контрольными суммами.")
            return
        shown = ", ".join(bad[:6])
        tail = "" if len(bad) <= 6 else f" и ещё {len(bad) - 6}"
        self.succeeded.emit(f"Не сходятся {len(bad)} файлов: {shown}{tail}. Скачай эту версию ещё раз.")


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
            self.failed.emit(network_error(exc))


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

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        paint_material(painter, self.rect(), "stone-bricks", 28)
        painter.end()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        reveal_materials(self)

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


_TEXTURES: dict[str, QPixmap] = {}


def texture_bytes(name: str) -> bytes:
    path = _bundle_root() / "ember_src" / "textures" / f"{name}.b64"
    try:
        return base64.b64decode("".join(path.read_text(encoding="ascii").split()))
    except (OSError, ValueError):
        return b""


def texture_pixmap(name: str) -> QPixmap:
    cached = _TEXTURES.get(name)
    if cached is not None:
        return cached
    pix = QPixmap()
    raw = texture_bytes(name)
    if raw:
        pix.loadFromData(raw, "PNG")
    _TEXTURES[name] = pix
    return pix


def materialize_texture(name: str) -> str:
    raw = texture_bytes(name)
    if not raw:
        return ""
    folder = pathlib.Path(tempfile.gettempdir()) / "ember-ui"
    try:
        folder.mkdir(exist_ok=True)
        dest = folder / f"{name}.png"
        if not dest.is_file() or dest.stat().st_size < 1000:
            dest.write_bytes(raw)
        return dest.resolve().as_posix()
    except OSError:
        return ""


def texture_stylesheet() -> str:
    return ""


def paint_tiled(painter: QPainter, rect, name: str) -> bool:
    """Кладёт текстуру клетками. Координаты целые: QRectF этот Qt на Windows не принимает."""
    pix = texture_pixmap(name)
    try:
        if pix.isNull() or pix.width() < 2 or rect.width() < 2 or rect.height() < 2:
            return False
        left = int(rect.left())
        top = int(rect.top())
        right = int(rect.right())
        bottom = int(rect.bottom())
    except Exception:
        return False
    painter.save()
    try:
        painter.setClipRect(rect)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        ratio = float(pix.devicePixelRatio() or 1)
        width = max(1, int(round(pix.width() / ratio)))
        height = max(1, int(round(pix.height() / ratio)))
        y = top
        while y <= bottom:
            x = left
            while x <= right:
                painter.drawPixmap(x, y, pix)
                x += width
            y += height
    except Exception:
        painter.restore()
        return False
    painter.restore()
    return True


def paint_material(painter: QPainter, rect, texture: str, wash: int = 0) -> None:
    """Жидкое стекло: полупрозрачная карточка и бегущий блик. Имя оставлено для старых вызовов."""
    del texture
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    body = rect.adjusted(2, 2, -4, -6)
    if body.width() <= 8 or body.height() <= 8:
        painter.restore()
        return
    radius = 26
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 42))
    painter.drawRoundedRect(body.adjusted(0, 10, 2, 6), radius, radius)
    fill = QLinearGradient(body.left(), body.top(), body.right(), body.bottom())
    fill.setColorAt(0.0, QColor(255, 255, 255, 208))
    fill.setColorAt(0.42, QColor(255, 255, 255, 154))
    fill.setColorAt(1.0, QColor(236, 244, 250, 176))
    painter.setPen(QPen(QColor(255, 255, 255, 230), 1.3))
    painter.setBrush(fill)
    painter.drawRoundedRect(body, radius, radius)
    if wash:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(150, 186, 230, min(42, int(wash))))
        painter.drawRoundedRect(body, radius, radius)
    paint_glass_sheen(painter, body, radius, 0.9)
    painter.restore()


def reveal_materials(root: QWidget) -> None:
    """Дочерние виджеты не должны закрашивать кожу и пергамент плоским цветом."""
    keep = (
        QLineEdit,
        QComboBox,
        QListWidget,
        QProgressBar,
        QScrollBar,
        QCheckBox,
        EmberButton,
        MaterialFrame,
        ServerCard,
        StageBanner,
    )
    for widget in [root, *root.findChildren(QWidget)]:
        if isinstance(widget, keep) or str(widget.objectName() or "") == "chip":
            continue
        parent = widget.parentWidget()
        if isinstance(parent, QAbstractScrollArea) and not isinstance(parent, QScrollArea):
            continue
        widget.setAutoFillBackground(False)
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        viewport = getattr(widget, "viewport", None)
        if not callable(viewport):
            continue
        view = viewport()
        if isinstance(view, QWidget) and isinstance(widget, QScrollArea):
            view.setAutoFillBackground(False)
            view.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)


def float_in(widget: QWidget, delay_ms: int = 0) -> None:
    """Карточка проявляется, затем эффект снимается, чтобы текст не мылился."""
    from PyQt6.QtWidgets import QGraphicsOpacityEffect

    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(520)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _clear() -> None:
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)

    anim.finished.connect(_clear)
    widget._ember_float = anim
    QTimer.singleShot(max(0, int(delay_ms)), anim.start)


class MaterialFrame(QFrame):
    """Панель с настоящей текстурой, а не с плоской заливкой из стилей."""

    def __init__(self, texture: str, wash: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._texture = texture
        self._wash = wash
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._glass_clock = QTimer(self)
        self._glass_clock.timeout.connect(self.update)
        self._glass_clock.start(70)

    def showEvent(self, event) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        super().showEvent(event)

    def paintEvent(self, event) -> None:
        del event
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        painter = QPainter(self)
        paint_material(painter, self.rect(), self._texture, self._wash)
        painter.end()


def style_mac_titlebar(widget) -> None:
    """Верхняя полоса macOS в цвет неба, не системная белая и не тёмное дерево."""
    if sys.platform != "darwin":
        return
    try:
        import ctypes
        from ctypes import c_byte, c_char_p, c_double, c_long, c_ulong, c_void_p

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = c_void_p
        objc.objc_getClass.argtypes = [c_char_p]
        objc.sel_registerName.restype = c_void_p
        objc.sel_registerName.argtypes = [c_char_p]

        def msg(restype, *argtypes):
            prototype = ctypes.CFUNCTYPE(restype, c_void_p, c_void_p, *argtypes)
            return prototype(("objc_msgSend", objc))

        def sel(name: str) -> int:
            return objc.sel_registerName(name.encode("ascii"))

        nsview = int(widget.winId())
        window = msg(c_void_p)(nsview, sel("window"))
        if not window:
            return
        own = isinstance(widget, GradientWindow) or str(widget.objectName() or "") == "downloadDialog"
        if own:
            mask = msg(c_ulong)(window, sel("styleMask"))
            msg(None, c_ulong)(window, sel("setStyleMask:"), mask | (1 << 15))
            if not widget.property("_ember_mac_inset"):
                layout = widget.layout()
                if layout is not None:
                    margins = layout.contentsMargins()
                    layout.setContentsMargins(margins.left(), max(margins.top(), 34), margins.right(), margins.bottom())
                widget.setProperty("_ember_mac_inset", True)
        msg(None, c_byte)(window, sel("setTitlebarAppearsTransparent:"), 1)
        msg(None, c_long)(window, sel("setTitleVisibility:"), 1)
        color = msg(c_void_p, c_double, c_double, c_double, c_double)(
            objc.objc_getClass(b"NSColor"),
            sel("colorWithCalibratedRed:green:blue:alpha:"),
            198 / 255,
            214 / 255,
            230 / 255,
            1.0,
        )
        if color:
            msg(None, c_void_p)(window, sel("setBackgroundColor:"), color)
        appearance_name = msg(c_void_p, c_char_p)(
            objc.objc_getClass(b"NSString"),
            sel("stringWithUTF8String:"),
            b"NSAppearanceNameAqua",
        )
        appearance = msg(c_void_p, c_void_p)(
            objc.objc_getClass(b"NSAppearance"),
            sel("appearanceNamed:"),
            appearance_name,
        )
        if appearance:
            msg(None, c_void_p)(window, sel("setAppearance:"), appearance)
    except Exception:
        return


class GradientWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._t = 0.0
        rng = random.Random(3)
        self._embers = [
            {
                "x": rng.random(),
                "y": rng.random(),
                "s": rng.uniform(14, 46),
                "v": rng.uniform(0.35, 0.9),
                "a": rng.randint(22, 58),
                "drift": rng.uniform(0.0, 6.28),
            }
            for _ in range(16)
        ]
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._advance)
        self._clock.start(50)
        self._mouse = (0.5, 0.5)
        self.setMouseTracking(True)

    def _advance(self) -> None:
        self._t += 0.02
        for ember in self._embers:
            ember["x"] = (ember["x"] + math.cos(self._t * ember["v"] + ember["drift"]) * 0.0011) % 1.0
            ember["y"] = (ember["y"] + math.sin(self._t * ember["v"] + ember["drift"]) * 0.0014) % 1.0
        local = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(local) and self.width() and self.height():
            self._mouse = (local.x() / self.width(), local.y() / self.height())
        self.update()
        for button in self.findChildren(EmberButton):
            button.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        enable_windows_dark_title(int(self.winId()))
        style_mac_titlebar(self)
        QTimer.singleShot(0, lambda: style_mac_titlebar(self))
        QTimer.singleShot(180, lambda: style_mac_titlebar(self))

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(1, self.width())
        height = max(1, self.height())
        mx, my = getattr(self, "_mouse", (0.5, 0.5))
        shift_x = (mx - 0.5) * 22
        shift_y = (my - 0.5) * 12
        sky = QLinearGradient(0, 0, 0, height)
        sky.setColorAt(0.0, QColor("#8EB7DE"))
        sky.setColorAt(0.42, QColor("#D5E4F2"))
        sky.setColorAt(0.72, QColor("#C3B7AE"))
        sky.setColorAt(1.0, QColor("#8E857E"))
        painter.fillRect(self.rect(), sky)
        orb_x = width * (0.18 + 0.62 * (0.5 + 0.5 * math.sin(self._t * 0.35)))
        orb_y = height * (0.16 + 0.06 * math.cos(self._t * 0.27))
        orb = QRadialGradient(orb_x, orb_y, max(80.0, width * 0.28))
        orb.setColorAt(0.0, QColor(255, 255, 255, 170))
        orb.setColorAt(0.28, QColor(198, 186, 255, 90))
        orb.setColorAt(1.0, QColor(198, 186, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(orb)
        painter.drawEllipse(QRectF(orb_x - width * 0.28, orb_y - width * 0.18, width * 0.56, width * 0.36))
        ridge = QPainterPath()
        ridge.moveTo(0, height * 0.58 + shift_y)
        ridge.quadTo(width * 0.18 + shift_x, height * 0.40 + shift_y, width * 0.36, height * 0.56 + shift_y * 0.4)
        ridge.quadTo(width * 0.55 - shift_x * 0.3, height * 0.72, width * 0.72, height * 0.48 + shift_y * 0.5)
        ridge.quadTo(width * 0.86 + shift_x * 0.4, height * 0.34, width, height * 0.52)
        ridge.lineTo(width, height)
        ridge.lineTo(0, height)
        ridge.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(92, 99, 108, 90))
        painter.drawPath(ridge)
        far = QPainterPath()
        far.moveTo(0, height * 0.70 + shift_y * 0.35)
        far.quadTo(width * 0.3 - shift_x * 0.5, height * 0.58, width * 0.62, height * 0.74 + shift_y * 0.2)
        far.quadTo(width * 0.82 + shift_x * 0.2, height * 0.82, width, height * 0.66)
        far.lineTo(width, height)
        far.lineTo(0, height)
        far.closeSubpath()
        painter.setBrush(QColor(70, 76, 84, 70))
        painter.drawPath(far)
        for ember in self._embers:
            x = ember["x"] * width - shift_x * 0.6
            y = ember["y"] * height - shift_y * 0.4
            size = ember["s"]
            painter.setBrush(QColor(255, 255, 255, ember["a"]))
            painter.drawEllipse(QRectF(x, y, size, size * 0.72))
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
        paint_material(painter, self.rect(), "parchment", 16)
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

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        paint_material(painter, self.rect(), "stone-bricks", 28)
        painter.end()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        reveal_materials(self)

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
