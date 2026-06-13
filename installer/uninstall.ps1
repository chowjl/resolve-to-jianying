$ErrorActionPreference = "Stop"

try {
    $ResolveSupport = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support"
    $ToolRoot = Join-Path $ResolveSupport "XiaoerTools"
    $MenuScripts = @(
        (Join-Path $ResolveSupport "Fusion\Scripts\Utility\Current Timeline to Jianying.py")
    )

    foreach ($MenuScript in $MenuScripts) {
        if (Test-Path -LiteralPath $MenuScript) {
            Remove-Item -LiteralPath $MenuScript -Force
        }
    }
    if (Test-Path -LiteralPath $ToolRoot) {
        Remove-Item -LiteralPath $ToolRoot -Recurse -Force
    }

    Write-Host "Uninstall completed. Existing Jianying drafts were not deleted." -ForegroundColor Green
    Write-Host "Restart DaVinci Resolve to refresh the Scripts menu."
} catch {
    Write-Host "Uninstall failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
