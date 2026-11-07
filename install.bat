@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM HackBot — Windows Installer
REM ═══════════════════════════════════════════════════════════════════════════════
setlocal enabledelayedexpansion

set VERSION=1.1.0
set REPO=yashab-cyber/hackbot

echo.
echo   _   _            _    ____        _
echo  ^| ^| ^| ^| __ _  ___^| ^| _^| __ )  ___ ^| ^|_
echo  ^| ^|_^| ^|/ _` ^|/ __^| ^|/ /  _ \ / _ \^| __^|
echo  ^|  _  ^| (_^| ^| (__^|   ^<^| ^|_) ^| (_) ^| ^|_
echo  ^|_^| ^|_^|\__,_^|\___^|_^|\_\____/ \___/ \__^|
echo.
echo   AI Cybersecurity Assistant — Installer v%VERSION%
echo   ---------------------------------------------
echo   Developed by Yashab Alam
echo   GitHub:   https://github.com/yashab-cyber
echo   LinkedIn: https://www.linkedin.com/in/yashab-alam
echo   Email:    yashabalam707@gmail.com ^| yashabalam9@gmail.com
echo   ---------------------------------------------
echo   Support HackBot: https://github.com/yashab-cyber/hackbot/blob/main/DONATE.md
echo.

REM ── Check Python ───────────────────────────────────────────────────────────────
echo [INFO] Checking Python installation...

where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3.9+ is required.
        echo         Download from: https://www.python.org/downloads/
        echo         Make sure to check "Add Python to PATH" during installation.
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

for /f "tokens=*" %%i in ('%PYTHON% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%i
echo [OK] Python %PY_VERSION% found

REM ── Check version ──────────────────────────────────────────────────────────────
for /f %%i in ('%PYTHON% -c "import sys; print(1 if sys.version_info >= (3, 9) else 0)"') do set PY_OK=%%i
if "%PY_OK%"=="0" (
    echo [ERROR] Python 3.9+ required, found %PY_VERSION%
    exit /b 1
)

REM ── Install Mode ───────────────────────────────────────────────────────────────
set MODE=%1
if "%MODE%"=="" set MODE=pip
echo.
echo   Interface preference:
echo     1) CLI only (default)
echo     2) CLI + Web GUI
echo.
set /p GUI_CHOICE="Choose [1/2]: "
if "%GUI_CHOICE%"=="" set GUI_CHOICE=1
if "%GUI_CHOICE%"=="2" (
    set INSTALL_GUI=true
    echo [INFO] Will install with GUI support
) else (
    set INSTALL_GUI=false
    echo [INFO] Installing CLI only
)
echo.
if "%MODE%"=="pip" goto :install_pip
if "%MODE%"=="local" goto :install_local
if "%MODE%"=="full" goto :install_full
goto :usage

:install_pip
echo [INFO] Installing HackBot via pip...

set EXTRAS=[all]
if "%INSTALL_GUI%"=="true" set EXTRAS=[all]

REM Try pipx first
where pipx >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Using pipx for isolated installation...
    pipx install "hackbot%EXTRAS% @ git+https://github.com/%REPO%.git"
    if %errorlevel% equ 0 goto :post_install
    echo [WARN] pipx failed, falling back to pip...
)

%PYTHON% -m pip install --user "hackbot%EXTRAS% @ git+https://github.com/%REPO%.git"
if %errorlevel% neq 0 (
    echo [ERROR] Installation failed.
    exit /b 1
)
goto :post_install

:install_local
echo [INFO] Installing HackBot from local source...
if not exist "pyproject.toml" (
    echo [ERROR] Not in the hackbot repository. Run from project root.
    exit /b 1
)
if "%INSTALL_GUI%"=="true" (
    %PYTHON% -m pip install --user -e ".[all,dev]"
) else (
    %PYTHON% -m pip install --user -e ".[all]"
)
goto :post_install

:install_full
call :install_pip

echo.
echo [INFO] For security tools on Windows, we recommend:
echo   - Nmap:     https://nmap.org/download.html
echo   - Nikto:    https://github.com/sullo/nikto
echo   - SQLMap:   https://sqlmap.org/
echo   - Nuclei:   https://github.com/projectdiscovery/nuclei
echo   - ffuf:     https://github.com/ffuf/ffuf
echo.
echo   Or use WSL2 for the full Linux tool ecosystem:
echo   wsl --install
echo.
goto :post_install

:post_install
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║          HackBot Installation Complete!          ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo   Quick start:
echo     hackbot                    # Interactive mode
echo     hackbot setup ^<API_KEY^>    # Set your API key
echo     hackbot agent ^<TARGET^>     # Start security testing
echo     hackbot chat               # Chat mode
echo     hackbot plan ^<TARGET^>      # Plan an assessment
echo     hackbot tools              # Check available tools
echo     hackbot --gui              # Launch web GUI
echo.
echo   WARNING: Only test systems you have explicit authorization to test!
echo.
echo   Developed by Yashab Alam
echo   GitHub:   https://github.com/yashab-cyber
echo   LinkedIn: https://www.linkedin.com/in/yashab-alam
echo   Email:    yashabalam707@gmail.com ^| yashabalam9@gmail.com
echo   Support:  https://github.com/yashab-cyber/hackbot/blob/main/DONATE.md
echo.

REM ── Desktop Shortcut ───────────────────────────────────────────────────────
if "%INSTALL_GUI%"=="true" (
    echo [INFO] Creating desktop shortcut...
    set SHORTCUT_VBS=%TEMP%\hackbot_shortcut.vbs
    >"%SHORTCUT_VBS%" (
        echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
        echo Set lnk = WshShell.CreateShortcut^(WshShell.SpecialFolders^("Desktop"^) ^& "\HackBot.lnk"^)
        echo lnk.TargetPath = WshShell.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%"^) ^& "\Programs\Python\Python3*\Scripts\hackbot.exe"
        echo lnk.Arguments = "--gui"
        echo lnk.Description = "HackBot - AI Cybersecurity Assistant"
        echo lnk.WorkingDirectory = WshShell.ExpandEnvironmentStrings^("%%USERPROFILE%%"^)
        echo lnk.Save
    )
    cscript //nologo "%SHORTCUT_VBS%" 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Desktop shortcut created
    ) else (
        echo [WARN] Could not create desktop shortcut automatically
        echo         Run: hackbot --gui ^(to launch the desktop app^)
    )
    del "%SHORTCUT_VBS%" 2>nul

    REM Also add to Start Menu
    set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
    set SM_VBS=%TEMP%\hackbot_startmenu.vbs
    >"%SM_VBS%" (
        echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
        echo Set lnk = WshShell.CreateShortcut^("%STARTMENU%\HackBot.lnk"^)
        echo lnk.TargetPath = WshShell.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%"^) ^& "\Programs\Python\Python3*\Scripts\hackbot.exe"
        echo lnk.Arguments = "--gui"
        echo lnk.Description = "HackBot - AI Cybersecurity Assistant"
        echo lnk.WorkingDirectory = WshShell.ExpandEnvironmentStrings^("%%USERPROFILE%%"^)
        echo lnk.Save
    )
    cscript //nologo "%SM_VBS%" 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Start Menu shortcut created
    )
    del "%SM_VBS%" 2>nul
    echo.
)
exit /b 0

:usage
echo Usage: install.bat [pip^|local^|full]
echo.
echo   pip    Install HackBot via pip (default)
echo   local  Install from local source (dev mode)
echo   full   Install HackBot + show tool install links
exit /b 1
