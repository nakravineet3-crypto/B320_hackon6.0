# How to Launch MissionCart

## One-command launch (Windows):
```
cd missioncart
launch.bat
```

## One-command launch (Mac/Linux):
```
cd missioncart
chmod +x launch.sh
./launch.sh
```

## What it does:
1. Detects your LAN IP automatically
2. Updates frontend/.env with correct API URL
3. Starts backend (FastAPI) in a new terminal
4. Waits for backend to be ready
5. Starts Expo (React Native) in a new terminal

## Prerequisites:
- Python 3.11 installed
- Node.js installed
- Android device connected via USB with USB debugging on
- OR Android emulator running

## Manual launch (if script fails):

Terminal 1 — Backend:
```
cd missioncart/backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — Frontend:
```
cd missioncart/frontend
npx expo start --android
```
