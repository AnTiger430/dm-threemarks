param(
    [switch]$Open
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$AuditPy = Join-Path $Root "tools\render_audit.py"
$PyExe = "C:\Python27\python.exe"

if (-not (Test-Path $PyExe)) { throw "Missing Python 2.7 at $PyExe" }
if (-not (Test-Path $AuditPy)) { throw "Missing render audit script at $AuditPy" }

& $PyExe $AuditPy
$rc = $LASTEXITCODE

$IndexHtml = Join-Path $Root "dist\ui_audit\index.html"
if ($Open -and (Test-Path $IndexHtml)) {
    Start-Process $IndexHtml
}

exit $rc
