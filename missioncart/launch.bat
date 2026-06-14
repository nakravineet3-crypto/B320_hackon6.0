@echo off
echo.
echo ==========================================
echo   MISSIONCART DEMO LAUNCHER
echo ==========================================
echo.

REM Step 1: Detect LAN IP and update frontend .env
echo [1/4] Detecting LAN IP and updating frontend .env...
python scripts/update_env.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to update .env
    echo Make sure Python is installed
    pause
    exit /b 1
)
echo.

REM Step 2: Start backend in new terminal window
echo [2/4] Starting backend server...
start "MissionCart Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo.

REM Step 3: Wait for backend to be ready
echo [3/4] Waiting for backend to be ready...
python scripts/health_check.py http://localhost:8000
if %errorlevel% neq 0 (
    echo WARNING: Backend may not be ready
    echo Check the Backend terminal window
    timeout /t 5 /nobreak > nul
)
echo.

REM Step 4: Start Expo in new terminal window
echo [4/4] Starting Expo for Android...
start "MissionCart Frontend" cmd /k "cd frontend && npx expo start --android --clear"
echo.

echo ==========================================
echo   BOTH SERVERS STARTING IN NEW WINDOWS
echo ==========================================
echo.
echo Backend:  http://localhost:8000
echo Health:   http://localhost:8000/health
echo.
echo Scan the QR code in the Expo window
echo OR press 'a' in the Expo window for Android
echo.
echo Press any key to close this launcher...
pause > nul
