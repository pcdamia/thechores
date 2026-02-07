# The Chores - Home Assistant Add-on

**Version 1.5.1**

A modern chore and inventory tracking system with a beautiful glass morphism UI, designed as a Home Assistant add-on.

## Features

- **Chore Management**: Track chores with frequency, assignments, rewards, and room associations
- **Inventory Tracking**: Monitor items with quantity tracking, low stock alerts, and purchase history
- **Store Management**: Track stores with budgets and categories
- **Room Management**: Organize chores by room with cleaning schedules
- **Project Tracking**: Manage projects with severity levels and rewards
- **Tokens & Chore Store**: Earn tokens from chores/projects; spend in Chore Store; cash out at admin-set rate
- **User Management**: Admin can create/delete users, edit tokens, reset passwords
- **Security**: Password encryption with bcrypt and security questions for password reset

## Installation

**Add-ons (Supervisor) are only available on Home Assistant OS or Supervised.** If you run **Home Assistant Core** (the Python app only), there is no Supervisor and no Settings → Add-ons or “Local Add-ons” — use one of the options below instead.

### Option A: As a Home Assistant Add-on (Home Assistant OS or Supervised only)

1. Copy this directory into your Home Assistant `addons` folder (e.g. `config/addons/thechores` or via the add-on store if you add a custom repository).
2. In Home Assistant, go to **Settings → Add-ons → Add-on Store**. If you use a local folder, open **Add-on Store** and check for **Local add-ons** (or the three dots → Repositories) and add/refresh so “The Chores” appears.
3. Install “The Chores”, then Start the add-on.
4. Open the web UI at `http://your-home-assistant-ip:5050`.
5. **Production**: Set `secret_key` in the add-on **Configuration** tab and change the default admin password after first login.

**If the add-on keeps restarting or the Log tab is empty:** The add-on writes a startup trace to **add-on data**: `startup.log`. To view it: **Settings → Add-ons → The Chores → Configuration** (three dots) → **Diagnostics** → **Download diagnostics** (or use the File editor / Samba to open the add-on’s data folder and open `startup.log`). You should see lines like `[The Chores] run.sh started` and where it stopped. Also check **Settings → Add-ons → The Chores → Log** (or on the host: `ha addons logs local_thechores`); if you see `[The Chores] ...` lines, the last one shows how far startup got before the crash.

### Option B: With Home Assistant Core (no Supervisor / no add-ons)

If you run **Home Assistant Core** (e.g. 2026.1.x in a venv or Docker), there is no add-on system. Run The Chores as a separate service:

**Using Docker (recommended)**

1. Build and run the container, and pass config via environment variables:

   ```bash
   docker build -t thechores .
   docker run -d --name thechores -p 5050:5050 \
     -v thechores_data:/data \
     -e SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
     thechores
   ```

   Data (database, uploads) is stored in the `thechores_data` volume. Generate a real `SECRET_KEY` (see below) and change the default admin password after first login.

2. Open `http://localhost:5050` (or your host IP).

**Using Python (no Docker)**

1. Install dependencies and set environment variables (include a strong `SECRET_KEY`):

   ```bash
   pip install -r requirements.txt
   export FLASK_APP=app
   export DATABASE_URL=sqlite:///$(pwd)/data/chores.db
   export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
   ```

2. Initialize the database and run migrations:

   ```bash
   python3 init_database.py
   python3 migrate_database.py
   ```

3. Start the app:

   ```bash
   flask run --host=0.0.0.0 --port=5050
   ```

   Or use `./run.sh` (it will use `./data` when `/data` is not present).

### Running on Windows

1. Install Python 3 and ensure `python` is on your PATH.
2. In a terminal (Command Prompt or PowerShell) in the project folder:
   ```bat
   pip install -r requirements.txt
   run.bat
   ```
   Or double‑click `run.bat` in Explorer (run from the project folder).
3. Open **http://localhost:5050**. Default login: `admin` / `admin`.

   For a production-like setup, set `SECRET_KEY` before running (e.g. in a `.env` file or in System environment variables). Generate one with:
   ```bat
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   **Access from other computers on the network**  
   `run.bat` already binds to all interfaces (`--host=0.0.0.0`), so other devices on your LAN can reach the app. From another computer or phone on the same network, open `http://<this-PC-IP>:5050` (e.g. `http://192.168.1.100:5050`). Find this PC’s IP in Windows: **Settings → Network & Internet → Wi‑Fi or Ethernet → your connection → IPv4 address**. If the connection is blocked, allow Python or port 5050 in **Windows Defender Firewall → Advanced settings → Inbound rules**.

   **Single codebase / one place to update**  
   Keep the project in one folder (e.g. `C:\thechores`). Edit and run from that folder; everyone connects to the same instance. To edit the same code from multiple machines, use a shared drive or Git, but run the app on **one** machine so all clients hit the same server.

