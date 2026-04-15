@echo off
echo ============================================
echo  ClaimIQ - Fix Local Environment
echo  Updates decommissioned Groq model names
echo ============================================
echo.

set ENV_FILE=.env

if not exist %ENV_FILE% (
    echo ERROR: .env file not found in current directory.
    echo Make sure you are in D:\insurance-claims-platform\
    echo Run: copy .env.example .env
    pause
    exit /b 1
)

echo [1/4] Backing up .env to .env.backup ...
copy /Y .env .env.backup >nul
echo       Done.

echo [2/4] Replacing decommissioned model names ...

:: Replace old model names with new ones using PowerShell
powershell -Command "(Get-Content '.env') -replace 'llama3-70b-8192', 'llama-3.3-70b-versatile' | Set-Content '.env'"
powershell -Command "(Get-Content '.env') -replace 'llama3-8b-8192', 'llama-3.1-8b-instant' | Set-Content '.env'"
powershell -Command "(Get-Content '.env') -replace 'mixtral-8x7b-32768', 'llama-3.3-70b-versatile' | Set-Content '.env'"

echo       Done.

echo [3/4] Verifying new model names ...
findstr "GROQ_MODEL" .env
echo.

echo [4/4] Reinstalling dependencies with fixed chromadb version ...
call venv\Scripts\activate.bat 2>nul || (
    echo       Note: venv not found, using system Python
)
pip install "chromadb==0.4.24" --quiet
pip install "pytest-timeout==2.3.1" --quiet
echo       Done.

echo.
echo ============================================
echo  DONE! Your .env now uses:
echo  - GROQ_MODEL_PRIMARY=llama-3.3-70b-versatile
echo  - GROQ_MODEL_FAST=llama-3.1-8b-instant
echo ============================================
echo.
echo Now restart the backend:
echo   python -m uvicorn app.main:app --reload --port 8000
echo.
pause
