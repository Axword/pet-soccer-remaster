Unicode true
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "Pet Soccer Remaster Online"
OutFile "..\release\PetSoccer-Remaster-Online-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\Pet Soccer Remaster Online"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32
BrandingText "Pet Soccer Remaster Online"
VIProductVersion "0.2.0.1"
VIAddVersionKey "ProductName" "Pet Soccer Remaster Online"
VIAddVersionKey "FileDescription" "Instalator Pet Soccer Remaster Online — beta 1"
VIAddVersionKey "FileVersion" "0.2.0-beta.1"
VIAddVersionKey "LegalCopyright" "Axword — kod moda; zasoby gier należą do ich autorów"
ShowInstDetails show
ShowUninstDetails show

Var SourceDir
Var SourceField
Var SourceDialog
Var SourceBrowse
Var DesktopField
Var DesktopWanted
Var NoIntegration
Var Parameters

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Pet Soccer Remaster Online — beta"
!define MUI_WELCOMEPAGE_TEXT "Zainstalujesz osobną kopię Pet Soccer z testowym Online 1vs1 i lobby oraz dodatkowymi klubami Gothic, Minecraft, Wiedźmin, League of Legends i Jagniellonia.$\r$\n$\r$\nPaczka zawiera poprawki grafiki i sterowania, lokalny turniej oraz czysty zapis z odblokowanymi zespołami. Dodatkowe kluby włączysz w Więcej opcji.$\r$\n$\r$\nPotrzebujesz zainstalowanej polskiej wersji Pet Soccer. Oryginalny folder gry i jego zapisy pozostaną nietknięte."
!insertmacro MUI_PAGE_WELCOME
Page custom SourcePage SourceLeave
!define MUI_DIRECTORYPAGE_TEXT_TOP "Wybierz nowy folder dla kopii z modem. Folder nie może jeszcze istnieć. Oryginalna instalacja zostanie tylko odczytana."
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE VerifyDestination
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "Mod został zainstalowany"
!define MUI_FINISHPAGE_TEXT "Gotowe. Uruchom PetSoccer-Online.exe z nowego folderu lub użyj utworzonego skrótu.$\r$\n$\r$\nPrzycisk Online otwiera testowe lobby 1vs1. Multiplayer → TURNIEJ otwiera drabinkę ośmiu drużyn.$\r$\nSamo PetSoccer.exe nadal pozwala uruchomić grę offline.$\r$\n$\r$\nOryginalna gra i jej zapis pozostają bez zmian."
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Polish"

Function .onInit
    InitPluginsDir
    StrCpy $SourceDir "$PROGRAMFILES32\Techland\Pet Soccer"
    StrCpy $DesktopWanted 1
    StrCpy $NoIntegration 0
    ${GetParameters} $Parameters
    ${GetOptions} $Parameters "/SOURCE=" $0
    ${IfNot} ${Errors}
        StrCpy $SourceDir $0
    ${EndIf}
    ClearErrors
    ${GetOptions} $Parameters "/TARGET=" $0
    ${IfNot} ${Errors}
        StrCpy $INSTDIR $0
    ${EndIf}
    ClearErrors
    ${GetOptions} $Parameters "/NOINTEGRATION" $0
    ${IfNot} ${Errors}
        StrCpy $NoIntegration 1
    ${EndIf}
FunctionEnd

Function SourcePage
    !insertmacro MUI_HEADER_TEXT "Oryginalna gra" "Wskaż folder z zainstalowanym Pet Soccer."
    nsDialogs::Create 1018
    Pop $SourceDialog
    ${NSD_CreateLabel} 0 0 100% 32u "Wybierz oryginalną polską wersję gry, np. Techland\Pet Soccer. Instalator skopiuje potrzebne pliki do nowej lokalizacji."
    Pop $0
    ${NSD_CreateDirRequest} 0 42u 82% 14u "$SourceDir"
    Pop $SourceField
    ${NSD_CreateBrowseButton} 84% 42u 16% 14u "Wybierz…"
    Pop $SourceBrowse
    ${NSD_OnClick} $SourceBrowse BrowseSource
    ${NSD_CreateCheckbox} 0 78u 100% 14u "Utwórz skrót na pulpicie"
    Pop $DesktopField
    ${NSD_Check} $DesktopField
    nsDialogs::Show
FunctionEnd

Function BrowseSource
    nsDialogs::SelectFolderDialog "Folder oryginalnego Pet Soccer" "$SourceDir"
    Pop $0
    ${If} $0 != error
        StrCpy $SourceDir $0
        ${NSD_SetText} $SourceField $0
    ${EndIf}
FunctionEnd

Function SourceLeave
    ${NSD_GetText} $SourceField $SourceDir
    ${NSD_GetState} $DesktopField $DesktopWanted
    IfFileExists "$SourceDir\PetSoccer.exe" +3 0
        MessageBox MB_OK|MB_ICONEXCLAMATION "W tym folderze nie ma PetSoccer.exe. Wybierz folder oryginalnej gry."
        Abort
    IfFileExists "$SourceDir\jre\bin\classic\jvm.dll" +3 0
        MessageBox MB_OK|MB_ICONEXCLAMATION "Brakuje oryginalnego środowiska gry (jre\bin\classic\jvm.dll)."
        Abort
