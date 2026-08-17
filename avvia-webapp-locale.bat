@echo off
cd /d "%~dp0"
if not exist "index.html" (
  echo ERRORE: index.html non trovato in questa cartella.
  echo Questo file deve stare dentro credito-salute-sq-app.
  pause
  exit /b 1
)

set PORT=8099
echo Avvio web app Credito Salute SQ...
echo.
echo Cartella corrente:
echo %cd%
echo.
echo Se il browser non si apre da solo, usa questo indirizzo:
echo http://127.0.0.1:%PORT%/index.html
echo.
start "" /min cmd /c "timeout /t 2 >nul & start "" "http://127.0.0.1:%PORT%/index.html""
python -m http.server %PORT% --bind 127.0.0.1
pause
