param(
    [ValidateSet("EU", "Lesta")]
    [string]$Client = "EU",
    [string]$WotDir = "",
    [string]$ModSubdir = "",
    [string]$ModExt = "",
    [string]$PythonHome = "C:\Python27",
    [switch]$Install
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
if ([string]::IsNullOrWhiteSpace($ModExt)) {
    $ModExt = if ($Client -eq "Lesta") { ".mtmod" } else { ".wotmod" }
}
$ProcPattern = if ($Client -eq "Lesta") { "Tanki*" } else { "WorldOfTanks*" }

$Root = $PSScriptRoot
$SrcDir = Join-Path $Root "src"
$SrcPy = Join-Path $SrcDir "mod_three_marks.py"
$PkgSrcDir = Join-Path $SrcDir "dm_threemarks"
$PkgDir = Join-Path $Root "package"
$MetaPath = Join-Path $PkgDir "meta.xml"
$UiDir = Join-Path $PkgDir "res\gui\gameface\mods\dm\ThreeMarks"
$ModsSubDir = Join-Path $PkgDir "res\scripts\client\gui\mods"
$DistDir = Join-Path $Root "dist"
$PyDll = Join-Path $WotDir "win64\python27.dll"
$PyExe = Join-Path $PythonHome "python.exe"

if (-not (Test-Path $SrcPy)) { throw "Missing source file: $SrcPy" }
if (-not (Test-Path $MetaPath)) { throw "Missing meta.xml: $MetaPath" }
if (-not (Test-Path $PyDll) -and -not (Test-Path $PyExe)) {
    throw "Neither $PyDll nor $PyExe found for Python 2.7 bytecode compilation"
}

[xml]$metaXml = Get-Content $MetaPath -Raw -Encoding UTF8
$Version = [string]$metaXml.root.version
if ([string]::IsNullOrWhiteSpace($Version)) { throw "Failed to read <version> from $MetaPath" }

# 1. Node.js syntax check for ALL .js files under ThreeMarks UI directory
$NodeExe = $null
$cmdNode = Get-Command node -ErrorAction SilentlyContinue
if ($cmdNode) { $NodeExe = $cmdNode.Source }
elseif (Test-Path "C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe") {
    $NodeExe = "C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe"
}
if ($NodeExe -and (Test-Path $UiDir)) {
    $jsFiles = Get-ChildItem -Path $UiDir -Filter "*.js" -Recurse | Sort-Object FullName
    foreach ($jf in $jsFiles) {
        & $NodeExe --check $jf.FullName
        if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax check failed for $($jf.FullName)" }
    }
    Write-Host ("JS check OK: {0} file(s)" -f $jsFiles.Count)
}

# 2. Clean stale scripts/ and ensure dist/ exists
if (Test-Path $ModsSubDir) {
    Remove-Item -Path $ModsSubDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ModsSubDir, $DistDir | Out-Null
$WotmodOut = Join-Path $DistDir ("dm.threemarks_{0}{1}" -f $Version, $ModExt)

# 3. Compile Python 2.7 bytecode & build ZIP_STORED archive via WoT python27.dll or Python 2.7 CLI
$pyBuild = @"
# -*- coding: utf-8 -*-
import os, py_compile, zipfile, json, xml.etree.ElementTree as ET, codecs, traceback

src_dir = r'''$SrcDir'''
src_py = r'''$SrcPy'''
mods_sub_dir = r'''$ModsSubDir'''
pkg_dir = r'''$PkgDir'''
wotmod_out = r'''$WotmodOut'''
expected_ver = r'''$Version'''
status_file = os.path.join(r'''$DistDir''', '_build_status.txt')

try:
    expected_pyc_arcs = set()

    def compile_one(src_file, out_pyc, arc_path):
        parent = os.path.dirname(out_pyc)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        py_compile.compile(src_file, cfile=out_pyc, doraise=True)
        magic = open(out_pyc, 'rb').read(4)
        assert magic == '\x03\xf3\r\n', 'Unexpected PYC magic for %s: %r' % (out_pyc, magic)
        expected_pyc_arcs.add(arc_path)

    compile_one(
        src_py,
        os.path.join(mods_sub_dir, 'mod_three_marks.pyc'),
        'res/scripts/client/gui/mods/mod_three_marks.pyc',
    )

    pkg_src = os.path.join(src_dir, 'dm_threemarks')
    if os.path.isdir(pkg_src):
        for root, dirs, files in os.walk(pkg_src):
            dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
            rel_root = os.path.relpath(root, pkg_src).replace('\\', '/')
            for fn in sorted(files):
                if not fn.endswith('.py'):
                    continue
                src_file = os.path.join(root, fn)
                pyc_name = fn[:-3] + '.pyc'
                if rel_root == '.':
                    out_pyc = os.path.join(mods_sub_dir, 'dm_threemarks', pyc_name)
                    arc_path = 'res/scripts/client/gui/mods/dm_threemarks/' + pyc_name
                else:
                    out_pyc = os.path.join(mods_sub_dir, 'dm_threemarks', rel_root.replace('/', os.sep), pyc_name)
                    arc_path = 'res/scripts/client/gui/mods/dm_threemarks/' + rel_root + '/' + pyc_name
                compile_one(src_file, out_pyc, arc_path)

    if os.path.exists(wotmod_out):
        os.remove(wotmod_out)
    z = zipfile.ZipFile(wotmod_out, 'w', zipfile.ZIP_STORED)
    try:
        for root, dirs, files in os.walk(pkg_dir):
            dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
            rel_root = os.path.relpath(root, pkg_dir).replace('\\', '/')
            if rel_root != '.':
                z.writestr(rel_root.rstrip('/') + '/', '')
            for fn in sorted(files):
                if fn.endswith('.tmp') or fn.endswith('.py'):
                    continue
                full = os.path.join(root, fn)
                arc = fn if rel_root == '.' else (rel_root + '/' + fn)
                z.write(full, arc, zipfile.ZIP_STORED)
    finally:
        z.close()

    zv = zipfile.ZipFile(wotmod_out, 'r')
    try:
        infos = zv.infolist()
        assert len(infos) > 0
        present_arcs = set()
        pyc_count = 0
        for info in infos:
            assert info.compress_type == zipfile.ZIP_STORED, (info.filename, info.compress_type)
            assert not info.filename.endswith('.py'), 'Unexpected .py in wotmod: %s' % info.filename
            assert not info.filename.endswith('.tmp'), 'Unexpected .tmp in wotmod: %s' % info.filename
            present_arcs.add(info.filename)
            if info.filename.endswith('.json'):
                json.loads(zv.read(info.filename).decode('utf-8'))
            if info.filename.endswith('.pyc'):
                pyc_count += 1
                assert zv.read(info.filename)[:4] == '\x03\xf3\r\n', 'Bad PYC magic: %s' % info.filename
        meta_root = ET.fromstring(zv.read('meta.xml'))
        assert meta_root.find('version').text == expected_ver
        missing = sorted(expected_pyc_arcs - present_arcs)
        assert not missing, 'Missing .pyc entries in wotmod: %r' % (missing,)
        count = len(infos)
    finally:
        zv.close()

    codecs.open(status_file, 'w', 'utf-8').write(u'OK|%d|%d' % (count, pyc_count))
except Exception:
    codecs.open(status_file, 'w', 'utf-8').write(u'ERR\n' + traceback.format_exc())
"@

$tmpBuildPy = Join-Path $DistDir "_build_step.py"
$statusFile = Join-Path $DistDir "_build_status.txt"
[System.IO.File]::WriteAllText($tmpBuildPy, $pyBuild, [System.Text.Encoding]::UTF8)

if (Test-Path $PyDll) {
    if (-not ("DmPy27" -as [type])) {
        $cs = @"
using System;
using System.Runtime.InteropServices;
public class DmPy27 {
    [DllImport(@"$($PyDll.Replace('"','\"'))", CallingConvention=CallingConvention.Cdecl)]
    public static extern void Py_SetPythonHome(IntPtr home);
    [DllImport(@"$($PyDll.Replace('"','\"'))", CallingConvention=CallingConvention.Cdecl)]
    public static extern void Py_Initialize();
    [DllImport(@"$($PyDll.Replace('"','\"'))", CallingConvention=CallingConvention.Cdecl)]
    public static extern int PyRun_SimpleString(string code);
    [DllImport(@"$($PyDll.Replace('"','\"'))", CallingConvention=CallingConvention.Cdecl)]
    public static extern void Py_Finalize();
}
"@
        Add-Type -TypeDefinition $cs
    }
    $homePtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalAnsi($PythonHome)
    try {
        [DmPy27]::Py_SetPythonHome($homePtr)
        [DmPy27]::Py_Initialize()
        $ret = [DmPy27]::PyRun_SimpleString("execfile(r'$tmpBuildPy')")
        [DmPy27]::Py_Finalize()
    } finally {
        [System.Runtime.InteropServices.Marshal]::FreeHGlobal($homePtr)
    }
} else {
    & $PyExe $tmpBuildPy
    if ($LASTEXITCODE -ne 0) {
        throw "Python 2.7 build step exited with code $LASTEXITCODE"
    }
}
Remove-Item $tmpBuildPy -ErrorAction SilentlyContinue

$status = Get-Content $statusFile -Raw -Encoding UTF8
Remove-Item $statusFile -ErrorAction SilentlyContinue
if (-not $status.StartsWith("OK|")) {
    throw "Build failed:`n$status"
}
$parts = $status.Split('|')
$entryCount = $parts[1].Trim()
$pycCount = $parts[2].Trim()
$hash = (Get-FileHash $WotmodOut -Algorithm SHA256).Hash
Write-Host ("Built {0} ({1} bytes, {2} ZIP_STORED entries, {3} PYC modules, SHA256={4})" -f $WotmodOut, (Get-Item $WotmodOut).Length, $entryCount, $pycCount, $hash)

# 4. Optional install into game mods folder
if ($Install) {
    $wotProc = Get-Process -Name $ProcPattern -ErrorAction SilentlyContinue
    if ($wotProc) {
        throw "Close game client ($ProcPattern) before running -Install (locked by PID $($wotProc[0].Id))."
    }
    $targetMods = Join-Path $WotDir ("mods\{0}" -f $ModSubdir)
    if (-not (Test-Path $targetMods)) { throw "Target mods dir not found: $targetMods" }
    $bakDir = Join-Path $DistDir "backups"
    New-Item -ItemType Directory -Force -Path $bakDir | Out-Null
    Get-ChildItem $targetMods -Filter "dm.threemarks*.*mod" | ForEach-Object {
        Move-Item $_.FullName (Join-Path $bakDir $_.Name) -Force
    }
    $dest = Join-Path $targetMods (Split-Path $WotmodOut -Leaf)
    Copy-Item $WotmodOut $dest -Force
    $destHash = (Get-FileHash $dest -Algorithm SHA256).Hash
    if ($destHash -ne $hash) { throw "SHA-256 mismatch after copy: $destHash != $hash" }
    Write-Host ("Installed to {0} (SHA256 verified)" -f $dest)

    if ($Client -eq "Lesta") {
        $lestaOwgDir = Join-Path $targetMods "net.openwg"
        New-Item -ItemType Directory -Force -Path $lestaOwgDir | Out-Null
        $lestaGf = Join-Path $lestaOwgDir "net.openwg.gameface_1.2.2.mtmod"
        if (-not (Test-Path $lestaGf)) {
            $euGfItem = Get-ChildItem "F:\game\TankiEU\World_of_Tanks_EU\mods\*\net.openwg\net.openwg.gameface_1.2.2.wotmod" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
            if (-not $euGfItem) { throw "Missing net.openwg.gameface loader to install for Lesta under F:\game\TankiEU\World_of_Tanks_EU\mods\*" }
            $euGf = $euGfItem.FullName
            $srcGfHash = (Get-FileHash $euGf -Algorithm SHA256).Hash
            Copy-Item $euGf $lestaGf -Force
            $dstGfHash = (Get-FileHash $lestaGf -Algorithm SHA256).Hash
            if ($dstGfHash -ne $srcGfHash) { throw "SHA-256 mismatch copying net.openwg.gameface: $dstGfHash != $srcGfHash" }
            Write-Host ("Installed Gameface loader to {0} (SHA256 verified)" -f $lestaGf)
        }
    }
}
