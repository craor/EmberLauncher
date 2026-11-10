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
    print("ok")


if __name__ == "__main__":
    main()
