@echo off
cd /d "%~dp0"
py -3 electrical_work.py
if errorlevel 1 pause
