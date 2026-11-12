"""Диагностика запуска: Java из манифеста, natives, ресурспаки, краш и режимы совместимости."""

import platform

# Формат ресурспака. Источник: Minecraft Wiki и таблица релизов до 26.3.
# Новее 26.3 здесь нет: такие паки не отключаю, потому что номер я не выдумываю.
_RESOURCE_FORMATS = (
    ((1, 6, 1), 1),
    ((1, 9, 0), 2),
    ((1, 11, 0), 3),
    ((1, 13, 0), 4),
    ((1, 15, 0), 5),
    ((1, 16, 2), 6),
    ((1, 17, 0), 7),
    ((1, 18, 0), 8),
    ((1, 19, 0), 9),
    ((1, 19, 3), 12),
    ((1, 19, 4), 13),
    ((1, 20, 0), 15),
    ((1, 20, 2), 18),
    ((1, 20, 3), 22),
    ((1, 20, 5), 32),
    ((1, 21, 0), 34),
    ((1, 21, 2), 42),
    ((1, 21, 4), 46),
    ((1, 21, 5), 55),
    ((1, 21, 6), 63),
    ((1, 21, 7), 64),
    ((1, 21, 9), 69),
    ((1, 21, 11), 75),
    ((26, 1, 0), 84),
    ((26, 2, 0), 88),
    ((26, 3, 0), 97.1),
)
_JAVA_FALLBACK = (
    ((1, 17, 0), 16, "java-runtime-alpha"),
    ((1, 18, 0), 17, "java-runtime-gamma"),
    ((1, 20, 5), 21, "java-runtime-delta"),
    ((26, 1, 0), 25, "java-runtime-epsilon"),
)


def version_triple(version: str) -> tuple[int, int, int]:
    parts = version_parts(version) or ()
    nums = list(parts) + [0, 0, 0]
    return (int(nums[0]), int(nums[1]), int(nums[2]))


def resource_pack_format(game_version: str) -> float | None:
    """Формат ресурспака этой версии. None, если версия новее известной таблицы."""
    current = version_triple(game_version)
    if current[0] == 0:
        return None
    found: float | None = None
    newest = _RESOURCE_FORMATS[-1][0]
    if current > newest:
        return None
    for border, pack_format in _RESOURCE_FORMATS:
        if current >= border:
            found = float(pack_format)
    return found


def _format_number(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, list) and value:
        return _format_number(value[0])
    return None


def pack_is_incompatible(meta: dict, game_format: float | None) -> str:
    """Пустая строка значит пак можно оставить. Слишком старый без диапазона не трогаю."""
    if not isinstance(meta, dict):
        return "битый pack.mcmeta"
    pack = meta.get("pack")
    if not isinstance(pack, dict):
        return "в pack.mcmeta нет блока pack"
    if game_format is None:
        return ""
    minimum = _format_number(pack.get("min_format"))
    maximum = _format_number(pack.get("max_format"))
    if minimum is not None and maximum is not None:
        if game_format < minimum or game_format > maximum:
            return f"формат игры {game_format:g} вне {minimum:g}–{maximum:g}"
        return ""
    supported = pack.get("supported_formats")
    if isinstance(supported, list) and len(supported) >= 2:
        low = _format_number(supported[0])
        high = _format_number(supported[1])
        if low is not None and high is not None and (game_format < low or game_format > high):
            return f"формат игры {game_format:g} вне диапазона пака"
        return ""
    single = _format_number(pack.get("pack_format"))
    if single is None:
        return "не написан pack_format"
    if single > game_format:
        return f"пак новее игры ({single:g} > {game_format:g})"
    return ""


def _read_pack_meta(path: str) -> dict | None:
    import zipfile

    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("pack.mcmeta")
    except (OSError, zipfile.BadZipFile, KeyError):
        return None
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def disable_incompatible_packs(game_dir: str, game_version: str) -> list[str]:
    """Выключает битые и слишком новые ресурспаки. Файлы остаются с суффиксом .disabled."""
    folder = os.path.join(game_dir, "resourcepacks")
    if not os.path.isdir(folder):
        return []
    game_format = resource_pack_format(game_version)
    disabled: list[str] = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".zip"):
            continue
        path = os.path.join(folder, name)
        meta = _read_pack_meta(path)
        if meta is None:
            reason = "битый архив или нет pack.mcmeta"
        else:
            reason = pack_is_incompatible(meta, game_format)
        if not reason:
            continue
        dest = path + ".disabled"
        try:
            os.replace(path, dest)
        except OSError:
            continue
        disabled.append(f"{name} ({reason})")
    if disabled:
        _drop_disabled_from_options(game_dir, [item.split(" ", 1)[0] for item in disabled])
    return disabled


