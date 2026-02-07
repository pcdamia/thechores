#!/usr/bin/env python3
"""
Database migration script to add new fields for images and categories.
Run this after updating the models to add the new columns to existing databases.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('FLASK_APP', 'app')

from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print("Migrating database...")
    try:
        # This will add new columns if they don't exist
        # Note: SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly
        # So we'll use a try/except approach or check if columns exist first
        
        # For SQLite, we need to check if columns exist before adding
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        store_columns = [col['name'] for col in inspector.get_columns('stores')]
        item_columns = [col['name'] for col in inspector.get_columns('items')]
        
        # Add new columns to users table
        if 'profile_image' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN profile_image VARCHAR(255)'))
            db.session.commit()
            print("Added profile_image to users")
        if 'background_image' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN background_image VARCHAR(255)'))
            db.session.commit()
            print("Added background_image to users")
        if 'background_gradient' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN background_gradient VARCHAR(100)'))
            db.session.commit()
            print("Added background_gradient to users")
        if 'color_scheme' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN color_scheme VARCHAR(50) DEFAULT "default"'))
            db.session.commit()
            print("Added color_scheme to users")
        if 'background_position' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN background_position VARCHAR(50) DEFAULT "centered"'))
            db.session.commit()
            print("Added background_position to users")
        
        # Add new columns to stores table
        if 'image' not in store_columns:
            db.session.execute(text('ALTER TABLE stores ADD COLUMN image VARCHAR(255)'))
            db.session.commit()
            print("Added image to stores")
        if 'color_code' not in store_columns:
            db.session.execute(text('ALTER TABLE stores ADD COLUMN color_code VARCHAR(20)'))
            db.session.commit()
            print("Added color_code to stores")
        if 'categories_text' not in store_columns:
            db.session.execute(text('ALTER TABLE stores ADD COLUMN categories_text VARCHAR(255)'))
            db.session.commit()
            print("Added categories_text to stores")
        if 'logo' not in store_columns:
            db.session.execute(text('ALTER TABLE stores ADD COLUMN logo VARCHAR(255)'))
            db.session.commit()
            print("Added logo to stores")
        
        # Remove old category column from stores if it exists (we're using many-to-many now)
        # But keep it for backward compatibility for now
        
        # Add new columns to items table
        if 'image' not in item_columns:
            db.session.execute(text('ALTER TABLE items ADD COLUMN image VARCHAR(255)'))
            db.session.commit()
            print("Added image to items")
        
        # Create item_stores junction table (items can have multiple stores)
        try:
            inspector.get_columns('item_stores')
            print("item_stores table already exists")
        except Exception:
            from app.models import item_stores
            db.create_all()
            print("Created item_stores table")
            # Backfill from items.store_id
            for row in db.session.execute(text('SELECT id, store_id FROM items WHERE store_id IS NOT NULL')):
                db.session.execute(text('INSERT OR IGNORE INTO item_stores (item_id, store_id) VALUES (:i, :s)'), {'i': row[0], 's': row[1]})
            db.session.commit()
            print("Backfilled item_stores from items.store_id")
        
        # Create categories table if it doesn't exist
        try:
            inspector.get_columns('categories')
            print("Categories table already exists")
        except:
            from app.models import Category, store_categories, item_categories
            db.create_all()
            print("Created categories and junction tables")
        
        # Create events table if it doesn't exist
        try:
            event_columns = [col['name'] for col in inspector.get_columns('events')]
            # Add event_type column if it doesn't exist
            if 'event_type' not in event_columns:
                db.session.execute(text('ALTER TABLE events ADD COLUMN event_type VARCHAR(50)'))
                db.session.commit()
                print("Added event_type to events")
        except:
            from app.models import Event
            db.create_all()
            print("Created events table")
        
        # Update shopping lists table
        try:
            shopping_columns = [col['name'] for col in inspector.get_columns('shopping_lists')]
            # Add budget and actual_spent columns if they don't exist
            if 'budget' not in shopping_columns:
                db.session.execute(text('ALTER TABLE shopping_lists ADD COLUMN budget FLOAT DEFAULT 0.0'))
                db.session.commit()
                print("Added budget to shopping_lists")
            if 'actual_spent' not in shopping_columns:
                db.session.execute(text('ALTER TABLE shopping_lists ADD COLUMN actual_spent FLOAT DEFAULT 0.0'))
                db.session.commit()
                print("Added actual_spent to shopping_lists")
        except Exception as e:
            print(f"Note: shopping_lists table may not exist yet: {e}")
        
        # Update projects table
        try:
            project_columns = [col['name'] for col in inspector.get_columns('projects')]
            if 'completed' not in project_columns:
                db.session.execute(text('ALTER TABLE projects ADD COLUMN completed BOOLEAN DEFAULT 0'))
                db.session.commit()
                print("Added completed to projects")
            if 'completed_date' not in project_columns:
                db.session.execute(text('ALTER TABLE projects ADD COLUMN completed_date DATE'))
                db.session.commit()
                print("Added completed_date to projects")
            if 'assignee_notes' not in project_columns:
                db.session.execute(text('ALTER TABLE projects ADD COLUMN assignee_notes TEXT'))
                db.session.commit()
                print("Added assignee_notes to projects")
            if 'completed_photo' not in project_columns:
                db.session.execute(text('ALTER TABLE projects ADD COLUMN completed_photo VARCHAR(255)'))
                db.session.commit()
                print("Added completed_photo to projects")
            if 'completed_by_id' not in project_columns:
                db.session.execute(text('ALTER TABLE projects ADD COLUMN completed_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
                print("Added completed_by_id to projects")
            # Create project_users junction if not exists
            try:
                inspector.get_columns('project_users')
                print("project_users table already exists")
            except Exception:
                from app.models import Project, project_users
                db.create_all()
                print("Created project_users table")
            # Backfill project_users from existing user_id (only if junction is empty)
            try:
                from app.models import Project, project_users
                from sqlalchemy import func
                count = db.session.query(func.count()).select_from(project_users).scalar()
                if count == 0:
                    for proj in db.session.query(Project).all():
                        if proj.user_id:
                            db.session.execute(project_users.insert().values(project_id=proj.id, user_id=proj.user_id))
                    db.session.commit()
                    print("Backfilled project_users from user_id")
            except Exception as be:
                print(f"Backfill project_users: {be}")
        except Exception as e:
            print(f"Note: projects table may not exist yet: {e}")
        
        # Create notifications table if it doesn't exist
        try:
            inspector.get_columns('notifications')
            print("notifications table already exists")
        except Exception:
            from app.models import Notification
            db.create_all()
            print("Created notifications table")
        
        # Create chore_history table if it doesn't exist
        try:
            inspector.get_columns('chore_history')
            print("Chore history table already exists")
        except:
            from app.models import ChoreHistory
            db.create_all()
            print("Created chore_history table")
        
        # User color_code (family member color)
        if 'color_code' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN color_code VARCHAR(7)'))
            db.session.commit()
            print("Added color_code to users")
        if 'status' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN status VARCHAR(50)'))
            db.session.commit()
            print("Added status to users")
        if 'title' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN title VARCHAR(100)'))
            db.session.commit()
            print("Added title to users")
        if 'quick_chores' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN quick_chores TEXT'))
            db.session.commit()
            print("Added quick_chores to users")
        if 'quick_events' not in user_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN quick_events TEXT'))
            db.session.commit()
            print("Added quick_events to users")
        
        # Event updated_at / updated_by_id
        try:
            ev_cols = [col['name'] for col in inspector.get_columns('events')]
            if 'updated_at' not in ev_cols:
                db.session.execute(text('ALTER TABLE events ADD COLUMN updated_at DATETIME'))
                db.session.commit()
                print("Added updated_at to events")
            if 'updated_by_id' not in ev_cols:
                db.session.execute(text('ALTER TABLE events ADD COLUMN updated_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
                print("Added updated_by_id to events")
        except Exception as e:
            print(f"Note: events table columns: {e}")
        
        # ChoreTracker updated_at / updated_by_id
        try:
            ct_cols = [col['name'] for col in inspector.get_columns('chore_tracker')]
            if 'updated_at' not in ct_cols:
                db.session.execute(text('ALTER TABLE chore_tracker ADD COLUMN updated_at DATETIME'))
                db.session.commit()
                print("Added updated_at to chore_tracker")
            if 'updated_by_id' not in ct_cols:
                db.session.execute(text('ALTER TABLE chore_tracker ADD COLUMN updated_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
                print("Added updated_by_id to chore_tracker")
            if 'due_by_date' not in ct_cols:
                db.session.execute(text('ALTER TABLE chore_tracker ADD COLUMN due_by_date DATE'))
                db.session.commit()
                print("Added due_by_date to chore_tracker")
            if 'assigner_notes' not in ct_cols:
                db.session.execute(text('ALTER TABLE chore_tracker ADD COLUMN assigner_notes TEXT'))
                db.session.commit()
                print("Added assigner_notes to chore_tracker")
            if 'approved_by_id' not in ct_cols:
                db.session.execute(text('ALTER TABLE chore_tracker ADD COLUMN approved_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
                print("Added approved_by_id to chore_tracker")
        except Exception as e:
            print(f"Note: chore_tracker columns: {e}")
        
        # Chore assigned_by_id
        try:
            chore_cols = [col['name'] for col in inspector.get_columns('chores')]
            if 'assigned_by_id' not in chore_cols:
                db.session.execute(text('ALTER TABLE chores ADD COLUMN assigned_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
                print("Added assigned_by_id to chores")
        except Exception as e:
            print(f"Note: chores columns: {e}")
        
        # Items store_id (preferred store for this item)
        try:
            item_cols = [col['name'] for col in inspector.get_columns('items')]
            if 'store_id' not in item_cols:
                db.session.execute(text('ALTER TABLE items ADD COLUMN store_id INTEGER REFERENCES stores(id)'))
                db.session.commit()
                print("Added store_id to items")
        except Exception as e:
            print(f"Note: items store_id: {e}")
        
        # Token / cash-out / Chore Store tables
        from app.models import SiteSettings, CashOutRequest, StoreItem, UserPurchase
        for table in ['site_settings', 'cash_out_requests', 'store_items', 'user_purchases']:
            try:
                inspector.get_columns(table)
                print(f"{table} table already exists")
            except Exception:
                db.create_all()
                print(f"Created {table} table")
        
        # Default token settings if missing
        if not SiteSettings.query.get('tokens_per_dollar'):
            s = SiteSettings(key='tokens_per_dollar', value='100')
            db.session.add(s)
            db.session.commit()
            print("Added default tokens_per_dollar = 100")
        if not SiteSettings.query.get('cash_out_interest_rate'):
            s = SiteSettings(key='cash_out_interest_rate', value='1.0')
            db.session.add(s)
            db.session.commit()
            print("Added default cash_out_interest_rate = 1.0")
        
        # Seed Chore Store with example items if empty
        if StoreItem.query.count() == 0:
            for order, (title, desc, rules, cost) in enumerate([
                ('No-No', "When used on a parent or event, the parent cannot say 'No'.", "Must be used within reason. Cannot be used to ask for monetary prizes unless cashing in.\nMust be used within 30 days of purchase. Cannot be extended.\nThe physical ticket should be presented to a parent when cashing in.", 1000),
                ('Chore Forwarder', "When used, Person A can forward a chore to another person. Unless Person B has a 'No-No' or 'Chore Free' ticket.", '', 50),
                ('Chore Free', "When used the recipient is exempt from all chores for 24 hours. The chores are reassigned to another user for the duration.", '', 50),
            ]):
                item = StoreItem(title=title, description=desc, rules=rules or None, cost_tokens=cost, active=True, sort_order=order)
                db.session.add(item)
            db.session.commit()
            print("Added example Chore Store items")
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
