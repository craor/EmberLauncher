def app_config_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "EmberLauncher")
    os.makedirs(folder, exist_ok=True)
    return folder


def config_path() -> str:
    return os.path.join(app_config_dir(), "config.json")


def log_path() -> str:
    return os.path.join(app_config_dir(), "launch.log")


def resource_path(name: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, name)  # type: ignore[attr-defined]
        if os.path.isfile(bundled):
            return bundled
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def clean_repo(value: str) -> str:
    text = str(value or "").strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = text.strip().strip("/").removesuffix(".git")
    return text if REPO_RE.fullmatch(text) else ""


def version_numbers(value: str) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", str(value or ""))[:4]]
    return tuple(numbers or [0])


def load_server() -> dict:
    empty = {
        "name": "",
        "season": "",
        "about": "",
        "host": "",
        "discord": "",
        "telegram": "",
        "credit": "",
        "update_repo": "",
    }
    try:
        with open(resource_path("server.json"), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(data, dict):
        return empty
    for key in empty:
        value = str(data.get(key) or "").strip()[:160]
        if key in ("discord", "telegram") and not value.startswith("https://"):
            value = ""
        if key == "host":
            value = value.replace("https://", "").replace("http://", "").split("/")[0]
            if not re.fullmatch(r"[A-Za-z0-9.-]{1,80}", value or ""):
                value = ""
        empty[key] = value
    empty["update_repo"] = clean_repo(str(data.get("update_repo") or ""))
    return empty


def split_server_address(value: str) -> tuple[str, int]:
    """Адрес вида host или host:порт. Пустой и кривой адрес никуда не подключаются."""
    text = str(value or "").strip()
    for prefix in ("https://", "http://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = text.split("/")[0].strip()
    if not text:
        return "", 25565
    host, port = text, 25565
    if text.count(":") == 1:
        left, right = text.rsplit(":", 1)
        if right.isdigit():
            host, port = left, int(right)
    host = host.strip().strip("[]")
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,80}", host) or not 1 <= port <= 65535:
        return "", 25565
    return host, port


def _mc_varint(value: int) -> bytes:
    number = int(value) & 0xFFFFFFFF
    out = bytearray()
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        out.append(byte)
        if not number:
            break
    return bytes(out)


def status_request_packet(host: str, port: int) -> bytes:
    """Рукопожатие статуса Minecraft и пустой запрос. Без этого сервер молчит."""
    import struct

    encoded = host.encode("utf-8")
    body = b"\x00" + _mc_varint(47) + _mc_varint(len(encoded)) + encoded + struct.pack(">H", int(port)) + b"\x01"
    return _mc_varint(len(body)) + body + b"\x01\x00"


def _take_varint(data: bytes, index: int) -> tuple[int, int]:
    number = 0
    shift = 0
    for step in range(5):
        if index + step >= len(data):
            raise ValueError("обрыв")
        byte = data[index + step]
        number |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return number, index + step + 1
        shift += 7
    raise ValueError("varint")


def query_server_status(address: str, timeout: float = 4.0) -> dict:
    """Сколько игроков на сервере. Обычный запрос списка, отдельный хостинг не нужен."""
    host, port = split_server_address(address)
    empty = {"ok": False, "online": 0, "max": 0}
    if not host:
        return empty
    import socket

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError:
        return empty
    try:
        sock.settimeout(timeout)
        sock.sendall(status_request_packet(host, port))

        def read_varint() -> int:
            number = 0
            shift = 0
            for _step in range(5):
                raw = sock.recv(1)
                if not raw:
                    raise OSError("пустой ответ")
                byte = raw[0]
                number |= (byte & 0x7F) << shift
                if not byte & 0x80:
                    return number
                shift += 7
            raise OSError("длинный ответ")

        length = read_varint()
        if length <= 0 or length > 1_000_000:
            return empty
        blob = b""
        while len(blob) < length:
            chunk = sock.recv(length - len(blob))
            if not chunk:
                break
            blob += chunk
    except OSError:
        return empty
    finally:
        try:
            sock.close()
        except OSError:
            pass
    try:
        _packet_id, cursor = _take_varint(blob, 0)
        size, cursor = _take_varint(blob, cursor)
        payload = json.loads(blob[cursor:cursor + size].decode("utf-8", errors="replace"))
    except (ValueError, json.JSONDecodeError, UnicodeError):
        return empty
    players = payload.get("players") if isinstance(payload, dict) else None
    if not isinstance(players, dict):
        return empty
    try:
        online = max(0, int(players.get("online") or 0))
        maximum = max(0, int(players.get("max") or 0))
    except (TypeError, ValueError):
        return empty
    return {"ok": True, "online": online, "max": maximum}


def load_config() -> dict:
    defaults = {
        "nickname": "Player",
        "minecraft_dir": "",
        "java_path": "",
        "java_runtime": "java-runtime-delta",
        "ram_gb": 4,
        "last_version": "",
        "loader": "fabric",
        "target_version": "26.3",
        "accounts": [],
        "update_repo": "",
        "llm_provider": "off",
        "ollama_model": "qwen2.5:3b",
        "ollama_url": "http://127.0.0.1:11434",
        "openrouter_model": "meta-llama/llama-3.2-3b-instruct:free",
        "active_instance": "",
        "assistant_optimize": True,
        "ram_auto": True,
        "linux_compat": "auto",
        "mac_thread": "auto",
        "status_host": "",
    }
    try:
        with open(config_path(), "r", encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, json.JSONDecodeError):
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    defaults.update({key: stored[key] for key in defaults if key in stored})
    try:
        defaults["ram_gb"] = max(1, min(16, int(defaults["ram_gb"])))
    except (TypeError, ValueError):
        defaults["ram_gb"] = 4
    defaults["nickname"] = str(defaults["nickname"] or "Player")
    defaults["minecraft_dir"] = str(defaults["minecraft_dir"] or "")
    defaults["java_path"] = str(defaults["java_path"] or "")
    defaults["java_runtime"] = str(defaults["java_runtime"] or "java-runtime-delta")
    defaults["last_version"] = str(defaults["last_version"] or "")
    defaults["loader"] = str(defaults["loader"] or "fabric")
    defaults["target_version"] = str(defaults["target_version"] or "26.3")
    defaults["update_repo"] = clean_repo(str(stored.get("update_repo") or ""))
    provider = str(defaults.get("llm_provider") or "off")
    defaults["llm_provider"] = provider if provider in ("off", "ollama", "deepseek", "openrouter") else "off"
    ollama_model = str(defaults.get("ollama_model") or "")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", ollama_model):
        defaults["ollama_model"] = "qwen2.5:3b"
    router_model = str(defaults.get("openrouter_model") or "")
    if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,80}", router_model):
        defaults["openrouter_model"] = "meta-llama/llama-3.2-3b-instruct:free"
    defaults["ollama_url"] = str(defaults.get("ollama_url") or "http://127.0.0.1:11434")
    instance_name = str(defaults.get("active_instance") or "")
    defaults["active_instance"] = instance_name if re.fullmatch(r"[a-z0-9-]{1,48}", instance_name) else ""
    defaults["assistant_optimize"] = stored.get("assistant_optimize") is not False
    defaults["ram_auto"] = stored.get("ram_auto") is not False
    linux_mode = str(defaults.get("linux_compat") or "auto")
    defaults["linux_compat"] = linux_mode if linux_mode in {"auto", "wayland", "x11", "nvidia", "mesa", "openal"} else "auto"
    mac_mode = str(defaults.get("mac_thread") or "auto")
    defaults["mac_thread"] = mac_mode if mac_mode in {"auto", "always", "never"} else "auto"
    status_host, _status_port = split_server_address(str(defaults.get("status_host") or ""))
    defaults["status_host"] = status_host if not _status_port or _status_port == 25565 else f"{status_host}:{_status_port}"
    if not status_host:
        defaults["status_host"] = ""
    accounts: list[str] = []
    raw_accounts = stored.get("accounts")
    if isinstance(raw_accounts, list):
        for item in raw_accounts:
            nick = str(item or "").strip()
            if NICK_RE.fullmatch(nick) and nick not in accounts:
                accounts.append(nick)
            if len(accounts) >= 16:
                break
    if NICK_RE.fullmatch(defaults["nickname"]) and defaults["nickname"] not in accounts:
        accounts.insert(0, defaults["nickname"])
    defaults["accounts"] = accounts
    return defaults


def save_config(data: dict) -> None:
    target = config_path()
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, target)


def offline_player_uuid(username: str) -> str:
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(digest)))


def version_sort_key(value: str) -> tuple:
    parts: list[tuple] = []
    for piece in re.split(r"[^0-9A-Za-z]+", value):
        if not piece:
            continue
        if piece.isdigit():
            parts.append((0, int(piece)))
        else:
            parts.append((1, piece.lower()))
    return tuple(parts)


def installed_version_ids(minecraft_dir: str) -> list[str]:
    versions_dir = os.path.join(minecraft_dir, "versions")
    found: list[str] = []
    if not os.path.isdir(versions_dir):
        return found
    for name in os.listdir(versions_dir):
        json_file = os.path.join(versions_dir, name, name + ".json")
        if os.path.isfile(json_file):
            found.append(name)
    found.sort(key=version_sort_key, reverse=True)
    return found


def default_minecraft_dir() -> str:
    if minecraft_launcher_lib is not None:
        return minecraft_launcher_lib.utils.get_minecraft_directory()
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(appdata, ".minecraft")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "minecraft")
    return os.path.join(os.path.expanduser("~"), ".minecraft")


def _java_names() -> tuple[str, ...]:
    if os.name == "nt":
        return ("javaw.exe", "java.exe")
    return ("java",)


def _collect_java_under(root: str, max_depth: int = 4) -> list[str]:
    found: list[str] = []
    if not root or not os.path.isdir(root):
        return found
    names = set(_java_names())
    root = os.path.abspath(root)
    for current, dirs, files in os.walk(root):
        depth = current[len(root):].count(os.sep)
        if depth > max_depth:
            dirs.clear()
            continue
        for name in names:
            if name in files:
                found.append(os.path.join(current, name))
    return found


def find_java_candidates(minecraft_dir: str) -> list[str]:
    found: list[str] = []
    found.extend(_collect_java_under(os.path.join(minecraft_dir, "runtime"), max_depth=6))
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        folder_names = (
            "Java", "Eclipse Adoptium", "Microsoft", "Zulu", "BellSoft",
            "Amazon Corretto", "Semeru", "GraalVM",
        )
        bases = [program_files, program_files_x86]
        if local_app:
            bases.append(os.path.join(local_app, "Programs"))
        for base in bases:
            for folder in folder_names:
                found.extend(_collect_java_under(os.path.join(base, folder), max_depth=4))
    for binary in ("javaw", "java"):
        which = shutil.which(binary)
        if which:
            found.append(which)
    unique: list[str] = []
    seen: set[str] = set()
    for path in found:
        normalized = os.path.normcase(os.path.normpath(path))
        if normalized in seen or not os.path.isfile(path):
            continue
        seen.add(normalized)
        unique.append(path)

    def rank(path: str) -> tuple:
        base = os.path.basename(path).lower()
        runtime_bonus = 0 if f"{os.sep}runtime{os.sep}" in os.path.normcase(path) else 1
        name_bonus = 0 if base.startswith("javaw") else 1
        return (runtime_bonus, name_bonus, path.lower())

    unique.sort(key=rank)
    return unique


