# AI Hedge Fund — Start-Skript
# Startet Backend (FastAPI) und Frontend (Next.js) gleichzeitig

Write-Host "=== AI Hedge Fund wird gestartet ===" -ForegroundColor Cyan

# Backend in neuem Fenster starten
Write-Host "Starte Backend (FastAPI :8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location 'C:\Users\Tim\hedge-fund\backend'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

# Frontend in neuem Fenster starten (Next.js Binary direkt nutzen)
Write-Host "Starte Frontend (Next.js :3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location 'C:\Users\Tim\hedge-fund\frontend'; & 'C:\Users\Tim\hedge-fund\frontend\node_modules\.bin\next.cmd' dev"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Backend:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Beide Fenster mit Ctrl+C beenden." -ForegroundColor Gray

# Browser öffnen
Start-Sleep -Seconds 10
Start-Process "http://localhost:3000"
