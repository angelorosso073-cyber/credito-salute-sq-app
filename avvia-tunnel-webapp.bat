@echo off
set APP_DIR=C:\Users\angel\OneDrive\Desktop\Salute Quotidiana\Documenti Sq\credito-salute-sq-app

echo Avvio web app Salute Quotidiana...
echo.
echo Si apriranno due finestre:
echo 1. Server locale della web app
echo 2. Tunnel pubblico Cloudflare
echo.
echo Nel tunnel copia il link che finisce con .trycloudflare.com
echo e aprilo dal telefono.
echo.

start "SQ - Server locale" cmd /k "cd /d ""%APP_DIR%"" && python -m http.server 8000 --bind 127.0.0.1"

timeout /t 3 /nobreak >nul

start "SQ - Tunnel telefono" cmd /k "cloudflared tunnel --url http://127.0.0.1:8000"

echo.
echo Fatto. Cerca nella finestra del tunnel il link https://...trycloudflare.com
echo.
pause
