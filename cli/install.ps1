$ErrorActionPreference = "Stop"

$InstallDir = "$env:LOCALAPPDATA\vew"
$BinName = "vew.exe"

Write-Host "Building vew (release)..."
cargo build --release

Write-Host "Installing to $InstallDir\$BinName..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item "target\release\$BinName" "$InstallDir\$BinName" -Force

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -split ";" | Where-Object { $_ -eq $InstallDir }) {
    Write-Host "✓ $InstallDir is already in your PATH."
} else {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
    Write-Host "✓ Added $InstallDir to your user PATH."
    Write-Host "  Restart your terminal for the change to take effect."
}

Write-Host "Done. Run 'vew --help' to get started."
