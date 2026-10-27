param([switch]$Apply, [switch]$Quiet)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$base = 'https://raw.githubusercontent.com/mmgblabel-png/SPMG-Quant-Nexus-Access-Verifier/main/command-center'
$tempDir = Join-Path $env:TEMP ('spmg-update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
try {
    $manifestFile = Join-Path $tempDir 'manifest.json'
    Invoke-WebRequest -Uri "$base/manifest.json" -OutFile $manifestFile -UseBasicParsing -TimeoutSec 25
    $manifest = Get-Content $manifestFile -Raw | ConvertFrom-Json
    $allowed = @('app.py','start.ps1','START-SPMG.cmd','UPDATE-SPMG.cmd','README.md','test_app.py','update.ps1','path_builder.py')
    foreach ($entry in $manifest.files) {
        if ($entry.path -notin $allowed) { throw "Onbekend updatebestand: $($entry.path)" }
        if ($entry.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw "Ongeldige checksum: $($entry.path)" }
        $stage = Join-Path $tempDir $entry.path
        Invoke-WebRequest -Uri "$base/$($entry.path)" -OutFile $stage -UseBasicParsing -TimeoutSec 25
        $hash = (Get-FileHash -LiteralPath $stage -Algorithm SHA256).Hash
        if ($hash -ine $entry.sha256) { throw "Checksum onjuist: $($entry.path)" }
    }
    $changes = @()
    foreach ($entry in $manifest.files) {
        $target=Join-Path $here $entry.path
        if (-not (Test-Path $target) -or (Get-FileHash $target -Algorithm SHA256).Hash -ine $entry.sha256) { $changes += $entry.path }
    }
    if ($changes.Count -eq 0) { if (-not $Quiet) { Write-Host 'SPMG is bijgewerkt.' -ForegroundColor Green }; return }
    $backup = Join-Path $here ('backups\update-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($name in $changes) {
        $target=Join-Path $here $name
        if (Test-Path $target) { Copy-Item -LiteralPath $target -Destination (Join-Path $backup $name) -Force }
        Copy-Item -LiteralPath (Join-Path $tempDir $name) -Destination $target -Force
    }
    if (-not $Quiet) { Write-Host "SPMG bijgewerkt naar $($manifest.version). Bestanden: $($changes -join ', ')" -ForegroundColor Green }
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}