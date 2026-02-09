from app.models import db, User
from app.auth import hash_password
import os

def init_db():
    """Initialize the database with tables and default admin user"""
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create default admin user
            admin = User(
                username='admin',
                password_hash=hash_password('admin'),
                name='Administrator',
                is_admin=True,
                bank=0.0
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: username='admin', password='admin'")
            print("Please change the password on first login!")
