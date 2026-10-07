#!/bin/bash
echo "========================================================"
echo "  Starting AgentPay Nexus (FastAPI Backend + Next.js)"
echo "========================================================"

# Launch Backend
(
  echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
  cd server || exit
  python3 -m venv venv 2>/dev/null || python -m venv venv
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000
) &

# Launch Frontend
(
  echo "[2/2] Starting Next.js Frontend on http://localhost:3000 ..."
  cd client || exit
  npm install
  npm run dev
) &

echo "Both services started in background!"
echo "Backend: http://127.0.0.1:8000 (Docs: http://127.0.0.1:8000/docs)"
echo "Frontend: http://localhost:3000"
wait
