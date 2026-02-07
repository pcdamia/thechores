from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.models import db, Category

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/api', methods=['GET'])
@login_required
def get_categories():
    category_type = request.args.get('type', 'item')  # 'item' or 'store'
    categories = Category.query.filter_by(type=category_type).all()
    return jsonify([cat.to_dict() for cat in categories])

@categories_bp.route('/api', methods=['POST'])
@login_required
def create_category():
    data = request.json
    name = data.get('name', '').strip()
    category_type = data.get('type', 'item')
    
    if not name:
        return jsonify({'error': 'Category name is required'}), 400
    
    # Check if category already exists
    existing = Category.query.filter_by(name=name, type=category_type).first()
    if existing:
        return jsonify(existing.to_dict())
    
    # Create new category
    category = Category(name=name, type=category_type)
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201

@categories_bp.route('/api/search', methods=['GET'])
@login_required
def search_categories():
    query = request.args.get('q', '').strip()
    category_type = request.args.get('type', 'item')
    
    if not query:
        categories = Category.query.filter_by(type=category_type).limit(10).all()
    else:
        categories = Category.query.filter(
            Category.type == category_type,
            Category.name.ilike(f'%{query}%')
        ).limit(10).all()
    
    return jsonify([cat.to_dict() for cat in categories])
