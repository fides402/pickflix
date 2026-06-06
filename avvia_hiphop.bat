@echo off
chcp 65001 >nul
title HipHop – Top 30 Tracks Scraper

echo.
echo  ============================================
echo   HipHop ^| Top 30 Tracks per Artista
echo  ============================================
echo.
echo   Artisti: Earl Sweatshirt, Navy Blue, Kanye West,
echo            The Alchemist, Westside Gunn, Roc Marciano,
echo            Conway the Machine, Mick Jenkins, Joey Badass, J Cole
echo.

REM --- Cerca Python ---
set PY=
where python >nul 2>&1 && set PY=python
if "%PY%"=="" where py >nul 2>&1 && set PY=py
if "%PY%"=="" (
    echo  ERRORE: Python non trovato.
    echo  Scaricalo da https://www.python.org/downloads/
    pause
    exit /b 1
)
echo  Python trovato: %PY%

REM --- Installa dipendenze ---
echo  Installazione dipendenze...
%PY% -m pip install flask requests --quiet --disable-pip-version-check

REM --- Apri il browser dopo 2 secondi ---
echo  Apertura browser su http://localhost:5051 ...
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5051"

REM --- Forza UTF-8 ---
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM --- Avvia il server ---
echo.
echo  Server in ascolto su http://localhost:5051
echo  Premi CTRL+C per uscire.
echo.
%PY% app_hiphop.py

pause