def find_best_java(minecraft_dir: str) -> str:
    candidates = find_java_candidates(minecraft_dir)
    return candidates[0] if candidates else ""


def apply_ram(command: list[str], ram_gb: int) -> list[str]:
    ram_gb = max(1, min(16, int(ram_gb)))
    xms = ram_gb if ram_gb < 2 else min(2, ram_gb)
    if not command:
        return command
    tail = [arg for arg in command[1:] if not (arg.startswith("-Xmx") or arg.startswith("-Xms"))]
    return [command[0], f"-Xms{xms}G", f"-Xmx{ram_gb}G", *tail]


def scrub_launch_command(command: list[str], username: str, player_uuid: str, token: str) -> list[str]:
    replacements = {
        "${auth_player_name}": username,
        "${auth_uuid}": player_uuid,
        "${auth_access_token}": token,
        "${auth_session}": token,
        "${user_type}": "legacy",
        "${clientid}": "",
        "${auth_xuid}": "",
        "{username}": username,
        "{uuid}": player_uuid,
        "{token}": token,
    }
    cleaned: list[str] = []
    for arg in command:
        for source, target in replacements.items():
            if source in arg:
                arg = arg.replace(source, target)
        cleaned.append(arg)
    for index in range(len(cleaned) - 1):
        if cleaned[index] == "--userType":
            cleaned[index + 1] = "legacy"
        elif cleaned[index] == "--accessToken" and not cleaned[index + 1]:
            cleaned[index + 1] = token
    return cleaned


def translate_status(text: str) -> str:
    known = {
        "Download Libraries": "Загрузка библиотек",
        "Download Assets": "Загрузка ресурсов",
        "Install java runtime": "Установка Java для этой версии",
        "Installation complete": "Установка завершена",
        "Running installer": "Запуск установщика",
    }
    if text in known:
        return known[text]
    if text.startswith("Download "):
        return "Файл: " + text[len("Download "):]
    return text


def minecraft_release_from_id(version_id: str) -> str:
    found = _GAME_VERSION_RE.findall(version_id or "")
    classic = [item for item in found if item.startswith("1.")]
    if classic:
        return classic[0]
    for item in found:
        year = int(item.split(".", 1)[0])
        if 20 <= year <= 39:
            return item
    return ""


