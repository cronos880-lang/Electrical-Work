@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo Electrical Work necesita Python 3 instalado en Windows.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
%PYTHON_CMD% -c "from PIL import Image, ImageTk" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Para visualizar simbolos y letras con suavizado de alta calidad
    echo se recomienda instalar Pillow una sola vez.
    echo El programa tambien funciona sin Pillow, pero sin suavizado adicional.
    choice /C SN /N /M "Instalar Pillow ahora? [S/N]: "
    if errorlevel 2 goto LAUNCH
    %PYTHON_CMD% -m pip install --user "Pillow>=9"
    if errorlevel 1 (
        echo No se ha podido instalar Pillow. Se abrira con el dibujo clasico.
        pause
    )
)
:LAUNCH
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
%PYTHON_CMD% "%~dp0electrical_work.py"
exit /b %errorlevel%
