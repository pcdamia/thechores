"""Chore Store: spend tokens, cash out, admin token settings and store items."""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, User, SiteSettings, CashOutRequest, StoreItem, UserPurchase, Notification

store_bp = Blueprint('store', __name__)


def get_setting(key, default=None):
    s = SiteSettings.query.get(key)
    return s.value if s else default


def tokens_to_dollars(tokens):
    try:
        per_dollar = float(get_setting('tokens_per_dollar') or 100)
        rate = float(get_setting('cash_out_interest_rate') or 1.0)
        return (tokens / per_dollar) * rate
    except (TypeError, ValueError):
        return 0.0


@store_bp.route('/')
@login_required
def store_page():
    return render_template('store.html')


@store_bp.route('/api/items', methods=['GET'])
@login_required
def list_items():
    admin = getattr(current_user, 'is_admin', False)
    q = StoreItem.query.filter_by(active=True) if not admin else StoreItem.query
    items = q.order_by(StoreItem.sort_order, StoreItem.id).all()
    return jsonify([{
        'id': i.id,
        'title': i.title,
        'description': i.description or '',
        'rules': i.rules or '',
        'cost_tokens': float(i.cost_tokens),
        'active': i.active,
    } for i in items])


@store_bp.route('/api/purchase', methods=['POST'])
@login_required
def purchase():
    data = request.get_json() or {}
    item_id = data.get('store_item_id')
    if not item_id:
        return jsonify({'error': 'store_item_id required'}), 400
    item = db.session.get(StoreItem, item_id)
    if not item or not item.active:
        return jsonify({'error': 'Item not found or inactive'}), 404
    user = db.session.get(User, current_user.id)
    cost = float(item.cost_tokens)
    if user.bank < cost:
        return jsonify({'error': 'Not enough tokens'}), 400
    user.bank -= cost
    purchase_record = UserPurchase(user_id=user.id, store_item_id=item.id, status='pending')
    db.session.add(purchase_record)
    db.session.commit()
    return jsonify({'success': True, 'balance': float(user.bank), 'message': f'Purchased {item.title}'})


@store_bp.route('/api/cash-out-info', methods=['GET'])
@login_required
def cash_out_info():
    user = db.session.get(User, current_user.id)
    per_dollar = get_setting('tokens_per_dollar', '100')
    rate = get_setting('cash_out_interest_rate', '1.0')
    try:
        per_dollar_f = float(per_dollar)
        rate_f = float(rate)
    except (TypeError, ValueError):
        per_dollar_f, rate_f = 100.0, 1.0
    balance = float(user.bank)
    dollar_value_full = (balance / per_dollar_f) * rate_f if per_dollar_f else 0
    return jsonify({
        'balance': balance,
        'tokens_per_dollar': per_dollar,
        'cash_out_interest_rate': rate,
        'dollar_value_if_cash_out_all': round(dollar_value_full, 2),
    })


@store_bp.route('/cash-out')
@login_required
def cash_out_page():
    return render_template('cash_out.html')


@store_bp.route('/api/cash-out', methods=['POST'])
@login_required
def submit_cash_out():
    data = request.get_json() or {}
    tokens = data.get('tokens')
    try:
        tokens = float(tokens)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid token amount'}), 400
    if tokens <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    user = db.session.get(User, current_user.id)
    if user.bank < tokens:
        return jsonify({'error': 'Not enough tokens'}), 400
    dollar_value = tokens_to_dollars(tokens)
    user.bank -= tokens
    req = CashOutRequest(user_id=user.id, tokens=tokens, dollar_value=dollar_value, status='pending')
    db.session.add(req)
    db.session.flush()
    # Notify all admins about the cash-out request
    admins = User.query.filter_by(is_admin=True).all()
    msg = f'{user.name} requested cash-out of {int(tokens)} tokens (${dollar_value:.2f}).'
    link = '/store/token-settings'
    for admin in admins:
        if admin.id != user.id:
            db.session.add(Notification(user_id=admin.id, message=msg, link=link))
    db.session.commit()
    return jsonify({'success': True, 'balance': float(user.bank), 'dollar_value': round(dollar_value, 2)})


@store_bp.route('/api/token-settings', methods=['GET'])
@login_required
def get_token_settings():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({
        'tokens_per_dollar': get_setting('tokens_per_dollar', '100'),
        'cash_out_interest_rate': get_setting('cash_out_interest_rate', '1.0'),
    })