def version_json_text(directory: str, version_id: str) -> str:
    if not version_id:
        return ""
    path = os.path.join(directory, "versions", version_id, version_id + ".json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def installed_game_version(directory: str, version_id: str) -> str:
    raw = version_json_text(directory, version_id)
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            for key in ("inheritsFrom", "id"):
                parsed = minecraft_release_from_id(str(data.get(key) or ""))
                if parsed:
                    return parsed
    return minecraft_release_from_id(version_id)


def version_json_has_loader(directory: str, version_id: str, loader: str) -> bool:
    raw = version_json_text(directory, version_id).lower()
    if not raw:
        return False
    if loader == "vanilla":
        return True
    if loader == "forge":
        return "forge" in raw and "neoforge" not in raw
    return loader in raw


def loader_from_text(text: str, fallback: str) -> str:
    low = (text or "").lower()
    options = (
        ("neoforge", ("neoforge", "неофорж")),
        ("fabric", ("fabric", "фабрик")),
        ("forge", ("forge", "форж")),
        ("quilt", ("quilt", "квилт")),
        ("optifine", ("optifine", "оптифайн")),
        ("vanilla", ("vanilla", "ваниль")),
    )
    for key, needles in options:
        if any(word in low for word in needles):
            return key
    return fallback


def clean_search_text(text: str) -> str:
    cleaned = _GAME_VERSION_RE.sub(" ", text or "")
    cleaned = re.sub(
        r"\b(fabric|forge|neoforge|quilt|optifine|vanilla|фабрик|форж|неофорж|квилт|оптифайн|ваниль|версия|версии|сделай|мне|сборку|сборка|моды|мод|много|хочу|добавь|поставь|игру|там|ещё|еще|очень|просто|какую|какие|нибудь|скачай|поставь)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", cleaned).strip()


SEARCH_HINTS = (
    (("зомби", "zombie", "апокал", "нежить", "орда"), "zombie apocalypse"),
    (("ужас", "хоррор", "horror", "туман"), "horror"),
    (("выжив", "survival", "хардкор"), "survival"),
    (("оруж", "gun", "стрел", "мушкет", "воен", "солдат", "танк", "арми"), "guns military"),
    (("живот", "зоо", "питом", "собак", "кош", "лошад", "волк", "ферм"), "animals"),
    (("динозав",), "dinosaurs"),
    (("дракон", "dragon"), "dragon"),
    (("машин", "транспорт", "автомоб"), "vehicles"),
    (("рпг", "rpg", "квест"), "rpg adventure"),
    (("реалист",), "realistic"),
    (("моб",), "mobs"),
    (("строит", "декор", "мебел"), "building decoration"),
    (("еда", "ферм", "готов"), "food cooking"),
    (("маг", "magic", "волшеб", "закл"), "magic"),
    (("тех", "механ", "create", "завод"), "technology"),
    (("данж", "приключ", "пещер"), "dungeon"),
    (("пвп", "pvp"), "pvp"),
    (("шейд", "shader"), "shader"),
    (("оптим", "фпс", "fps", "лаг"), "performance"),
    (("анимац", "animat"), "animation"),
    (("природ", "биом", "измер"), "biomes"),
    (("бос", "boss"), "bosses"),
    (("пират", "кораб", "океан", "море", "лодк"), "ships"),
    (("космос", "планет", "ракета"), "space"),
    (("рыцар", "средневек", "замок"), "medieval"),
    (("незер", "адск"), "nether"),
    (("эндер", "the end"), "ender"),
    (("робот",), "robot"),
    (("рыб",), "fishing"),
    (("шахт", "рудник"), "mining"),
)


def query_variants(text: str) -> list[str]:
    """Короткие английские запросы. Несколько слов Modrinth склеивает через И, поэтому каждое слово отдельно."""
    low = (text or "").lower()
    queries: list[str] = []

    def add(query: str) -> None:
        query = re.sub(r"\s+", " ", query or "").strip()
        if query and query.lower() not in {item.lower() for item in queries}:
            queries.append(query)

    for words, query in SEARCH_HINTS:
        if any(word in low for word in words):
            parts = query.split()
            for part in reversed(parts):
                add(part)
    cleaned = clean_search_text(text)
    for word in cleaned.split():
        if re.search(r"[A-Za-z]", word):
            add(word)
    return queries[:6]


def english_search_query(text: str) -> str:
    return " ".join(query_variants(text))


def resolve_pack_version(query: str, target: str, selected: str, directory: str) -> str:
    found = minecraft_release_from_id(query)
    if found:
        return found
    target = (target or "").strip()
    if target:
        return minecraft_release_from_id(target) or target
    installed = installed_game_version(directory, selected)
    return installed or "26.3"


def version_has_loader(version_id: str, loader: str) -> bool:
    value = (version_id or "").lower()
    if loader == "forge":
        return "forge" in value and "neoforge" not in value
    return loader in value


def prefer_javaw(command: list[str]) -> list[str]:
    if os.name != "nt" or not command:
        return command
    folder = os.path.dirname(command[0])
    if os.path.basename(command[0]).lower() != "java.exe":
        return command
    javaw = os.path.join(folder, "javaw.exe")
    if os.path.isfile(javaw):
        return [javaw, *command[1:]]
    return command


def mac_launch_command(command: list[str], platform_name: str = "", thread_mode: str = "auto") -> list[str]:
    """Флаг главного потока нужен, когда Java не является Cocoa-процессом. Режим «never» его убирает."""
    if (platform_name or sys.platform) != "darwin" or not command:
        return command
    mode = thread_mode if thread_mode in {"auto", "always", "never"} else "auto"
    if mode == "never":
        return [arg for arg in command if arg != "-XstartOnFirstThread"]
    extras: list[str] = []
    if "-XstartOnFirstThread" not in command:
        extras.append("-XstartOnFirstThread")
    if not any(arg.startswith("-Dfml.earlyprogresswindow=") for arg in command):
        extras.append("-Dfml.earlyprogresswindow=false")
    if not extras:
        return command
    return [command[0], *extras, *command[1:]]


def macho_cpus(path: str) -> set[str]:
    """Какие архитектуры в Mach-O: arm64, x86_64. Пусто, если это не бинарник."""
    import struct

    try:
        with open(path, "rb") as handle:
            blob = handle.read(512)
    except OSError:
        return set()
    if len(blob) < 8:
        return set()
    names = {0x7: "x86_64", 0x01000007: "x86_64", 0xC: "arm64", 0x0100000C: "arm64"}
    magic = blob[:4]
    found: set[str] = set()
    if magic == b"\xca\xfe\xba\xbe":
        count = struct.unpack(">I", blob[4:8])[0]
        offset = 8
        for _ in range(min(count, 8)):
            if offset + 4 > len(blob):
                break
            cpu = struct.unpack(">I", blob[offset:offset + 4])[0]
            if cpu in names:
                found.add(names[cpu])
            offset += 20
        return found
    if magic == b"\xcf\xfa\xed\xfe":
        cpu = struct.unpack("<I", blob[4:8])[0]
        if cpu in names:
            found.add(names[cpu])
    return found


def _java_mach_arch(java_path: str) -> str:
    import platform

    cpus = macho_cpus(java_path) if java_path and os.path.isfile(java_path) else set()
    if cpus == {"arm64"}:
        return "arm64"
    if cpus == {"x86_64"}:
        return "x86_64"
    machine = (platform.machine() or "").lower()
    return "arm64" if machine in {"arm64", "aarch64"} else "x86_64"


def _mac_native_kind(name: str) -> str:
    low = os.path.basename(name).lower()
    if any(token in low for token in ("macos-arm64", "osx-arm64", "darwin-arm64")):
        return "arm64"
    if any(token in low for token in (
        "natives-macos.jar",
        "natives-macos-x64",
        "natives-macos-x86",
        "natives-osx.jar",
        "natives-darwin.jar",
    )):
        return "x64"
    return ""


def filter_mac_classpath(classpath: str, java_arch: str) -> str:
    """Оставляет natives только под архитектуру Java. Чужие роняют игру до меню."""
    parts = [part for part in str(classpath or "").split(":") if part]
    if java_arch not in {"arm64", "x86_64"}:
        return ":".join(parts)
    arm_present = any(_mac_native_kind(part) == "arm64" for part in parts)
    kept: list[str] = []
    for part in parts:
        kind = _mac_native_kind(part)
        if java_arch == "arm64" and kind == "x64" and arm_present:
            continue
        if java_arch == "x86_64" and kind == "arm64":
            continue
        kept.append(part)
    return ":".join(kept)


def prune_mac_natives(directory: str, java_arch: str) -> None:
    """Убирает из папки natives dylib не той архитектуры, иначе lwjgl грузит её первой."""
    if java_arch not in {"arm64", "x86_64"} or not directory or not os.path.isdir(directory):
        return
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if not name.endswith((".dylib", ".jnilib")):
                continue
            path = os.path.join(root, name)
            cpus = macho_cpus(path)
            if not cpus or cpus == {"arm64", "x86_64"}:
                continue
            wrong = (java_arch == "arm64" and "arm64" not in cpus) or (
                java_arch == "x86_64" and "x86_64" not in cpus
            )
            if not wrong:
                continue
            try:
                os.remove(path)
            except OSError:
                pass


def prepare_mac_game_command(
    command: list[str],
    platform_name: str = "",
    java_arch: str = "",
    thread_mode: str = "auto",
) -> list[str]:
    plat = platform_name or sys.platform
    if plat != "darwin" or not command:
        return command
    command = mac_launch_command(list(command), plat, thread_mode)
    arch = java_arch or _java_mach_arch(command[0])
    prepared: list[str] = []
    index = 0
    while index < len(command):
        arg = command[index]
        if arg in {"-cp", "-classpath"} and index + 1 < len(command):
            prepared.append(arg)
            prepared.append(filter_mac_classpath(command[index + 1], arch))
            index += 2
            continue
        if arg.startswith("-Djava.library.path="):
            prune_mac_natives(arg.split("=", 1)[1], arch)
        prepared.append(arg)
        index += 1
    return prepared


def mac_minecraft_alive() -> bool:
    """open -W иногда возвращается сразу, хотя Java уже держит окно."""
    if sys.platform != "darwin":
        return False
    try:
        found = subprocess.run(
            ["pgrep", "-f", "net.minecraft.client.main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return found.returncode == 0


def write_mac_game_bundle(command: list[str], cwd: str, log_file: str) -> str:
    """Отдельное .app, а не дочерний процесс Qt: иначе Cocoa не даёт окно и игра умирает до меню."""
    import shlex

    folder = os.path.join(app_config_dir(), "MinecraftGame.app")
    contents = os.path.join(folder, "Contents")
    macos = os.path.join(contents, "MacOS")
    os.makedirs(macos, exist_ok=True)
    plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>launch</string>
<key>CFBundleIdentifier</key><string>dev.emberlauncher.minecraft</string>
<key>CFBundleName</key><string>Minecraft</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSMinimumSystemVersion</key><string>11.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSSupportsAutomaticGraphicsSwitching</key><true/>
</dict></plist>
"""
    with open(os.path.join(contents, "Info.plist"), "w", encoding="utf-8") as handle:
        handle.write(plist)
    script = "\n".join((
        "#!/bin/bash",
        f"cd {shlex.quote(cwd)} || exit 1",
        f"exec {shlex.join(command)} >> {shlex.quote(log_file)} 2>&1",
        "",
    ))
    executable = os.path.join(macos, "launch")
    with open(executable, "w", encoding="utf-8") as handle:
        handle.write(script)
    os.chmod(executable, 0o755)
    for cmd in (
        ["xattr", "-dr", "com.apple.quarantine", folder],
        ["codesign", "--force", "--sign", "-", folder],
    ):
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
    return folder


def game_process_env(compat: str = "") -> dict[str, str]:
    env = os.environ.copy()
    if sys.platform.startswith("linux"):
        apply_linux_compat(env, compat or "auto")
        return env
    if sys.platform != "darwin":
        return env
    for key in list(env):
        if key.startswith(("DYLD_", "QT_", "PYTHON", "SIP_")) or key in {
            "PYTHONHOME", "PYTHONPATH", "PYTHONNOUSERSITE", "VERSIONER_PYTHON_PREFER_32_BIT",
        }:
            env.pop(key, None)
    env["MallocNanoZone"] = "0"
    env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    return env


def unlock_downloaded_java(java_path: str, minecraft_dir: str = "", version_id: str = "") -> None:
    """Снимает карантин macOS с Java и библиотек, иначе процесс убивается до меню."""
    if sys.platform != "darwin":
        return
    targets: list[str] = []
    if java_path and java_path != "java" and os.path.exists(java_path):
        real = os.path.realpath(java_path)
        try:
            os.chmod(real, os.stat(real).st_mode | 0o755)
        except OSError:
            pass
        home = os.path.dirname(os.path.dirname(real))
        if home:
            targets.append(home)
    if minecraft_dir:
        for name in ("runtime", "libraries", "versions", "bin"):
            folder = os.path.join(minecraft_dir, name)
            if os.path.isdir(folder):
                targets.append(folder)
        natives = os.path.join(minecraft_dir, "versions", version_id, "natives")
        if version_id and os.path.isdir(natives):
            targets.append(natives)
    seen: set[str] = set()
    for target in targets:
        if target in seen or not os.path.exists(target):
            continue
        seen.add(target)
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", target],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def open_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def network_error(exc: BaseException) -> str:
    text = str(exc)
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
        return (
            "HTTPS не прошёл: у сборки Python на Mac нет корневых сертификатов. "
            "Скачай новую версию в браузере: https://github.com/craor/EmberLauncher/releases/latest"
        )
    return text


def http_json(url: str, timeout: int = 30):
    _require_https(url, ALLOWED_HOSTS)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        _require_https(response.geturl(), ALLOWED_HOSTS)
        return json.loads(response.read().decode("utf-8"))


def http_download(url: str, dest: str, timeout: int = 180) -> None:
    _require_https(url, ALLOWED_HOSTS)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temporary = dest + ".part"
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, open(temporary, "wb") as handle:
            _require_https(response.geturl(), ALLOWED_HOSTS)
            copied = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > MAX_DOWNLOAD_BYTES:
                    raise ValueError(
                        f"Файл больше {MAX_DOWNLOAD_BYTES // (1024 * 1024)} МБ, загрузка остановлена."
                    )
                handle.write(chunk)
        os.replace(temporary, dest)
    except Exception:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


_JAR_CACHE: dict[str, bytes] = {}
_JAR_CACHE_BYTES = 0
_LIBRARY_JAR_LIMIT = 64 * 1024 * 1024


def http_bytes(url: str, limit: int = _LIBRARY_JAR_LIMIT) -> bytes:
    cached = _JAR_CACHE.get(url)
    if cached is not None:
        return cached
    _require_https(url, ALLOWED_HOSTS)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        _require_https(response.geturl(), ALLOWED_HOSTS)
        chunks: list[bytes] = []
        copied = 0
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            copied += len(chunk)
            if copied > limit:
                raise ValueError("Архив мода слишком большой, зависимости не прочитал.")
            chunks.append(chunk)
    data = b"".join(chunks)
    global _JAR_CACHE_BYTES
    if _JAR_CACHE_BYTES < 180 * 1024 * 1024:
        _JAR_CACHE[url] = data
        _JAR_CACHE_BYTES += len(data)
    return data


def active_update_repo(config: dict | None = None) -> str:
    if config:
        saved = clean_repo(str(config.get("update_repo") or ""))
        if saved:
            return saved
    bundled = clean_repo(str(load_server().get("update_repo") or ""))
    if bundled:
        return bundled
    return DEFAULT_UPDATE_REPO


def github_update(repo: str, current: str) -> dict | None:
    owner, name = repo.split("/", 1)
    url = (
        "https://api.github.com/repos/"
        f"{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/releases/latest"
    )
    try:
        payload = http_json(url, timeout=20)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"На GitHub ещё нет релиза. Нужен файл {release_filename()}."
            ) from exc
        raise RuntimeError(f"GitHub ответил ошибкой {exc.code}.") from exc
    if not isinstance(payload, dict):
        return None
    tag = str(payload.get("tag_name") or "").strip()
    if version_numbers(tag) <= version_numbers(current):
        return None
    wanted = release_filename().lower()
    asset = next(
        (
            item for item in payload.get("assets") or []
            if isinstance(item, dict) and str(item.get("name") or "").lower() == wanted
        ),
        None,
    )
    if not isinstance(asset, dict):
        raise RuntimeError(f"В релизе нет файла {release_filename()}.")
    download = str(asset.get("browser_download_url") or "")
    if not download.startswith("https://github.com/"):
        raise RuntimeError("Ссылка обновления ведёт не на GitHub.")
    notes = re.sub(r"\s+", " ", str(payload.get("body") or "")).strip()
    return {
        "version": tag.lstrip("vV") or tag,
        "url": download,
        "notes": notes[:280],
        "digest": str(asset.get("digest") or ""),
    }


def github_release_notes(repo: str) -> list[dict]:
    cleaned = clean_repo(repo)
    if not cleaned or "/" not in cleaned:
        return []
    owner, name = cleaned.split("/", 1)
    url = (
        "https://api.github.com/repos/"
        f"{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/releases?per_page=6"
    )
    payload = http_json(url, timeout=20)
    if not isinstance(payload, list):
        return []
    notes: list[dict] = []
    for item in payload:
        if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
            continue
        body = re.sub(r"\s+", " ", str(item.get("body") or "")).strip()
        notes.append({
            "version": str(item.get("tag_name") or "").strip(),
            "date": str(item.get("published_at") or "")[:10],
            "body": body[:420] or "Обновление лаунчера.",
        })
    return notes


def github_download_total(repo: str) -> int:
    cleaned = clean_repo(repo)
    if not cleaned or "/" not in cleaned:
        return 0
    owner, name = cleaned.split("/", 1)
    total = 0
    page = 1
    while page <= 3:
        url = (
            "https://api.github.com/repos/"
            f"{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/releases?per_page=20&page={page}"
        )
        payload = http_json(url, timeout=20)
        if not isinstance(payload, list) or not payload:
            break
        for item in payload:
            if not isinstance(item, dict):
                continue
            for asset in item.get("assets") or []:
                if not isinstance(asset, dict):
                    continue
                try:
                    total += int(asset.get("download_count") or 0)
                except (TypeError, ValueError):
                    continue
        if len(payload) < 20:
            break
        page += 1
    return total


def verify_update_file(path: str, digest: str) -> None:
    size = os.path.getsize(path)
    if size < MIN_UPDATE_BYTES or size > MAX_DOWNLOAD_BYTES:
        raise RuntimeError("Файл обновления странного размера, он не установлен.")
    magic = b"MZ" if os.name == "nt" else (b"PK" if sys.platform == "darwin" else b"\x7fELF")
    with open(path, "rb") as handle:
        if handle.read(len(magic)) != magic:
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


def assert_safe_path(path: str) -> str:
    full = os.path.abspath(path)
    if any(char in full for char in '"\r\n%&|<>$;`'):
        raise RuntimeError("Путь содержит запрещённые символы.")
    return full


def mac_app_bundle(executable: str) -> str:
    path = os.path.abspath(executable)
    while path != os.path.dirname(path):
        if path.endswith(".app") and os.path.isdir(path):
            return path
        path = os.path.dirname(path)
    raise RuntimeError("Не нашёл EmberLauncher.app")


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
        bundle = mac_app_bundle(sys.executable)
        bundle = assert_safe_path(bundle)
        parent = assert_safe_path(os.path.dirname(bundle))
        script_path = os.path.join(tempfile.gettempdir(), "ember-update.sh")
        script = (
            "#!/bin/sh\n"
            "sleep 2\n"
            f'rm -rf "{bundle}"\n'
            f'ditto -x -k "{new_file}" "{parent}"\n'
            f'open "{bundle}"\n'
            "rm -f \"$0\"\n"
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


def _require_https(url: str, hosts: frozenset[str]) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in hosts or parsed.username or parsed.password:
        raise ValueError("Разрешены только заранее известные https-адреса.")


def installed_mod_names(directory: str) -> set[str]:
    found: set[str] = set()
    for folder in ("mods", "shaderpacks"):
        path = os.path.join(directory, folder)
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            low = name.lower()
            if not low.endswith((".jar", ".zip", ".disabled")):
                continue
            found.add(low)
            found.add(os.path.splitext(low)[0])
    return found


def mod_already_installed(mod: dict, present: set[str]) -> bool:
    filename = str(mod.get("filename") or "").lower()
    slug = str(mod.get("slug") or "").lower().replace("_", "-")
    if filename and (filename in present or os.path.splitext(filename)[0] in present):
        return True
    if len(slug) >= 4:
        return any(slug in name for name in present)
    return False


def safe_filename(name: str) -> str:
    base = os.path.basename(str(name or "")).strip()
    if not base or base in (".", "..") or any(char in base for char in ("/", "\\", ":", "*")):
        return ""
    return base


def _pick_mod_file(version: dict, allow_zip: bool) -> dict | None:
    files = version.get("files") or []
    primary = next((item for item in files if item.get("primary")), None)
    chosen = primary or (files[0] if files else None)
    if not chosen:
        return None
    filename = safe_filename(chosen.get("filename") or "")
    url = str(chosen.get("url") or "")
    if not filename or not url.startswith("https://cdn.modrinth.com/"):
        return None
    if filename.endswith(".jar") or (allow_zip and filename.endswith(".zip")):
        hashes = chosen.get("hashes") if isinstance(chosen.get("hashes"), dict) else {}
        return {
            "filename": filename,
            "url": url,
            "sha1": str(hashes.get("sha1") or ""),
            "sha512": str(hashes.get("sha512") or ""),
        }
    return None


def curse_cdn_url(file_id: int, filename: str) -> str:
    name = safe_filename(filename)
    return f"https://edge.forgecdn.net/files/{file_id // 1000}/{file_id % 1000}/{urllib.parse.quote(name)}"


def resolve_modrinth(slug: str, loader: str, game_version: str, shader: bool = False) -> dict | None:
    quoted = urllib.parse.quote(slug)
    meta = http_json(f"https://api.modrinth.com/v2/project/{quoted}")
    project_type = str(meta.get("project_type") or "mod")
    is_shader = shader or project_type == "shader"
    params = {"game_versions": json.dumps([game_version])}
    if not is_shader:
        params["loaders"] = json.dumps([loader])
    versions = http_json(
        f"https://api.modrinth.com/v2/project/{quoted}/version?{urllib.parse.urlencode(params)}"
    )
    if not isinstance(versions, list):
        return None
    releases = [item for item in versions if item.get("version_type") == "release"]
    ordered = releases or versions
    for version in ordered:
        picked = _pick_mod_file(version, allow_zip=is_shader)
        if not picked:
            continue
        return {
            "slug": str(meta.get("slug") or slug),
            "title": str(meta.get("title") or slug),
            "filename": picked["filename"],
            "url": picked["url"],
            "sha1": picked.get("sha1") or "",
            "sha512": picked.get("sha512") or "",
            "folder": "shaderpacks" if is_shader else "mods",
            "deps": version.get("dependencies") or [],
            "blurb": str(meta.get("description") or "").strip(),
            "source": "Modrinth",
        }
    return None


def resolve_curseforge(slug: str, loader: str, game_version: str, shader: bool = False) -> dict | None:
    kinds = ("shaders", "mc-mods") if shader else ("mc-mods", "shaders")
    data = None
    for kind in kinds:
        try:
            payload = http_json(f"https://api.cfwidget.com/minecraft/{kind}/{urllib.parse.quote(slug)}")
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("files"):
            data = payload
            break
    if not data:
        return None
    wanted_version = game_version.lower()
    wanted_loader = loader.lower()
    ranked: list[tuple[tuple, dict]] = []
    for item in data.get("files") or []:
        if not isinstance(item, dict):
            continue
        versions = [str(value).lower() for value in item.get("versions") or []]
        name = str(item.get("name") or "").lower()
        if wanted_version not in versions and wanted_version not in name:
            continue
        if not shader and wanted_loader not in versions and wanted_loader not in name:
            continue
        if shader and not name.endswith(".zip"):
            continue
        if not shader and not name.endswith(".jar"):
            continue
        release = 0 if str(item.get("type") or "").lower() == "release" else 1
        ranked.append(((release, name), item))
    if not ranked:
        return None
    ranked.sort(key=lambda pair: pair[0])
    chosen = ranked[0][1]
    filename = safe_filename(str(chosen.get("name") or ""))
    try:
        file_id = int(chosen.get("id"))
    except (TypeError, ValueError):
        return None
    if not filename:
        return None
    return {
        "slug": slug,
        "title": str(data.get("title") or slug),
        "filename": filename,
        "url": curse_cdn_url(file_id, filename),
        "folder": "shaderpacks" if shader else "mods",
        "deps": [],
        "blurb": str(data.get("summary") or "").strip(),
        "source": "CurseForge",
    }


def resolve_project(
    slug: str,
    loader: str,
    game_version: str,
    shader: bool = False,
    sources: tuple[str, ...] = ("modrinth", "curseforge"),
) -> dict | None:
    if "modrinth" in sources:
        try:
            info = resolve_modrinth(slug, loader, game_version, shader=shader)
        except Exception:
            info = None
        if info:
            return info
    if "curseforge" in sources:
        try:
            info = resolve_curseforge(slug, loader, game_version, shader=shader)
        except Exception:
            info = None
        if info:
            return info
    return None


def _line_key(version: str) -> tuple | None:
    parts = (version or "").split(".")
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    if parts[0] == "1":
        return ("1", parts[1])
    if parts[0].isdigit() and len(parts[0]) == 2:
        return (parts[0], parts[1])
    return None


def version_parts(version: str) -> tuple | None:
    parsed = minecraft_release_from_id(version) or (version or "").strip()
    bits: list[int] = []
    for part in parsed.split("."):
        if not part.isdigit():
            return None
        bits.append(int(part))
    if len(bits) < 2:
        return None
    return tuple(bits)


def library_game_versions(game_version: str) -> list[str]:
    """Точный номер и соседние релизы той же линии. GeckoLib для 1.21 часто лежит только как 1.21.1."""
    found: list[str] = []
    for item in [game_version, *pack_version_attempts(game_version)]:
        item = (item or "").strip()
        if item and item not in found:
            found.append(item)
    return found[:6]


def pack_version_allowed(version: str) -> bool:
    parts = version_parts(version)
    if not parts:
        return False
    if parts[0] >= 20:
        return True
    if parts[0] != 1:
        return False
    minor = parts[1]
    patch = parts[2] if len(parts) > 2 else 0
    if minor > 19:
        return True
    if minor < 19:
        return False
    if len(parts) == 2:
        return False
    return patch >= 2


def pack_version_attempts(game_version: str) -> list[str]:
    """Точная версия и соседние релизы той же линии, не старше 1.19.2."""
    parsed = minecraft_release_from_id(game_version) or (game_version or "").strip()
    if not parsed or not pack_version_allowed(parsed):
        return []
    attempts = [parsed]
    key = _line_key(parsed)
    preferred = {
        ("1", "19"): ("1.19.2", "1.19.4"),
        ("1", "20"): ("1.20.1", "1.20.4", "1.20.6", "1.20"),
        ("1", "21"): ("1.21.1", "1.21.4", "1.21.8", "1.21.11", "1.21"),
        ("26", "1"): ("26.1",),
        ("26", "2"): ("26.2",),
        ("26", "3"): ("26.3",),
    }
    for item in preferred.get(key, ()):
        if item not in attempts and pack_version_allowed(item):
            attempts.append(item)
    for item in PACK_VERSIONS:
        if _line_key(item) == key and item not in attempts and pack_version_allowed(item):
            attempts.append(item)
    return attempts[:6]


def modrinth_search_slugs(search_text: str, loader: str, game_version: str | None, limit: int = 8) -> list[str]:
    query = (search_text or "").strip()
    if not query or not loader:
        return []
    facets = [["project_type:mod"], [f"categories:{loader}"]]
    if game_version:
        facets.append([f"versions:{game_version}"])
    try:
        search = http_json(
            "https://api.modrinth.com/v2/search?"
            + urllib.parse.urlencode({
                "query": query,
                "limit": limit,
                "index": "relevance",
                "facets": json.dumps(facets),
            })
        )
    except Exception:
        return []
    slugs: list[str] = []
    for hit in search.get("hits") or []:
        slug = str(hit.get("slug") or "")
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


_LOADER_IDS = frozenset({
    "forge", "neoforge", "fabric", "fabricloader", "quilt", "quiltloader", "javafml",
})
_LIBRARY_SLUGS = {
    "superbwarfare": "superb-warfare",
    "clothconfig": "cloth-config",
    "architectury": "architectury-api",
}
_PROJECT_CACHE: dict[str, dict | None] = {}
_SLUG_CACHE: dict[str, str | None] = {}
_VERS_CACHE: dict[str, list] = {}
_REQ_CACHE: dict[str, tuple] = {}
_LIB_CACHE: dict[tuple, dict | None] = {}


def _compact_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _provided_ids(loader: str) -> set[str]:
    ids = {"minecraft", "java", "javafml"}
    if loader == "forge":
        ids.add("forge")
    elif loader == "neoforge":
        ids.add("neoforge")
    elif loader == "fabric":
        ids.update({"fabric", "fabricloader", "fabric-resource-loader-v0"})
    elif loader == "quilt":
        ids.update({
            "quilt", "quiltloader", "quilt_resource_loader", "fabric", "fabricloader",
            "fabric-resource-loader-v0",
        })
    return {_compact_id(item) for item in ids}


def version_key(value: str) -> tuple:
    raw = (value or "").strip().lower().split("+", 1)[0]
    match = re.search(r"\d+(?:\.\d+){0,6}", raw)
    if not match:
        return ((0, 0, 0, 0, 0, 0), 1)
    nums = [int(part) for part in match.group(0).split(".")]
    while len(nums) < 6:
        nums.append(0)
    rest = raw[match.end():]
    pre = 0 if rest.startswith("-") and not rest.startswith("-final") else 1
    return (tuple(nums[:6]), pre)


def _cmp_versions(left: str, right: str) -> int:
    a = version_key(left)
    b = version_key(right)
    if a[0] != b[0]:
        return -1 if a[0] < b[0] else 1
    if a[1] != b[1]:
        return -1 if a[1] < b[1] else 1
    return 0


def range_allows(spec: str, version: str) -> bool:
    text = (spec or "").strip()
    if not text or text in {"*", "any"} or "${" in text:
        return True
    if "||" in text:
        return any(range_allows(part.strip(), version) for part in text.split("||") if part.strip())
    if text[0] in "[(":
        return any(_maven_range(part, version) for part in _split_maven_ranges(text))
    return all(_fabric_clause(part, version) for part in text.split() if part)


def _split_maven_ranges(text: str) -> list[str]:
    ranges: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in text:
        if char in "[(":
            depth += 1
        elif char in "])":
            depth = max(0, depth - 1)
        buf.append(char)
        if depth == 0 and buf:
            piece = "".join(buf).strip().strip(",")
            if piece:
                ranges.append(piece)
            buf = []
    tail = "".join(buf).strip().strip(",")
    if tail:
        ranges.append(tail)
    return ranges or [text]


def _maven_range(text: str, version: str) -> bool:
    match = re.match(r"^([\[\(])\s*([^,\]\)]*)\s*,\s*([^,\]\)]*)\s*([\]\)])$", text.strip())
    if not match:
        inner = text.strip()
        if inner and inner[0] in "[(" and inner[-1] in "])" and "," not in inner:
            return _cmp_versions(version, inner[1:-1].strip()) == 0
        return True
    low = match.group(2).strip()
    high = match.group(3).strip()
    if low:
        compared = _cmp_versions(version, low)
        if compared < 0 or (compared == 0 and match.group(1) != "["):
            return False
    if high:
        compared = _cmp_versions(version, high)
        if compared > 0 or (compared == 0 and match.group(4) != "]"):
            return False
    return True


def _fabric_clause(clause: str, version: str) -> bool:
    text = clause.strip()
    if not text or text == "*":
        return True
    for op in (">=", "<=", ">", "<", "="):
        if text.startswith(op):
            other = text[len(op):].strip()
            compared = _cmp_versions(version, other)
            if op == ">=":
                return compared >= 0
            if op == "<=":
                return compared <= 0
            if op == ">":
                return compared > 0
            if op == "<":
                return compared < 0
            return compared == 0
    if text[:1] in "~^" or text.endswith((".x", ".*")):
        base = text[1:] if text[:1] in "~^" else text.rsplit(".", 1)[0]
        if _cmp_versions(version, base) < 0:
            return False
        parts = [int(part) for part in re.findall(r"\d+", base)[:3]] or [0]
        if text.startswith("^") and parts[0] > 0:
            ceiling = f"{parts[0] + 1}"
        else:
            if len(parts) >= 2:
                ceiling = f"{parts[0]}.{parts[1] + 1}"
            else:
                ceiling = f"{parts[0] + 1}"
        return _cmp_versions(version, ceiling) < 0
    return _cmp_versions(version, text) == 0


def _spec_ok(spec: str, version: str) -> bool:
    if not version or "${" in version or version.startswith("$"):
        return True
    return range_allows(spec, version)


def _strip_toml_comment(line: str) -> str:
    out: list[str] = []
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            out.append(char)
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in ("'", '"') and line[index:index + 3] == char * 3:
            end = line.find(char * 3, index + 3)
            if end < 0:
                return line
            out.append(line[index:end + 3])
            index = end + 3
            continue
        if char in ("'", '"'):
            quote = char
            out.append(char)
            index += 1
            continue
        if char == "#":
            break
        out.append(char)
        index += 1
    return "".join(out)


def _logical_toml_lines(text: str) -> list[str]:
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    logical: list[str] = []
    index = 0
    while index < len(raw_lines):
        line = raw_lines[index]
        if line.count("'''") % 2 == 1 or line.count('"""') % 2 == 1:
            quote = "'''" if line.count("'''") % 2 == 1 else '"""'
            block = [line]
            index += 1
            while index < len(raw_lines) and quote not in raw_lines[index]:
                block.append(raw_lines[index])
                index += 1
            if index < len(raw_lines):
                block.append(raw_lines[index])
            logical.append("\n".join(block))
        else:
            logical.append(line)
        index += 1
    return logical


def _toml_value(raw: str) -> str:
    value = (raw or "").strip()
    if len(value) >= 6 and value.startswith("'''") and value.endswith("'''"):
        return value[3:-3]
    if len(value) >= 6 and value.startswith('"""') and value.endswith('"""'):
        return value[3:-3]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _add_required(deps: list[tuple[str, str]], mod_id, spec) -> None:
    name = str(mod_id or "").strip()
    if not name:
        return
    if isinstance(spec, list):
        spec = spec[0] if spec else "*"
    if isinstance(spec, dict):
        spec = spec.get("version") or spec.get("versions") or spec.get("versionRange") or "*"
    deps.append((name, str(spec or "*").strip() or "*"))


def _parse_mods_toml(text: str, own: dict[str, str], deps: list[tuple[str, str]]) -> None:
    section = ""
    mod_id = ""
    mod_ver = ""
    dep_id = ""
    dep_spec = "*"
    dep_ok = True

    def flush_mod() -> None:
        nonlocal mod_id, mod_ver
        if mod_id:
            own.setdefault(mod_id, mod_ver or "0")
        mod_id = ""
        mod_ver = ""

    def flush_dep() -> None:
        nonlocal dep_id, dep_spec, dep_ok
        if dep_id and dep_ok:
            deps.append((dep_id, dep_spec or "*"))
        dep_id = ""
        dep_spec = "*"
        dep_ok = True

    for raw in _logical_toml_lines(text):
        line = _strip_toml_comment(raw).strip()
        if not line:
            continue
        if line.startswith("[[") and line.endswith("]]"):
            flush_mod()
            flush_dep()
            section = line[2:-2].strip()
            continue
        if line.startswith("[") and line.endswith("]"):
            flush_mod()
            flush_dep()
            section = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = _toml_value(raw_value)
        if section == "mods":
            if key == "modId":
                mod_id = value
            elif key == "version":
                mod_ver = value
        elif section.startswith("dependencies"):
            if key == "modId":
                dep_id = value
            elif key in ("versionRange", "version"):
                dep_spec = value
            elif key == "mandatory":
                dep_ok = value.lower() == "true"
            elif key == "type":
                dep_ok = value.lower() in ("required", "mandatory")
    flush_mod()
    flush_dep()
    _parse_inline_mod_tables(text, own, deps)


def _skip_quoted(text: str, index: int) -> int:
    quote = text[index]
    if text[index:index + 3] == quote * 3:
        end = text.find(quote * 3, index + 3)
        return len(text) if end < 0 else end + 3
    index += 1
    while index < len(text) and text[index] != quote:
        if text[index] == "\\":
            index += 2
            continue
        index += 1
    return min(len(text), index + 1)


def _matching_brace(text: str, start: int) -> int:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            index = _skip_quoted(text, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _inline_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    size = len(body)
    while index < size:
        while index < size and body[index] in " \t\r\n,":
            index += 1
        if index >= size:
            break
        equals = body.find("=", index)
        if equals < 0:
            break
        key = body[index:equals].strip()
        index = equals + 1
        while index < size and body[index] in " \t":
            index += 1
        if index >= size or not key:
            break
        if body[index] in ("'", '"'):
            end = _skip_quoted(body, index)
            raw = body[index:end]
            fields[key] = _toml_value(raw)
            index = end
            continue
        end = index
        while end < size and body[end] not in ",\r\n":
            end += 1
        fields[key] = body[index:end].strip()
        index = end
    return fields


def _parse_inline_mod_tables(text: str, own: dict[str, str], deps: list[tuple[str, str]]) -> None:
    index = 0
    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            index = _skip_quoted(text, index)
            continue
        if char != "{":
            index += 1
            continue
        end = _matching_brace(text, index)
        if end < 0:
            break
        fields = _inline_fields(text[index + 1:end])
        index = end + 1
        mod_id = fields.get("modId") or ""
        if not mod_id:
            continue
        kind = (fields.get("type") or "").lower()
        if "versionRange" in fields or "mandatory" in fields or "ordering" in fields or kind in (
            "required", "optional", "incompatible", "discouraged", "mandatory"
        ):
            required = kind not in ("optional", "incompatible", "discouraged")
            if (fields.get("mandatory") or "").lower() == "false":
                required = False
            if required:
                deps.append((mod_id, fields.get("versionRange") or fields.get("version") or "*"))
            continue
        if "displayName" in fields or "logoFile" in fields or "authors" in fields or "version" in fields:
            own.setdefault(mod_id, fields.get("version") or "0")


def _consume_depends(depends, deps: list[tuple[str, str]]) -> None:
    if isinstance(depends, dict):
        for key, value in depends.items():
            required = True
            if isinstance(value, dict) and "mandatory" in value:
                required = bool(value.get("mandatory"))
            if isinstance(value, dict) and str(value.get("type") or "").lower() in (
                "optional", "incompatible", "discouraged"
            ):
                required = False
            if required:
                _add_required(deps, key, value)
        return
    if not isinstance(depends, list):
        return
    for item in depends:
        if isinstance(item, str):
            _add_required(deps, item, "*")
        elif isinstance(item, dict):
            required = str(item.get("type") or "required").lower() not in (
                "optional", "incompatible", "discouraged"
            )
            if "mandatory" in item:
                required = bool(item.get("mandatory"))
        if required and "unless" not in item:
            _add_required(
                deps,
                item.get("id") or item.get("modId") or item.get("modid"),
                item.get("version") or item.get("versions") or item.get("versionRange") or "*",
            )


def _parse_json_meta(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _parse_fabric_meta(text: str, own: dict[str, str], deps: list[tuple[str, str]]) -> None:
    data = _parse_json_meta(text)
    if not data:
        return
    mod_id = str(data.get("id") or "").strip()
    if mod_id:
        own.setdefault(mod_id, str(data.get("version") or ""))
    _consume_depends(data.get("depends"), deps)


def _parse_quilt_meta(text: str, own: dict[str, str], deps: list[tuple[str, str]]) -> None:
    data = _parse_json_meta(text)
    loader = data.get("quilt_loader") if data else None
    if not isinstance(loader, dict):
        return
    mod_id = str(loader.get("id") or "").strip()
    if mod_id:
        own.setdefault(mod_id, str(loader.get("version") or ""))
    _consume_depends(loader.get("depends"), deps)


def _dedupe_deps(deps: list[tuple[str, str]], own: dict[str, str]) -> list[tuple[str, str]]:
    own_ids = {_compact_id(item) for item in own}
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for mod_id, spec in deps:
        cid = _compact_id(mod_id)
        if not cid or cid in seen or cid in own_ids:
            continue
        seen.add(cid)
        result.append((mod_id, spec))
    return result


def read_jar_requirements(
    data: bytes, depth: int = 0, loader: str = ""
) -> tuple[dict[str, str], list[tuple[str, str]], set[str]]:
    """Свои id мода, обязательные зависимости и id из вложенных jar."""
    import io
    import zipfile

    forge_own: dict[str, str] = {}
    forge_deps: list[tuple[str, str]] = []
    fabric_own: dict[str, str] = {}
    fabric_deps: list[tuple[str, str]] = []
    embedded: set[str] = set()
    if not data or depth > 2:
        return {}, [], embedded
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        return {}, [], embedded
    names = set(archive.namelist())

    def load(path: str) -> str:
        try:
            return archive.read(path).decode("utf-8", errors="replace")
        except Exception:
            return ""

    if "fabric.mod.json" in names:
        _parse_fabric_meta(load("fabric.mod.json"), fabric_own, fabric_deps)
    if "quilt.mod.json" in names:
        _parse_quilt_meta(load("quilt.mod.json"), fabric_own, fabric_deps)
    toml_name = ""
    if loader == "neoforge" and "META-INF/neoforge.mods.toml" in names:
        toml_name = "META-INF/neoforge.mods.toml"
    elif "META-INF/mods.toml" in names:
        toml_name = "META-INF/mods.toml"
    elif "META-INF/neoforge.mods.toml" in names:
        toml_name = "META-INF/neoforge.mods.toml"
    if toml_name:
        _parse_mods_toml(load(toml_name), forge_own, forge_deps)
    if depth < 2:
        for name in archive.namelist():
            low = name.lower()
            if not low.endswith(".jar"):
                continue
            if not (low.startswith("meta-inf/jarjar/") or low.startswith("meta-inf/jars/")):
                continue
            try:
                nested = archive.read(name)
            except Exception:
                continue
            nested_own, _, nested_embedded = read_jar_requirements(nested, depth + 1, loader)
            embedded.update(nested_own)
            embedded.update(nested_embedded)
    # Forge не читает fabric.mod.json. У датапаков Modrinth там чужие зависимости.
    if loader in ("forge", "neoforge") and toml_name:
        own, deps = forge_own, forge_deps
    elif loader in ("fabric", "quilt") and (fabric_own or "fabric.mod.json" in names or "quilt.mod.json" in names):
        own, deps = fabric_own, fabric_deps
    else:
        own = dict(forge_own)
        for key, value in fabric_own.items():
            own.setdefault(key, value)
        deps = forge_deps + fabric_deps
    return own, _dedupe_deps(deps, own), embedded


def _slug_candidates(mod_id: str) -> list[str]:
    raw = (mod_id or "").strip().lower().replace("_", "-")
    compact = _compact_id(raw)
    found: list[str] = []

    def add(value: str) -> None:
        value = (value or "").strip("-").lower()
        if value and value not in found:
            found.append(value)

    add(raw)
    add(compact)
    size = len(compact)
    if size >= 6:
        splits = sorted(range(3, size - 2), key=lambda index: (abs(index - size / 2), index))
        for index in splits[:5]:
            add(compact[:index] + "-" + compact[index:])
    for token in ("lib", "api"):
        index = compact.find(token)
        if 2 < index < size - 1:
            add(compact[:index] + "-" + compact[index:])
    return found[:8]


def _library_queries(mod_id: str) -> list[str]:
    queries: list[str] = []
    for slug in _slug_candidates(mod_id):
        if "-" not in slug:
            continue
        query = re.sub(r"\s+", " ", slug.replace("-", " ")).strip()
        if query and query not in queries:
            queries.append(query)
    return queries[:4]


def _project_meta(slug: str) -> dict | None:
    if slug in _PROJECT_CACHE:
        return _PROJECT_CACHE[slug]
    try:
        data = http_json(f"https://api.modrinth.com/v2/project/{urllib.parse.quote(slug)}")
    except Exception:
        data = None
    if not isinstance(data, dict) or str(data.get("project_type") or "mod") != "mod":
        data = None
    _PROJECT_CACHE[slug] = data
    return data


def _project_matches(meta: dict, mod_id: str) -> bool:
    wanted = _compact_id(mod_id)
    if len(wanted) < 3 or not meta:
        return False
    return wanted in {_compact_id(str(meta.get("slug") or "")), _compact_id(str(meta.get("title") or ""))}


def find_library_slug(mod_id: str, loader: str, game_version: str) -> str | None:
    compact = _compact_id(mod_id)
    if compact in _SLUG_CACHE:
        return _SLUG_CACHE[compact]
    found = ""
    alias = _LIBRARY_SLUGS.get(compact)
    if alias:
        meta = _project_meta(alias)
        if meta and _project_matches(meta, mod_id):
            found = str(meta.get("slug") or alias)
    if not found:
        for candidate in _slug_candidates(mod_id):
            meta = _project_meta(candidate)
            if meta and _project_matches(meta, mod_id):
                found = str(meta.get("slug") or candidate)
                break
    if not found:
        for query in _library_queries(mod_id):
            for slug in modrinth_search_slugs(query, loader, game_version, limit=6):
                meta = _project_meta(slug)
                if meta and _project_matches(meta, mod_id):
                    found = str(meta.get("slug") or slug)
                    break
            if found:
                break
    if not found:
        for query in _library_queries(mod_id):
            for slug in modrinth_search_slugs(query, loader, None, limit=6):
                meta = _project_meta(slug)
                if meta and _project_matches(meta, mod_id):
                    found = str(meta.get("slug") or slug)
                    break
            if found:
                break
    _SLUG_CACHE[compact] = found or None
    return found or None


def _project_versions(slug: str, loader: str) -> list:
    key = f"{slug}|{loader}"
    if key in _VERS_CACHE:
        return _VERS_CACHE[key]
    try:
        data = http_json(
            f"https://api.modrinth.com/v2/project/{urllib.parse.quote(slug)}/version?"
            + urllib.parse.urlencode({"loaders": json.dumps([loader])})
        )
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    _VERS_CACHE[key] = data
    return data


def _library_file(slug: str, loader: str, game_version: str, spec: str) -> dict | None:
    meta = _project_meta(slug) or {}
    allowed = library_game_versions(game_version)
    ranked: list[tuple] = []
    for version in _project_versions(slug, loader):
        if not isinstance(version, dict):
            continue
        games = {str(item) for item in version.get("game_versions") or []}
        overlap = [item for item in allowed if item in games]
        if not overlap:
            continue
        number = str(version.get("version_number") or "")
        if number and not range_allows(spec, number):
            continue
        picked = _pick_mod_file(version, allow_zip=False)
        if not picked:
            continue
        closeness = min(allowed.index(item) for item in overlap)
        release = 0 if version.get("version_type") == "release" else 1
        key = version_key(number)
        ranked.append((closeness, release, tuple(-part for part in key[0]), -key[1], picked, number))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[:4])
    picked, number = ranked[0][4], ranked[0][5]
    return {
        "slug": str(meta.get("slug") or slug),
        "title": str(meta.get("title") or slug),
        "filename": picked["filename"],
        "url": picked["url"],
        "sha1": picked.get("sha1") or "",
        "sha512": picked.get("sha512") or "",
        "folder": "mods",
        "deps": [],
        "blurb": "Библиотека, без неё мод не запустится.",
        "source": "Modrinth",
        "library": True,
        "version_number": number,
    }


def _inspect_cached(mod: dict, loader: str = "") -> tuple[dict[str, str], list[tuple[str, str]], set[str]] | None:
    url = str(mod.get("url") or "")
    if not url:
        return None
    key = url + "\n" + loader
    if key in _REQ_CACHE:
        return _REQ_CACHE[key]
    try:
        parsed = read_jar_requirements(http_bytes(url), loader=loader)
    except Exception:
        return None
    _REQ_CACHE[key] = parsed
    return parsed


def _public_mod(info: dict) -> dict:
    return {key: value for key, value in info.items() if not str(key).startswith("_")}


def resolve_library(mod_id: str, spec: str, loader: str, game_version: str) -> dict | None:
    key = (_compact_id(mod_id), spec or "", loader, game_version)
    if key in _LIB_CACHE:
        cached = _LIB_CACHE[key]
        return dict(cached) if cached else None
    found: dict | None = None
    slug = find_library_slug(mod_id, loader, game_version)
    if slug:
        info = _library_file(slug, loader, game_version, spec)
        parsed = _inspect_cached(info, loader) if info else None
        if info and parsed:
            own, _, _embedded = parsed
            if _compact_id(mod_id) in {_compact_id(item) for item in own}:
                info["version_number"] = str(info.get("version_number") or next(iter(own.values()), ""))
                found = info
    _LIB_CACHE[key] = dict(found) if found else None
    return dict(found) if found else None


def _own_version(info: dict, cid: str) -> str:
    for mod_id, version in (info.get("_own") or {}).items():
        if _compact_id(mod_id) == cid:
            return str(version or "")
    return ""


def _decorate(mod: dict, loader: str = "") -> dict:
    info = dict(mod)
    parsed = _inspect_cached(mod, loader)
    if not parsed:
        info["_unreadable"] = True
        info["_own"] = {}
        info["_deps"] = []
        info["_ids"] = set()
        return info
    own, deps, embedded = parsed
    info["_own"] = own
    info["_deps"] = deps
    info["_ids"] = {_compact_id(item) for item in own} | {_compact_id(item) for item in embedded}
    return info


def close_libraries(mods: list[dict], loader: str, game_version: str) -> tuple[list[dict], list[str]]:
    """Скачивает библиотеки из jar. Мод без файла библиотеки на эту версию выкидывает."""
    provided = _provided_ids(loader)
    shaders = [dict(item) for item in mods if item.get("folder") == "shaderpacks"]
    parsed = [_decorate(item, loader) for item in mods if item.get("folder") != "shaderpacks"]
    libraries: dict[str, dict] = {}
    failed: set[str] = set()

    def version_present(cid: str) -> str:
        for info in parsed:
            found = _own_version(info, cid)
            if found:
                return found
        lib = libraries.get(cid)
        if lib:
            return str(lib.get("version_number") or _own_version(lib, cid) or "")
        return ""

    for _wave in range(8):
        grew = False
        pool = parsed + list({id(item): item for item in libraries.values()}.values())
        for info in pool:
            if info.get("_unreadable"):
                continue
            for dep_id, spec in info.get("_deps") or []:
                cid = _compact_id(dep_id)
                if len(cid) < 3 or cid in failed or cid in provided:
                    continue
                if cid in _LOADER_IDS and cid not in provided:
                    failed.add(cid)
                    continue
                current = version_present(cid)
                if current and _spec_ok(spec, current):
                    continue
                if cid in libraries and _spec_ok(spec, str(libraries[cid].get("version_number") or "")):
                    continue
                lib = resolve_library(dep_id, spec, loader, game_version)
                if not lib or not _spec_ok(spec, str(lib.get("version_number") or "")):
                    failed.add(cid)
                    continue
                decorated = _decorate(lib, loader)
                decorated["library"] = True
                decorated["blurb"] = "Библиотека, без неё мод не запустится."
                decorated["version_number"] = lib.get("version_number") or ""
                for key_id in decorated.get("_ids") or []:
                    libraries[key_id] = decorated
                grew = True
        if not grew:
            break

    dropped: list[str] = []
    changed = True
    while changed:
        changed = False

        def satisfied(dep_id: str, spec: str, info: dict) -> bool:
            cid = _compact_id(dep_id)
            if cid in provided or cid in (info.get("_ids") or ()):
                return True
            lib = libraries.get(cid)
            if lib and _spec_ok(spec, str(lib.get("version_number") or _own_version(lib, cid))):
                return True
            for other in parsed:
                version = _own_version(other, cid)
                if version and _spec_ok(spec, version):
                    return True
                if cid in (other.get("_ids") or ()) and (not version or _spec_ok(spec, version)):
                    return True
            return False

        next_parsed = []
        for info in parsed:
            if info.get("_unreadable"):
                next_parsed.append(info)
                continue
            missing = [dep_id for dep_id, spec in info.get("_deps") or [] if not satisfied(dep_id, spec, info)]
            if missing:
                dropped.append(str(info.get("title") or info.get("slug") or "мод"))
                changed = True
            else:
                next_parsed.append(info)
        parsed = next_parsed
        needed: set[str] = set()
        stack = [
            _compact_id(dep_id)
            for info in parsed
            for dep_id, _spec in info.get("_deps") or []
        ]
        while stack:
            cid = stack.pop()
            lib = libraries.get(cid)
            if not lib or cid in needed:
                continue
            needed.update(lib.get("_ids") or ())
            needed.add(cid)
            stack.extend(_compact_id(dep_id) for dep_id, _spec in lib.get("_deps") or [])
        for cid in list(libraries):
            if cid not in needed:
                libraries.pop(cid, None)
                changed = True

    unique_libs: list[dict] = []
    seen: set[str] = set()
    for info in libraries.values():
        slug = str(info.get("slug") or info.get("filename") or "")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        unique_libs.append(_public_mod(info))
    result = [_public_mod(info) for info in parsed] + unique_libs + shaders
    return result, dropped


def infer_loader(version_id: str) -> str:
    value = (version_id or "").lower()
    if "neoforge" in value:
        return "neoforge"
    if "quilt" in value:
        return "quilt"
    if "fabric" in value:
        return "fabric"
    if "forge" in value:
        return "forge"
    return ""


def _write_library(folder: str, lib: dict) -> str:
    filename = safe_filename(str(lib.get("filename") or ""))
    if not filename:
        raise ValueError("Пустое имя библиотеки.")
    dest = os.path.join(folder, filename)
    if os.path.isfile(dest):
        return dest
    url = str(lib.get("url") or "")
    data = _JAR_CACHE.get(url)
    temporary = dest + ".part"
    if data:
        with open(temporary, "wb") as handle:
            handle.write(data)
        os.replace(temporary, dest)
        verify_mod_file(dest, lib)
        return dest
    http_download(url, dest)
    verify_mod_file(dest, lib)
    return dest


def finish_mod_folder(directory: str, loader: str, game_version: str, status=None) -> str:
    """Докачивает библиотеки уже установленных модов и отключает те, которым их нет."""
    if loader not in ("forge", "neoforge", "fabric", "quilt") or not game_version:
        return ""
    folder = os.path.join(directory, "mods")
    if not os.path.isdir(folder):
        return ""
    entries: list[dict] = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".jar"):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, "rb") as handle:
                data = handle.read(_LIBRARY_JAR_LIMIT + 1)
        except OSError:
            continue
        if len(data) > _LIBRARY_JAR_LIMIT:
            continue
        own, deps, embedded = read_jar_requirements(data, loader=loader)
        entries.append({
            "path": path,
            "name": name,
            "own": own,
            "deps": deps,
            "ids": {_compact_id(item) for item in own} | {_compact_id(item) for item in embedded},
        })
    if not entries:
        return ""
    provided = _provided_ids(loader)
    added: list[str] = []
    failed: set[str] = set()

    def provides(dep_id: str, spec: str, pool: list[dict] | None = None) -> bool:
        cid = _compact_id(dep_id)
        if cid in provided:
            return True
        for entry in entries if pool is None else pool:
            for mod_id, version in entry["own"].items():
                if _compact_id(mod_id) == cid and _spec_ok(spec, str(version or "")):
                    return True
            if cid in entry["ids"] and not any(_compact_id(mod_id) == cid for mod_id in entry["own"]):
                return True
        return False

    for _wave in range(6):
        grew = False
        for entry in list(entries):
            for dep_id, spec in entry["deps"]:
                cid = _compact_id(dep_id)
                if len(cid) < 3 or cid in failed or provides(dep_id, spec):
                    continue
                if cid in _LOADER_IDS and cid not in provided:
                    failed.add(cid)
                    continue
                if status:
                    status(f"Ищу библиотеку {dep_id}")
                lib = resolve_library(dep_id, spec, loader, game_version)
                if not lib:
                    failed.add(cid)
                    continue
                try:
                    dest = _write_library(folder, lib)
                    with open(dest, "rb") as handle:
                        blob = handle.read(_LIBRARY_JAR_LIMIT + 1)
                    own, deps, embedded = read_jar_requirements(blob, loader=loader)
                except Exception:
                    failed.add(cid)
                    continue
                if _compact_id(dep_id) not in {_compact_id(item) for item in own}:
                    failed.add(cid)
                    continue
                entries.append({
                    "path": dest,
                    "name": os.path.basename(dest),
                    "own": own,
                    "deps": deps,
                    "ids": {_compact_id(item) for item in own} | {_compact_id(item) for item in embedded},
                })
                title = str(lib.get("title") or dep_id)
                if title not in added:
                    added.append(title)
                grew = True
        if not grew:
            break

    disabled: list[str] = []
    changed = True
    alive = entries
    while changed:
        changed = False
        next_alive = []
        for entry in alive:
            missing = [dep_id for dep_id, spec in entry["deps"] if not provides(dep_id, spec, alive)]
            if not missing:
                next_alive.append(entry)
                continue
            dest = entry["path"] + ".disabled"
            try:
                os.replace(entry["path"], dest)
            except OSError:
                next_alive.append(entry)
                continue
            disabled.append(entry["name"])
            changed = True
        alive = next_alive
    notes: list[str] = []
    if added:
        notes.append("Добавил библиотеки: " + ", ".join(added[:8]) + ".")
    if disabled:
        notes.append(
            "Отключил моды без нужной библиотеки на этой версии: "
            + ", ".join(disabled[:8])
            + ". Файлы переименованы в .disabled, игра запустится без них."
        )
    return " ".join(notes)


def preset_from_text(text: str) -> dict | None:
    """Кнопка «Выживание» и фраза «собери выживание» — один и тот же набор, не случайный поиск."""
    low = (text or "").lower()
    order = (
        ("zombie", ("зомби", "zombie", "апокал", "нежить", "орда")),
        ("weapons", ("оруж", "weapon", "мушкет")),
        ("machines", ("механ", "физик", "криэйт", "create")),
        ("magic", ("маги", "magic", "ботан", "закл")),
        ("visual", ("визуал", "шейдер", "shader")),
        ("survival", ("выжив", "survival", "хардкор")),
    )
    for preset_id, words in order:
        if any(word in low for word in words):
            return next((pack for pack in PRESETS if pack["id"] == preset_id), None)
    return None


def _crash_blobs(directory: str, launcher_log: str) -> str:
    parts: list[str] = []
    paths = [os.path.join(directory, "logs", "latest.log")]
    crash_dir = os.path.join(directory, "crash-reports")
    if os.path.isdir(crash_dir):
        reports = [
            os.path.join(crash_dir, name)
            for name in os.listdir(crash_dir)
            if name.endswith(".txt")
        ]
        reports.sort(key=lambda path: os.path.getmtime(path) if os.path.isfile(path) else 0, reverse=True)
        paths.extend(reports[:1])
    if launcher_log:
        paths.append(launcher_log)
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - 80_000))
                parts.append(handle.read())
        except OSError:
            continue
    return "\n".join(parts)


