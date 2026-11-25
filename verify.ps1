param(
    [ValidateSet("EU", "Lesta")]
    [string]$Client = "EU",
    [switch]$NoBuild,
    [switch]$NoInstall,
    [switch]$CheckGameLog,
    [string]$WotDir = "",
    [string]$ModSubdir = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WotDir)) {
    $WotDir = if ($Client -eq "Lesta") { "F:\game\Tanki" } else { "F:\game\TankiEU\World_of_Tanks_EU" }
}
if ([string]::IsNullOrWhiteSpace($ModSubdir)) {
    $verXml = Join-Path $WotDir "version.xml"
    if (Test-Path $verXml) {
        $verRaw = Get-Content $verXml -Raw -Encoding UTF8
        if ($verRaw -match 'v\.(\d+\.\d+\.\d+\.\d+)') { $ModSubdir = $Matches[1] }
    }
    if ([string]::IsNullOrWhiteSpace($ModSubdir)) {
        $ModSubdir = if ($Client -eq "Lesta") { "1.46.0.0" } else { "2.4.2.0" }
    }
}
$ModExt = if ($Client -eq "Lesta") { ".mtmod" } else { ".wotmod" }
$ProcPattern = if ($Client -eq "Lesta") { "Tanki*" } else { "WorldOfTanks*" }

$Root = $PSScriptRoot
$BuildScript = Join-Path $Root "build.ps1"
$VerifyPy = Join-Path $Root "tools\verify_mod.py"
$PyExe = "C:\Python27\python.exe"

if (-not (Test-Path $PyExe)) { throw "Missing Python 2.7 at $PyExe" }
if (-not (Test-Path $VerifyPy)) { throw "Missing verifier script at $VerifyPy" }

$SkipInstallCheck = [bool]$NoInstall

if (-not $NoBuild) {
    $wotRunning = Get-Process -Name $ProcPattern -ErrorAction SilentlyContinue
    if (-not $NoInstall -and $wotRunning) {
        Write-Warning "Game client ($ProcPattern) is running (PID $($wotRunning[0].Id)); building dist/ without -Install."
        $SkipInstallCheck = $true
    }
    if ($NoInstall -or $wotRunning) {
        & $BuildScript -Client $Client -WotDir $WotDir -ModSubdir $ModSubdir -ModExt $ModExt
    } else {
        & $BuildScript -Client $Client -WotDir $WotDir -ModSubdir $ModSubdir -ModExt $ModExt -Install
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$pyArgs = @($VerifyPy, "--wot-dir", $WotDir, "--mod-subdir", $ModSubdir, "--mod-ext", $ModExt, "--client", $Client)
if ($SkipInstallCheck) { $pyArgs += "--no-install-check" }
if ($CheckGameLog) { $pyArgs += "--check-game-log" }

& $PyExe @pyArgs
exit $LASTEXITCODE
