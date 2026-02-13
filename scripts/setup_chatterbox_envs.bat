@echo off
REM =============================================================
REM  Chatterbox TTS Multi-Environment Setup — Windows 11
REM
REM  Creates two conda environments with SHARED torch/CUDA:
REM    chatterbox-official  →  original + turbo (same package)
REM    chatterbox-rsxdalv   →  rsxdalv-faster (torch.compile)
REM
REM  Your system CUDA 12.6 driver is NEVER touched.
REM  Switch between envs with: conda activate <env-name>
REM =============================================================

setlocal enabledelayedexpansion

where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [FAIL] conda not found in PATH.
    echo        Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo   Chatterbox Multi-Environment Setup (Windows 11)
echo   Two conda envs, shared CUDA 12.6, zero conflicts
echo  =====================================================
echo.
echo   [1] Create BOTH environments (recommended first time)
echo   [2] Create chatterbox-official only (original + turbo)
echo   [3] Create chatterbox-rsxdalv only (rsxdalv-faster)
echo   [4] Show status of existing environments
echo   [5] Exit
echo.

set /p CHOICE="  Enter choice [1-5]: "

if "%CHOICE%"=="1" goto BOTH
if "%CHOICE%"=="2" goto OFFICIAL
if "%CHOICE%"=="3" goto RSXDALV
if "%CHOICE%"=="4" goto STATUS
if "%CHOICE%"=="5" exit /b 0

echo [FAIL] Invalid choice.
pause
exit /b 1

:OFFICIAL
echo.
echo  Creating chatterbox-official environment...
call :CREATE_ENV chatterbox-official chatterbox-tts
if %ERRORLEVEL% neq 0 goto FAIL
echo.
echo  [OK] chatterbox-official ready!
echo       Activate with: conda activate chatterbox-official
echo       Models:        original + turbo
pause
exit /b 0

:RSXDALV
echo.
echo  Creating chatterbox-rsxdalv environment...
call :CREATE_ENV chatterbox-rsxdalv "git+https://github.com/rsxdalv/chatterbox.git@faster"
if %ERRORLEVEL% neq 0 goto FAIL
REM Install the one extra dep rsxdalv needs
conda activate chatterbox-rsxdalv && pip install resampy==0.4.3
echo.
echo  [OK] chatterbox-rsxdalv ready!
echo       Activate with: conda activate chatterbox-rsxdalv
echo       Models:        original (with torch.compile speed)
pause
exit /b 0

:BOTH
echo.
echo  Creating BOTH environments...
echo.
echo  --- Environment 1/2: chatterbox-official ---
call :CREATE_ENV chatterbox-official chatterbox-tts
if %ERRORLEVEL% neq 0 goto FAIL
echo.
echo  --- Environment 2/2: chatterbox-rsxdalv ---
call :CREATE_ENV chatterbox-rsxdalv "git+https://github.com/rsxdalv/chatterbox.git@faster"
if %ERRORLEVEL% neq 0 goto FAIL
conda activate chatterbox-rsxdalv && pip install resampy==0.4.3
echo.
echo  =====================================================
echo   BOTH environments created successfully!
echo  =====================================================
echo.
echo   conda activate chatterbox-official   # original + turbo
echo   conda activate chatterbox-rsxdalv    # rsxdalv-faster
echo.
echo   Then run: python scripts/install_chatterbox.py --check
echo   to verify each environment.
echo.
pause
exit /b 0

:STATUS
echo.
echo  Checking environments...
echo.
conda env list 2>nul | findstr chatterbox
echo.
for %%E in (chatterbox-official chatterbox-rsxdalv) do (
    echo  --- %%E ---
    conda run -n %%E --no-banner python -c "import torch; print(f'  torch={torch.__version__}, CUDA={torch.version.cuda}, GPU={torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" 2>nul
    if !ERRORLEVEL! neq 0 echo   [not found or torch missing]
    conda run -n %%E --no-banner python -c "from chatterbox.tts import ChatterboxTTS2; print('  ChatterboxTTS2: OK')" 2>nul
    conda run -n %%E --no-banner python -c "from chatterbox.tts import ChatterboxTurbo; print('  ChatterboxTurbo: OK')" 2>nul
    echo.
)
pause
exit /b 0

:CREATE_ENV
REM %1 = env name, %2 = chatterbox package to install
set ENV_NAME=%1
set CHATTERBOX_PKG=%~2

REM Check if env already exists
conda env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [WARN] Environment %ENV_NAME% already exists.
    set /p OVERWRITE="  Recreate it? [y/N]: "
    if /i not "!OVERWRITE!"=="y" (
        echo  Skipping %ENV_NAME%.
        exit /b 0
    )
    echo  Removing old %ENV_NAME%...
    conda env remove -n %ENV_NAME% -y >nul 2>&1
)

echo  Creating conda env: %ENV_NAME% (Python 3.11)...
conda create -n %ENV_NAME% python=3.11 -y
if %ERRORLEVEL% neq 0 exit /b 1

echo  Installing torch + CUDA 12.6 wheels...
conda run -n %ENV_NAME% --no-banner pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126
if %ERRORLEVEL% neq 0 exit /b 1

echo  Installing chatterbox (--no-deps)...
conda run -n %ENV_NAME% --no-banner pip install --no-deps %CHATTERBOX_PKG%
if %ERRORLEVEL% neq 0 exit /b 1

echo  Installing non-torch dependencies...
conda run -n %ENV_NAME% --no-banner pip install transformers accelerate conformer scipy tqdm librosa soundfile encodec nemo_text_processing huggingface-hub safetensors
if %ERRORLEVEL% neq 0 exit /b 1

echo  Verifying torch + CUDA...
conda run -n %ENV_NAME% --no-banner python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print(f'  torch {torch.__version__} + CUDA {torch.version.cuda} OK')"
if %ERRORLEVEL% neq 0 (
    echo  [WARN] CUDA check failed — torch may be CPU-only
)

exit /b 0

:FAIL
echo.
echo  [FAIL] Environment creation failed. See errors above.
pause
exit /b 1