def _crash_reason(text: str) -> str:
    low = text.lower()
    if "unsupportedclassversionerror" in low or "more recent version of the java runtime" in low:
        return (
            "Java слишком старая для этой игры. Во вкладке «Установка» выбери Java 21, "
            "для номеров 26.x — Java 25, и скачай её."
        )
    if any(mark in low for mark in ("glfw", "service port", "nsinternalinconsistency", "only be used on the main thread")):
        return "macOS закрыла окно игры до меню. Нажми «Играть» ещё раз: теперь она стартует отдельным приложением, не из окна лаунчера."
    if "incompatible architecture" in low or "have 'x86_64'" in low or 'have "x86_64"' in low or "not a mach-o" in low:
        return "Библиотека была не под этот Mac. Нажми «Играть» ещё раз: лаунчер оставит natives только нужной архитектуры."
    if "library load disallowed" in low or "code signature" in low or "killed: 9" in low or "process exit -9" in low or "process exit 137" in low:
        return "macOS заблокировала Java или библиотеки. Нажми «Играть» ещё раз: карантин с них уже снимается."
    for line in text.splitlines():
        low_line = line.lower()
        if "requires" in low_line and ("mod" in low_line or "мод" in low_line):
            return "Мод не нашёл библиотеку: " + line.strip()[-220:]
        stripped = line.strip()
        if stripped.lower().startswith("failure message:"):
            return stripped.split(":", 1)[1].strip()[:240]
    caused = [line.strip() for line in text.splitlines() if line.strip().startswith("Caused by:")]
    if caused:
        return caused[-1][:240]
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("at ") or stripped.startswith("---"):
            continue
        if any(mark in stripped.lower() for mark in ("error", "exception", "fatal", "dyld", "abort", "cannot")):
            return "Игра упала при запуске, до меню не дошла. " + stripped[:180]
    return "Игра упала при запуске, до меню не дошла."


