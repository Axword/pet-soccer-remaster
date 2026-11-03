param(
    [string]$Source = "${env:ProgramFiles(x86)}\Techland\Pet Soccer",
    [string]$Target = "$env:LOCALAPPDATA\Programs\Pet Soccer Remaster Online"
)
$ErrorActionPreference = 'Stop'
$helper = Join-Path $PSScriptRoot 'installer/GMWInstallerHelper.exe'
if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) {
    throw 'Brak pomocnika instalatora. Pobierz ZIP ModFiles z Releases albo zbuduj installer/build_backend.cmd.'
}
if (Test-Path -LiteralPath $Target) { throw 'Wybierz nowy, nieistniejacy folder docelowy.' }
& $helper install $Source $Target (Join-Path $PSScriptRoot 'package/payload') (Join-Path $PSScriptRoot 'metadata/base-allowlist.tsv') (Join-Path $PSScriptRoot 'package/payload.tsv') (Join-Path $PSScriptRoot 'package/patches.tsv')
if ($LASTEXITCODE -ne 0) { throw ('Instalacja przerwana, kod: ' + $LASTEXITCODE) }
Write-Output ('Gotowe. Uruchom: ' + (Join-Path $Target 'PetSoccer-Online.exe'))
Write-Output 'Dodatkowe kluby wlaczysz w Audio video -> Wiecej opcji.'
