from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Item, Category, Store
from app.utils import save_uploaded_file, delete_uploaded_file
from datetime import datetime
import json

items_bp = Blueprint('items', __name__)


def _parse_store_id(val):
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _parse_store_ids(data, key='store_ids'):
    """Return list of store IDs from form/JSON (list or JSON string)."""
    val = data.get(key)
    if val is None:
        return []
    if isinstance(val, list):
        return [int(x) for x in val if x is not None and str(x).strip() and str(x) != 'undefined']
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return []
        try:
            out = json.loads(val)
            return [int(x) for x in (out if isinstance(out, list) else [out]) if x is not None and str(x).strip() and str(x) != 'undefined']
        except (ValueError, TypeError):
            sid = _parse_store_id(val)
            return [sid] if sid is not None else []
    return []


@items_bp.route('/')
@login_required
def list_items():
    return redirect(url_for('stores.list_stores') + '#items-section')

@items_bp.route('/api', methods=['GET'])
@login_required
def get_items():
    store_id = request.args.get('store_id', type=int)
    if store_id is not None:
        items = Item.query.filter(
            (Item.store_id == store_id) | Item.stores.any(Store.id == store_id)
        ).all()
    else:
        items = Item.query.all()
    return jsonify([item.to_dict() for item in items])

@items_bp.route('/api', methods=['POST'])
@login_required
def create_item():
    # Handle form data (for file uploads) or JSON
    if request.is_json:
        data = request.json
        image = None
    else:
        data = request.form.to_dict()
        image = request.files.get('image')
    
    store_id_val = request.form.get('store_id') if not request.is_json else data.get('store_id')
    store_ids = _parse_store_ids(data, 'store_ids')
    if not store_ids and store_id_val is not None:
        sid = _parse_store_id(store_id_val)
        if sid is not None:
            store_ids = [sid]
    first_store_id = store_ids[0] if store_ids else None
    
    item = Item(
        name=data.get('name'),
        quantity=float(data.get('quantity', 0)),
        full_amount=int(data.get('full_amount', 0)),
        low_amount=int(data.get('low_amount', 0)),
        purchase_frequency=data.get('purchase_frequency') if current_user.is_admin else None,
        last_purchase_date=datetime.strptime(data['last_purchase_date'], '%Y-%m-%d').date() if (current_user.is_admin and data.get('last_purchase_date')) else None,
        purchase_unit_type=data.get('purchase_unit_type'),
        usage_frequency=data.get('usage_frequency') if current_user.is_admin else None,
        store_id=first_store_id
    )
    
    db.session.add(item)
    db.session.flush()
    for sid in store_ids:
        store = Store.query.get(sid)
        if store and store not in item.stores:
            item.stores.append(store)
    
    # Handle image upload
    if image and image.filename:
        filepath = save_uploaded_file(image, 'items')
        if filepath:
            item.image = filepath
    
    # Handle categories (may be JSON string e.g. '["Grocery","Dairy"]')
    category_names = data.get('categories', [])
    if isinstance(category_names, str):
        s = category_names.strip()
        if s.startswith('['):
            try:
                parsed = json.loads(s)
                category_names = [str(x).strip() for x in (parsed if isinstance(parsed, list) else [parsed]) if x]
            except (ValueError, TypeError):
                category_names = [c.strip() for c in s.split(',') if c.strip()]
        else:
            category_names = [c.strip() for c in s.split(',') if c.strip()]
    if not isinstance(category_names, list):
        category_names = []
    for cat_name in category_names[:5]:  # Limit to 5 categories
        if cat_name:
            category = Category.query.filter_by(name=cat_name, type='item').first()
            if not category:
                category = Category(name=cat_name, type='item')
                db.session.add(category)
            item.categories.append(category)
    
    db.session.commit()
    return jsonify(item.to_dict()), 201

@items_bp.route('/api/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(item.to_dict())

@items_bp.route('/api/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    # Handle form data or JSON
    if request.is_json:
        data = request.json
        image = None
    else:
        data = request.form.to_dict()
        image = request.files.get('image')
    
    item.name = data.get('name', item.name)
    item.quantity = float(data.get('quantity', item.quantity))
    item.full_amount = int(data.get('full_amount', item.full_amount))
    item.low_amount = int(data.get('low_amount', item.low_amount))
    if current_user.is_admin:
        item.purchase_frequency = data.get('purchase_frequency', item.purchase_frequency)
        if data.get('last_purchase_date'):
            item.last_purchase_date = datetime.strptime(data['last_purchase_date'], '%Y-%m-%d').date()
        item.usage_frequency = data.get('usage_frequency', item.usage_frequency)
    # Store(s): read explicitly from form when multipart (fixes persistence); support multiple stores
    store_id_val = request.form.get('store_id') if not request.is_json else data.get('store_id')
    store_ids = _parse_store_ids(data, 'store_ids')
    if not store_ids and store_id_val not in (None, ''):
        sid = _parse_store_id(store_id_val)
        if sid is not None:
            store_ids = [sid]
    item.stores.clear()
    for sid in store_ids:
        store = Store.query.get(sid)
        if store and store not in item.stores:
            item.stores.append(store)
    item.store_id = item.stores[0].id if item.stores else None
    item.purchase_unit_type = data.get('purchase_unit_type', item.purchase_unit_type)
    
    # Handle image upload
    if image and image.filename:
        if item.image:
            delete_uploaded_file(item.image)
        filepath = save_uploaded_file(image, 'items')
        if filepath:
            item.image = filepath
    
    # Handle categories (may be JSON string)
    if 'categories' in data:
        item.categories.clear()
        category_names = data.get('categories', [])
        if isinstance(category_names, str):
            s = category_names.strip()
            if s.startswith('['):
                try:
                    parsed = json.loads(s)
                    category_names = [str(x).strip() for x in (parsed if isinstance(parsed, list) else [parsed]) if x]
                except (ValueError, TypeError):
                    category_names = [c.strip() for c in s.split(',') if c.strip()]
            else:
                category_names = [c.strip() for c in s.split(',') if c.strip()]
        if not isinstance(category_names, list):
            category_names = []
        for cat_name in category_names[:5]:
            if cat_name:
                category = Category.query.filter_by(name=cat_name, type='item').first()
                if not category:
                    category = Category(name=cat_name, type='item')
                    db.session.add(category)
                item.categories.append(category)
    
    db.session.commit()
    return jsonify(item.to_dict())

@items_bp.route('/api/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    # Delete associated image
    if item.image:
        delete_uploaded_file(item.image)
    
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

@items_bp.route('/api/low-stock', methods=['GET'])
@login_required
def get_low_stock():
    items = Item.query.all()
    low_stock = [item.to_dict() for item in items if item.quantity <= item.low_amount]
    return jsonify(low_stock)
