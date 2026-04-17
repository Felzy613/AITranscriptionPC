param(
    [ValidateSet("x64", "x86")]
    [string]$TargetArchitecture,

    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VersionMatch = Select-String -Path ".\setup.iss" -Pattern '^#define MyAppVersion "(.+)"$'
if (-not $VersionMatch) {
    throw "Could not determine app version from setup.iss"
}
$AppVersion = $VersionMatch.Matches[0].Groups[1].Value

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

if ([string]::IsNullOrWhiteSpace($TargetArchitecture)) {
    $TargetArchitecture = Read-Host "Select target architecture [x64/x86] (default x64)"
}
$TargetArchitecture = if ([string]::IsNullOrWhiteSpace($TargetArchitecture)) { "x64" } else { $TargetArchitecture.Trim().ToLower() }

if ($TargetArchitecture -eq 'x86' -or $TargetArchitecture -eq 'i386') {
    throw "Spec-based builds currently support x64 only."
} else {
    $pyInstallerArch = 'x64'
}

Write-Host "Compiling Python to executable for $pyInstallerArch..." -ForegroundColor Yellow
& ".\venv\Scripts\pyinstaller.exe" --clean --noconfirm build-spec.spec

$BuiltExe = ".\dist\AITranscriptionPC\AI Transcription PC.exe"
if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller build did not produce $BuiltExe"
}

if ($SkipInstaller) {
    Write-Host ""
    Write-Host "Skipping installer build." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  Build Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Executable:  dist\AITranscriptionPC\AI Transcription PC.exe" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

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

$BuiltInstaller = ".\dist-installer\AITranscriptionPCSetup-v$AppVersion.exe"
if (-not (Test-Path $BuiltInstaller)) {
    throw "Installer build did not produce $BuiltInstaller"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Executable:  $BuiltExe" -ForegroundColor Cyan
Write-Host "  Installer:   $BuiltInstaller" -ForegroundColor Cyan
Write-Host ""
