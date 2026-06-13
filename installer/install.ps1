param(
    [string]$TestRoot = "",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PackageRoot "payload"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    $candidates = @()
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { $candidates += $python.Source }

    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @("-3.12", "-3.11", "-3.10", "-3")) {
            try {
                $path = & $launcher.Source $version -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $path) { $candidates += $path.Trim() }
            } catch {}
        }
    }

    $candidates += @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    )

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $check = & $candidate -c "import sys, tkinter; assert sys.version_info >= (3, 8); print('OK')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $check -match "OK") { return $candidate }
        } catch {}
    }
    return $null
}

function Find-Jianying {
    $base = Join-Path $env:LOCALAPPDATA "JianyingPro\Apps"
    $launcher = Join-Path $base "JianyingPro.exe"
    if (Test-Path -LiteralPath $launcher) { return $launcher }
    if (Test-Path -LiteralPath $base) {
        $found = Get-ChildItem $base -Recurse -Filter "JianyingPro.exe" -File -ErrorAction SilentlyContinue |
            Sort-Object { $_.VersionInfo.ProductVersion } -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

try {
    Write-Host "DaVinci Resolve to Jianying" -ForegroundColor White
    Write-Host "One-click installer" -ForegroundColor White

    if (-not (Test-Path -LiteralPath $PayloadRoot)) {
        throw "Incomplete package: payload folder is missing."
    }

    Write-Step "Checking Python"
    $PythonExe = Find-Python
    if (-not $PythonExe) {
        throw "Python 3.8+ with tkinter was not found. Install Python 3.11/3.12 and enable Add Python to PATH."
    }
    Write-Host "Python: $PythonExe"

    Write-Step "Checking Jianying Pro"
    $JianyingExe = Find-Jianying
    if (-not $JianyingExe) {
        throw "Jianying Pro was not found. Install and launch Jianying at least once."
    }
    Write-Host "Jianying: $JianyingExe"
    $ResolveExe = "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    if (-not (Test-Path -LiteralPath $ResolveExe)) {
        Write-Warning "DaVinci Resolve was not found in the default location. The user script will still be installed."
    }

    if ($TestRoot) {
        $ToolRoot = Join-Path $TestRoot "XiaoerTools"
        $MenuRoot = Join-Path $TestRoot "Fusion\Scripts\Utility"
    } else {
        $ResolveSupport = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support"
        $ToolRoot = Join-Path $ResolveSupport "XiaoerTools"
        $MenuRoot = Join-Path $ResolveSupport "Fusion\Scripts\Utility"
    }
    $DraftRoot = Join-Path $env:LOCALAPPDATA "JianyingPro\User Data\Projects\com.lveditor.draft"

    Write-Step "Preparing Python dependencies"
    if (-not $SkipDependencyInstall) {
        & $PythonExe -m pip install --user --disable-pip-version-check --quiet pymediainfo imageio pillow
        if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed. Check the network connection." }
    } else {
        Write-Host "Test mode: dependency installation skipped."
    }

    Write-Step "Installing Resolve menu script"
    New-Item -ItemType Directory -Force -Path $ToolRoot, $MenuRoot, $DraftRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $PayloadRoot "xml_to_jianying_draft.py") -Destination $ToolRoot -Force
    Copy-Item -LiteralPath (Join-Path $PayloadRoot "resolve_to_jianying_worker.py") -Destination $ToolRoot -Force
    Copy-Item -LiteralPath (Join-Path $PayloadRoot "Current Timeline to Jianying.py") -Destination $MenuRoot -Force
    Copy-Item -LiteralPath (Join-Path $PayloadRoot "vendor") -Destination $ToolRoot -Recurse -Force

    $Config = [ordered]@{
        python_exe = $PythonExe
        jianying_exe = $JianyingExe
        draft_root = $DraftRoot
        installed_at = (Get-Date).ToString("s")
        version = "1.2.0"
    }
    $ConfigJson = $Config | ConvertTo-Json
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $ToolRoot "config.json"), $ConfigJson, $Utf8NoBom)
    Write-Step "Validating installation"
    & $PythonExe -m py_compile `
        (Join-Path $ToolRoot "xml_to_jianying_draft.py") `
        (Join-Path $ToolRoot "resolve_to_jianying_worker.py") `
        (Join-Path $MenuRoot "Current Timeline to Jianying.py")
    if ($LASTEXITCODE -ne 0) { throw "Helper script validation failed." }

    Write-Host "`nInstallation completed." -ForegroundColor Green
    Write-Host "Restart DaVinci Resolve, then run:"
    Write-Host "Workspace > Scripts > Utility > Current Timeline to Jianying" -ForegroundColor Yellow
} catch {
    Write-Host "`nInstallation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