def _drop_disabled_from_options(game_dir: str, names: list[str]) -> None:
    path = os.path.join(game_dir, "options.txt")
    if not os.path.isfile(path):
        return
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    changed = False
    output: list[str] = []
    for line in lines:
        if not line.startswith("resourcePacks:"):
            output.append(line)
            continue
        updated = line
        for name in names:
            updated = updated.replace("file/" + name, "")
        if updated != line:
            changed = True
        output.append(updated)
    if not changed:
        return
    temporary = path + ".tmp"
    pathlib.Path(temporary).write_text("\n".join(output) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def java_requirement(directory: str, version_id: str) -> tuple[str, int]:
    """Компонент Java из version.json. Таблица ниже только если Mojang поле не записал."""
    seen: set[str] = set()
    current = version_id
    while current and current not in seen:
        seen.add(current)
        raw = version_json_text(directory, current)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        java = data.get("javaVersion")
        if isinstance(java, dict) and java.get("component"):
            try:
                major = int(java.get("majorVersion") or 0)
            except (TypeError, ValueError):
                major = 0
            return str(java.get("component")), major
        current = str(data.get("inheritsFrom") or "")
    game = installed_game_version(directory, version_id) or minecraft_release_from_id(version_id)
    current_version = version_triple(game)
    component = "jre-legacy"
    major = 8
    for border, border_major, name in _JAVA_FALLBACK:
        if current_version >= border:
            major = border_major
            component = name
    return component, major


def runtime_executable(directory: str, component: str) -> str:
    if minecraft_launcher_lib is None or not component:
        return ""
    try:
        path = minecraft_launcher_lib.runtime.get_executable_path(component, directory) or ""
    except Exception:
        return ""
    return path if path and os.path.isfile(path) else ""


def java_for_loader(directory: str, version_id: str, preferred: str = "") -> str:
    """Java, которой можно запустить установщик Fabric, Forge или OptiFine."""
    typed = (preferred or "").strip().strip('"')
    if typed and os.path.isfile(typed):
        return typed
    component, _major = java_requirement(directory, version_id)
    found = runtime_executable(directory, component)
    if found:
        return found
    return find_best_java(directory)


def explain_install_error(exc: BaseException) -> str:
    """Окно ошибки по-русски, без сырого WinError «файл не найден»."""
    if isinstance(exc, FileNotFoundError):
        name = os.path.basename(str(getattr(exc, "filename", "") or "")).lower()
        if name in {"java", "javaw", "java.exe", "javaw.exe"}:
            return (
                "Установщик не нашёл Java. Игра уже могла скачаться, "
                "но Fabric, Forge, NeoForge и OptiFine без Java не ставятся. "
                "Открой «Установка», нажми «Скачать Java» и скачай версию ещё раз."
            )
        missing = getattr(exc, "filename", None) or str(exc)
        return (
            f"Файл не найден: {missing}. "
            "Скачай эту версию ещё раз: лаунчер докачает только то, чего не хватает."
        )
    if isinstance(exc, subprocess.CalledProcessError):
        detail = exc.stderr or exc.stdout or ""
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", "replace")
        detail = str(detail).strip()
        text = (
            "Установщик модов закрылся с ошибкой. "
            "Для 1.21 нужна Java 21: вкладка «Установка», «Скачать Java», затем скачай версию ещё раз."
        )
        if detail:
            return text + "\n" + detail[-500:]
        return text
    if type(exc).__name__ in {"UnsupportedVersion", "VersionNotFound"}:
        return (
            f"Эта сборка загрузчика не подходит к версии {exc}. "
            "Для 1.21 и новее обычно берут Fabric или NeoForge."
        )
    text = str(exc)
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
        return (
            "HTTPS не прошёл: у сборки Python на Mac нет корневых сертификатов. "
            "Скачай новую версию в браузере: https://github.com/craor/EmberLauncher/releases/latest"
        )
    return text


def network_error(exc: BaseException) -> str:
    return explain_install_error(exc)


import time


def ensure_download_dir(path: str) -> None:
    """Папка для файла. Повтор нужен, когда несколько закачек создают её сразу."""
    folder = os.path.dirname(os.fspath(path))
    if not folder:
        return
    last: BaseException | None = None
    for _attempt in range(8):
        try:
            os.makedirs(folder, exist_ok=True)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.02)
    if last is not None:
        raise last


