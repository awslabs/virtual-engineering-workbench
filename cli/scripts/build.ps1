param(
    [Parameter(Mandatory)][string]$Target
)
$ErrorActionPreference = "Stop"
$BinName = "vew"

rustup target add $Target 2>$null
cargo build --release --target $Target

New-Item -ItemType Directory -Force -Path dist | Out-Null
$src = "target\$Target\release\$BinName.exe"
$archive = "dist\$BinName-$Target.zip"
Compress-Archive -Path $src -DestinationPath $archive -Force
(Get-FileHash -Algorithm SHA256 $archive).Hash + "  " + (Split-Path $archive -Leaf) | Out-File -Encoding ascii "$archive.sha256"
Write-Host "Built: $archive"
