@echo off
title Tarot Bot Starter

echo ===================================
echo  Tarot Bot Starter
echo ===================================
echo.
echo Checking and installing requirements...
pip install -r requirements.txt
echo.
echo Requirements check complete.
echo.
echo ===================================
echo  Starting Tarot Bot...
echo  (Press Ctrl+C in this window to stop the bot)
echo ===================================
echo.
python main.py
echo.
echo Bot has been stopped.
pause
