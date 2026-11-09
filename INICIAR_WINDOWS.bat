@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%~dp0electrical_work.py"
    exit /b 0
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0electrical_work.py"
    exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0electrical_work.py"
    exit /b %errorlevel%
)
echo Electrical Work necesita Python 3 instalado en Windows.
echo Descarga Python 3 desde https://www.python.org/downloads/
pause