def startup_failure(directory: str, launcher_log: str = "") -> tuple[str, list[str]]:
    """Коротко говорит, почему игра сразу закрылась, и выключает мод из строк ошибки."""
    text = _crash_blobs(directory, launcher_log)
    if not text.strip():
        return "Minecraft закрылся сразу после старта. Лог игры ещё пустой.", []
    low = text.lower()
    if "unsupportedclassversionerror" in low or "more recent version of the java runtime" in low:
        return _crash_reason(text), []
    reason = _crash_reason(text)
    interesting = [
        line for line in text.splitlines()
        if any(mark in line.lower() for mark in (
            "error", "fatal", "exception", "missing", "requires", "failed", "crash", "mixin",
        ))
    ]
    blob = "\n".join(interesting[-80:])
    compact_blob = _compact_id(blob)
    skip_words = {
        "exception", "missing", "runtime", "version", "loader", "mixin", "failed", "caused",
        "error", "fatal", "minecraft", "javafml", "required", "modid", "thread", "system",
    }
    tokens: set[str] = set()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{5,}", blob):
        token = _compact_id(word)
        if len(token) >= 6 and token not in skip_words:
            tokens.add(token)
    mods_dir = os.path.join(directory, "mods")
    disabled: list[str] = []
    if os.path.isdir(mods_dir) and tokens:
        for name in sorted(os.listdir(mods_dir)):
            if not name.lower().endswith(".jar") or len(disabled) >= 4:
                continue
            stem = _compact_id(os.path.splitext(name)[0])
            if len(stem) < 6:
                continue
            if not any(token in stem or stem in token for token in tokens):
                continue
            if stem not in compact_blob and not any(token in stem for token in tokens):
                continue
            dest = os.path.join(mods_dir, name + ".disabled")
            try:
                os.replace(os.path.join(mods_dir, name), dest)
            except OSError:
                continue
            disabled.append(name)
    if disabled:
        return (
            f"{reason} Отключил моды из лога ошибки: {', '.join(disabled)}. Нажми «Играть» ещё раз.",
            disabled,
        )
    return reason, []


