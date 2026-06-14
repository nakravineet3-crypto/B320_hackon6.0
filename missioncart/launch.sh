#!/bin/bash

echo ""
echo "=========================================="
echo "  MISSIONCART DEMO LAUNCHER"
echo "=========================================="
echo ""

# Step 1: Update frontend .env with LAN IP
echo "[1/4] Detecting LAN IP and updating frontend .env..."
python3 scripts/update_env.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to update .env"
    exit 1
fi
echo ""

# Step 2: Start backend in new terminal
echo "[2/4] Starting backend server..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"'
else
    # Linux
    gnome-terminal -- bash -c "cd $(pwd)/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; exec bash" 2>/dev/null || \
    xterm -e "cd $(pwd)/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" &
fi
echo ""

# Step 3: Wait for backend
echo "[3/4] Waiting for backend to be ready..."
python3 scripts/health_check.py http://localhost:8000
if [ $? -ne 0 ]; then
    echo "WARNING: Backend may not be ready. Check the backend terminal."
    sleep 5
fi
echo ""

# Step 4: Start Expo
echo "[4/4] Starting Expo for Android..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/frontend && npx expo start --android --clear"'
else
    gnome-terminal -- bash -c "cd $(pwd)/frontend && npx expo start --android --clear; exec bash" 2>/dev/null || \
    xterm -e "cd $(pwd)/frontend && npx expo start --android --clear" &
fi
echo ""

echo "=========================================="
echo "  SERVERS STARTING IN NEW TERMINALS"
echo "=========================================="
echo ""
echo "Backend:  http://localhost:8000"
echo "Health:   http://localhost:8000/health"
echo ""
