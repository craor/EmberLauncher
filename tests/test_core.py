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
    import struct
    import tempfile
    binary = pathlib.Path(tempfile.mkdtemp()) / "liblwjgl.dylib"
    binary.write_bytes(struct.pack("<II", 0xFEEDFACF, 0x0100000C) + b"\0" * 32)
    assert launcher.macho_cpus(str(binary)) == {"arm64"}
    print("ok")


if __name__ == "__main__":
    main()
