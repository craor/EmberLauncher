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
    for name, text in (("launcher.py", launcher_text), ("server.example.json", example), ("README.md", readme)):
        for needle in FORBIDDEN:
            if needle in text:
                raise SystemExit(f"{name} содержит запрещённое: {needle}")
    if 'AUTHOR = "craor"' not in launcher_text:
        raise SystemExit("нет ника автора")
    if 'DEFAULT_UPDATE_REPO = "craor/EmberLauncher"' not in launcher_text:
        raise SystemExit("нет репозитория обновлений")
    import launcher

    assert launcher.clean_repo("https://github.com/craor/EmberLauncher.git") == "craor/EmberLauncher"
    assert launcher.clean_repo("javascript:alert(1)") == ""
    assert launcher.version_numbers("v1.8.1") > launcher.version_numbers("1.8.0")
    assert launcher.DEFAULT_UPDATE_REPO == "craor/EmberLauncher"
    print("ok")


if __name__ == "__main__":
    main()
