def release_filename() -> str:
    if os.name == "nt":
        return "EmberLauncher.exe"
    if sys.platform == "darwin":
        return "EmberLauncher-macOS.dmg"
    return "EmberLauncher-linux"


def mac_update_destination(executable: str) -> str:
    """Куда класть новую сборку. Копия из DMG и App Translocation — не настоящая программа."""
    bundle = mac_app_bundle(executable)
    marker = bundle.replace("\\", "/")
    transient = (
        "AppTranslocation" in marker
        or "/Volumes/" in marker
        or marker.startswith("/private/var/folders/")
    )
    if not transient:
        return bundle
    system_apps = "/Applications/EmberLauncher.app"
    home_apps = os.path.join(os.path.expanduser("~"), "Applications", "EmberLauncher.app")
    for candidate in (system_apps, home_apps):
        if os.path.isdir(candidate):
            return candidate
    os.makedirs(os.path.dirname(home_apps), exist_ok=True)
    return home_apps


def update_payload_ok(header: bytes, trailer: bytes, platform: str = "") -> bool:
    kind = platform or sys.platform
    if kind in ("win32", "nt", "windows"):
        return header.startswith(b"MZ")
    if kind == "darwin":
        return trailer.startswith(b"koly")
    return header.startswith(b"\x7fELF")


def verify_update_file(path: str, digest: str) -> None:
    size = os.path.getsize(path)
    if size < MIN_UPDATE_BYTES or size > MAX_DOWNLOAD_BYTES:
        raise RuntimeError("Файл обновления странного размера, он не установлен.")
    with open(path, "rb") as handle:
        header = handle.read(4)
        trailer = b""
        if size >= 512:
            handle.seek(-512, os.SEEK_END)
            trailer = handle.read(4)
        if not update_payload_ok(header, trailer):
            raise RuntimeError("Скачанный файл не похож на сборку для этой системы.")
        if digest.startswith("sha256:"):
            expected = digest.split(":", 1)[1].strip().lower()
            handle.seek(0)
            hasher = hashlib.sha256()
            while True:
                chunk = handle.read(1024 * 256)
                if not chunk:
                    break
                hasher.update(chunk)
            if hasher.hexdigest() != expected:
                raise RuntimeError("Контрольная сумма обновления не сошлась.")


def schedule_self_replace(downloaded: str) -> None:
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Из исходников файл сам себя не подменяет. Поставь собранную версию.")
    new_file = assert_safe_path(downloaded)
    if os.name == "nt":
        current = assert_safe_path(sys.executable)
        script_path = os.path.join(tempfile.gettempdir(), "ember-update.cmd")
        script = (
            "@echo off\r\n"
            "ping 127.0.0.1 -n 3 >nul\r\n"
            ":wait\r\n"
            f'del /f /q "{current}" >nul 2>&1\r\n'
            f'if exist "{current}" (\r\n'
            "  ping 127.0.0.1 -n 2 >nul\r\n"
            "  goto wait\r\n"
            ")\r\n"
            f'move /y "{new_file}" "{current}" >nul\r\n'
            f'start "" "{current}"\r\n'
            'del "%~f0"\r\n'
        )
        with open(script_path, "w", encoding="ascii", newline="") as handle:
            handle.write(script)
        flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        subprocess.Popen(["cmd", "/c", script_path], creationflags=flags, close_fds=True)
        return
    if sys.platform == "darwin":
        bundle = assert_safe_path(mac_update_destination(sys.executable))
        parent = assert_safe_path(os.path.dirname(bundle))
        script_path = os.path.join(tempfile.gettempdir(), "ember-update.sh")
        # Старые версии качали zip и распаковывали ditto. Новые — dmg.
        script = (
            "#!/bin/sh\n"
            "sleep 2\n"
            f'header=$(dd if="{new_file}" bs=4 count=1 2>/dev/null)\n'
            'case "$header" in\n'
            "PK*)\n"
            f'  rm -rf "{bundle}"\n'
            f'  ditto -x -k "{new_file}" "{parent}" || exit 1\n'
            "  ;;\n"
            "*)\n"
            '  mount=$(mktemp -d)\n'
            f'  hdiutil attach -nobrowse -readonly -mountpoint "$mount" "{new_file}" || exit 1\n'
            f'  rm -rf "{bundle}"\n'
            f'  ditto "$mount/EmberLauncher.app" "{bundle}" || {{ hdiutil detach "$mount"; exit 1; }}\n'
            '  hdiutil detach "$mount" || true\n'
            '  rmdir "$mount" 2>/dev/null || true\n'
            "  ;;\n"
            "esac\n"
            f'xattr -dr com.apple.quarantine "{bundle}" 2>/dev/null || true\n'
            f'open "{bundle}"\n'
            'rm -f "$0"\n'
        )
        with open(script_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(script_path, 0o700)
        subprocess.Popen(["/bin/sh", script_path], start_new_session=True)
        return
    current = assert_safe_path(sys.executable)
    script_path = os.path.join(tempfile.gettempdir(), "ember-update.sh")
    script = (
        "#!/bin/sh\n"
        "sleep 2\n"
        f'rm -f "{current}"\n'
        f'mv -f "{new_file}" "{current}"\n'
        f'chmod +x "{current}"\n'
        f'"{current}" >/dev/null 2>&1 &\n'
        "rm -f \"$0\"\n"
    )
    with open(script_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(script)
    os.chmod(script_path, 0o700)
    subprocess.Popen(["/bin/sh", script_path], start_new_session=True)
