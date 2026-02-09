from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Junction table for many-to-many relationship between Rooms and Chores
room_chores = db.Table('room_chores',
    db.Column('room_id', db.Integer, db.ForeignKey('rooms.id'), primary_key=True),
    db.Column('chore_id', db.Integer, db.ForeignKey('chores.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    bank = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    
    # User customization
    profile_image = db.Column(db.String(255), nullable=True)
    background_image = db.Column(db.String(255), nullable=True)
    background_gradient = db.Column(db.String(100), nullable=True)  # e.g., "135deg, #667eea 0%, #764ba2 100%"
    background_position = db.Column(db.String(50), default='centered')  # centered, tiled, stretched, fit
    color_scheme = db.Column(db.String(50), default='default')  # default, dark, light, custom
    color_code = db.Column(db.String(7), nullable=True)  # hex e.g. #ff5733 for family member display
    status = db.Column(db.String(50), nullable=True)  # at_school, at_work, overnight_stay, grocery_shopping, or custom
    title = db.Column(db.String(100), nullable=True)  # optional title/label
    quick_chores = db.Column(db.Text, nullable=True)  # JSON array of chore IDs for quick chores (max 8)
    quick_events = db.Column(db.Text, nullable=True)  # JSON array of event IDs for quick events (max 8)
    
    # Security questions
    security_question_1 = db.Column(db.String(255))
    security_answer_1_hash = db.Column(db.String(255))
    security_question_2 = db.Column(db.String(255))
    security_answer_2_hash = db.Column(db.String(255))
    security_question_3 = db.Column(db.String(255))
    security_answer_3_hash = db.Column(db.String(255))
    
    # Relationships
    assigned_chores = db.relationship('Chore', backref='assigned_user', lazy=True, foreign_keys='Chore.assigned_user_id')
    projects = db.relationship('Project', backref='user', lazy=True, foreign_keys='Project.user_id')
    
    def __repr__(self):
        return f'<User {self.username}>'


class SiteSettings(db.Model):
    """Key-value store for app-wide settings (e.g. token conversion rate)."""
    __tablename__ = 'site_settings'
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=True)


class CashOutRequest(db.Model):
    """User request to convert tokens to dollars at current rate."""
    __tablename__ = 'cash_out_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tokens = db.Column(db.Float, nullable=False)
    dollar_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('cash_out_requests', lazy=True))


class StoreItem(db.Model):
    """Item in the Chore Store that users can buy with tokens."""
    __tablename__ = 'store_items'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rules = db.Column(db.Text, nullable=True)  # optional rules text
    cost_tokens = db.Column(db.Float, nullable=False, default=0)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class UserPurchase(db.Model):
    """Record of a user purchasing a store item."""
    __tablename__ = 'user_purchases'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_item_id = db.Column(db.Integer, db.ForeignKey('store_items.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, used, expired
    user = db.relationship('User', backref=db.backref('purchases', lazy=True))
    store_item = db.relationship('StoreItem', backref=db.backref('purchases', lazy=True))


class Notification(db.Model):
    """In-app notification for a user (e.g. project needs more details)."""
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(255), nullable=True)  # optional URL to open
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'store', 'item'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type
        }

# Junction table for many-to-many relationship between Stores and Categories
store_categories = db.Table('store_categories',
    db.Column('store_id', db.Integer, db.ForeignKey('stores.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

# Junction table for many-to-many relationship between Items and Categories
item_categories = db.Table('item_categories',
    db.Column('item_id', db.Integer, db.ForeignKey('items.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

# Junction table for many-to-many: Items can be linked to multiple Stores
item_stores = db.Table('item_stores',
    db.Column('item_id', db.Integer, db.ForeignKey('items.id'), primary_key=True),
    db.Column('store_id', db.Integer, db.ForeignKey('stores.id'), primary_key=True)
)

class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, default=0.0)
    image = db.Column(db.String(255), nullable=True)
    logo = db.Column(db.String(255), nullable=True)  # small icon for store chip (e.g. in items, lists)
    color_code = db.Column(db.String(20), nullable=True)  # e.g. #hex for card tint/border
    categories_text = db.Column(db.String(255), nullable=True)  # literal text + emoji, e.g. "Produce 🥬, Dairy 🧀"
    
    # Many-to-many relationship with Categories
    categories = db.relationship('Category', secondary=store_categories, lazy='subquery', backref=db.backref('stores', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'budget': self.budget,
            'image': self.image,
            'logo': self.logo,
            'color_code': self.color_code,
            'categories_text': self.categories_text,
            'category_names': [cat.name for cat in self.categories]
        }

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    full_amount = db.Column(db.Integer, default=0)
    low_amount = db.Column(db.Integer, default=0)
    purchase_frequency = db.Column(db.String(50))
    last_purchase_date = db.Column(db.Date)
    purchase_unit_type = db.Column(db.String(50))
    usage_frequency = db.Column(db.String(50), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)  # primary/first store for backward compat
    
    # Many-to-many relationship with Categories
    categories = db.relationship('Category', secondary=item_categories, lazy='subquery', backref=db.backref('items', lazy=True))
    store = db.relationship('Store', backref=db.backref('items', lazy=True), foreign_keys=[store_id])
    # Multiple stores (many-to-many)
    stores = db.relationship('Store', secondary=item_stores, lazy='subquery', backref=db.backref('item_list', lazy=True))
    
    def to_dict(self):
        store_list = getattr(self, 'stores', None) or []
        store_ids = [s.id for s in store_list]
        store_names = [s.name for s in store_list]
        store_logos = [s.logo for s in store_list]
        return {
            'id': self.id,
            'name': self.name,
            'quantity': self.quantity,
            'full_amount': self.full_amount,
            'low_amount': self.low_amount,
            'purchase_frequency': self.purchase_frequency,
            'last_purchase_date': self.last_purchase_date.isoformat() if self.last_purchase_date else None,
            'purchase_unit_type': self.purchase_unit_type,
            'usage_frequency': self.usage_frequency,
            'image': self.image,
            'store_id': self.store_id,
            'store_name': self.store.name if self.store else None,
            'store_logo': self.store.logo if self.store else None,
            'store_ids': store_ids,
            'store_names': store_names,
            'store_logos': store_logos,
            'is_low': self.quantity <= self.low_amount if self.low_amount else False,
            'category_names': [cat.name for cat in self.categories]
        }

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    last_deep_cleaned = db.Column(db.Date)
    last_cleaned = db.Column(db.Date)
    
    # Many-to-many relationship with Chores
    chores = db.relationship('Chore', secondary=room_chores, lazy='subquery', backref=db.backref('rooms', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'last_deep_cleaned': self.last_deep_cleaned.isoformat() if self.last_deep_cleaned else None,
            'last_cleaned': self.last_cleaned.isoformat() if self.last_cleaned else None,
            'chore_ids': [chore.id for chore in self.chores]
        }

class Chore(db.Model):
    __tablename__ = 'chores'
    
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Description/details about the chore
    frequency = db.Column(db.String(50), nullable=True)  # Now nullable - frequency is on assignments, not template
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable - template doesn't need assignment
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who assigned this chore (usually admin)
    reward = db.Column(db.Float, default=0.0)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)  # Legacy single room - use rooms relationship
    
    # Relationships
    tracker_entries = db.relationship('ChoreTracker', backref='chore', lazy=True, cascade='all, delete-orphan')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='chores_created_by_me')
    
    def to_dict(self):
        room_names = [r.name for r in self.rooms] if self.rooms else []
        return {
            'id': self.id,
            'task': self.task,
            'description': self.description,
            'frequency': self.frequency,
            'assigned_user_id': self.assigned_user_id,
            'assigned_user_name': self.assigned_user.name if self.assigned_user else None,
            'assigned_by_id': self.assigned_by_id,
            'assigned_by_name': self.assigned_by.name if self.assigned_by else None,
            'reward': self.reward,
            'room_id': self.room_id,
            'room_name': self.rooms[0].name if self.rooms else None,
            'room_ids': [r.id for r in self.rooms] if self.rooms else [],
            'room_names': room_names
        }

class ChoreTracker(db.Model):
    __tablename__ = 'chore_tracker'

    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    due_by_datetime = db.Column(db.DateTime, nullable=True)  # Changed to datetime to include time
    frequency = db.Column(db.String(50), nullable=True)  # Frequency for this assignment (daily, weekly, etc.)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Assignment-specific user
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)  # Assignment-specific room
    status = db.Column(db.String(20), default='pending')  # pending, pending_approval, completed, skipped
    assigner_notes = db.Column(db.Text, nullable=True)  # Notes from assigner when reinstating
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who approved the completion
    updated_at = db.Column(db.DateTime, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id], backref='chore_assignments')
    room = db.relationship('Room', foreign_keys=[room_id], backref='chore_tracker_entries')

    def to_dict(self):
        return {
            'id': self.id,
            'chore_id': self.chore_id,
            'chore_task': self.chore.task if self.chore else None,
            'date': self.date.isoformat() if self.date else None,
            'due_by_datetime': self.due_by_datetime.isoformat() if self.due_by_datetime else None,
            'due_by_date': self.due_by_datetime.date().isoformat() if self.due_by_datetime else None,  # Backward compat
            'due_by_time': self.due_by_datetime.time().strftime('%H:%M') if self.due_by_datetime else None,
            'frequency': self.frequency,
            'assigned_user_id': self.assigned_user_id,
            'assigned_user_name': self.assigned_user.name if self.assigned_user else None,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room_id and hasattr(self, 'room') and self.room else None,
            'status': self.status,
            'assigner_notes': self.assigner_notes,
            'approved_by_id': self.approved_by_id,
            'approved_by_name': self.approved_by.name if self.approved_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.name if self.updated_by else None
        }

class ChoreHistory(db.Model):
    __tablename__ = 'chore_history'
    
    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=True)  # Nullable in case chore is deleted
    task = db.Column(db.String(255), nullable=False)  # Store task name in case chore is deleted
    frequency = db.Column(db.String(50), nullable=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_user_name = db.Column(db.String(100), nullable=True)  # Store name in case user is deleted
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    room_name = db.Column(db.String(100), nullable=True)  # Store name in case room is deleted
    reward = db.Column(db.Float, default=0.0)
    completed_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'chore_id': self.chore_id,
            'task': self.task,
            'frequency': self.frequency,
            'assigned_user_id': self.assigned_user_id,
            'assigned_user_name': self.assigned_user_name,
            'room_id': self.room_id,
            'room_name': self.room_name,
            'reward': float(self.reward),
            'completed_date': self.completed_date.isoformat() if self.completed_date else None
        }

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    event_type = db.Column(db.String(50), nullable=True)  # shopping, appointment, birthday, meeting, reminder, travel, event
    updated_at = db.Column(db.DateTime, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.strftime('%H:%M') if self.time else None,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.name if self.updated_by else None
        }

# Junction table for many-to-many: projects can have multiple assigned users
project_users = db.Table('project_users',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)


class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # primary assignee (backward compat)
    description = db.Column(db.Text)
    severity = db.Column(db.String(50))  # low, medium, high, urgent
    reward = db.Column(db.Float, default=0.0)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.Date, nullable=True)
    assignee_notes = db.Column(db.Text, nullable=True)  # notes from the assigned user(s)
    completed_photo = db.Column(db.String(255), nullable=True)  # optional photo when completed
    completed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # who marked complete (for card color)
    
    completed_by = db.relationship('User', foreign_keys=[completed_by_id])
    assigned_users = db.relationship('User', secondary=project_users, lazy='subquery', backref=db.backref('assigned_projects', lazy=True))
    
    def to_dict(self):
        # Primary assignee and list of all assignees
        user_ids = [u.id for u in self.assigned_users] if self.assigned_users else ([self.user_id] if self.user_id else [])
        user_names = [u.name for u in self.assigned_users] if self.assigned_users else ([self.user.name] if self.user else [])
        if not user_ids and self.user_id:
            user_ids = [self.user_id]
            user_names = [self.user.name] if self.user else []
        completed_by_user = self.completed_by
        color_code = (completed_by_user.color_code if completed_by_user and completed_by_user.color_code else None) or (self.user.color_code if self.user and self.user.color_code else None) or '#6b7280'
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'user_ids': user_ids,
            'user_names': user_names,
            'description': self.description,
            'severity': self.severity,
            'reward': self.reward,
            'completed': self.completed,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'assignee_notes': self.assignee_notes,
            'completed_photo': self.completed_photo,
            'completed_by_id': self.completed_by_id,
            'completed_by_name': self.completed_by.name if self.completed_by else None,
            'color_code': color_code,
        }

class ShoppingList(db.Model):
    __tablename__ = 'shopping_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    budget = db.Column(db.Float, default=0.0)
    actual_spent = db.Column(db.Float, default=0.0)
    
    # Relationships
    store = db.relationship('Store', backref='shopping_lists', lazy=True)
    user = db.relationship('User', backref='shopping_lists', lazy=True)
    items = db.relationship('ShoppingListItem', backref='shopping_list', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        budget_status = 'spot_on'
        if self.budget > 0:
            if self.actual_spent > self.budget:
                budget_status = 'over'
            elif self.actual_spent < self.budget:
                budget_status = 'under'
        
        return {
            'id': self.id,
            'name': self.name,
            'store_id': self.store_id,
            'store_name': self.store.name if self.store else None,
            'store_logo': self.store.logo if self.store else None,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed': self.completed,
            'budget': float(self.budget),
            'actual_spent': float(self.actual_spent),
            'budget_status': budget_status,
            'items': [item.to_dict() for item in self.items]
        }

class ShoppingListItem(db.Model):
    __tablename__ = 'shopping_list_items'
    
    id = db.Column(db.Integer, primary_key=True)
    shopping_list_id = db.Column(db.Integer, db.ForeignKey('shopping_lists.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(50), nullable=True)
    checked = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'shopping_list_id': self.shopping_list_id,
            'item_id': self.item_id,
            'name': self.name,
            'quantity': self.quantity,
            'unit': self.unit,
            'checked': self.checked
        }
