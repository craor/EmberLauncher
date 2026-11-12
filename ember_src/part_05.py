

def _install_excepthook() -> None:
    shown = {"done": False}

    def hook(exc_type, exc_value, exc_tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        where = "".join(traceback.format_tb(exc_tb))
        if any(mark in where for mark in ("paintEvent", "paint_tiled", "paint_material")):
            sys.stderr.write(text)
            return
        if shown["done"]:
            sys.stderr.write(text)
            return
        shown["done"] = True
        try:
            QMessageBox.critical(None, APP_NAME, text[-1600:])
        except Exception:
            sys.stderr.write(text)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def running_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_installed_copy() -> bool:
    if not running_frozen():
        return True
    marker = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), INSTALL_MARKER)
    try:
        with open(marker, "r", encoding="utf-8") as handle:
            return handle.read().strip() == "ok"
    except OSError:
        return False


def default_install_dir() -> str:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local, "Programs", "Ember")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Applications")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "Ember")


def desktop_dir() -> str:
    home = os.path.expanduser("~")
    if os.name == "nt":
        home = os.environ.get("USERPROFILE") or home
        candidates = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(os.environ.get("OneDrive", ""), "Desktop"),
        ]
        for path in candidates:
            if path and os.path.isdir(path):
                return path
    else:
        config = os.path.join(home, ".config", "user-dirs.dirs")
        try:
            with open(config, "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("XDG_DESKTOP_DIR"):
                        raw = line.split("=", 1)[1].strip().strip('"')
                        raw = raw.replace("$HOME", home)
                        if os.path.isdir(raw):
                            return raw
        except OSError:
            pass
    desktop = os.path.join(home, "Desktop")
    return desktop if os.path.isdir(desktop) else home


def checked_install_dir(path: str) -> str:
    raw = (path or "").strip().strip('"')
    if not raw:
        raise ValueError("Укажи папку установки.")
    folder = os.path.abspath(raw)
    tail = os.path.splitdrive(folder)[1]
    if tail in ("\\", "/"):
        raise ValueError("Нельзя ставить в корень диска.")
    if os.name == "nt":
        windows = os.path.normcase(os.environ.get("WINDIR") or r"C:\Windows")
        if os.path.normcase(folder).startswith(windows):
            raise ValueError("В папку Windows ставить нельзя.")
    else:
        for prefix in ("/usr", "/bin", "/sbin", "/System", "/etc", "/Library"):
            if folder == prefix or folder.startswith(prefix + os.sep):
                raise ValueError("Системная папка не подходит.")
    if len(folder) > 180:
        raise ValueError("Слишком длинный путь.")
    return folder


def create_shortcut(target: str, shortcut_path: str, workdir: str) -> None:
    if os.name != "nt":
        return
    payload = json.dumps({"target": target, "lnk": shortcut_path, "workdir": workdir}, ensure_ascii=False)
    spec = os.path.join(os.environ.get("TEMP") or ".", "ember-shortcut.json")
    with open(spec, "w", encoding="utf-8") as handle:
        handle.write(payload)
    script = (
        "$raw = Get-Content -Raw -Encoding UTF8 $env:EMBER_SHORTCUT; "
        "$o = ConvertFrom-Json $raw; "
        "$ws = New-Object -ComObject WScript.Shell; "
        "$s = $ws.CreateShortcut($o.lnk); "
        "$s.TargetPath = $o.target; "
        "$s.WorkingDirectory = $o.workdir; "
        "$s.IconLocation = $o.target; "
        "$s.Description = 'Ember'; "
        "$s.Save()"
    )
    env = os.environ.copy()
    env["EMBER_SHORTCUT"] = spec
    flags = subprocess.CREATE_NO_WINDOW
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
        env=env,
        creationflags=flags,
        check=False,
    )


def install_launcher(folder: str) -> str:
    """Copy the frozen build into folder. Returns the path that should be launched."""
    os.makedirs(folder, exist_ok=True)
    if sys.platform == "darwin":
        bundle = mac_app_bundle(sys.executable)
        target = os.path.join(folder, "EmberLauncher.app")
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(bundle, target)
        marker = os.path.join(target, "Contents", "MacOS", INSTALL_MARKER)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("ok\n")
        return target
    name = "EmberLauncher.exe" if os.name == "nt" else "EmberLauncher"
    source = os.path.abspath(sys.executable)
    target = os.path.join(folder, name)
    if os.path.normcase(source) != os.path.normcase(target):
        shutil.copy2(source, target)
    if os.name != "nt":
        os.chmod(target, 0o755)
    with open(os.path.join(folder, INSTALL_MARKER), "w", encoding="utf-8") as handle:
        handle.write("ok\n")
    return target


