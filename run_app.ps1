# ConfiRoute Unified Full-Stack Application Launcher
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ConfiRoute - Confidence-Aware Medical LLM Safety Layer   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting unified full-stack application at http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Interactive API documentation available at http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to terminate." -ForegroundColor Gray
Write-Host ""

& ".\.venv\Scripts\uvicorn.exe" confiroute.api.main:app --host 127.0.0.1 --port 8000 --reload
