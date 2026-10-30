@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo ===================================================
echo [1/2] O'zgarishlar GitHub'ga yuklanmoqda...
echo ===================================================
git add .
git commit -m "auto update"
git push origin main

echo.
echo ===================================================
echo [2/2] Serverdagi kodlar va bot yangilanmoqda...
echo ===================================================
echo [info] Parol faqat 1 marta so'raladi (barcha sync + deploy bitta SSH).

REM Barcha .env sync + deploy bitta remote skriptda
set "TMPSH=%TEMP%\tarix_bot_deploy.sh"
> "%TMPSH%" (
  echo #!/bin/bash
  echo set -e
  echo cd /root/TARIX_bot
  echo touch .env
  echo upsert_env^(^) {
  echo   local key="$1"
  echo   local val="$2"
  echo   if [ -z "$val" ]; then return 0; fi
  echo   if grep -q "^${key}=" .env; then
  echo     sed -i "s|^${key}=.*|${key}=${val}|" .env
  echo   else
  echo     printf '%%s=%%s\n' "$key" "$val" ^>^> .env
  echo   fi
  echo   echo "[sync] $key OK"
  echo }
)

call :emit_upsert GEMINI_API_KEY
call :emit_upsert CLICK_SERVICE_ID
call :emit_upsert CLICK_MERCHANT_ID
call :emit_upsert CLICK_SECRET_KEY
call :emit_upsert CLICK_MERCHANT_USER_ID
call :emit_upsert WEBAPP_URL

>> "%TMPSH%" (
  echo echo "[deploy] git pull + restart..."
  echo git stash
  echo git pull origin main
  echo PY=./venv/bin/python
  echo test -x "$PY" ^|^| PY=./.venv/bin/python
  echo "$PY" -m pip install -q httpx openpyxl python-multipart
  echo "$PY" import_master_baza.py
  echo pm2 restart fastapi-app tg-bot
  echo sleep 2
  echo "$PY" -c "from data.config import GEMINI_API_KEY; print('GEMINI:', 'OK' if GEMINI_API_KEY else 'YOQ')"
  echo pm2 describe fastapi-app ^| head -n 40
)

REM Bitta SSH (stdin orqali) — parol 1 marta
REM Windows CRLF ni serverda olib tashlaymiz (aks holda bash \r dan yiqiladi)
ssh root@134.209.228.223 "tr -d '\r' | bash -s" < "%TMPSH%"
set "SSH_EXIT=%ERRORLEVEL%"
del /q "%TMPSH%" >nul 2>&1

if not "%SSH_EXIT%"=="0" goto :deploy_fail

echo.
echo ===================================================
echo  Muvaffaqiyatli yakunlandi!
echo  Mini App va bot serverda yangilandi.
echo ===================================================
echo.
echo Tip: 0 marta parol uchun SSH kalit:
echo   ssh-keygen -t ed25519 -N "" -f %%USERPROFILE%%\.ssh\id_ed25519
echo   type %%USERPROFILE%%\.ssh\id_ed25519.pub ^| ssh root@134.209.228.223 "mkdir -p ~/.ssh && cat ^>^> ~/.ssh/authorized_keys"
echo.
pause
exit /b 0

:deploy_fail
echo.
echo [xato] Server deploy muvaffaqiyatsiz (exit %SSH_EXIT%).
echo Maslahat: SSH kalit sozlang — keyin umuman parol so'ralmaydi.
pause
exit /b %SSH_EXIT%

:emit_upsert
set "K=%~1"
set "V="
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"%K%=" ".env" 2^>nul`) do set "V=%%B"
if defined V (
  echo [queue] %K% sync qilinadi
  >> "%TMPSH%" echo upsert_env '%K%' '%V%'
) else (
  echo [warn] Lokal .env da %K% topilmadi/bo'sh.
)
goto :eof
