from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, ShoppingList, ShoppingListItem, Store, Item
from datetime import datetime

shopping_lists_bp = Blueprint('shopping_lists', __name__)

@shopping_lists_bp.route('/')
def list_shopping_lists():
    """Redirect to Shopping page (lists section is there)."""
    return redirect(url_for('stores.list_stores') + '#lists-section')

@shopping_lists_bp.route('/api', methods=['GET'])
def get_shopping_lists():
    """Get all active shopping lists"""
    shopping_lists = ShoppingList.query.filter_by(completed=False).order_by(ShoppingList.created_at.desc()).all()
    return jsonify([sl.to_dict() for sl in shopping_lists])

@shopping_lists_bp.route('/api/completed', methods=['GET'])
def get_completed_shopping_lists():
    """Get completed shopping lists grouped by date"""
    completed_lists = ShoppingList.query.filter_by(completed=True).order_by(ShoppingList.created_at.desc()).all()
    
    # Group by date (using created_at date part)
    from datetime import date
    grouped = {}
    for sl in completed_lists:
        if sl.created_at:
            date_str = sl.created_at.date().isoformat() if hasattr(sl.created_at, 'date') else sl.created_at.isoformat()[:10]
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(sl.to_dict())
    
    return jsonify(grouped)

@shopping_lists_bp.route('/api', methods=['POST'])
@login_required
def create_shopping_list():
    """Create a new shopping list"""
    data = request.json
    shopping_list = ShoppingList(
        name=data.get('name', 'New Shopping List'),
        store_id=data.get('store_id'),
        user_id=current_user.id if current_user.is_authenticated else None,
        budget=float(data.get('budget', 0)),
        actual_spent=float(data.get('actual_spent', 0))
    )
    db.session.add(shopping_list)
    db.session.commit()
    return jsonify(shopping_list.to_dict()), 201

@shopping_lists_bp.route('/api/<int:list_id>', methods=['GET'])
def get_shopping_list(list_id):
    """Get a specific shopping list"""
    shopping_list = db.session.get(ShoppingList, list_id)
    if not shopping_list:
        return jsonify({'error': 'Shopping list not found'}), 404
    return jsonify(shopping_list.to_dict())

@shopping_lists_bp.route('/api/<int:list_id>', methods=['PUT'])
@login_required
def update_shopping_list(list_id):
    """Update a shopping list"""
    shopping_list = db.session.get(ShoppingList, list_id)
    if not shopping_list:
        return jsonify({'error': 'Shopping list not found'}), 404
    
    data = request.json
    shopping_list.name = data.get('name', shopping_list.name)
    shopping_list.store_id = data.get('store_id', shopping_list.store_id)
    if 'completed' in data:
        shopping_list.completed = data.get('completed', shopping_list.completed)
    shopping_list.budget = float(data.get('budget', shopping_list.budget))
    shopping_list.actual_spent = float(data.get('actual_spent', shopping_list.actual_spent))
    
    db.session.commit()
    return jsonify(shopping_list.to_dict())

@shopping_lists_bp.route('/api/<int:list_id>', methods=['DELETE'])
@login_required
def delete_shopping_list(list_id):
    """Delete a shopping list"""
    shopping_list = db.session.get(ShoppingList, list_id)
    if not shopping_list:
        return jsonify({'error': 'Shopping list not found'}), 404
    
    db.session.delete(shopping_list)
    db.session.commit()
    return jsonify({'success': True})

@shopping_lists_bp.route('/api/<int:list_id>/items', methods=['DELETE'])
@login_required
def clear_list_items(list_id):
    """Remove all items from a shopping list (used when replacing items on edit)."""
    shopping_list = db.session.get(ShoppingList, list_id)
    if not shopping_list:
        return jsonify({'error': 'Shopping list not found'}), 404
    ShoppingListItem.query.filter_by(shopping_list_id=list_id).delete()
    db.session.commit()
    return jsonify({'success': True})


@shopping_lists_bp.route('/api/<int:list_id>/items', methods=['POST'])
@login_required
def add_item_to_list(list_id):
    """Add an item to a shopping list. If name is given and no item_id, create a new Item for the list's store."""
    shopping_list = db.session.get(ShoppingList, list_id)
    if not shopping_list:
        return jsonify({'error': 'Shopping list not found'}), 404
    
    data = request.json or {}
    name = (data.get('name') or '').strip()
    item_id = data.get('item_id')
    quantity = float(data.get('quantity', 1.0))
    unit = data.get('unit')
    
    if not item_id and name:
        store_id = shopping_list.store_id
        existing = Item.query.filter(Item.name.ilike(name)).all()
        item_obj = next((i for i in existing if (i.store_id == store_id or (store_id and any(s.id == store_id for s in i.stores)))), None)
        if not item_obj and existing:
            item_obj = existing[0]
        if not item_obj:
            item_obj = Item(name=name, quantity=0, store_id=store_id)
            db.session.add(item_obj)
            db.session.flush()
            if store_id:
                store = db.session.get(Store, store_id)
                if store and store not in item_obj.stores:
                    item_obj.stores.append(store)
        item_id = item_obj.id
    
    item_name = name
    if item_id:
        existing_item = db.session.get(Item, item_id)
        if existing_item:
            item_name = item_name or existing_item.name
    row = ShoppingListItem(
        shopping_list_id=list_id,
        item_id=item_id,
        name=item_name or name or 'Item',
        quantity=quantity,
        unit=unit
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201

@shopping_lists_bp.route('/api/items/<int:item_id>', methods=['PUT'])
@login_required
def update_list_item(item_id):
    """Update a shopping list item"""
    item = db.session.get(ShoppingListItem, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    data = request.json
    item.name = data.get('name', item.name)
    item.quantity = float(data.get('quantity', item.quantity))
    item.unit = data.get('unit', item.unit)
    item.checked = data.get('checked', item.checked)
    
    db.session.commit()
    return jsonify(item.to_dict())

@shopping_lists_bp.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_list_item(item_id):
    """Delete a shopping list item"""
    item = db.session.get(ShoppingListItem, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})
