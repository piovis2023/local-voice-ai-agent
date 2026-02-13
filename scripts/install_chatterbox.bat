@echo off
REM =============================================================
REM  Chatterbox TTS Safe Installer — Windows 11
REM  Double-click this file or run from cmd/PowerShell.
REM =============================================================
REM
REM  This script will NOT touch your existing torch/CUDA/cuDNN.
REM  It uses --no-deps to install chatterbox safely.
REM
REM  Usage:
REM    install_chatterbox.bat original
REM    install_chatterbox.bat turbo
REM    install_chatterbox.bat rsxdalv-faster
REM    install_chatterbox.bat --check
REM
REM  If no argument given, shows a menu.
REM =============================================================

setlocal enabledelayedexpansion

REM --- Find Python ---
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Python not found in PATH.
    echo        Install Python 3.11 from https://python.org
    pause
    exit /b 1
)

REM --- If argument provided, use it directly ---
if not "%~1"=="" (
    python "%~dp0install_chatterbox.py" %*
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [FAIL] Installation failed. See errors above.
        pause
        exit /b 1
    )
    echo.
    echo Done. Press any key to close.
    pause
    exit /b 0
)

REM --- No argument: show menu ---
echo.
echo  ============================================
echo   Chatterbox TTS Safe Installer
echo   (will NOT touch your torch/CUDA drivers)
echo  ============================================
echo.
echo   Select a model to install:
echo.
echo   [1] original        Voice cloning + emotion control
echo                        0.5B params, ~1.5-2.5s/sentence on RTX 4080
echo.
echo   [2] turbo            Fastest official, English-only
echo                        350M params, ~0.5-0.8s/sentence on RTX 4080
echo.
echo   [3] rsxdalv-faster   torch.compile + CUDA graphs (max speed)
echo                        ~1.0-1.8s/sentence on RTX 4080
echo.
echo   [4] Check only       Verify environment, install nothing
echo.
echo   [5] Exit
echo.

set /p CHOICE="  Enter choice [1-5]: "

if "%CHOICE%"=="1" set MODEL=original
if "%CHOICE%"=="2" set MODEL=turbo
if "%CHOICE%"=="3" set MODEL=rsxdalv-faster
if "%CHOICE%"=="4" (
    python "%~dp0install_chatterbox.py" --check
    pause
    exit /b 0
)
if "%CHOICE%"=="5" exit /b 0

if not defined MODEL (
    echo [FAIL] Invalid choice: %CHOICE%
    pause
    exit /b 1
)

echo.
echo  Installing: %MODEL%
echo  This will use --no-deps to protect your drivers.
echo.

python "%~dp0install_chatterbox.py" %MODEL% --save-snapshot "%~dp0install_snapshot.json"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] Installation failed. See errors above.
    echo        Snapshot saved to install_snapshot.json for diagnostics.
    pause
    exit /b 1
)

echo.
echo  Success! Snapshot saved to install_snapshot.json
echo.
pause
