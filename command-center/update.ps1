param([switch]$Apply, [switch]$Quiet)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$base = 'https://raw.githubusercontent.com/mmgblabel-png/SPMG-Quant-Nexus-Access-Verifier/main/command-center'
$tempDir = Join-Path $env:TEMP ('spmg-update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -LiteralPath $tempDir -Force | Out-Null
try {
    $manifestFile = Join-Path $tempDir 'manifest.json'
    Invoke-WebRequest -Uri "$base/manifest.json" -OutFile $manifestFile -UseBasicParsing -TimeoutSec 30
    $manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
    $entries = @($manifest.files)
    if ($entries.Count -lt 1 -or $entries.Count -gt 30) { throw 'Update-manifest bevat ongeldig aantal bestanden.' }
    if ([string]::IsNullOrWhiteSpace([string]$manifest.version)) { throw 'Update-manifest mist versie.' }

    # Restrict to root-level source/docs/launcher files. Never follow a manifest
    # path into data/, users' Game Maker projects, wallets or the agent runtime.
    # Unlike a frozen filename allowlist, future safe source names are accepted.
    $seen = @{}
    foreach ($entry in $entries) {
        $name = [string]$entry.path
        if ($name -cnotmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\.(py|ps1|cmd|md)$') {
            throw "Onveilig pad in update-manifest: $name"
        }
        if ($name -in @('bootstrap.ps1')) {
            throw "Bootstrap wordt niet door een lopende installatie gewijzigd."
        }
        if ($seen.ContainsKey($name.ToLowerInvariant())) { throw "Dubbele manifestvermelding: $name" }
        $seen[$name.ToLowerInvariant()] = $true
        if ([string]$entry.sha256 -notmatch '^[a-fA-F0-9]{64}$') {
            throw "Ongeldige SHA-256 voor $name"
        }
        $stage = Join-Path $tempDir $name
        Invoke-WebRequest -Uri "$base/$name" -OutFile $stage -UseBasicParsing -TimeoutSec 30
        if ((Get-Item -LiteralPath $stage).Length -gt 2000000) {
            throw "Updatebestand te groot: $name"
        }
        $hash = (Get-FileHash -LiteralPath $stage -Algorithm SHA256).Hash
        if ($hash -ine [string]$entry.sha256) { throw "Checksum onjuist: $name" }
        if ($name.EndsWith('.py', [StringComparison]::OrdinalIgnoreCase)) {
            & py -3 -m py_compile $stage
            if ($LASTEXITCODE -ne 0) { throw "Python-syntaxcontrole mislukt: $name" }
        }
    }

    $changes = @()
    foreach ($entry in $entries) {
        $name = [string]$entry.path
        $target = Join-Path $here $name
        if (-not (Test-Path -LiteralPath $target) -or
            (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine [string]$entry.sha256) {
            $changes += $name
        }
    }
    if ($changes.Count -eq 0) {
        if (-not $Quiet) { Write-Host "SPMG v$($manifest.version) is al bijgewerkt." -ForegroundColor Green }
        return
    }

    $backup = Join-Path $here ('backups\update-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    $attempted = @()
    try {
        foreach ($name in $changes) {
            $target = Join-Path $here $name
            if (Test-Path -LiteralPath $target) {
                Copy-Item -LiteralPath $target -Destination (Join-Path $backup $name) -Force -ErrorAction Stop
            }
        }
        foreach ($name in $changes) {
            $target = Join-Path $here $name
            $attempted += $name
            Copy-Item -LiteralPath (Join-Path $tempDir $name) -Destination $target -Force -ErrorAction Stop
        }
        if (-not $Quiet) {
            Write-Host "SPMG bijgewerkt naar $($manifest.version): $($changes -join ', ')" -ForegroundColor Green
        }
    } catch {
        $originalError = $_
        foreach ($name in $attempted) {
            $old = Join-Path $backup $name
            $target = Join-Path $here $name
            if (Test-Path -LiteralPath $old) {
                Copy-Item -LiteralPath $old -Destination $target -Force -ErrorAction SilentlyContinue
            } else {
                Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
            }
        }
        throw "Update teruggedraaid wegens schrijffout: $originalError"
    }
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
