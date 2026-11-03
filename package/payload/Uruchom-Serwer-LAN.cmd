@echo off
setlocal
title Pet Soccer - serwer LAN
if not exist "%~dp0online\runtime\python.exe" (
 echo Brakuje skladnikow Online. Zainstaluj pelna paczke moda.
 pause
 exit /b 1
)
echo Serwer LAN: port 27889. W obu grach wpisz adres LAN tego komputera i port 27889.
echo Okno pozostaw otwarte podczas gry. Ctrl+C zamyka serwer.
echo Lokalne lobby launchera na porcie 27888 moze dzialac osobno.
echo Systemowa zapora nie jest zmieniana automatycznie.
"%~dp0online\runtime\python.exe" -I -u "%~dp0online\broker.py" --bind 0.0.0.0 --port 27889 --db "%~dp0online\data\leaderboard-lan.sqlite3"
if errorlevel 1 (
 echo Nie uruchomiono serwera. Port 27889 moze byc zajety lub folder danych jest tylko do odczytu.
 pause
 exit /b 1
)
