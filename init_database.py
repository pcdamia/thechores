#!/usr/bin/env python3
"""
Standalone database initialization script.
Run this to initialize the database without importing the full Flask app.
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables before importing Flask
os.environ.setdefault('FLASK_APP', 'app')

# Set database URL - use absolute path for local development (cross-platform)
db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'chores.db'))
db_dir = os.path.dirname(db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
# SQLite URL: use forward slashes (Windows paths need conversion for sqlite:///C:/path)
db_url_path = db_path.replace('\\', '/')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{db_url_path}')

from app.database import init_db

if __name__ == '__main__':
    print("Initializing database...")
    try:
        init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
