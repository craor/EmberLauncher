"""Помощник сборки: нейросеть только понимает запрос, моды качает код с Modrinth."""

import threading
import time

# Нейросеть не имеет права называть файлы. Эти слаги проверяет сам лаунчер на Modrinth.
_OPT_SLUGS = {
    "fabric": ("fabric-api", "sodium", "lithium", "ferrite-core"),
    "quilt": ("sodium", "lithium", "ferrite-core"),
    "forge": ("embeddium", "ferrite-core", "modernfix"),
    "neoforge": ("embeddium", "ferrite-core", "modernfix"),
}
_SHADER_MOD_SLUGS = {
    "fabric": ("fabric-api", "sodium", "iris"),
    "quilt": ("sodium", "iris"),
    "forge": ("embeddium", "oculus"),
    "neoforge": ("embeddium", "oculus"),
}
_SHADER_PACK_SLUGS = ("complementary-reimagined", "bsl-shaders")
_CONFLICTS = {
    "sodium": {"embeddium", "optifine", "vulkanmod"},
    "embeddium": {"sodium", "optifine", "vulkanmod"},
    "iris": {"oculus", "optifine"},
    "oculus": {"iris", "optifine"},
    "vulkanmod": {"sodium", "embeddium", "iris"},
    "optifine": {"sodium", "embeddium", "iris", "oculus"},
}
_KIND_WORDS = (
    ("graphics", ("шейд", "shader", "график", "красив", "визуал")),
    ("optimization", ("оптим", "фпс", "fps", "лаг", "натрий")),
    ("magic", ("маг", "magic", "волшеб", "закл", "ботан")),
    ("tech", ("тех", "механ", "create", "завод", "криэйт")),
    ("survival", ("выжив", "survival", "хардкор")),
    ("adventure", ("данж", "приключ", "пещер", "биом")),
)
_ASSISTANT_SYSTEM = (
    "Ты разбираешь просьбу игрока Minecraft и отвечаешь только JSON, без текста вокруг. "
    "Ключи строго такие: game_version (строка версии вроде 1.20.1 или пустая строка), "
    "loader (одно из: fabric, forge, neoforge, quilt), "
    "queries (массив из 1-4 коротких английских поисковых слов, не имена файлов и не слаги модов), "
    "kind (одно из: optimization, graphics, magic, tech, survival, adventure, mixed), "
    "shaders (true или false). "
    "Не выдумывай моды, не пиши ссылки, не пиши код и не пиши пути к файлам."
)
_MODRINTH_GAP = 0.21
_modrinth_lock = threading.Lock()
_modrinth_next = 0.0