### How to get and set `secret_key`

- **Set (Home Assistant):** In the add-on’s **Configuration** tab, set the `secret_key` option to a long random string. The add-on reads it from `/data/options.json` and uses it as Flask’s `SECRET_KEY`.
- **Set (local / env):** Run with `SECRET_KEY=your-long-random-string` in the environment (e.g. `export SECRET_KEY=...` before starting, or in your process manager).
- **Get a value:** Generate a secure random key, for example:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
  Use the printed string as `secret_key` in HA Configuration or as `SECRET_KEY` in the environment. Do not use the default dev key in production.

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export FLASK_APP=app
   export DATABASE_URL=sqlite:///data/chores.db
   ```

3. Initialize the database:
   ```bash
   python3 init_database.py
   ```
   
   Or alternatively:
   ```bash
   python3 -c "from app.database import init_db; init_db()"
   ```
   
   **Note**: If you encounter SQLAlchemy compatibility issues with Python 3.13, upgrade SQLAlchemy:
   ```bash
   pip3 install --upgrade 'SQLAlchemy>=2.0.36'
   ```
   
   **Upgrading**: If you already have a database and are pulling new changes, run the migration to add new columns (e.g. user color codes, event/chore “last updated” tracking):
   ```bash
   python3 migrate_database.py
   ```

4. Run the application:
   ```bash
   flask run
   ```

## Default Login Credentials

**Default Admin Account:**
- **Username**: `admin`
- **Password**: `admin`

**⚠️ Important**: Change the password immediately after first login!

The default admin user is automatically created when the database is first initialized. If you need to reset the database, delete the `data/chores.db` file and run the initialization script again.

## Database Schema

- **Users**: Authentication, security questions, bank balances
- **Stores**: Store information with budgets
- **Items**: Inventory items with quantity tracking
- **Chores**: Task definitions with frequency and rewards
- **Chore Tracker**: Completion history
- **Rooms**: Room organization with cleaning schedules
- **Projects**: Project tracking with severity and rewards

## API Endpoints

All endpoints require authentication unless specified.

### Authentication
- `GET/POST /auth/login` - Login
- `GET /auth/logout` - Logout
- `GET/POST /auth/register` - Register new user (admin only)
- `GET/POST /auth/reset-password` - Reset password flow

### CRUD Operations
- `/stores/api` - Stores CRUD
- `/items/api` - Items CRUD
- `/chores/api` - Chores CRUD
- `/rooms/api` - Rooms CRUD
- `/projects/api` - Projects CRUD
- `/users/` - User management (admin only)

## UI Design

The application features a modern glass morphism (Apple Glass Effect) design with:
- Backdrop blur effects
- Semi-transparent cards
- Smooth transitions
- Responsive layout
- Card-based interface similar to donetick

## Production & Home Assistant checklist

- **SECRET_KEY**: Set in add-on options (`secret_key`) when using the add-on; when using **Home Assistant Core** (Docker or Python), set the `SECRET_KEY` environment variable. If unset, the app uses a default (change in production).
- **Database**: Stored in `/data/chores.db` when running in Docker with a `/data` volume; migrations run automatically on container start if the DB exists.
- **Uploads**: Profile/images stored in `/data/uploads` when using `/data`; otherwise `static/uploads` (or `UPLOAD_FOLDER` env).
- **Default password**: Change the default `admin` / `admin` login after first use.
- **Port**: Web UI is on port 5050 (configurable in add-on port mapping or when running Docker/Python).

## Security

- Passwords and security answers are hashed using bcrypt
- Session-based authentication
- Admin-only routes are protected
- SQL injection prevention via SQLAlchemy ORM

## Still to do (roadmap)

- **Chores**: Due-by date picker; 2 tokens/day late penalty.
- **Stores**: Merge items below stores; store card color; categories as literal text + emoji.
- **Items**: Usage frequency value + unit (Day/Week/Month); low-stock alert flow.
- **Household page**: New page merging Users, Rooms, Projects + parking/garbage.
- **Rooms/Projects/Users**: Date format, room type, bedroom assignee, notes, completed, photo, multi-assign, “need more details”, card styling, profile pic, status, schedule, details view.
## License

MIT License
