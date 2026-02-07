#!/bin/sh
# The Chores v1.5 - Run script (Linux / Home Assistant add-on)
# Prerequisites: Python 3, pip install -r requirements.txt (for local dev)
# Unbuffered output so add-on log shows output before container exits
export PYTHONUNBUFFERED=1

_log() {
  echo "[The Chores] $*"
  [ -d "/data" ] && echo "[The Chores] $*" >> /data/startup.log 2>/dev/null
}
_log "run.sh started (cwd=$(pwd))"

# Set Flask app
export FLASK_APP=app

# Determine database and upload paths (Home Assistant uses /data, local dev uses ./data)
if [ -d "/data" ]; then
    DB_PATH="/data/chores.db"
    export DATABASE_URL="sqlite:///$DB_PATH"
    export UPLOAD_FOLDER="/data/uploads"
    mkdir -p /data/uploads
    _log "using /data: DB=$DB_PATH"
    # Read add-on options (secret_key, log_level) from HA options.json if present
    if [ -f "/data/options.json" ]; then
        _sk="$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('secret_key',''))" 2>/dev/null)"
        _ll="$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('log_level',''))" 2>/dev/null)"
        [ -n "$_sk" ] && export SECRET_KEY="$_sk"
        [ -n "$_ll" ] && export LOG_LEVEL="$_ll"
    fi
else
    # Local development - use project directory
    DB_PATH="$(pwd)/data/chores.db"
    export DATABASE_URL="sqlite:///$DB_PATH"
    _log "using local data: DB=$DB_PATH"
fi

# Initialize database if it doesn't exist
if [ ! -f "$DB_PATH" ]; then
    _log "Initializing database..."
    python3 -c "from app.database import init_db; init_db()" || { _log "init_db failed"; exit 1; }
    _log "Default login: admin / admin"
fi

# Run migrations if database exists (adds new columns/tables)
if [ -f "$DB_PATH" ]; then
    _log "Running migrations..."
    python3 migrate_database.py 2>/dev/null || true
fi

# Run Flask application
_log "Starting Flask on 0.0.0.0:5050..."
exec python3 -u -m flask run --host=0.0.0.0 --port=5050