def log_assistant(text: str) -> None:
    """Журнал помощника. Ключи сюда попадать не должны, но строка всё равно чистится."""
    try:
        path = os.path.join(app_config_dir(), "assistant.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(datetime.now().isoformat(timespec="seconds") + " " + redact_secrets(text)[:500] + "\n")
    except OSError:
        return


def redact_secrets(text: str) -> str:
    cleaned = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{6,}", r"\1[скрыто]", str(text or ""))
    cleaned = re.sub(r"(?i)(sk-|or-)[A-Za-z0-9._\-]{6,}", "[скрыто]", cleaned)
    return cleaned


def modrinth_pause() -> None:
    """Modrinth просит не больше 300 запросов в минуту. Держим запас."""
    global _modrinth_next
    with _modrinth_lock:
        wait = _modrinth_next - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _modrinth_next = time.monotonic() + _MODRINTH_GAP


def parse_assistant_json(raw: str) -> dict:
    """Принимает только ожидаемый JSON. Всё лишнее выбрасывается, код не выполняется."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("В ответе нет JSON.")
    if end - start > 4000:
        raise ValueError("Ответ нейросети слишком длинный.")
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("JSON нейросети сломан.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Нейросеть вернула не объект.")
    loader = str(payload.get("loader") or "").strip().lower()
    if loader not in ("fabric", "forge", "neoforge", "quilt", ""):
        raise ValueError("Неизвестный загрузчик в ответе.")
    version = str(payload.get("game_version") or "").strip()
    if version and not re.fullmatch(r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?", version):
        raise ValueError("Версия в ответе выглядит не как номер Minecraft.")
    if version and not pack_version_allowed(version):
        version = ""
    kind = str(payload.get("kind") or "mixed").strip().lower()
    if kind not in ("optimization", "graphics", "magic", "tech", "survival", "adventure", "mixed"):
        kind = "mixed"
    queries_raw = payload.get("queries")
    if not isinstance(queries_raw, list) or not queries_raw:
        raise ValueError("Нет поисковых запросов.")
    queries: list[str] = []
    for item in queries_raw:
        query = re.sub(r"[^A-Za-z0-9 \-]", "", str(item or "")).strip()
        query = re.sub(r"\s+", " ", query)[:40]
        if len(query) < 2 or query.lower() in {one.lower() for one in queries}:
            continue
        queries.append(query)
        if len(queries) >= 4:
            break
    if not queries:
        raise ValueError("Поисковые слова пустые или это не поиск, а имена файлов.")
    shaders = payload.get("shaders")
    if not isinstance(shaders, bool):
        shaders = kind == "graphics"
    return {
        "game_version": version,
        "loader": loader,
        "queries": queries,
        "kind": kind,
        "shaders": shaders or kind == "graphics",
        "optimize": True,
        "source": "model",
    }


def intent_without_model(text: str, loader: str, game_version: str) -> dict:
    """Запасной разбор без нейросети: те же поля, что ждал бы JSON модели."""
    low = (text or "").lower()
    found = minecraft_release_from_id(text) or ""
    version = found if found and pack_version_allowed(found) else ""
    if not version and pack_version_allowed(game_version):
        version = game_version
    kind = "mixed"
    for name, words in _KIND_WORDS:
        if any(word in low for word in words):
            kind = name
            break
    shaders = kind == "graphics" or any(word in low for word in ("шейд", "shader", "график", "красив"))
    if shaders and kind == "mixed":
        kind = "graphics"
    loader_name = loader if loader in ("fabric", "forge", "neoforge", "quilt") else "fabric"
    queries = [item for item in query_variants(text) if re.fullmatch(r"[A-Za-z0-9 \-]{2,40}", item)]
    if shaders and not any(item.lower() == "shader" for item in queries):
        queries.insert(0, "shader")
    if kind == "optimization" and not queries:
        queries.append("performance")
    if not queries:
        queries.append("optimization" if kind == "optimization" else "adventure")
    return {
        "game_version": version,
        "loader": loader_name,
        "queries": queries[:4],
        "kind": kind,
        "shaders": shaders,
        "optimize": True,
        "source": "rules",
    }


def _loopback_ollama(url: str) -> str:
    """Ollama только на этом компьютере. Чужой адрес из настроек не открываем."""
    parsed = urllib.parse.urlparse((url or "").strip() or "http://127.0.0.1:11434")
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "http" or host not in ("127.0.0.1", "localhost") or parsed.username or parsed.password:
        raise ValueError("Ollama можно звать только с этого компьютера: http://127.0.0.1:11434")
    port = parsed.port or 11434
    if port < 1 or port > 65535:
        raise ValueError("Неверный порт Ollama.")
    return f"http://{host}:{port}/api/chat"


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: int, local: bool = False) -> dict:
    if not local:
        _require_https(url, ALLOWED_HOSTS)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not local:
                _require_https(response.geturl(), ALLOWED_HOSTS)
            body = response.read(80_000)
    except Exception as exc:
        raise RuntimeError(redact_secrets(str(exc))) from exc
    try:
        parsed = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Сервис ответил не JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Сервис ответил не объектом.")
    return parsed


class OllamaProvider:
    """Локальная модель. Интернет для самого разбора запроса не нужен, Modrinth всё равно нужен."""

    def __init__(self, model: str, base_url: str) -> None:
        self.model = model or "qwen2.5:3b"
        self.url = _loopback_ollama(base_url)

    def complete(self, system: str, user: str) -> str:
        payload = _post_json(
            self.url,
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            {"Content-Type": "application/json", "Accept": "application/json"},
            timeout=40,
            local=True,
        )
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        return str(message.get("content") or "")


class DeepSeekProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def complete(self, system: str, user: str) -> str:
        payload = _post_json(
            "https://api.deepseek.com/chat/completions",
            {
                "model": "deepseek-chat",
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
            timeout=40,
        )
        choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
        return str((message or {}).get("content") or "")


class OpenRouterProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model or "meta-llama/llama-3.2-3b-instruct:free"

    def complete(self, system: str, user: str) -> str:
        payload = _post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer " + self.api_key,
                "X-Title": "EmberLauncher",
            },
            timeout=40,
        )
        choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
        return str((message or {}).get("content") or "")


def _write_private(path: str, data: bytes) -> None:
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    temporary = path + ".tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        return


def _secret_file(name: str) -> str:
    return os.path.join(app_config_dir(), "secret-" + name)


def secret_get(name: str) -> str:
    if name not in ("deepseek", "openrouter"):
        return ""
    if sys.platform == "darwin":
        try:
            raw = subprocess.check_output(
                ["/usr/bin/security", "find-generic-password", "-s", "EmberLauncher", "-a", name, "-w"],
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return raw.decode("utf-8", errors="replace").strip()
        except (OSError, subprocess.SubprocessError):
            pass
    elif os.name != "nt":
        try:
            raw = subprocess.check_output(
                ["secret-tool", "lookup", "service", "emberlauncher", "account", name],
                stderr=subprocess.DEVNULL,
                timeout=4,
            )
            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                return text
        except (OSError, subprocess.SubprocessError):
            pass
    elif os.name == "nt":
        protected = _secret_file(name) + ".dpapi"
        if os.path.isfile(protected):
            try:
                return _dpapi_unprotect(pathlib.Path(protected).read_bytes()).decode("utf-8")
            except (OSError, UnicodeError):
                return ""
    path = _secret_file(name)
    if not os.path.isfile(path):
        return ""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def secret_set(name: str, value: str) -> str:
    """Кладёт ключ в связку системы. В config.json и в логи он не пишется."""
    if name not in ("deepseek", "openrouter"):
        raise ValueError("Неизвестное имя ключа.")
    secret = (value or "").strip()
    if len(secret) < 8 or len(secret) > 300 or any(char in secret for char in "\r\n\x00"):
        raise ValueError("Ключ пустой или в нём есть перевод строки.")
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["/usr/bin/security", "add-generic-password", "-U", "-s", "EmberLauncher", "-a", name, "-w", secret],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return "Связка ключей macOS"
        except (OSError, subprocess.SubprocessError):
            pass
    elif os.name == "nt":
        try:
            _write_private(_secret_file(name) + ".dpapi", _dpapi_protect(secret.encode("utf-8")))
            return "Шифрование Windows"
        except OSError:
            pass
    else:
        try:
            subprocess.run(
                ["secret-tool", "store", "--label=EmberLauncher", "service", "emberlauncher", "account", name],
                input=secret.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
            )
            return "Связка ключей Linux"
        except (OSError, subprocess.SubprocessError):
            pass
    _write_private(_secret_file(name), secret.encode("utf-8"))
    return "Файл только для вашего пользователя, связки ключей нет"


def _dpapi_protect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data)
    incoming = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    outgoing = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(incoming), "EmberLauncher", None, None, None, 0, ctypes.byref(outgoing)
    ):
        raise OSError("Windows не зашифровал ключ.")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data)
    incoming = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    outgoing = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(incoming), None, None, None, None, 0, ctypes.byref(outgoing)
    ):
        raise OSError("Windows не расшифровал ключ.")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.pbData)


def _provider_for(settings: dict):
    provider = str(settings.get("llm_provider") or "off")
    if provider == "off":
        return None
    if provider == "ollama":
        return OllamaProvider(str(settings.get("ollama_model") or ""), str(settings.get("ollama_url") or ""))
    if provider == "deepseek":
        key = secret_get("deepseek")
        if not key:
            raise RuntimeError("Ключ DeepSeek не сохранён. Впиши его в установке и нажми «Запомнить ключ».")
        return DeepSeekProvider(key)
    if provider == "openrouter":
        key = secret_get("openrouter")
        if not key:
            raise RuntimeError("Ключ OpenRouter не сохранён. Впиши его в установке и нажми «Запомнить ключ».")
        return OpenRouterProvider(key, str(settings.get("openrouter_model") or ""))
    return None


def assistant_intent(text: str, loader: str, game_version: str, settings: dict | None) -> dict:
    """До двух повторов кривого ответа. Потом вызывающий код берёт разбор без модели."""
    config = settings or {}
    provider = _provider_for(config)
    if provider is None:
        intent = intent_without_model(text, loader, game_version)
        intent["note"] = "Нейросеть выключена, запрос разобран по словам."
        return intent
    user = (
        f"Запрос игрока: {text[:240]}\n"
        f"Версия в лаунчере: {game_version}\n"
        f"Загрузчик в лаунчере: {loader}"
    )
    last = "пустой ответ"
    for _attempt in range(3):
        try:
            raw = provider.complete(_ASSISTANT_SYSTEM, user)
        except Exception as exc:
            last = redact_secrets(str(exc))
            log_assistant("провайдер: " + last)
            continue
        try:
            intent = parse_assistant_json(raw)
        except ValueError as exc:
            last = str(exc)
            log_assistant("json: " + last)
            user = user + "\nПрошлый ответ не подошёл. Верни только один JSON."
            continue
        if not intent["loader"]:
            intent["loader"] = loader if loader in ("fabric", "forge", "neoforge", "quilt") else "fabric"
        if config.get("assistant_optimize") is False:
            intent["optimize"] = False
        intent["note"] = "Запрос разобрала нейросеть, моды она не называла."
        return intent
    raise RuntimeError(last)


def conflicts_with(slug: str, chosen: set[str]) -> str:
    for other in chosen:
        if slug in _CONFLICTS.get(other, ()) or other in _CONFLICTS.get(slug, ()):
            return other
    return ""


def verify_mod_file(path: str, mod: dict) -> None:
    """Сверяет файл с хэшем Modrinth. Чужой или битый файл удаляется."""
    sha512 = str(mod.get("sha512") or "").lower()
    sha1 = str(mod.get("sha1") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{128}", sha512):
        sha512 = ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha1):
        sha1 = ""
    if not sha512 and not sha1:
        if str(mod.get("url") or "").startswith("https://cdn.modrinth.com/"):
            try:
                os.remove(path)
            except OSError:
                pass
            raise RuntimeError(f"У «{mod.get('title') or 'мода'}» нет хэша Modrinth, файл не оставлен.")
        return
    digest = hashlib.sha512() if sha512 else hashlib.sha1()
    expected = sha512 or sha1
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != expected:
        try:
            os.remove(path)
        except OSError:
            pass
        raise RuntimeError(f"Хэш не совпал у «{mod.get('title') or 'файла'}». Файл удалён, в игру он не попадёт.")


def _remember_slug(info: dict, chosen: list[dict], seen: set[str]) -> str:
    slug = str(info.get("slug") or "")
    if not slug or slug in seen:
        return ""
    other = conflicts_with(slug, seen)
    if other:
        return f"{info.get('title') or slug} конфликтует с {other}"
    if str(info.get("url") or "").startswith("https://cdn.modrinth.com/") and not (
        info.get("sha1") or info.get("sha512")
    ):
        return f"У {info.get('title') or slug} нет хэша"
    seen.add(slug)
    chosen.append(info)
    return ""


def attach_support_mods(plan: dict, intent: dict, sources: tuple[str, ...]) -> dict:
    """Добавляет оптимизацию и шейдерный мод, только если Modrinth отдаёт их на эту версию."""
    loader = str(plan.get("loader") or "")
    version = str(plan.get("game_version") or "")
    mods = [dict(item) for item in plan.get("mods") or []]
    seen = {str(item.get("slug") or "") for item in mods}
    notes: list[str] = []
    wanted: list[tuple[str, bool, str]] = []
    if intent.get("optimize", True):
        for slug in _OPT_SLUGS.get(loader, ()):
            wanted.append((slug, False, "оптимизация"))
    if intent.get("shaders"):
        for slug in _SHADER_MOD_SLUGS.get(loader, ()):
            wanted.append((slug, False, "шейдеры"))
        for slug in _SHADER_PACK_SLUGS:
            wanted.append((slug, True, "шейдерпак"))
    added_pack = False
    for slug, shader, role in wanted:
        if slug in seen:
            continue
        if shader and added_pack:
            continue
        try:
            modrinth_pause()
            info = resolve_project(slug, loader, version, shader=shader, sources=sources)
        except Exception as exc:
            notes.append(str(exc)[:120])
            continue
        if not info:
            notes.append(f"{slug} нет на {version} ({loader})")
            continue
        info["support"] = role
        problem = _remember_slug(info, mods, seen)
        if problem:
            notes.append(problem)
            continue
        if shader:
            added_pack = True
    plan = dict(plan)
    plan["mods"] = mods
    if notes:
        plan["summary"] = str(plan.get("summary") or "") + " Не добавлено: " + "; ".join(notes[:6]) + "."
    return plan


def assist_build(query: str, loader: str, game_version: str, settings: dict | None = None) -> dict:
    """Собирает план. Модель не качает файлы: после неё работает обычный поиск Modrinth."""
    config = dict(settings or {})
    try:
        intent = assistant_intent(query, loader, game_version, config)
    except Exception as exc:
        log_assistant(str(exc))
        intent = intent_without_model(query, loader, game_version)
        intent["note"] = "Нейросеть не ответила нормально, разобрал запрос без неё. " + redact_secrets(str(exc))[:140]
    use_loader = intent["loader"] if intent.get("loader") in ("fabric", "forge", "neoforge", "quilt") else loader
    use_version = intent["game_version"] or game_version
    if config.get("assistant_optimize") is False:
        intent["optimize"] = False
    search = " ".join(intent.get("queries") or []) or query
    try:
        plan = build_pack(search, use_loader, use_version, "", ("modrinth",), free_search=True)
    except RuntimeError as exc:
        plan = {
            "title": (search or query)[:48] or "Подбор",
            "summary": str(exc),
            "loader": use_loader if use_loader in ("fabric", "forge", "neoforge", "quilt") else "fabric",
            "game_version": use_version,
            "mods": [],
        }
    plan = attach_support_mods(plan, intent, ("modrinth",))
    if not plan.get("mods"):
        raise RuntimeError(str(plan.get("summary") or "По запросу ничего не нашлось на Modrinth."))
    plan["isolated"] = True
    plan["instance_name"] = safe_instance_name(str(plan.get("title") or "pack"))
    note = str(intent.get("note") or "")
    if note:
        plan["summary"] = note + " " + str(plan.get("summary") or "")
    plan["summary"] += " Ставлю в отдельный профиль, папку mods основной игры не трогаю."
    return plan


def safe_instance_name(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:32]
    if not slug:
        slug = "pack"
    digest = hashlib.sha1((title or slug).encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{digest}"[:48]


def instance_slug(name: str) -> str:
    text = (name or "").strip().lower()
    if re.fullmatch(r"[a-z0-9-]{1,48}", text):
        return text
    return safe_instance_name(name)


def instance_dir(minecraft_dir: str, name: str) -> str:
    slug = instance_slug(name)
    root = os.path.join(os.path.abspath(minecraft_dir), "ember-instances")
    folder = os.path.abspath(os.path.join(root, slug))
    if os.path.commonpath([root, folder]) != os.path.abspath(root):
        raise ValueError("Неверное имя профиля.")
    return folder


def prepare_instance(minecraft_dir: str, name: str) -> str:
    folder = instance_dir(minecraft_dir, name)
    for sub in ("mods", "shaderpacks", "config"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    return folder


def backup_instance(folder: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = folder.rstrip("\\/") + "-backup-" + stamp
    if os.path.exists(dest):
        dest += "-2"
    shutil.copytree(folder, dest)
    return dest


def rollback_instance(minecraft_dir: str, name: str) -> str:
    folder = instance_dir(minecraft_dir, name)
    parent = os.path.dirname(folder)
    slug = os.path.basename(folder)
    if not os.path.isdir(parent):
        raise RuntimeError("Профиля ещё нет, откатывать нечего.")
    backups = sorted(
        item for item in os.listdir(parent)
        if item.startswith(slug + "-backup-") and os.path.isdir(os.path.join(parent, item))
    )
    if not backups:
        raise RuntimeError("Бэкапа этого профиля нет.")
    source = os.path.join(parent, backups[-1])
    for sub in ("mods", "shaderpacks", "config"):
        dest = os.path.join(folder, sub)
        src = os.path.join(source, sub)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        if os.path.isdir(src):
            shutil.copytree(src, dest)
        else:
            os.makedirs(dest, exist_ok=True)
    meta_src = os.path.join(source, "instance.json")
    meta_dest = os.path.join(folder, "instance.json")
    if os.path.isfile(meta_src):
        shutil.copy2(meta_src, meta_dest)
    return source


def write_shader_choice(folder: str, filename: str) -> None:
    """Iris и Oculus читают имя пака из своего файла настроек."""
    safe = safe_filename(filename)
    if not safe:
        return
    config = os.path.join(folder, "config")
    os.makedirs(config, exist_ok=True)
    for name in ("iris.properties", "oculus.properties"):
        path = os.path.join(config, name)
        lines: list[str] = []
        seen_enable = False
        seen_pack = False
        if os.path.isfile(path):
            try:
                previous = pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                previous = []
        else:
            previous = []
        for line in previous:
            if line.startswith("enableShaders="):
                lines.append("enableShaders=true")
                seen_enable = True
            elif line.startswith("shaderPack="):
                lines.append("shaderPack=" + safe)
                seen_pack = True
            else:
                lines.append(line)
        if not seen_enable:
            lines.append("enableShaders=true")
        if not seen_pack:
            lines.append("shaderPack=" + safe)
        pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_instance_meta(folder: str, plan: dict, version_id: str) -> None:
    payload = {
        "name": os.path.basename(folder),
        "title": str(plan.get("title") or ""),
        "game_version": str(plan.get("game_version") or ""),
        "loader": str(plan.get("loader") or ""),
        "version_id": version_id,
        "files": [
            {"folder": str(item.get("folder") or "mods"), "filename": str(item.get("filename") or "")}
            for item in plan.get("mods") or []
        ],
    }
    path = os.path.join(folder, "instance.json")
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def _install_assistant_hooks() -> None:
    """Вешает паузу Modrinth на уже объявленные функции, не меняя их логику."""
    if "http_json" not in globals() or "build_pack" not in globals():
        return
    original_http = http_json
    original_build = build_pack

    def paced_http_json(url: str, timeout: int = 30):
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        if host == "api.modrinth.com":
            modrinth_pause()
        return original_http(url, timeout)

    def build_pack_with_intent(
        query: str,
        loader: str,
        game_version: str,
        preset_id: str = "",
        sources: tuple[str, ...] = ("modrinth", "curseforge"),
        free_search: bool = False,
        intent: dict | None = None,
    ) -> dict:
        plan = original_build(query, loader, game_version, preset_id, sources, free_search)
        if intent:
            plan = attach_support_mods(plan, intent, sources)
        return plan

    globals()["http_json"] = paced_http_json
    globals()["build_pack"] = build_pack_with_intent


_install_assistant_hooks()
