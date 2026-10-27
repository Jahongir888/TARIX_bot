@echo off
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
REM Lokal .env dagi GEMINI_API_KEY ni serverga yuborish (gitga kiritilmaydi)
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"GEMINI_API_KEY=" ".env" 2^>nul`) do set "GEMINI_SYNC_KEY=%%B"
if defined GEMINI_SYNC_KEY (
  echo [sync] GEMINI_API_KEY serverga yozilmoqda...
  ssh root@134.209.228.223 "cd /root/TARIX_bot && touch .env && if grep -q '^GEMINI_API_KEY=' .env; then sed -i 's|^GEMINI_API_KEY=.*|GEMINI_API_KEY=%GEMINI_SYNC_KEY%|' .env; else echo GEMINI_API_KEY=%GEMINI_SYNC_KEY% >> .env; fi"
) else (
  echo [warn] Lokal .env da GEMINI_API_KEY topilmadi — ovozli STT serverda ishlamasligi mumkin.
)

ssh root@134.209.228.223 "cd /root/TARIX_bot && git stash && git pull origin main && PY=./venv/bin/python; test -x \"$PY\" || PY=./.venv/bin/python; \"$PY\" -m pip install -q httpx openpyxl; \"$PY\" import_master_baza.py; pm2 restart fastapi-app tg-bot && sleep 2 && \"$PY\" -c \"from data.config import GEMINI_API_KEY; print('GEMINI:', 'OK' if GEMINI_API_KEY else 'YOQ')\" && pm2 describe fastapi-app | head -n 40"

echo.
echo ===================================================
echo  Muvaffaqiyatli yakunlandi! 
echo  Mini App va bot serverda yangilandi.
echo ===================================================
pause