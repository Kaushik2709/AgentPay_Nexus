@echo off
echo ========================================================
echo   Starting AgentPay Nexus (FastAPI Backend + Next.js)
echo ========================================================

:: Launch Backend in separate window
start "AgentPay Backend (FastAPI)" cmd /k "cd /d %~dp0server && (if not exist venv python -m venv venv) && call venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000"

:: Launch Frontend in separate window
start "AgentPay Frontend (Next.js)" cmd /k "cd /d %~dp0client && npm install && npm run dev"

echo.
echo Both services are launching in separate windows!
echo Backend:  http://127.0.0.1:8000  (API Docs: http://127.0.0.1:8000/docs)
echo Frontend: http://localhost:3000
echo.
pause
