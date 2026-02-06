@echo off
TITLE BudgetEase Server
echo Starting BudgetEase...
echo.

:: Change to the script's directory
cd /d "%~dp0"

:: Check for common virtual environment names
IF EXIST "venv\Scripts\activate.bat" (
    echo Activating 'venv' virtual environment...
    call "venv\Scripts\activate.bat"
) ELSE IF EXIST ".venv\Scripts\activate.bat" (
    echo Activating '.venv' virtual environment...
    call ".venv\Scripts\activate.bat"
) ELSE IF EXIST "env\Scripts\activate.bat" (
    echo Activating 'env' virtual environment...
    call "env\Scripts\activate.bat"
) ELSE (
    echo No virtual environment found. Using system Python...
)

echo.
echo ---------------------------------------------------
echo  Server is running at http://127.0.0.1:5000/
echo  Press Ctrl+C to stop.
echo ---------------------------------------------------
echo.

:: Run the Flask app
python app.py

:: If python fails (non-zero exit code), pause so user can read error
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application crashed or exited with an error.
    pause
)
