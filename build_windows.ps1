$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AI Transcription PC Build" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Create or use existing venv
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Activating venv and installing dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
& ".\venv\Scripts\python.exe" -m pip install pyinstaller --quiet

$arch = Read-Host "Select target architecture [x64/x86] (default x64)"
if ([string]::IsNullOrWhiteSpace($arch)) {
    $arch = 'x64'
}
$arch = $arch.Trim().ToLower()
if ($arch -eq 'x86' -or $arch -eq 'i386') {
    $pyInstallerArch = 'x86'
} else {
    $pyInstallerArch = 'x64'
}

Write-Host "Compiling Python to executable for $pyInstallerArch..." -ForegroundColor Yellow
& ".\venv\Scripts\pyinstaller.exe" --clean --noconfirm --target-architecture $pyInstallerArch build-spec.spec

# Check for Inno Setup
$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$Iscc = $IsccCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $Iscc) {
    Write-Host ""
    Write-Host "ERROR: Inno Setup 6 not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Download and install Inno Setup 6:" -ForegroundColor Yellow
    Write-Host "https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
    Write-Host ""
    throw "Inno Setup 6 required to build installer"
}

Write-Host "Building installer with Inno Setup..." -ForegroundColor Yellow
& $Iscc ".\setup.iss"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Executable:  dist\AITranscriptionPC\AI Transcription PC.exe" -ForegroundColor Cyan
Write-Host "  Installer:   dist-installer\AITranscriptionPCSetup-v1.0.1.exe" -ForegroundColor Cyan
Write-Host ""
