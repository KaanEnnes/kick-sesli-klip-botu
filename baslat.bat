@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Kick Sesli Klip Botu - mpagee
echo Bot calisiyor... Kapatmak icin bu pencereyi kapat.
echo.
python -u bot.py
echo.
echo Bot durdu.
pause
