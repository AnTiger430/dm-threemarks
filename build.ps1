param(
    [string]$WotDir = "F:\game\TankiEU\World_of_Tanks_EU",
    [string]$ModSubdir = "2.4.1.1",
    [string]$PythonHome = "C:\Python27",
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$SrcPy = Join-Path $Root "src\mod_three_marks.py"
$PkgDir = Join-Path $Root "package"
$MetaPath = Join-Path $PkgDir "meta.xml"
$JsPath = Join-Path $PkgDir "res\gui\gameface\mods\dm\ThreeMarks\ThreeMarks.js"
$ModsSubDir = Join-Path $PkgDir "res\scripts\client\gui\mods"
$PycOut = Join-Path $ModsSubDir "mod_three_marks.pyc"
$DistDir = Join-Path $Root "dist"
$PyDll = Join-Path $WotDir "win64\python27.dll"

if (-not (Test-Path $SrcPy)) { throw "Missing source file: $SrcPy" }
if (-not (Test-Path $MetaPath)) { throw "Missing meta.xml: $MetaPath" }
if (-not (Test-Path $PyDll)) { throw "Missing python27.dll at: $PyDll" }

[xml]$metaXml = Get-Content $MetaPath -Raw -Encoding UTF8
$Version = [string]$metaXml.root.version
if ([string]::IsNullOrWhiteSpace($Version)) { throw "Failed to read <version> from $MetaPath" }

# 1. Optional Node.js syntax check for ThreeMarks.js
$NodeExe = $null
$cmdNode = Get-Command node -ErrorAction SilentlyContinue
if ($cmdNode) { $NodeExe = $cmdNode.Source }
elseif (Test-Path "C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe") {
    $NodeExe = "C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe"
}
if ($NodeExe -and (Test-Path $JsPath)) {
    & $NodeExe --check $JsPath
    if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax check failed for $JsPath" }
    Write-Host "JS check OK: $JsPath"
}

# 2. Ensure build output folders exist
New-Item -ItemType Directory -Force -Path $ModsSubDir, $DistDir | Out-Null
$WotmodOut = Join-Path $DistDir ("dm.threemarks_{0}.wotmod" -f $Version)

# 3. Compile Python 2.7 bytecode & build ZIP_STORED .wotmod via WoT python27.dll
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

$pyBuild = @"
# -*- coding: utf-8 -*-
import os, py_compile, zipfile, json, xml.etree.ElementTree as ET, codecs, traceback

src_py = r'''$SrcPy'''
pyc_out = r'''$PycOut'''
pkg_dir = r'''$PkgDir'''
wotmod_out = r'''$WotmodOut'''
expected_ver = r'''$Version'''
status_file = os.path.join(r'''$DistDir''', '_build_status.txt')

try:
    if os.path.exists(pyc_out):
        os.remove(pyc_out)
    py_compile.compile(src_py, cfile=pyc_out, doraise=True)
    magic = open(pyc_out, 'rb').read(4)
    assert magic == '\x03\xf3\r\n', 'Unexpected PYC magic: %r' % (magic,)

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
                if fn.endswith('.tmp'):
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
        for info in infos:
            assert info.compress_type == zipfile.ZIP_STORED, (info.filename, info.compress_type)
            if info.filename.endswith('.json'):
                json.loads(zv.read(info.filename).decode('utf-8'))
        meta_root = ET.fromstring(zv.read('meta.xml'))
        assert meta_root.find('version').text == expected_ver
        assert zv.read('res/scripts/client/gui/mods/mod_three_marks.pyc')[:4] == '\x03\xf3\r\n'
        count = len(infos)
    finally:
        zv.close()

    codecs.open(status_file, 'w', 'utf-8').write(u'OK|%d' % count)
except Exception:
    codecs.open(status_file, 'w', 'utf-8').write(u'ERR\n' + traceback.format_exc())
"@

$tmpBuildPy = Join-Path $DistDir "_build_step.py"
$statusFile = Join-Path $DistDir "_build_status.txt"
[System.IO.File]::WriteAllText($tmpBuildPy, $pyBuild, [System.Text.Encoding]::UTF8)

$homePtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalAnsi($PythonHome)
try {
    [DmPy27]::Py_SetPythonHome($homePtr)
    [DmPy27]::Py_Initialize()
    $ret = [DmPy27]::PyRun_SimpleString("execfile(r'$tmpBuildPy')")
    [DmPy27]::Py_Finalize()
} finally {
    [System.Runtime.InteropServices.Marshal]::FreeHGlobal($homePtr)
}
Remove-Item $tmpBuildPy -ErrorAction SilentlyContinue

$status = Get-Content $statusFile -Raw -Encoding UTF8
Remove-Item $statusFile -ErrorAction SilentlyContinue
if (-not $status.StartsWith("OK|")) {
    throw "Build failed:`n$status"
}
$entryCount = $status.Split('|')[1].Trim()
$hash = (Get-FileHash $WotmodOut -Algorithm SHA256).Hash
Write-Host ("Built {0} ({1} bytes, {2} ZIP_STORED entries, SHA256={3})" -f $WotmodOut, (Get-Item $WotmodOut).Length, $entryCount, $hash)

# 4. Optional install into World of Tanks mods folder
if ($Install) {
    $wotProc = Get-Process -Name "WorldOfTanks*" -ErrorAction SilentlyContinue
    if ($wotProc) {
        throw "Close World of Tanks before running -Install (locked by PID $($wotProc[0].Id))."
    }
    $targetMods = Join-Path $WotDir ("mods\{0}" -f $ModSubdir)
    if (-not (Test-Path $targetMods)) { throw "Target mods dir not found: $targetMods" }
    $bakDir = Join-Path $DistDir "backups"
    New-Item -ItemType Directory -Force -Path $bakDir | Out-Null
    Get-ChildItem $targetMods -Filter "dm.threemarks*.wotmod" | ForEach-Object {
        Move-Item $_.FullName (Join-Path $bakDir $_.Name) -Force
    }
    $dest = Join-Path $targetMods (Split-Path $WotmodOut -Leaf)
    Copy-Item $WotmodOut $dest -Force
    $destHash = (Get-FileHash $dest -Algorithm SHA256).Hash
    if ($destHash -ne $hash) { throw "SHA-256 mismatch after copy: $destHash != $hash" }
    Write-Host ("Installed to {0} (SHA256 verified)" -f $dest)
}
