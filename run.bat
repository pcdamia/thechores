@echo off
REM The Chores v1.5 - Run script (Windows)
REM Prerequisites: Python 3, pip install -r requirements.txt
REM Change to the directory where this script lives (project root)
cd /d "%~dp0"

REM Unbuffered output so add-on log shows output before container exits
set PYTHONUNBUFFERED=1

REM Set Flask app
set FLASK_APP=app

REM Local development - use project directory (Windows)
set DB_PATH=%CD%\data\chores.db
REM SQLite URL: use relative path so it works from project root
set DATABASE_URL=sqlite:///data/chores.db
set UPLOAD_FOLDER=%CD%\data\uploads

echo [The Chores] run.bat started (cwd=%CD%)

REM Create data directory if it doesn't exist
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads

REM Initialize database if it doesn't exist
if not exist "%DB_PATH%" (
    echo [The Chores] Initializing database...
    python -c "from app.database import init_db; init_db()"
    if errorlevel 1 (
        echo [The Chores] init_db failed
        exit /b 1
    )
    echo [The Chores] Default login: admin / admin
)

REM Run migrations if database exists
if exist "%DB_PATH%" (
    echo [The Chores] Running migrations...
    python migrate_database.py 2>nul
)

REM Run Flask application
echo [The Chores] Starting Flask on 0.0.0.0:5050...
python -u -m flask run --host=0.0.0.0 --port=5050