def publish_shortcut(target: str, folder: str) -> None:
    desktop = desktop_dir()
    os.makedirs(desktop, exist_ok=True)
    if os.name == "nt":
        create_shortcut(target, os.path.join(desktop, "Ember.lnk"), folder)
        return
    if sys.platform == "darwin":
        link = os.path.join(desktop, "Ember")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(target, link)
        return
    desktop_file = os.path.join(desktop, "Ember.desktop")
    menu_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    os.makedirs(menu_dir, exist_ok=True)
    body = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Ember\n"
        f"Exec=\"{target}\"\n"
        f"Path={folder}\n"
        "Terminal=false\n"
        "Categories=Game;\n"
    )
    for path in (desktop_file, os.path.join(menu_dir, "Ember.desktop")):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        os.chmod(path, 0o755)


class InstallerWindow(GradientWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Установка Ember")
        self.setFixedSize(560, 280)
        self.setWindowIcon(load_app_icon())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        title = QLabel("Куда установить Ember")
        title.setObjectName("title")
        hint = QLabel("Выбери папку. После установки на рабочем столе появится ярлык.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        self.path_edit = QLineEdit(default_install_dir())
        row = QHBoxLayout()
        browse = EmberButton("Обзор")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        self.status = QLabel("Ярлык будет называться Ember.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        self.install_btn = EmberButton("Установить", primary=True)
        self.install_btn.clicked.connect(self._install)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(row)
        layout.addWidget(self.status)
        layout.addStretch(1)
        layout.addWidget(self.install_btn)
        reveal_materials(self)

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Папка установки", self.path_edit.text())
        if chosen:
            self.path_edit.setText(chosen)

    def _install(self) -> None:
        try:
            folder = checked_install_dir(self.path_edit.text())
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.status.setText("Копирую файлы…")
        QApplication.processEvents()
        try:
            target = install_launcher(folder)
            publish_shortcut(target, folder)
        except OSError as exc:
            self.status.setText(f"Не удалось установить: {exc}")
            return
        self.status.setText("Готово. Ярлык Ember на рабочем столе.")
        QApplication.processEvents()
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
            subprocess.Popen([target], cwd=folder, creationflags=flags)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen([target], cwd=folder, start_new_session=True)
        QTimer.singleShot(400, QApplication.instance().quit)


def load_ui_fonts() -> None:
    folder = _bundle_root() / "ember_src" / "fonts"
    if not folder.is_dir():
        return
    for path in sorted(folder.glob("*.b64")):
        try:
            raw = base64.b64decode("".join(path.read_text(encoding="ascii").split()))
        except (OSError, ValueError):
            continue
        QFontDatabase.addApplicationFontFromData(QByteArray(raw))


def main() -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ember.launcher.desktop")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if sys.platform == "darwin":
        from PyQt6.QtCore import QEvent, QObject

        class _MacBar(QObject):
            def eventFilter(self, obj, event) -> bool:
                if event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
                    if not obj.inherits("QFileDialog"):
                        style_mac_titlebar(obj)
                return False

        app._mac_bar = _MacBar(app)
        app.installEventFilter(app._mac_bar)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(load_app_icon())
    load_ui_fonts()
    patch_minecraft_downloads()
    app.setStyleSheet(STYLESHEET + "\n" + texture_stylesheet())
    app.setFont(QFont("Alegreya Sans", 11))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#C5D7E8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1B2430"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#E7EEF5"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1B2430"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1B2430"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#5B4BFF"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    _install_excepthook()
    if minecraft_launcher_lib is None:
        QMessageBox.critical(None, APP_NAME, "Нет пакета minecraft-launcher-lib.\npip install -r requirements.txt")
        sys.exit(1)
    if running_frozen() and not is_installed_copy():
        window = InstallerWindow()
    else:
        window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