FunctionEnd

Function VerifyDestination
    System::Call 'kernel32::GetFileAttributesW(w "$INSTDIR") i .r0'
    ${If} $0 != -1
        MessageBox MB_OK|MB_ICONEXCLAMATION "Ten folder już istnieje. Wybierz nową nazwę folderu dla kopii z modem."
        Abort
    ${EndIf}
FunctionEnd

Section "Pet Soccer Remaster Online" SEC_MAIN
    AddSize 700000
    SetDetailsPrint textonly
    DetailPrint "Przygotowywanie paczki…"
    SetOutPath "$PLUGINSDIR\gmw"
    File "GMWInstallerHelper.exe"
    File "..\metadata\base-allowlist.tsv"
    File "..\package\payload.tsv"
    File "..\package\patches.tsv"
    SetOutPath "$PLUGINSDIR\gmw\payload"
    File /r "..\package\payload\*"
    SetDetailsPrint both
    DetailPrint "Kopiowanie oryginalnej gry i sprawdzanie plików…"
    nsExec::ExecToLog '"$PLUGINSDIR\gmw\GMWInstallerHelper.exe" install "$SourceDir" "$INSTDIR" "$PLUGINSDIR\gmw\payload" "$PLUGINSDIR\gmw\base-allowlist.tsv" "$PLUGINSDIR\gmw\payload.tsv" "$PLUGINSDIR\gmw\patches.tsv"'
    Pop $0
    ${If} $0 != 0
        SetErrorLevel 1
        MessageBox MB_OK|MB_ICONSTOP "Instalacja nie powiodła się. Sprawdź, czy wskazano oryginalną polską wersję gry i nowy folder docelowy. Szczegóły znajdują się powyżej." /SD IDOK
        Abort
    ${EndIf}
    SetOutPath "$INSTDIR"
    ClearErrors
    CopyFiles /SILENT "$PLUGINSDIR\gmw\GMWInstallerHelper.exe" "$INSTDIR\GMWInstallerHelper.exe"
    ${If} ${Errors}
        Goto metadata_failed
    ${EndIf}
    ClearErrors
    WriteUninstaller "$INSTDIR\Odinstaluj.exe"
    ${If} ${Errors}
        Goto metadata_failed
    ${EndIf}
    ${If} $NoIntegration == 0
        ${If} $DesktopWanted != 0
            ClearErrors
            CreateShortcut "$DESKTOP\Pet Soccer Remaster Online.lnk" "$INSTDIR\PetSoccer-Online.exe" "" "$INSTDIR\PetSoccer-Online.exe" 0
            ${If} ${Errors}
                DetailPrint "Nie utworzono skrótu. Grę można uruchomić z wybranego folderu."
            ${EndIf}
        ${EndIf}
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "DisplayName" "Pet Soccer Remaster Online"
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "DisplayVersion" "0.2.0-beta.1"
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "InstallLocation" "$INSTDIR"
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "UninstallString" '$\"$INSTDIR\Odinstaluj.exe$\"'
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "DisplayIcon" "$INSTDIR\PetSoccer-Online.exe"
        WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "NoModify" 1
        WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "NoRepair" 1
    ${EndIf}
    Goto metadata_done
metadata_failed:
    SetOutPath "$PLUGINSDIR"
    nsExec::ExecToLog '"$PLUGINSDIR\gmw\GMWInstallerHelper.exe" uninstall "$INSTDIR"'
    Pop $0
    ${If} $0 != 0
        SetErrorLevel 1
        MessageBox MB_OK|MB_ICONSTOP "Instalacja jest niepełna i nie udało się jej całkowicie wycofać. Oryginalna gra jest bez zmian. Pliki kopii pozostały w: $INSTDIR. Zamknij tę kopię gry przed ponowną próbą." /SD IDOK
        Abort
    ${EndIf}
    Delete "$INSTDIR\GMWInstallerHelper.exe"
    Delete "$INSTDIR\Odinstaluj.exe"
    RMDir "$INSTDIR"
    SetErrorLevel 1
    MessageBox MB_OK|MB_ICONSTOP "Nie udało się zapisać deinstalatora. Instalacja została wycofana; wybierz folder z prawem zapisu." /SD IDOK
    Abort
metadata_done:
SectionEnd

Section "Uninstall"
    nsExec::ExecToLog '"$INSTDIR\GMWInstallerHelper.exe" uninstall "$INSTDIR"'
    Pop $0
    ${If} $0 != 0
        SetErrorLevel 1
        MessageBox MB_OK|MB_ICONSTOP "Nie usunięto plików spoza potwierdzonej instalacji. Zamknij tę kopię gry i uruchom ponownie jej deinstalator." /SD IDOK
        Abort
    ${EndIf}
    ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline" "InstallLocation"
    ${If} $0 == $INSTDIR
        Delete "$DESKTOP\Pet Soccer Remaster Online.lnk"
        DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PetSoccerRemasterOnline"
    ${EndIf}
    Delete "$INSTDIR\GMWInstallerHelper.exe"
    Delete "$INSTDIR\Odinstaluj.exe"
    RMDir "$INSTDIR"
SectionEnd
