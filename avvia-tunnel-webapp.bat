@echo off
set APP_DIR=C:\Users\angel\OneDrive\Desktop\Salute Quotidiana\Documenti Sq\credito-salute-sq-app

echo Avvio web app Salute Quotidiana...
echo.
echo IMPORTANTE: chiudi prima eventuali vecchie finestre server/tunnel.
echo.
echo Si apriranno due finestre:
echo 1. Server locale della web app
echo 2. Tunnel pubblico Cloudflare
echo.
echo Nel tunnel copia il link che finisce con .trycloudflare.com
echo e aprilo dal telefono.
echo.

start "SQ - Server locale no-cache" cmd /k "cd /d ""%APP_DIR%"" && python server-no-cache.py"

timeout /t 3 /nobreak >nul

start "SQ - Tunnel telefono" cmd /k "echo Avvio tunnel Cloudflare... && echo Se resta fermo su Requesting new quick Tunnel, attendi 60-90 secondi. && echo. && where cloudflared && echo. && cloudflared tunnel --url http://127.0.0.1:8000 --loglevel info"

echo.
echo Fatto. Cerca nella finestra del tunnel il link https://...trycloudflare.com
echo.
pause
