# Ember Launcher

Офлайн-лаунчер Minecraft. Автор: [craor](https://github.com/craor).

Игра и Java качаются с серверов Mojang. Аккаунт Microsoft не нужен: для запуска собирается офлайн-профиль. Лицензионные серверы (`online-mode=true`) такого игрока не пустят. Одиночная игра и серверы с `online-mode=false` работают.

Код открытый, лицензия MIT. В репозитории нет личных ссылок, токенов и паролей. Единственное имя автора — ник `craor`.

## Сборки

Один и тот же лаунчер, три файла. Их собирает GitHub Actions и кладёт в [Releases](https://github.com/craor/EmberLauncher/releases).

| Система | Файл |
| --- | --- |
| Windows 10 и Windows 11 (64-bit) | `EmberLauncher.exe` |
| Linux x64, Ubuntu 22.04 и новее | `EmberLauncher-linux` |
| MacBook на Apple silicon (M1 и новее) | `EmberLauncher-macOS.dmg` |

Windows 10 и 11 используют один exe. Отдельной сборки под каждую из них нет: программа одна.

Первый запуск спрашивает папку и кладёт ярлык Ember на рабочий стол. Повторный запуск ярлыка открывает лаунчер сразу.

На Linux после скачивания: `chmod +x EmberLauncher-linux`. На Mac открой `EmberLauncher-macOS.dmg`, перетащи EmberLauncher в «Программы» и открой его оттуда правой кнопкой → «Открыть». Из окна диска или из zip программа молча не стартует: macOS прячет скачанные приложения. Сборка без сертификата Apple, на Intel её нет.

## Запуск из исходников

Нужен Python 3.10+.

```bash
pip install -r requirements.txt
python launcher.py
```

На Windows без консоли: `pythonw launcher.py`.

Настройки лежат в папке EmberLauncher: `%APPDATA%` на Windows, `~/Library/Application Support` на Mac, `~/.config` на Linux.

## Сборка у себя

Windows: `build.bat`.

Linux и Mac:

```bash
pip install -r requirements.txt pyinstaller
python build_release.py
```

Готовые файлы появятся в `dist/`. Публичная сборка на GitHub не вшивает `server.json`. Свой файл карточки сервера оставь только локально: скопируй `server.example.json` в `server.json` и заполни. `server.json` в `.gitignore`.

## Обновления

Лаунчер смотрит последний публичный Release репозитория `craor/EmberLauncher`. Если тег новее версии внутри программы, он предлагает скачать файл для своей системы и перезапуститься.

Новый багфикс:

1. Подними `APP_VERSION` в `launcher.py`.
2. Залей код в `main`.

Actions сам соберёт три файла и создаст релиз `v` + версия, если такого релиза ещё нет. Тег вручную не нужен. Черновики и prerelease не подхватываются. Качается только файл с GitHub, контрольная сумма сверяется, если GitHub её отдал.

## Проверка

При каждом пуше Actions проверяет, что код компилируется, и что в нём нет личных ссылок. Сборки Windows, Linux и macOS идут отдельными задачами.