def build_pack(
    query: str,
    loader: str,
    game_version: str,
    preset_id: str = "",
    sources: tuple[str, ...] = ("modrinth", "curseforge"),
    free_search: bool = False,
) -> dict:
    text = (query or "").strip()
    low = text.lower()
    mod_loader = "forge" if loader == "optifine" else loader
    if mod_loader not in ("fabric", "forge", "neoforge", "quilt"):
        mod_loader = "fabric"
    preset = next((pack for pack in PRESETS if pack["id"] == preset_id), None)
    if preset is None and not free_search:
        preset = preset_from_text(text)
    if not pack_version_allowed(game_version):
        raise RuntimeError(
            "Сборки модов ставятся с 1.19.2 и новее, на любой номер: 1.19.2, 1.20.1, 1.21, 1.21.8, 26.3. "
            "Более старую игру можно скачать, но моды для неё лаунчер не собирает."
        )
    attempts = pack_version_attempts(game_version)
    asked_version = game_version
    asked_loader = mod_loader
    search_queries = query_variants(text)
    search_text = " ".join(search_queries)
    matched = [] if preset else [pack for pack in CURATED if any(word in low for word in pack["words"])]
    if not preset and not matched and not search_queries:
        raise RuntimeError(
            "Не разобрал тему. Напиши проще: животные, военная, магия, данжи, динозавры, корабли, оптимизация. "
            "Можно и английское название мода."
        )
    titles = [preset["title"]] if preset else [pack["title"] for pack in matched]
    summaries = [preset["summary"]] if preset else [pack["summary"] for pack in matched]
    if not titles:
        shown = text[:48] or "Подбор"
        titles.append(shown)
        summaries.append(f"По запросу «{text or search_text}» взял моды с Modrinth, а если их там нет — с CurseForge.")
    loader_order = [mod_loader]
    parts = version_parts(game_version) or ()
    fresh_line = bool(parts) and (parts[0] >= 20 or (parts[0] == 1 and parts[1] >= 21))
    if mod_loader == "forge" and fresh_line:
        loader_order.append("neoforge")

    def slugs_for(active_loader: str, active_version: str) -> tuple[list[str], list[str]]:
        found: list[str] = []
        shader_slugs: list[str] = []
        seen: set[str] = set()

        def add(slug: str, shader: bool = False) -> None:
            if not slug or slug in seen:
                return
            seen.add(slug)
            if shader:
                shader_slugs.append(slug)
            else:
                found.append(slug)

        source = preset if preset else None
        packs = [source] if source else matched
        for pack in packs:
            if not pack:
                continue
            for slug in pack.get("mods", {}).get(active_loader, ()):
                add(slug)
            for slug in pack.get("shaders", ()):
                add(slug, True)
        if preset or "modrinth" not in sources:
            return found, shader_slugs
        for query in search_queries:
            if len(found) >= 8:
                break
            for slug in modrinth_search_slugs(query, active_loader, active_version, limit=5):
                add(slug)
                if len(found) >= 8:
                    break
        return found, shader_slugs

    def gather(active_loader: str, active_version: str, found: list[str], shader_slugs: list[str]) -> tuple[list[dict], list[str]]:
        queue: list[tuple[str, bool, bool]] = (
            [(slug, False, False) for slug in found] + [(slug, True, False) for slug in shader_slugs]
        )
        seen: set[str] = set()
        mods_found: list[dict] = []
        missed: list[str] = []
        limit = 16 if preset else 10
        while queue and len(mods_found) < limit + 12:
            slug, shader, from_dep = queue.pop(0)
            if slug in seen:
                continue
            seen.add(slug)
            content_count = sum(
                1 for item in mods_found if not item.get("from_dep") and item.get("folder") != "shaderpacks"
            )
            if not shader and not from_dep and content_count >= limit:
                continue
            try:
                info = resolve_project(slug, active_loader, active_version, shader=shader, sources=sources)
            except Exception:
                missed.append(slug)
                continue
            if not info:
                missed.append(slug)
                continue
            if any(item["slug"] == info["slug"] for item in mods_found):
                continue
            seen.add(info["slug"])
            if from_dep:
                info["from_dep"] = True
            mods_found.append(info)
            if not shader:
                for dep in info.get("deps") or []:
                    if dep.get("dependency_type") != "required":
                        continue
                    project_id = str(dep.get("project_id") or "")
                    if project_id and project_id not in seen and len(queue) < 24:
                        queue.append((project_id, False, True))
        return mods_found, missed

    best: tuple | None = None
    saw_mods = False

    def finish_candidate(active_loader: str, active: str, gathered: list[dict], skipped_now: list[str]) -> bool:
        nonlocal best, saw_mods
        if not gathered:
            return False
        saw_mods = True
        try:
            closed, dropped = close_libraries(gathered, active_loader, active)
        except Exception:
            closed, dropped = gathered, []
        content_left = [
            item for item in closed if not item.get("library") and item.get("folder") != "shaderpacks"
        ]
        if not content_left and not any(item.get("folder") == "shaderpacks" for item in closed):
            return False
        score = (
            len(content_left),
            1 if not dropped else 0,
            -len(dropped),
            1 if active == asked_version else 0,
            1 if active_loader == asked_loader else 0,
        )
        if best is None or score > best[0]:
            best = (score, active_loader, active, closed, skipped_now, dropped)
        return True

    def consider(active_loader: str, active: str) -> bool:
        found, shader_slugs = slugs_for(active_loader, active)
        if not found and not shader_slugs:
            return False
        gathered, skipped_now = gather(active_loader, active, found, shader_slugs)
        return finish_candidate(active_loader, active, gathered, skipped_now)

    if preset:
        pools: list[tuple] = []
        scan = [(asked_loader, active) for active in attempts[:4]]
        for active_loader, active in scan:
            found, shader_slugs = slugs_for(active_loader, active)
            if not found and not shader_slugs:
                continue
            gathered, skipped_now = gather(active_loader, active, found, shader_slugs)
            count = sum(1 for item in gathered if item.get("folder") != "shaderpacks")
            if count:
                pools.append((count, active_loader, active, gathered, skipped_now))
        if pools:
            same = [item for item in pools if item[1] == asked_loader]
            pool = same or pools
            pool.sort(
                key=lambda item: (
                    item[0],
                    1 if item[2] == asked_version else 0,
                ),
                reverse=True,
            )
            asked_pool = next((item for item in pool if item[2] == asked_version), None)
            top = pool[0]
            if asked_pool and asked_pool[0] >= top[0]:
                chosen = [asked_pool]
            else:
                chosen = [top]
                if asked_pool and asked_pool not in chosen:
                    chosen.append(asked_pool)
            for count, active_loader, active, gathered, skipped_now in chosen:
                del count
                finish_candidate(active_loader, active, gathered, skipped_now)
        if best is None and len(loader_order) > 1:
            for active in attempts[:2]:
                consider(loader_order[1], active)
    elif not consider(asked_loader, asked_version):
        checked = 0
        for active_loader in loader_order:
            if best is not None and best[0][1] == 1 and best[0][0] > 0:
                break
            for active in attempts:
                if active_loader == asked_loader and active == asked_version:
                    continue
                if checked >= 3:
                    break
                checked += 1
                consider(active_loader, active)
                if best is not None and best[0][1] == 1:
                    break
    if best is None:
        if saw_mods:
            raise RuntimeError(
                f"Моды нашлись, но нужных библиотек нет для {asked_loader} {asked_version}. "
                "Попробуй другую версию той же линии, например 1.21.1, или другой загрузчик."
            )
        raise RuntimeError(
            f"По запросу на {asked_version} ({asked_loader}) ничего не нашлось с 1.19.2 и новее. "
            "Напиши иначе или выбери Fabric, NeoForge, 1.20.1 или 1.21.1."
        )
    _score, mod_loader, game_version, mods, skipped, dropped = best
    names = ", ".join(item["title"] for item in mods[:16])
    extra = ""
    if loader == "optifine":
        extra = " OptiFine моды почти не грузит, поэтому набор под Forge."
    if mod_loader != asked_loader or game_version != asked_version:
        extra += (
            f" На {asked_version} ({asked_loader}) готовых модов мало, "
            f"поэтому собрал {game_version} ({mod_loader})."
        )
    libs = [item["title"] for item in mods if item.get("library")]
    if libs:
        extra += " Библиотеки, без которых моды не запустятся: " + ", ".join(libs[:10]) + "."
    if dropped:
        extra += " Не ставлю, библиотеки не выложены на эту версию: " + ", ".join(dropped[:8]) + "."
    if skipped:
        extra += " Часть модов не нашлась именно на этой версии и пропущена."
    labels = [name for key, name in (("modrinth", "Modrinth"), ("curseforge", "CurseForge")) if key in sources]
    where = " и ".join(labels) or "Modrinth"
    return {
        "title": " + ".join(titles),
        "summary": f"{' '.join(summaries)}{extra} Версия {game_version}. Источники: {where}. Состав: {names}.",
        "loader": mod_loader,
        "game_version": game_version,
        "mods": mods,
    }