def _stable_download_file(
    url: str,
    path: str,
    callback: dict | None = None,
    sha1: str | None = None,
    lzma_compressed: bool | None = False,
    session: object | None = None,
    minecraft_directory: str | None = None,
    overwrite: bool | None = False,
) -> bool:
    import minecraft_launcher_lib._helper as helper

    original = helper._ember_original_download
    last: BaseException | None = None
    for attempt in range(5):
        try:
            ensure_download_dir(str(path))
            result = original(
                url,
                path,
                callback or {},
                sha1,
                lzma_compressed,
                session,
                minecraft_directory,
                overwrite,
            )
        except (FileNotFoundError, OSError) as exc:
            last = exc
            time.sleep(0.05 * (attempt + 1))
            continue
        except Exception as exc:
            if type(exc).__name__ in {"InvalidChecksum", "RequestException", "ConnectionError", "Timeout", "ChunkedEncodingError"}:
                last = exc
                time.sleep(0.08 * (attempt + 1))
                continue
            raise
        if result is False and not os.path.isfile(path):
            last = FileNotFoundError(2, "не удалось скачать", str(path))
            time.sleep(0.08 * (attempt + 1))
            continue
        return bool(result)
    if last is not None:
        raise last
    raise FileNotFoundError(2, "не удалось скачать", str(path))


def _copy_inherited_jar(real_copy, src: str, dst: str, *args: object, **kwargs: object):
    """Библиотека копирует отсутствующий jar поверх родительского. Разворачиваем."""
    if not os.path.isfile(src) and os.path.isfile(dst):
        ensure_download_dir(src)
        return real_copy(dst, src, *args, **kwargs)
    return real_copy(src, dst, *args, **kwargs)


def patch_minecraft_downloads() -> None:
    """Чинит гонку папок и поиск Java после закачки Minecraft."""
    if minecraft_launcher_lib is None:
        return
    import minecraft_launcher_lib._helper as helper
    import minecraft_launcher_lib.install as install_mod
    import minecraft_launcher_lib.mod_loader as mod_loader_mod

    if not getattr(helper, "_ember_downloads_patched", False):
        helper._ember_original_download = helper.download_file
        helper.download_file = _stable_download_file
        for module_name in (
            "minecraft_launcher_lib.install",
            "minecraft_launcher_lib.runtime",
            "minecraft_launcher_lib.forge",
            "minecraft_launcher_lib.fabric",
            "minecraft_launcher_lib.quilt",
            "minecraft_launcher_lib.mrpack",
            "minecraft_launcher_lib.mod_loader._forge",
            "minecraft_launcher_lib.mod_loader._fabric",
            "minecraft_launcher_lib.mod_loader._neoforge",
            "minecraft_launcher_lib.mod_loader._quilt",
        ):
            try:
                module = __import__(module_name, fromlist=["download_file"])
            except Exception:
                continue
            if hasattr(module, "download_file"):
                module.download_file = _stable_download_file
        real_copy = install_mod.shutil.copyfile

        def copy_inherited_jar(src: str, dst: str, *args: object, **kwargs: object):
            return _copy_inherited_jar(real_copy, src, dst, *args, **kwargs)

        install_mod.shutil.copyfile = copy_inherited_jar
        helper._ember_downloads_patched = True

    if getattr(mod_loader_mod.ModLoader, "_ember_install", False):
        return

    def ember_install(
        self,
        minecraft_version: str,
        minecraft_directory,
        *,
        loader_version: str | None = None,
        callback: dict | None = None,
        java: str | None = None,
    ) -> str:
        from minecraft_launcher_lib.exceptions import UnsupportedVersion, VersionNotFound
        from minecraft_launcher_lib.install import install_minecraft_version
        from minecraft_launcher_lib.utils import is_version_valid

        directory = str(minecraft_directory)
        if callback is None:
            callback = {}
        if not is_version_valid(minecraft_version, directory):
            raise VersionNotFound(minecraft_version)
        if not self.is_minecraft_version_supported(minecraft_version):
            raise UnsupportedVersion(minecraft_version)
        install_minecraft_version(minecraft_version, directory, callback=callback)
        resolved = java_for_loader(directory, minecraft_version, str(java or ""))
        if not resolved:
            component, _major = java_requirement(directory, minecraft_version)
            if component:
                minecraft_launcher_lib.runtime.install_jvm_runtime(component, directory, callback=callback)
                resolved = java_for_loader(directory, minecraft_version, "")
        if not resolved:
            raise RuntimeError(
                "Java не найдена. Версия игры скачалась, но установщик Fabric, Forge или NeoForge её не запускает. "
                "Открой «Установка», нажми «Скачать Java» и скачай версию ещё раз."
            )
        if loader_version is None:
            loader_version = self.get_latest_loader_version(minecraft_version)
        self._base.install(minecraft_version, directory, callback, resolved, loader_version)
        installed_version = self.get_installed_version(minecraft_version, loader_version)
        install_minecraft_version(installed_version, directory, callback=callback)
        return installed_version

    mod_loader_mod.ModLoader.install = ember_install
    mod_loader_mod.ModLoader._ember_install = True


