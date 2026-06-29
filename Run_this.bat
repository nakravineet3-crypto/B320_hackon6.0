@echo off
setlocal enabledelayedexpansion
title MissionCart - Setup and Run

echo.
echo ============================================================
echo           MissionCart - Auto Setup and Run
echo ============================================================
echo.

:: -------------------------------------------------------
:: STEP 0: Check prerequisites
:: -------------------------------------------------------
echo [1/6] Checking prerequisites...

where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Node.js is not installed.
    echo  Please download and install it from https://nodejs.org
    echo  Then re-run this script.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo  ERROR: npm not found. Reinstall Node.js from https://nodejs.org
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: Python is not installed.
        echo  Please download and install it from https://python.org
        echo  Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=py -3.12
)

where adb >nul 2>&1
if errorlevel 1 (
    echo.
    echo  WARNING: ADB not found in PATH.
    echo  Trying common locations...
    if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
        set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
        echo  Found ADB at: !ADB!
    ) else if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe" (
        set ADB=%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe
        echo  Found ADB at: !ADB!
    ) else (
        echo.
        echo  ERROR: ADB not found. Download platform-tools from:
        echo  https://developer.android.com/tools/releases/platform-tools
        echo  Extract it and add the folder to your PATH, then re-run.
        pause
        exit /b 1
    )
) else (
    set ADB=adb
)

echo  Node : OK
echo  npm  : OK
echo  Python: OK
echo  ADB  : OK
echo.

:: -------------------------------------------------------
:: STEP 1: Check ADB device
:: -------------------------------------------------------
echo [2/6] Checking for connected Android device...

"%ADB%" start-server >nul 2>&1
for /f "skip=1 tokens=1,2" %%a in ('"%ADB%" devices') do (
    if "%%b"=="device" (
        set DEVICE_SERIAL=%%a
    )
)

if not defined DEVICE_SERIAL (
    echo.
    echo  No device detected. Please:
    echo   1. Connect your phone via USB
    echo   2. Enable USB Debugging: Settings ^> Developer Options ^> USB Debugging
    echo   3. Tap "Allow" on the USB debugging prompt on your phone
    echo.
    echo  Waiting 15 seconds for device...
    timeout /t 15 /nobreak >nul
    for /f "skip=1 tokens=1,2" %%a in ('"%ADB%" devices') do (
        if "%%b"=="device" set DEVICE_SERIAL=%%a
    )
    if not defined DEVICE_SERIAL (
        echo  Still no device found. Exiting.
        pause
        exit /b 1
    )
)

echo  Device connected: %DEVICE_SERIAL%
echo.

:: -------------------------------------------------------
:: STEP 2: Backend setup
:: -------------------------------------------------------
echo [3/6] Setting up Python backend...

set BACKEND_DIR=%~dp0missioncart\backend
set VENV_DIR=%BACKEND_DIR%\venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo  Creating virtual environment...
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo  Installing backend dependencies...
"%VENV_DIR%\Scripts\pip.exe" install -r "%BACKEND_DIR%\requirements.txt" --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  ERROR: Failed to install backend requirements.
    pause
    exit /b 1
)
echo  Backend ready.
echo.

:: -------------------------------------------------------
:: STEP 3: Frontend setup
:: -------------------------------------------------------
echo [4/6] Setting up frontend...

set FRONTEND_DIR=%~dp0missioncart\frontend

if not exist "%FRONTEND_DIR%\node_modules" (
    echo  Installing npm packages (this may take a few minutes)...
    pushd "%FRONTEND_DIR%"
    npm install --legacy-peer-deps
    if errorlevel 1 (
        echo  ERROR: npm install failed.
        popd
        pause
        exit /b 1
    )
    popd
) else (
    echo  node_modules found. Skipping install.
)

echo  Frontend ready.
echo.

:: -------------------------------------------------------
:: STEP 4: Start backend in a new window
:: -------------------------------------------------------
echo [5/6] Starting backend server...

:: Write a helper bat to %TEMP% (no spaces in path) to avoid CMD quoting issues
> "%TEMP%\mc_backend.bat" echo @echo off
>> "%TEMP%\mc_backend.bat" echo cd /d "%BACKEND_DIR%"
>> "%TEMP%\mc_backend.bat" echo "%VENV_DIR%\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload

start "MissionCart Backend" cmd /k "%TEMP%\mc_backend.bat"

echo  Backend starting at http://localhost:8000
echo  Waiting 8 seconds for it to boot...
timeout /t 8 /nobreak >nul
echo.

:: -------------------------------------------------------
:: STEP 5: Start Expo and open on device via ADB
:: -------------------------------------------------------
echo [6/6] Starting Expo and launching on device...

:: Forward the Metro bundler port so device can reach it over USB
"%ADB%" -s %DEVICE_SERIAL% reverse tcp:8081 tcp:8081 >nul 2>&1
"%ADB%" -s %DEVICE_SERIAL% reverse tcp:8000 tcp:8000 >nul 2>&1

echo  ADB port forwarding set (8081 Metro, 8000 backend).
echo.

:: Open Expo Go on the device if installed
"%ADB%" -s %DEVICE_SERIAL% shell monkey -p host.exp.exponent -c android.intent.category.LAUNCHER 1 >nul 2>&1

:: Write a helper bat to %TEMP% (no spaces in path) to avoid CMD quoting issues
> "%TEMP%\mc_frontend.bat" echo @echo off
>> "%TEMP%\mc_frontend.bat" echo cd /d "%FRONTEND_DIR%"
>> "%TEMP%\mc_frontend.bat" echo npx expo start --android --localhost

start "MissionCart Expo" cmd /k "%TEMP%\mc_frontend.bat"

echo.
echo ============================================================
echo  MissionCart is starting!
echo.
echo  - Backend : http://localhost:8000
echo  - Metro   : http://localhost:8081
echo  - Expo Go will open automatically on your phone.
echo.
echo  If the app does not open automatically:
echo    1. Open Expo Go on your phone
echo    2. Tap "Enter URL manually"
echo    3. Enter: exp://localhost:8081
echo.
echo  Keep this window and both server windows open.
echo ============================================================
echo.
pause
