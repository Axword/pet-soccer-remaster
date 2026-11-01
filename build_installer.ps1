param([string]$NsisCompiler = 'makensis.exe')
$ErrorActionPreference = 'Stop'
$publicBuildRoot = $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $publicBuildRoot 'release') | Out-Null
Push-Location (Join-Path $publicBuildRoot 'installer')
try {
    & cmd /c build_backend.cmd
    if ($LASTEXITCODE -ne 0) { throw 'Native backend compilation failed. Install MSVC Desktop C++ build tools.' }
    & $NsisCompiler /V2 /INPUTCHARSET UTF8 PetSoccerGMW.nsi
    if ($LASTEXITCODE -ne 0) { throw 'NSIS compilation failed.' }
    Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $publicBuildRoot 'release/PetSoccer-Remaster-GMW-Setup.exe')
}
finally { Pop-Location }
