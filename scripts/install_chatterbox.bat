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
REM    install_chatterbox.bat --swap turbo
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
        echo [FAIL] Operation failed. See errors above.
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
echo   INSTALL (fresh):
echo   [1] original        Voice cloning + emotion control
echo                        0.5B params, ~1.5-2.5s/sentence on RTX 4080
echo.
echo   [2] turbo            Fastest official, English-only
echo                        350M params, ~0.5-0.8s/sentence on RTX 4080
echo.
echo   [3] rsxdalv-faster   torch.compile + CUDA graphs (max speed)
echo                        ~1.0-1.8s/sentence on RTX 4080
echo.
echo   SWAP (keep deps, change model):
echo   [4] Swap to original
echo   [5] Swap to turbo
echo   [6] Swap to rsxdalv-faster
echo.
echo   OTHER:
echo   [7] Check only       Verify environment, install nothing
echo   [8] Setup multi-env  Create separate conda envs for A/B testing
echo   [9] Exit
echo.

set /p CHOICE="  Enter choice [1-9]: "

if "%CHOICE%"=="1" set "MODEL=original" & set "MODE=install"
if "%CHOICE%"=="2" set "MODEL=turbo" & set "MODE=install"
if "%CHOICE%"=="3" set "MODEL=rsxdalv-faster" & set "MODE=install"
if "%CHOICE%"=="4" set "MODEL=original" & set "MODE=swap"
if "%CHOICE%"=="5" set "MODEL=turbo" & set "MODE=swap"
if "%CHOICE%"=="6" set "MODEL=rsxdalv-faster" & set "MODE=swap"
if "%CHOICE%"=="7" (
    python "%~dp0install_chatterbox.py" --check
    pause
    exit /b 0
)
if "%CHOICE%"=="8" (
    call "%~dp0setup_chatterbox_envs.bat"
    exit /b 0
)
if "%CHOICE%"=="9" exit /b 0

if not defined MODEL (
    echo [FAIL] Invalid choice: %CHOICE%
    pause
    exit /b 1
)

echo.
if "%MODE%"=="swap" (
    echo  Swapping to: %MODEL%
    echo  Non-torch deps will be kept ^(99%% overlap^).
    echo.
    python "%~dp0install_chatterbox.py" --swap %MODEL% --save-snapshot "%~dp0install_snapshot.json"
) else (
    echo  Installing: %MODEL%
    echo  This will use --no-deps to protect your drivers.
    echo.
    python "%~dp0install_chatterbox.py" %MODEL% --save-snapshot "%~dp0install_snapshot.json"
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] Operation failed. See errors above.
    echo        Snapshot saved to install_snapshot.json for diagnostics.
    pause
    exit /b 1
)

echo.
echo  Success! Snapshot saved to install_snapshot.json
echo.
pause
