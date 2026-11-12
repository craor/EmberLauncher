"""Проверки, которые гоняет GitHub Actions. Сеть и окно не нужны."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FORBIDDEN = (
    "discord.gg",
    "t.me/",
    "craor.xyz",
    "N5xTSeW",
    "BEGIN PRIVATE",
    "ghp_",
    "github_pat_",
)


def main() -> None:
    launcher_text = (ROOT / "launcher.py").read_text(encoding="utf-8")
    example = (ROOT / "server.example.json").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    parts = sorted((ROOT / "ember_src").glob("part_*.py"))
    if len(parts) < 2:
        raise SystemExit("нет исходников ember_src")
    body = "".join(path.read_text(encoding="utf-8") for path in parts)
    compile(body, "ember_src/launcher.py", "exec")
    scanned = {
        "launcher.py": launcher_text,
        "server.example.json": example,
        "README.md": readme,
        "ember_src": body,
    }
    for name, text in scanned.items():
        for needle in FORBIDDEN:
            if needle in text:
                raise SystemExit(f"{name} содержит запрещённое: {needle}")
    if 'AUTHOR = "craor"' not in launcher_text:
        raise SystemExit("нет ника автора")
    if 'DEFAULT_UPDATE_REPO = "craor/EmberLauncher"' not in launcher_text:
        raise SystemExit("нет репозитория обновлений")
    if 'APP_VERSION = "' in body:
        raise SystemExit("версия должна задаваться только в launcher.py")
    import launcher
    import os

    cafile = os.environ.get("SSL_CERT_FILE") or ""
    if not cafile or not os.path.isfile(cafile):
        raise SystemExit("нет корневых сертификатов для HTTPS")
    if "REQUESTS_CA_BUNDLE" not in os.environ:
        raise SystemExit("requests не увидит сертификаты")
    ui = (ROOT / "ember_src" / "part_04.py").read_text(encoding="utf-8")
    if 'MaterialFrame("parchment"' not in ui or 'MaterialFrame("leather"' not in ui:
        raise SystemExit("панели без кожи и пергамента")
    if "paint_material" not in (ROOT / "ember_src" / "part_03.py").read_text(encoding="utf-8"):
        raise SystemExit("текстуры не рисуются")
    sample = launcher.parse_assistant_json(
        '```json\n{"game_version":"1.20.1","loader":"fabric","queries":["performance","graphics"],'
        '"kind":"graphics","shaders":true,"mods":["удали-систему"]}\n```'
    )
    if sample["game_version"] != "1.20.1" or sample["loader"] != "fabric" or "удали-систему" in str(sample):
        raise SystemExit("нейросеть смогла протащить лишнее")
    if launcher.conflicts_with("oculus", {"iris"}) != "iris":
        raise SystemExit("конфликт шейдерных модов не пойман")
    rules = launcher.intent_without_model("хочу оптимизацию и красивую графику на 1.20.1", "fabric", "1.21.1")
    if rules["game_version"] != "1.20.1" or not rules["shaders"]:
        raise SystemExit("запасной разбор не понял графику и версию")
    if launcher._loopback_ollama("http://127.0.0.1:11434") != "http://127.0.0.1:11434/api/chat":
        raise SystemExit("Ollama ушла не на этот компьютер")
    try:
        launcher._loopback_ollama("http://example.com/api/chat")
    except ValueError:
        pass
    else:
        raise SystemExit("Ollama приняла чужой адрес")
    folder = ROOT / "ember_src" / "textures"
    if not (folder / "wood.b64").is_file():
        raise SystemExit("нет текстур")

    assert launcher.clean_repo("https://github.com/craor/EmberLauncher.git") == "craor/EmberLauncher"
    assert launcher.clean_repo("javascript:alert(1)") == ""
    assert launcher.version_numbers("v1.8.1") > launcher.version_numbers("1.8.0")
    assert launcher.DEFAULT_UPDATE_REPO == "craor/EmberLauncher"
    assert launcher.range_allows("[4.8.0,)", "4.5.8") is False
    assert launcher.range_allows("[4.8.0,)", "4.8") is True
    assert launcher.range_allows("[4.8.0,)", "4.8.0") is True
    assert launcher.range_allows("[4.8.0,)", "4.9.3") is True
    assert launcher.range_allows("[0.8.0,)", "0.8.9.2-hotfix") is True
    assert launcher.range_allows("[1.20.1,1.21)", "1.20.1") is True
    assert launcher.range_allows("[1.20.1,1.21)", "1.21") is False
    assert launcher.range_allows(">=4.8.0", "4.9.3") is True
    import io
    import zipfile

    toml = (
        'modLoader="javafml"\n'
        '[[mods]]\n'
        'modId="wrecked"\n'
        'version="1.1.2"\n'
        "description='''Every punk picks up the junk.'''\n"
        "[[dependencies.wrecked]]\n"
        'modId="forge"\n'
        "mandatory=true\n"
        'versionRange="[47,)"\n'
        "[[dependencies.wrecked]]\n"
        'modId="geckolib"\n'
        "mandatory=true\n"
        'versionRange="[4.8.0,)"\n'
        "[[dependencies.wrecked]]\n"
        'modId="superbwarfare"\n'
        "mandatory=false\n"
        'versionRange="[0.8.0,)"\n'
    )
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        archive.writestr("META-INF/mods.toml", toml)
    own, deps, _embedded = launcher.read_jar_requirements(blob.getvalue())
    assert own.get("wrecked") == "1.1.2"
    assert ("geckolib", "[4.8.0,)") in deps
    assert ("forge", "[47,)") in deps
    assert all(item[0] != "superbwarfare" for item in deps)
    assert launcher._compact_id("superb-warfare") == "superbwarfare"
    assert launcher.preset_from_text("собери выживание")["id"] == "survival"
    assert launcher.preset_from_text("зомби выживание")["id"] == "zombie"
    assert launcher.preset_from_text("много животных") is None
    import tempfile
    crash_root = pathlib.Path(tempfile.mkdtemp())
    mods = crash_root / "mods"
    (crash_root / "logs").mkdir()
    mods.mkdir()
    (mods / "Waystones-1.2.jar").write_bytes(b"")
    (mods / "comforts-1.0.jar").write_bytes(b"")
    (crash_root / "logs" / "latest.log").write_text(
        "Loading mod comforts\n[main/ERROR]: Mod waystones requires cloth_config which is missing\n",
        encoding="utf-8",
    )
    note, disabled = launcher.startup_failure(str(crash_root), "")
    assert disabled == ["Waystones-1.2.jar"], disabled
    assert "библиотек" in note.lower() or "waystones" in note.lower()
    assert not (mods / "Waystones-1.2.jar").is_file()
    assert launcher.update_payload_ok(b"xxxx", b"koly", "darwin")
    assert not launcher.update_payload_ok(b"PK\x03\x04", b"", "darwin")
    assert launcher.update_payload_ok(b"\x7fELF", b"", "linux")
    mac = launcher.mac_launch_command(["/usr/bin/java", "-Xmx2G", "net.minecraft.client.main.Main"], "darwin")
    assert mac[1] == "-XstartOnFirstThread"
    assert any(item.startswith("-Dfml.earlyprogresswindow=") for item in mac)
    assert launcher.mac_launch_command(mac, "darwin").count("-XstartOnFirstThread") == 1
    assert launcher.mac_launch_command(["java", "-version"], "linux") == ["java", "-version"]
    mixed = ":".join((
        "/libs/lwjgl-glfw-3.3.3.jar",
        "/libs/lwjgl-glfw-3.3.3-natives-macos.jar",
        "/libs/lwjgl-glfw-3.3.3-natives-macos-arm64.jar",
    ))
    arm_cp = launcher.filter_mac_classpath(mixed, "arm64")
    assert any(part.endswith("natives-macos-arm64.jar") for part in arm_cp.split(":"))
    assert not any(part.endswith("natives-macos.jar") for part in arm_cp.split(":"))
    intel_cp = launcher.filter_mac_classpath(mixed, "x86_64")
    assert "natives-macos-arm64" not in intel_cp
    assert any(part.endswith("natives-macos.jar") for part in intel_cp.split(":"))
    prepared = launcher.prepare_mac_game_command(
        ["/usr/bin/java", "-cp", mixed, "net.minecraft.client.main.Main"],
        "darwin",
        "arm64",
    )
    assert prepared[1] == "-XstartOnFirstThread"
    prepared_cp = prepared[prepared.index("-cp") + 1]
    assert not any(part.endswith("natives-macos.jar") for part in prepared_cp.split(":"))
    assert any(part.endswith("natives-macos-arm64.jar") for part in prepared_cp.split(":"))
    assert launcher.prepare_mac_game_command(["java", "-version"], "linux") == ["java", "-version"]
    line = launcher.library_game_versions("1.21")
    assert line[0] == "1.21" and "1.21.1" in line and "1.20.1" not in line
    launcher._PROJECT_CACHE["geckolib"] = {
        "slug": "geckolib",
        "title": "GeckoLib",
        "project_type": "mod",
    }
    launcher._VERS_CACHE["geckolib|forge"] = [{
        "game_versions": ["1.21.1"],
        "version_number": "4.9.3",
        "version_type": "release",
        "files": [{
            "primary": True,
            "filename": "geckolib-forge-1.21.1-4.9.3.jar",
            "url": "https://cdn.modrinth.com/data/geckolib/versions/x/geckolib-forge-1.21.1-4.9.3.jar",
            "hashes": {},
        }],
    }]
    sibling = launcher._library_file("geckolib", "forge", "1.21", "[4.9.0,)")
    assert sibling and sibling["version_number"] == "4.9.3"
    launcher._VERS_CACHE["geckolib|forge"] = [{
        "game_versions": ["1.20.1"],
        "version_number": "4.4.0",
        "version_type": "release",
        "files": [{
            "primary": True,
            "filename": "geckolib-forge-1.20.1-4.4.jar",
            "url": "https://cdn.modrinth.com/data/geckolib/versions/x/geckolib-forge-1.20.1-4.4.jar",
            "hashes": {},
        }],
    }]
    assert launcher._library_file("geckolib", "forge", "1.21", "*") is None
    assert launcher.suggested_ram_gb(0, 8) == 2
    assert launcher.suggested_ram_gb(48, 16) >= 6
    assert launcher.suggested_ram_gb(48, 4) == 2
    natives = ";".join(("lwjgl-natives-windows.jar", "lwjgl-natives-windows-arm64.jar"))
    kept = launcher.filter_native_classpath(natives, "x64", ";")
    assert "arm64" not in kept and kept.endswith("natives-windows.jar")
    pack_root = pathlib.Path(tempfile.mkdtemp())
    packs = pack_root / "resourcepacks"
    packs.mkdir()
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        archive.writestr("pack.mcmeta", '{"pack":{"pack_format":99,"description":"new"}}')
    (packs / "TooNew.zip").write_bytes(blob.getvalue())
    disabled_packs = launcher.disable_incompatible_packs(str(pack_root), "1.20.1")
    assert disabled_packs and not (packs / "TooNew.zip").is_file()
    assert (packs / "TooNew.zip.disabled").is_file()
    java_root = pathlib.Path(tempfile.mkdtemp())
    (java_root / "versions" / "demo").mkdir(parents=True)
    (java_root / "versions" / "demo" / "demo.json").write_text(
        '{"id":"demo","javaVersion":{"component":"java-runtime-delta","majorVersion":21}}',
        encoding="utf-8",
    )
    assert launcher.java_requirement(str(java_root), "demo") == ("java-runtime-delta", 21)
    crash_dir = pathlib.Path(tempfile.mkdtemp())
    (crash_dir / "logs").mkdir()
    (crash_dir / "logs" / "latest.log").write_text(
        "java.lang.OutOfMemoryError: Java heap space\n",
        encoding="utf-8",
    )
    assert launcher.crash_fix_kind(str(crash_dir), "") == "ram"
    ui_paint = (ROOT / "ember_src" / "part_03.py").read_text(encoding="utf-8")
    assert "drawPixmap(QRectF" not in ui_paint
    assert "drawPixmap(x, y, pix)" in ui_paint
    assert launcher.split_server_address("play.example.com:25566") == ("play.example.com", 25566)
    assert launcher.split_server_address("https://play.example.com/path") == ("play.example.com", 25565)
    assert launcher.split_server_address("javascript:alert(1)") == ("", 25565)
    packet = launcher.status_request_packet("play.example.com", 25565)
    assert b"play.example.com" in packet and packet.endswith(b"\x01\x00")
    assert launcher.query_server_status("")["ok"] is False
    import shutil

    java_home = pathlib.Path(tempfile.mkdtemp())
    import minecraft_launcher_lib.runtime as runtime

    java_bin = (
        java_home
        / "runtime"
        / "java-runtime-delta"
        / runtime._get_jvm_platform_string()
        / "java-runtime-delta"
        / "bin"
        / "java"
    )
    java_bin.parent.mkdir(parents=True)
    java_bin.write_text("java", encoding="utf-8")
    assert launcher.java_for_loader(str(java_home), "1.21", "") == str(java_bin)
    assert launcher.java_for_loader(str(java_home), "1.21", str(java_bin)) == str(java_bin)
    missing_java = launcher.explain_install_error(FileNotFoundError(2, "Не удается найти указанный файл", "java"))
    assert "Java" in missing_java
    missing_asset = launcher.explain_install_error(FileNotFoundError(2, "No such file", str(java_home / "client.jar")))
    assert "ещё раз" in missing_asset
    nested = java_home / "assets" / "objects" / "ab" / "hash"
    launcher.ensure_download_dir(str(nested))
    assert nested.parent.is_dir()
    parent_jar = java_home / "1.21.jar"
    loader_jar = java_home / "fabric.jar"
    parent_jar.write_bytes(b"vanilla")
    assert launcher._copy_inherited_jar(shutil.copyfile, str(loader_jar), str(parent_jar))
    assert loader_jar.read_bytes() == b"vanilla"
    assert parent_jar.read_bytes() == b"vanilla"
    launcher.patch_minecraft_downloads()
    import minecraft_launcher_lib._helper as helper
    import minecraft_launcher_lib.install as install_mod

    patched = helper.download_file
    launcher.patch_minecraft_downloads()
    assert helper.download_file is patched
    assert install_mod.download_file is patched
    flipped = java_home / "from-parent.jar"
    assert not flipped.is_file()
    install_mod.shutil.copyfile(str(flipped), str(parent_jar))
    assert flipped.read_bytes() == b"vanilla"
    print("ok")


if __name__ == "__main__":
    main()
