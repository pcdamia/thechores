from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models import db, Store, Category
from app.utils import save_uploaded_file, delete_uploaded_file
import json

stores_bp = Blueprint('stores', __name__)

@stores_bp.route('/')
@login_required
def list_stores():
    stores = Store.query.all()
    return render_template('stores.html', stores=stores)

@stores_bp.route('/api', methods=['GET'])
@login_required
def get_stores():
    stores = Store.query.all()
    return jsonify([store.to_dict() for store in stores])

@stores_bp.route('/api', methods=['POST'])
@login_required
def create_store():
    # Handle form data (for file uploads) or JSON
    if request.is_json:
        data = request.json
        image = None
        logo = None
    else:
        data = request.form.to_dict()
        image = request.files.get('image')
        logo = request.files.get('logo')
    
    store = Store(
        name=data.get('name'),
        budget=float(data.get('budget', 0)),
        color_code=(data.get('color_code') or '').strip() or None,
        categories_text=(data.get('categories_text') or '').strip() or None
    )
    
    # Handle image upload
    if image and image.filename:
        filepath = save_uploaded_file(image, 'stores')
        if filepath:
            store.image = filepath
    # Handle logo upload (small icon for store chip)
    if logo and logo.filename:
        logopath = save_uploaded_file(logo, 'stores/logos')
        if logopath:
            store.logo = logopath
    
    # Handle categories (may be JSON string from FormData)
    category_names = data.get('categories', [])
    if isinstance(category_names, str):
        try:
            category_names = json.loads(category_names)
        except (ValueError, TypeError):
            category_names = [c.strip() for c in category_names.split(',') if c.strip()]
    if not isinstance(category_names, list):
        category_names = []
    
    for cat_name in category_names[:5]:  # Limit to 5 categories
        if cat_name:
            category = Category.query.filter_by(name=str(cat_name).strip(), type='store').first()
            if not category:
                category = Category(name=str(cat_name).strip(), type='store')
                db.session.add(category)
            store.categories.append(category)
    
    db.session.add(store)
    db.session.commit()
    return jsonify(store.to_dict()), 201

@stores_bp.route('/api/<int:store_id>', methods=['GET'])
@login_required
def get_store(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    return jsonify(store.to_dict())

@stores_bp.route('/api/<int:store_id>', methods=['PUT'])
@login_required
def update_store(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    # Handle form data or JSON
    if request.is_json:
        data = request.json
        image = None
        logo = None
    else:
        data = request.form.to_dict()
        image = request.files.get('image')
        logo = request.files.get('logo')
    
    store.name = data.get('name', store.name)
    store.budget = float(data.get('budget', store.budget))
    # Always apply these when present (FormData always sends them)
    store.color_code = (data.get('color_code') or '').strip() or None
    store.categories_text = (data.get('categories_text') or '').strip() or None
    
    # Handle image upload
    if image and image.filename:
        if store.image:
            delete_uploaded_file(store.image)
        filepath = save_uploaded_file(image, 'stores')
        if filepath:
            store.image = filepath
    # Handle logo upload
    if logo and logo.filename:
        if store.logo:
            delete_uploaded_file(store.logo)
        logopath = save_uploaded_file(logo, 'stores/logos')
        if logopath:
            store.logo = logopath
    
    # Clear old category links so they can be removed; categories_text is the single source of truth for display
    store.categories.clear()
    category_names = data.get('categories', [])
    if isinstance(category_names, str):
        try:
            category_names = json.loads(category_names)
        except (ValueError, TypeError):
            category_names = [c.strip() for c in category_names.split(',') if c.strip()]
    if isinstance(category_names, list):
        for cat_name in category_names[:5]:
            if cat_name:
                category = Category.query.filter_by(name=str(cat_name).strip(), type='store').first()
                if not category:
                    category = Category(name=str(cat_name).strip(), type='store')
                    db.session.add(category)
                store.categories.append(category)
    
    db.session.commit()
    return jsonify(store.to_dict())

@stores_bp.route('/api/<int:store_id>', methods=['DELETE'])
@login_required
def delete_store(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    # Delete associated image and logo
    if store.image:
        delete_uploaded_file(store.image)
    if store.logo:
        delete_uploaded_file(store.logo)
    
    db.session.delete(store)
    db.session.commit()
    return jsonify({'success': True})