@store_bp.route('/api/token-settings', methods=['PUT'])
@login_required
def update_token_settings():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for key in ('tokens_per_dollar', 'cash_out_interest_rate'):
        if key in data:
            val = str(data[key]).strip() if data[key] is not None else ''
            try:
                if key == 'tokens_per_dollar' and val:
                    float(val)
                if key == 'cash_out_interest_rate' and val:
                    float(val)
            except ValueError:
                continue
            s = SiteSettings.query.get(key) or SiteSettings(key=key)
            s.value = val or (get_setting(key, '100' if key == 'tokens_per_dollar' else '1.0'))
            db.session.merge(s)
    db.session.commit()
    return jsonify({
        'tokens_per_dollar': get_setting('tokens_per_dollar', '100'),
        'cash_out_interest_rate': get_setting('cash_out_interest_rate', '1.0'),
    })


@store_bp.route('/token-settings')
@login_required
def token_settings_page():
    if not current_user.is_admin:
        return redirect(url_for('store.store_page'))
    return render_template('token_settings.html')


@store_bp.route('/api/cash-out-requests', methods=['GET'])
@login_required
def list_cash_out_requests():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    reqs = CashOutRequest.query.order_by(CashOutRequest.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'user_id': r.user_id,
        'user_name': r.user.name,
        'username': r.user.username,
        'tokens': float(r.tokens),
        'dollar_value': round(r.dollar_value, 2),
        'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in reqs])


@store_bp.route('/api/cash-out-requests/<int:req_id>/paid', methods=['PATCH'])
@login_required
def mark_cash_out_paid(req_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    r = db.session.get(CashOutRequest, req_id)
    if not r:
        return jsonify({'error': 'Not found'}), 404
    r.status = 'paid'
    # Notify the user that their cash-out was marked paid
    msg = f'Your cash-out request of {int(r.tokens)} tokens (${r.dollar_value:.2f}) has been marked paid.'
    db.session.add(Notification(user_id=r.user_id, message=msg, link='/store/cash-out'))
    db.session.commit()
    return jsonify({'success': True})


# ----- Admin: Store items CRUD -----
@store_bp.route('/admin/items')
@login_required
def admin_items_page():
    if not current_user.is_admin:
        return redirect(url_for('store.store_page'))
    return render_template('store_admin.html')


@store_bp.route('/admin/items/api', methods=['GET'])
@login_required
def admin_list_items():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    items = StoreItem.query.order_by(StoreItem.sort_order, StoreItem.id).all()
    return jsonify([{
        'id': i.id,
        'title': i.title,
        'description': i.description or '',
        'rules': i.rules or '',
        'cost_tokens': float(i.cost_tokens),
        'active': i.active,
        'sort_order': i.sort_order or 0,
    } for i in items])


@store_bp.route('/admin/items/api', methods=['POST'])
@login_required
def admin_create_item():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title required'}), 400
    try:
        cost = float(data.get('cost_tokens', 0))
    except (TypeError, ValueError):
        cost = 0
    item = StoreItem(
        title=title,
        description=(data.get('description') or '').strip() or None,
        rules=(data.get('rules') or '').strip() or None,
        cost_tokens=cost,
        active=data.get('active', True),
        sort_order=int(data.get('sort_order', 0)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})


@store_bp.route('/admin/items/<int:item_id>/api', methods=['PATCH'])
@login_required
def admin_update_item(item_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    item = db.session.get(StoreItem, item_id)
    if not item:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        t = (data['title'] or '').strip()
        if t:
            item.title = t
    if 'description' in data:
        item.description = (data['description'] or '').strip() or None
    if 'rules' in data:
        item.rules = (data['rules'] or '').strip() or None
    if 'cost_tokens' in data:
        try:
            item.cost_tokens = float(data['cost_tokens'])
        except (TypeError, ValueError):
            pass
    if 'active' in data:
        item.active = bool(data['active'])
    if 'sort_order' in data:
        item.sort_order = int(data.get('sort_order', 0))
    db.session.commit()
    return jsonify({'success': True})


@store_bp.route('/admin/items/<int:item_id>/api', methods=['DELETE'])
@login_required
def admin_delete_item(item_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    item = db.session.get(StoreItem, item_id)
    if not item:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})
