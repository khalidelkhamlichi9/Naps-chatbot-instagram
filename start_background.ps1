
# start_background.ps1
# This script starts the NAPS Chatbot and Ngrok in the background on Windows.

$env_file = ".env"
if (-Not (Test-Path $env_file)) {
    Write-Host "❌ Error: .env file not found!" -ForegroundColor Red
    exit
}

# Load variables from .env manually (simple parser)
foreach ($line in Get-Content $env_file) {
    if ($line -match "^(?<name>[^#=]+)=(?<value>.*)$") {
        $name = $Matches['name'].Trim()
        $value = $Matches['value'].Trim()
        Set-Item -Path "Env:$name" -Value $value
    }
}

Write-Host "🚀 Starting Chatbot NAPS in background..." -ForegroundColor Cyan
# Using the virtual environment's python
Start-Process "venv\Scripts\python.exe" -ArgumentList "main.py" -WindowStyle Hidden -PassThru

Write-Host "🌐 Starting Ngrok with domain: $env:NGROK_DOMAIN" -ForegroundColor Green
Start-Process ngrok -ArgumentList "http 8000 --domain=$env:NGROK_DOMAIN --authtoken=$env:NGROK_AUTHTOKEN" -WindowStyle Hidden

Write-Host "✅ Both processes are running in the background." -ForegroundColor Yellow
Write-Host "Check your ngrok dashboard for the status."
