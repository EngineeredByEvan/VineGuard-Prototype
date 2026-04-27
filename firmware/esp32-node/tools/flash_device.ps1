# flash_device.ps1 — Provision and flash a VineGuard node (Windows PowerShell)
#
# Usage:
#   .\flash_device.ps1 -Serial VG-000001 [-Env lora_p2p] [-Manifest .\provisioning_manifest.csv] [-Port COM3]
#
# Requires: Python 3, PlatformIO Core (pio in PATH)

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Serial,

    [string]$Env = "lora_p2p",

    [string]$Manifest = "$PSScriptRoot\provisioning_manifest.csv",

    [string]$Port = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir   = $PSScriptRoot
$FirmwareDir = Split-Path $ScriptDir -Parent

# ─── Check required tools ─────────────────────────────────────────────────────
foreach ($cmd in @("python", "pio")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "Command '$cmd' not found. Install Python 3 and PlatformIO Core."
        exit 1
    }
}

# ─── Check manifest ───────────────────────────────────────────────────────────
if (-not (Test-Path $Manifest)) {
    Write-Error "Manifest not found: $Manifest`n  Copy provisioning_manifest.example.csv and fill in real values."
    exit 1
}

# ─── Validate serial in manifest ─────────────────────────────────────────────
$manifestContent = Get-Content $Manifest
$serialFound = $manifestContent | Where-Object { $_ -match "^$Serial," }
if (-not $serialFound) {
    Write-Error "Serial '$Serial' not found in $Manifest"
    exit 1
}

Write-Host "=== VineGuard Flash Tool ===" -ForegroundColor Cyan
Write-Host "Serial:   $Serial"
Write-Host "Env:      $Env"
Write-Host "Manifest: $Manifest"
Write-Host ""

# ─── Generate keys header ─────────────────────────────────────────────────────
Write-Host "[1/4] Generating lorawan_keys.h..." -ForegroundColor Yellow
python "$ScriptDir\make_keys_header.py" --serial $Serial --manifest $Manifest
if ($LASTEXITCODE -ne 0) { Write-Error "Key generation failed"; exit 1 }

# ─── Build firmware ───────────────────────────────────────────────────────────
Write-Host "[2/4] Building firmware (env: $Env)..." -ForegroundColor Yellow
Set-Location $FirmwareDir
pio run --environment $Env
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }

# ─── Flash device ─────────────────────────────────────────────────────────────
Write-Host "[3/4] Flashing device..." -ForegroundColor Yellow
if ($Port) {
    pio run --environment $Env --target upload --upload-port $Port
} else {
    pio run --environment $Env --target upload
}
if ($LASTEXITCODE -ne 0) { Write-Error "Flash failed"; exit 1 }

# ─── Print label info ─────────────────────────────────────────────────────────
$row     = $manifestContent | Where-Object { $_ -match "^$Serial," } | Select-Object -First 1
$fields  = $row -split ","
$DevId   = $fields[1].Trim()
$DevEui  = $fields[2].Trim()

Write-Host "[4/4] Flash complete!" -ForegroundColor Green
Write-Host ""
Write-Host "────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  DEVICE LABEL"
Write-Host "  Serial:   $Serial"
Write-Host "  DeviceID: $DevId"
Write-Host "  DevEUI:   $DevEui"
Write-Host "────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  Print this label and stick it inside the enclosure."
Write-Host ""