def optifine_builds(mc_version: str) -> list[dict]:
    payload = http_json(f"https://bmclapi2.bangbang93.com/optifine/{urllib.parse.quote(mc_version)}")
    if not isinstance(payload, list):
        return []

    def key(item: dict) -> tuple:
        patch = str(item.get("patch") or "")
        match = re.match(r"([A-Za-z]+)(\d+)", patch)
        if not match:
            return (patch, 0)
        return (match.group(1), int(match.group(2)))

    builds = [item for item in payload if isinstance(item, dict) and item.get("patch")]
    builds.sort(key=key)
    return builds


def launch_optifine_installer(mc_version: str, directory: str, java_path: str, status) -> str:
    builds = optifine_builds(mc_version)
    if not builds:
        raise RuntimeError(f"Для {mc_version} нет сборки OptiFine.")
    build = builds[-1]
    kind = str(build.get("type") or "HD_U")
    patch = str(build.get("patch"))
    filename = safe_filename(build.get("filename") or f"OptiFine_{mc_version}_{kind}_{patch}.jar")
    folder = os.path.join(directory, "ember-optifine")
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, filename)
    status(f"Качаю OptiFine {mc_version} {kind}_{patch}")
    http_download(
        f"https://bmclapi2.bangbang93.com/optifine/{urllib.parse.quote(mc_version)}/{urllib.parse.quote(kind)}/{urllib.parse.quote(patch)}",
        dest,
    )
    java = java_path or "java"
    status("Открываю установщик OptiFine")
    subprocess.Popen([java, "-jar", dest])
    return ""


