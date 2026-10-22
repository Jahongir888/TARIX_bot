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
ssh root@134.209.228.223 "cd /root/TARIX_bot && git stash && git pull origin main && (test -x .venv/bin/pip && .venv/bin/pip install -q httpx || pip3 install -q httpx || true) && pm2 restart fastapi-app tg-bot && sleep 2 && pm2 describe fastapi-app | head -n 40"

echo.
echo ===================================================
echo  Muvaffaqiyatli yakunlandi! 
echo  Mini App va bot serverda yangilandi.
echo ===================================================
pause