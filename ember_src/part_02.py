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


def open_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


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


def active_update_repo(config: dict | None = None) -> str:
    if config:
        saved = clean_repo(str(config.get("update_repo") or ""))
        if saved:
            return saved
    bundled = clean_repo(str(load_server().get("update_repo") or ""))
    if bundled:
        return bundled
    return DEFAULT_UPDATE_REPO


def release_filename() -> str:
    if os.name == "nt":
        return "EmberLauncher.exe"
    if sys.platform == "darwin":
        return "EmberLauncher-macOS.zip"
    return "EmberLauncher-linux"


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
        return {"filename": filename, "url": url}
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


def build_pack(
    query: str,
    loader: str,
    game_version: str,
    preset_id: str = "",
    sources: tuple[str, ...] = ("modrinth", "curseforge"),
) -> dict:
    text = (query or "").strip()
    low = text.lower()
    mod_loader = "forge" if loader == "optifine" else loader
    if mod_loader not in ("fabric", "forge", "neoforge", "quilt"):
        mod_loader = "fabric"
    preset = next((pack for pack in PRESETS if pack["id"] == preset_id), None)
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
        queue: list[tuple[str, bool]] = [(slug, False) for slug in found] + [(slug, True) for slug in shader_slugs]
        seen: set[str] = set()
        mods_found: list[dict] = []
        missed: list[str] = []
        limit = 16 if preset else 10
        while queue and len(mods_found) < limit:
            slug, shader = queue.pop(0)
            if slug in seen:
                continue
            seen.add(slug)
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
            mods_found.append(info)
            if not shader:
                for dep in info.get("deps") or []:
                    if dep.get("dependency_type") != "required":
                        continue
                    project_id = str(dep.get("project_id") or "")
                    if project_id and project_id not in seen and len(mods_found) + len(queue) < limit + 4:
                        queue.append((project_id, False))
        return mods_found, missed

    mods: list[dict] = []
    skipped: list[str] = []
    for active_loader in loader_order:
        for active in attempts:
            found, shader_slugs = slugs_for(active_loader, active)
            if not found and not shader_slugs:
                continue
            mods, skipped = gather(active_loader, active, found, shader_slugs)
            if mods:
                mod_loader = active_loader
                game_version = active
                break
        if mods:
            break
    if not mods:
        raise RuntimeError(
            f"По запросу на {asked_version} ({asked_loader}) ничего не нашлось с 1.19.2 и новее. "
            "Напиши иначе или выбери Fabric, NeoForge, 1.20.1 или 1.21.1."
        )
    names = ", ".join(item["title"] for item in mods[:16])
    extra = ""
    if loader == "optifine":
        extra = " OptiFine моды почти не грузит, поэтому набор под Forge."
    if mod_loader != asked_loader:
        extra += f" На {asked_loader} файлов не было, поэтому загрузчик {mod_loader}."
    if game_version != asked_version:
        extra += f" На {asked_version} файлов не нашлось, поэтому взял {game_version}."
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
