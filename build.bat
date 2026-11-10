@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

where python >nul 2>&1
if errorlevel 1 (
    echo [Ember] Python не найден. Установите Python 3.10+ с https://www.python.org/downloads/
    echo         и включите "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [Ember] Устанавливаю зависимости...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python -m pip install "pyinstaller>=6.0"
if errorlevel 1 goto :fail

echo [Ember] Рисую иконку...
python make_icon.py
if errorlevel 1 goto :fail

echo [Ember] Собираю один exe...
set EXTRA=
if exist server.json set EXTRA=--add-data "server.json;."
python -m PyInstaller --noconfirm --clean --onefile --windowed --name EmberLauncher --icon icon.ico --add-data "icon.ico;." --add-data "icon.png;." --add-data "ember_src;ember_src" %EXTRA% --collect-all minecraft_launcher_lib --collect-all PyQt6 launcher.py
if errorlevel 1 goto :fail

echo.
echo Готово: %cd%\dist\EmberLauncher.exe
echo Конфиг и лог после запуска: %%APPDATA%%\EmberLauncher\
pause
exit /b 0

:fail
echo.
echo Сборка остановилась с ошибкой.
pause
exit /b 1
