$installDir = Join-Path $env:LOCALAPPDATA "xGet"
$binDir = Join-Path $installDir "bin"

if (Test-Path $installDir) {
    Remove-Item $installDir -Recurse -Force
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = (($userPath -split ";") | Where-Object { $_ -and ($_ -ne $binDir) }) -join ";"
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")
Write-Host "xGet was removed. Shared tools such as aria2 and FFmpeg were kept because other applications may use them."
