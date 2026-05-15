@echo off
:: ============================================================
:: CaptureIQ — Windows Build Script
:: Run from the sbir-pipeline\ directory:
::   build_windows.bat
:: ============================================================

echo ==================================================
echo   CaptureIQ — Windows Build
echo ==================================================

:: 1. Install PyInstaller if missing
python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [BUILD] Installing PyInstaller...
    pip install pyinstaller
)

:: 2. Install requirements
echo [BUILD] Installing requirements...
pip install -r requirements.txt

:: 3. Clean previous build
echo [BUILD] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

:: 4. Run PyInstaller
echo [BUILD] Running PyInstaller...
python -m PyInstaller CaptureIQ_windows.spec --noconfirm

:: 5. Report result
if exist dist\CaptureIQ\CaptureIQ.exe (
    echo.
    echo ==================================================
    echo   Build successful!
    echo   App: %CD%\dist\CaptureIQ\CaptureIQ.exe
    echo.
    echo   To distribute:
    echo   Zip the dist\CaptureIQ\ folder and share it.
    echo   Recipients run CaptureIQ.exe — no install needed.
    echo ==================================================
) else (
    echo.
    echo [ERROR] Build failed — check output above.
    exit /b 1
)
