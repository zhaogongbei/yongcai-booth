# AI Booth Backend - Quick Start Script for Windows

Write-Host "🚀 Starting AI Booth Backend..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "📝 Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "⚠️  Please update .env with your configuration!" -ForegroundColor Yellow
}

# Check if virtual environment exists
if (-not (Test-Path venv)) {
    Write-Host "🐍 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
Write-Host "🗄️  Running database migrations..." -ForegroundColor Cyan
alembic upgrade head

# Start the server
Write-Host "✅ Starting FastAPI server..." -ForegroundColor Green
Write-Host "📡 API will be available at http://localhost:8000" -ForegroundColor Green
Write-Host "📚 API docs will be available at http://localhost:8000/docs" -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
