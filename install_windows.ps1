$ErrorActionPreference = "Stop"

Write-Host "xGet Windows installer" -ForegroundColor Cyan

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget was not found. Install Microsoft App Installer first."
}

$packages = @(
    @{ Id = "Python.Python.3.12"; Name = "Python" },
    @{ Id = "aria2.aria2"; Name = "aria2" },
    @{ Id = "Gyan.FFmpeg"; Name = "FFmpeg" },
    @{ Id = "DenoLand.Deno"; Name = "Deno" }
)

foreach ($package in $packages) {
    Write-Host "Installing $($package.Name)..."
    winget install --id $package.Id --exact --accept-source-agreements --accept-package-agreements --silent
}

$installDir = Join-Path $env:LOCALAPPDATA "xGet"
$binDir = Join-Path $env:LOCALAPPDATA "xGet\bin"
$venvDir = Join-Path $installDir ".venv"
New-Item -ItemType Directory -Force -Path $installDir, $binDir | Out-Null

Copy-Item (Join-Path $PSScriptRoot "xget.py") (Join-Path $installDir "xget.py") -Force
if (Test-Path (Join-Path $PSScriptRoot "cookies.txt")) {
    Copy-Item (Join-Path $PSScriptRoot "cookies.txt") (Join-Path $installDir "cookies.txt") -Force
}

$python = (Get-Command py -ErrorAction SilentlyContinue)
if ($python) {
    & py -3 -m venv $venvDir
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        $possiblePython = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if (-not $possiblePython) {
            throw "Python was installed but is not visible in this PowerShell session. Close PowerShell and run this installer again."
        }
        & $possiblePython.FullName -m venv $venvDir
    } else {
        & python -m venv $venvDir
    }
}
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Failed to create the xGet Python environment: $venvPython"
}
& $venvPython -m pip install --upgrade pip --pre "yt-dlp[default]" requests beautifulsoup4
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install the xGet Python modules. Check your internet connection and try again."
}
& $venvPython -c "from yt_dlp import YoutubeDL; import requests; from bs4 import BeautifulSoup; print('Python modules: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to verify the xGet Python modules."
}

$launcher = @"
@echo off
"$venvPython" "$installDir\xget.py" %*
"@
Set-Content -Path (Join-Path $binDir "xget.cmd") -Value $launcher -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $binDir) {
    $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $binDir } else { "$userPath;$binDir" }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

Write-Host ""
Write-Host "Installation complete. Open a new terminal and enter: xget" -ForegroundColor Green
Write-Host "Dependency check: xget --check"
