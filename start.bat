@echo off
title TARIX GRAND - Tizimni ishga tushirish
echo ===================================================
echo TARIX GRAND: FastAPI, Ngrok va Bot yoqilmoqda...
echo ===================================================

:: 1. FastAPI serverini alohida fonda yoqish
start "TARIX GRAND: FastAPI Server" cmd /k "call .venv\Scripts\activate && python -m web.server"

:: 2. Ngrok tunnelini alohida fonda yoqish
start "TARIX GRAND: Ngrok Tunnel" cmd /k "call .venv\Scripts\activate && python run_tunnel.py"

:: 3. Telegram botni ishga tushirish
start "TARIX GRAND: Aiogram Bot" cmd /k "call .venv\Scripts\activate && python main.py"

echo Barcha xizmatlar muvaffaqiyatli ishga tushirildi!