def java_major_version(java_path: str) -> int:
    if not java_path or not os.path.isfile(java_path):
        return 0
    try:
        result = subprocess.run(
            [java_path, "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    text = (result.stderr or "") + (result.stdout or "")
    match = re.search(r'version "(?:1\.)?(\d+)', text)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except ValueError:
        return 0


def host_arch() -> str:
    machine = (platform.machine() or "").lower()
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return "x64"


def _native_arch(path: str) -> str:
    low = os.path.basename(path).lower()
    if any(token in low for token in ("arm64", "aarch64")):
        return "arm64"
    if any(token in low for token in (
        "natives-windows.jar", "natives-linux.jar", "natives-macos.jar", "natives-osx.jar",
        "natives-darwin.jar", "x86_64", "-x64", "windows-x64", "linux-x64",
    )):
        return "x64"
    return ""


def filter_native_classpath(classpath: str, arch: str, separator: str) -> str:
    """Убирает natives чужой архитектуры, если рядом лежит правильный файл."""
    parts = [part for part in str(classpath or "").split(separator) if part]
    wanted = "arm64" if arch == "arm64" else "x64"
    other = "x64" if wanted == "arm64" else "arm64"
    has_wanted = any(_native_arch(part) == wanted for part in parts)
    if not has_wanted:
        return separator.join(parts)
    kept = [part for part in parts if _native_arch(part) != other]
    return separator.join(kept)


def prepare_native_command(command: list[str], arch: str = "") -> list[str]:
    if not command:
        return command
    machine = arch or host_arch()
    separator = ";" if os.name == "nt" else ":"
    prepared: list[str] = []
    index = 0
    while index < len(command):
        arg = command[index]
        if arg in {"-cp", "-classpath"} and index + 1 < len(command):
            prepared.append(arg)
            prepared.append(filter_native_classpath(command[index + 1], machine, separator))
            index += 2
            continue
        prepared.append(arg)
        index += 1
    return prepared


def system_ram_gb() -> int:
    if os.name == "nt":
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return max(1, int(status.ullTotalPhys / (1024 ** 3)))
        return 0
    if sys.platform == "darwin":
        try:
            raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=5, text=True)
            return max(1, int(int(raw.strip()) / (1024 ** 3)))
        except (OSError, subprocess.SubprocessError, ValueError):
            return 0
    try:
        for line in pathlib.Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return max(1, int(kb / (1024 * 1024)))
    except (OSError, IndexError, ValueError):
        return 0
    return 0


def suggested_ram_gb(mod_count: int, total_gb: int = 0) -> int:
    """Оставляет системе минимум 2 ГБ. Верх лаунчера по-прежнему 16."""
    total = total_gb or system_ram_gb() or 8
    usable = max(2, total - 2)
    count = max(0, int(mod_count))
    want = 2 + min(6, count // 12)
    if count >= 40:
        want = max(want, 6)
    return max(2, min(16, usable, want))


def count_mods(directory: str) -> int:
    folder = os.path.join(directory, "mods")
    if not os.path.isdir(folder):
        return 0
    return sum(1 for name in os.listdir(folder) if name.lower().endswith(".jar"))


def linux_gpu_vendor() -> str:
    if os.path.isfile("/proc/driver/nvidia/version"):
        return "nvidia"
    root = "/sys/class/drm"
    if not os.path.isdir(root):
        return ""
    vendors = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}
    try:
        for name in os.listdir(root):
            if not name.startswith("card") or "-" in name:
                continue
            path = os.path.join(root, name, "device", "vendor")
            if not os.path.isfile(path):
                continue
            code = pathlib.Path(path).read_text(encoding="utf-8", errors="replace").strip().lower()
            if code in vendors:
                return vendors[code]
    except OSError:
        return ""
    return ""


def linux_session() -> str:
    kind = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if kind in {"wayland", "x11"}:
        return kind
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return ""


def apply_linux_compat(env: dict[str, str], mode: str) -> str:
    """Режим выбирает пользователь. Авто только подставляет известный обход, не выдумывает драйвер."""
    vendor = linux_gpu_vendor()
    session = linux_session()
    chosen = mode if mode in {"auto", "wayland", "x11", "nvidia", "mesa", "openal"} else "auto"
    if chosen == "auto":
        if vendor == "nvidia" and session == "wayland":
            chosen = "x11"
        elif vendor == "nvidia":
            chosen = "nvidia"
        elif vendor in {"amd", "intel"}:
            chosen = "mesa"
        else:
            chosen = "x11" if session == "x11" else "wayland" if session == "wayland" else "auto"
    if chosen == "x11":
        env["GDK_BACKEND"] = "x11"
        env.pop("WAYLAND_DISPLAY", None)
    elif chosen == "wayland":
        env["GDK_BACKEND"] = "wayland"
    if chosen == "nvidia":
        env["__GL_THREADED_OPTIMIZATIONS"] = "0"
    if chosen == "mesa":
        env["MESA_GLTHREAD"] = "0"
    if chosen == "openal":
        env["ALSOFT_DRIVERS"] = "pulse"
    return chosen


def windows_gpu_names() -> list[str]:
    if os.name != "nt":
        return []
    try:
        raw = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            timeout=12,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


def prefer_discrete_gpu(java_path: str) -> str:
    """Просит Windows запускать эту Java на мощной видеокарте. На других системах ничего не делает."""
    if os.name != "nt":
        return "Это переключение есть только в Windows."
    if not java_path or not os.path.isfile(java_path):
        return "Сначала нужна Java, которую скачал лаунчер."
    import winreg

    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\DirectX\UserGpuPreferences")
        winreg.SetValueEx(key, os.path.abspath(java_path), 0, winreg.REG_SZ, "GpuPreference=2;")
        winreg.CloseKey(key)
    except OSError as exc:
        return f"Windows не дала записать настройку видеокарты: {exc}"
    return "Для этой Java включён приоритет мощной видеокарты. Если игра уже открыта, запусти её заново."


def file_sha1(path: str) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _version_documents(directory: str, version_id: str) -> list[dict]:
    documents: list[dict] = []
    seen: set[str] = set()
    current = version_id
    while current and current not in seen:
        seen.add(current)
        raw = version_json_text(directory, current)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            break
        if not isinstance(data, dict):
            break
        documents.append(data)
        current = str(data.get("inheritsFrom") or "")
    return documents


def mismatched_game_files(directory: str, version_id: str, limit: int = 40) -> list[str]:
    """Сверяет клиент и библиотеки с sha1 из version.json. Ассеты целиком не читает: их тысячи."""
    bad: list[str] = []
    for data in _version_documents(directory, version_id):
        downloads = data.get("downloads") if isinstance(data.get("downloads"), dict) else {}
        client = downloads.get("client") if isinstance(downloads.get("client"), dict) else {}
        expected = str(client.get("sha1") or "")
        version_name = str(data.get("id") or version_id)
        jar_path = os.path.join(directory, "versions", version_name, version_name + ".jar")
        if expected and os.path.isfile(jar_path):
            try:
                if file_sha1(jar_path) != expected:
                    bad.append(version_name + ".jar")
            except OSError:
                bad.append(version_name + ".jar")
        elif expected and not os.path.isfile(jar_path):
            bad.append(version_name + ".jar нет файла")
        for library in data.get("libraries") or []:
            if len(bad) >= limit:
                return bad
            if not isinstance(library, dict):
                continue
            artifact = (library.get("downloads") or {}).get("artifact") if isinstance(library.get("downloads"), dict) else None
            if not isinstance(artifact, dict):
                continue
            sha1 = str(artifact.get("sha1") or "")
            relative = str(artifact.get("path") or "")
            if not sha1 or not relative or ".." in relative.replace("\\", "/").split("/"):
                continue
            path = os.path.join(directory, "libraries", *relative.split("/"))
            if not os.path.isfile(path):
                bad.append(relative)
                continue
            try:
                actual = file_sha1(path)
            except OSError:
                bad.append(relative)
                continue
            if actual != sha1:
                bad.append(relative)
    return bad


def disable_shader_pack(game_dir: str) -> str:
    """Выключает текущий шейдерпак. Более лёгкий сам не скачивает: это отдельное согласие в сборках."""
    chosen = ""
    for properties in ("iris.properties", "oculus.properties"):
        path = os.path.join(game_dir, "config", properties)
        if not os.path.isfile(path):
            continue
        try:
            lines = pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        updated: list[str] = []
        for line in lines:
            if line.startswith("shaderPack="):
                chosen = chosen or line.split("=", 1)[1].strip()
                updated.append("shaderPack=")
            elif line.startswith("enableShaders="):
                updated.append("enableShaders=false")
            else:
                updated.append(line)
        if not any(line.startswith("enableShaders=") for line in updated):
            updated.append("enableShaders=false")
        temporary = path + ".tmp"
        pathlib.Path(temporary).write_text("\n".join(updated) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    packs = os.path.join(game_dir, "shaderpacks")
    target = safe_filename(chosen)
    if target and os.path.isfile(os.path.join(packs, target)):
        try:
            os.replace(os.path.join(packs, target), os.path.join(packs, target + ".disabled"))
        except OSError:
            return "Шейдеры выключены в настройках, файл пака переименовать не удалось."
        return f"Выключил шейдерпак {target}. Если нужен легче, попроси в сборке «лёгкие шейдеры»."
    return "Шейдеры выключены. Файл пака в shaderpacks не нашёл, смотри папку сам."


def redact_log(text: str) -> str:
    cleaned = redact_secrets(text)
    cleaned = re.sub(r"(?i)([A-Z]:\\Users\\)[^\\]+", r"\1player", cleaned)
    cleaned = re.sub(r"/Users/[^/\s]+", "/Users/player", cleaned)
    cleaned = re.sub(r"/home/[^/\s]+", "/home/player", cleaned)
    cleaned = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[почта]", cleaned)
    return cleaned[-2500:]


def crash_fix_kind(directory: str, launcher_log: str = "") -> str:
    text = _crash_blobs(directory, launcher_log).lower()
    if "unsupportedclassversionerror" in text or "more recent version of the java runtime" in text:
        return "java"
    if "outofmemoryerror" in text or "java heap space" in text or "gc overhead" in text:
        return "ram"
    if any(mark in text for mark in ("failed to load pack", "pack.mcmeta", "resource pack", "incompatible pack")):
        return "pack"
    shader = any(mark in text for mark in ("shader", "iris", "oculus", "framebuffer", "invalid program"))
    broken = any(mark in text for mark in ("error", "exception", "failed", "black screen"))
    if shader and broken:
        return "shader"
    return ""


def explain_crash(text: str, settings: dict | None) -> str:
    """Короткий ответ модели по обезличенному куску лога. Пусто, если модели нет."""
    provider = _provider_for(settings or {})
    if provider is None:
        return ""
    try:
        raw = provider.complete(
            "Объясни ошибку запуска Minecraft по-русски, двумя короткими предложениями. "
            "Не пиши код, не проси пароли и не выдумывай моды.",
            redact_log(text),
        )
    except Exception as exc:
        log_assistant(str(exc))
        return ""
    cleaned = redact_secrets(str(raw or "")).strip()
    return cleaned[:500]
