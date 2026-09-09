<#
.SYNOPSIS
    Start the TruthShield API locally and serve the demo page from the same
    origin (http://localhost:8000/demo).

.DESCRIPTION
    Windows counterpart of scripts/start_local_demo.sh. Serving the demo page
    from the API itself removes both the CORS pre-flight and the mixed-content
    restriction that applies when the GitHub Pages build calls http://localhost.

.EXAMPLE
    ./scripts/start_local_demo.ps1
    ./scripts/start_local_demo.ps1 -Port 8080
    ./scripts/start_local_demo.ps1 -FullDeps      # includes OCR/torch
#>
param(
    [int]$Port = 8000,
    [switch]$FullDeps
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvDir = ".venv"
$ReqFile = if ($FullDeps) { "requirements.txt" } else { "requirements-demo.txt" }

# --- 1. Virtual environment ------------------------------------------------
if (-not (Test-Path $VenvDir)) {
    Write-Host "📦 Creating virtual environment in $VenvDir ..."
    python -m venv $VenvDir
}
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { $VenvPy = Join-Path $VenvDir "bin/python" }

# --- 2. Dependencies (skipped when already importable) ---------------------
& $VenvPy -c "import fastapi, uvicorn, openai, tweepy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "📦 Installing dependencies from $ReqFile ..."
    & $VenvPy -m pip install --quiet --upgrade pip
    & $VenvPy -m pip install --quiet -r $ReqFile
} else {
    Write-Host "✅ Dependencies already installed (skipping pip)."
}

# --- 3. Configuration ------------------------------------------------------
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env found — copying .env.example (never commit .env)."
    Copy-Item ".env.example" ".env"
}

# --- 4. Pre-flight: report which analysis backend will be used -------------
$envText = Get-Content ".env" -Raw
if ($env:OPENAI_BASE_URL) {
    Write-Host "🔌 LLM endpoint: $($env:OPENAI_BASE_URL) (local / OpenAI-compatible)"
} elseif ($envText -match '(?m)^OPENAI_API_KEY=(?!your_).+') {
    Write-Host "🔑 LLM endpoint: api.openai.com (requires internet access)"
} else {
    Write-Host "⚠️  No usable OPENAI_API_KEY: the API will answer in DEGRADED mode"
    Write-Host "    (sources are returned, but no verdict and no Guardian response)."
    Write-Host "    Offline alternative — point the client at a local model:"
    Write-Host '      $env:OPENAI_API_KEY="local"; $env:OPENAI_BASE_URL="http://localhost:11434/v1"'
    Write-Host '      $env:OPENAI_MODEL_GENERATION="llama3.1"; $env:OPENAI_MODEL_CLASSIFICATION="llama3.1"'
}

# --- 5. Run ----------------------------------------------------------------
Write-Host ""
Write-Host "🛡️  TruthShield API starting"
Write-Host "    Demo page : http://localhost:$Port/demo"
Write-Host "    API docs  : http://localhost:$Port/docs"
Write-Host "    Health    : http://localhost:$Port/health"
Write-Host ""

& $VenvPy -m uvicorn src.api.main:app --host 0.0.0.0 --port $Port
