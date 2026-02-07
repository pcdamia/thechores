from flask import Flask
from flask_login import LoginManager, login_required
from app.database import db
from app.models import User
import os
import logging

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 180 * 24 * 3600  # 180 days for static caching in production
    
    # Database URL configuration
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Default to data/chores.db in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, 'data', 'chores.db')
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        # Use absolute path for SQLite
        # SQLite URLs: sqlite:///relative/path (3 slashes) or sqlite:////absolute/path (4 slashes)
        db_path = os.path.abspath(db_path)
        # For absolute paths, SQLite needs 4 slashes total: sqlite:////absolute/path
        # The path already starts with /, so we use sqlite:/// + /path = sqlite:////path
        db_url = f'sqlite:///{db_path}'
    elif db_url.startswith('sqlite:///'):
        # Handle existing sqlite:/// URLs
        db_path = db_url.replace('sqlite:///', '')
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        # Use absolute path for SQLite
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        # SQLite URLs: absolute paths need 4 slashes (sqlite:////path)
        # The path already starts with /, so sqlite:/// + /path = sqlite:////path
        db_url = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    
    # Log level from HA options or env (info, debug, warning, error, critical)
    log_level = os.environ.get('LOG_LEVEL', 'info').upper()
    level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=level)
    app.logger.setLevel(level)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.stores import stores_bp
    from app.routes.items import items_bp
    from app.routes.chores import chores_bp
    from app.routes.rooms import rooms_bp
    from app.routes.projects import projects_bp
    from app.routes.settings import settings_bp
    from app.routes.categories import categories_bp
    from app.routes.events import events_bp
    from app.routes.shopping_lists import shopping_lists_bp
    from app.routes.store import store_bp
    from app.routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(stores_bp, url_prefix='/stores')
    app.register_blueprint(items_bp, url_prefix='/items')
    app.register_blueprint(chores_bp, url_prefix='/chores')
    app.register_blueprint(rooms_bp, url_prefix='/rooms')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(shopping_lists_bp, url_prefix='/shopping-lists')
    app.register_blueprint(store_bp, url_prefix='/store')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    
    # Serve uploaded files with cache control
    @app.route('/static/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask import send_from_directory, make_response
        upload_root = app.config['UPLOAD_FOLDER']
        if not os.path.isabs(upload_root):
            upload_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), upload_root)
        response = make_response(send_from_directory(upload_root, filename))
        # Add cache control headers
        response.cache_control.max_age = 3600
        response.cache_control.public = True
        return response
    
    # Root route - public home page (dashboard for everyone)
    @app.route('/')
    def index():
        from flask import render_template, redirect, url_for
        from flask_login import current_user
        # Always show dashboard, but personalized if logged in
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('home.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        from flask import render_template
        return render_template('dashboard.html')
    
    @app.route('/health')
    def health():
        """Health check for HA / load balancers."""
        return '', 200
    
    return app
