@echo off
where cl >nul 2>nul
if not errorlevel 1 goto compile
set "GMW_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%GMW_VSWHERE%" exit /b 1
for /f "usebackq tokens=*" %%i in (`"%GMW_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do call "%%i\VC\Auxiliary\Build\vcvars32.bat" >nul
where cl >nul 2>nul
if errorlevel 1 exit /b 1
:compile
cd /d "%~dp0"
cl /nologo /utf-8 /std:c++17 /EHsc /W4 /O2 /MT backend.cpp /Fe:GMWInstallerHelper.exe /link bcrypt.lib /MANIFEST:EMBED /MANIFESTUAC:"level='asInvoker' uiAccess='false'"
if errorlevel 1 exit /b 1