def lerp_color(start: QColor, end: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, amount))
    return QColor(
        int(start.red() + (end.red() - start.red()) * amount),
        int(start.green() + (end.green() - start.green()) * amount),
        int(start.blue() + (end.blue() - start.blue()) * amount),
        int(start.alpha() + (end.alpha() - start.alpha()) * amount),
    )


def enable_windows_dark_title(hwnd: int) -> None:
    if os.name != "nt" or not hwnd:
        return
    try:
        import ctypes

        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        return


def fallback_icon(size: int = 128) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#101412"))
    radius = int(size * 0.23)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, radius, radius)
    cx = size / 2
    cy = size * 0.54
    s = float(size)
    top = QPointF(cx, cy - s * 0.24)
    right = QPointF(cx + s * 0.20, cy - 0.01 * s)
    left = QPointF(cx - s * 0.20, cy - 0.01 * s)
    bottom = QPointF(cx, cy + s * 0.26)
    mid = QPointF(cx, cy - 0.01 * s)
    painter.setBrush(QColor("#ffd6a4"))
    painter.drawPolygon(QPolygonF([top, right, mid]))
    painter.setBrush(QColor("#ffa440"))
    painter.drawPolygon(QPolygonF([top, mid, left]))
    painter.setBrush(QColor("#b03e12"))
    painter.drawPolygon(QPolygonF([left, mid, bottom]))
    painter.setBrush(QColor("#e27020"))
    painter.drawPolygon(QPolygonF([mid, right, bottom]))
    painter.end()
    return pixmap


def load_app_icon() -> QIcon:
    png = resource_path("icon.png")
    ico = resource_path("icon.ico")
    icon = QIcon()
    if os.path.isfile(png):
        icon.addFile(png)
    elif os.path.isfile(ico):
        icon.addFile(ico)
    else:
        icon.addPixmap(fallback_icon(64))
        icon.addPixmap(fallback_icon(256))
    return icon


_ORPHAN_THREADS: list[QThread] = []
