from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models import Notification, db

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/')
@login_required
def list_notifications():
    """Notifications list page."""
    return render_template('notifications.html')


@notifications_bp.route('/api')
@login_required
def get_notifications():
    """Get notifications for current user (count + items)."""
    unread_only = request.args.get('unread') == '1'
    q = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        q = q.filter_by(read=False)
    items = q.order_by(Notification.created_at.desc()).limit(100).all()
    count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return jsonify({
        'count': count,
        'items': [
            {'id': n.id, 'message': n.message, 'link': n.link, 'read': n.read, 'created_at': n.created_at.isoformat() if n.created_at else None}
            for n in items
        ]
    })


@notifications_bp.route('/api/<int:notification_id>/read', methods=['PATCH', 'POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read."""
    n = db.session.get(Notification, notification_id)
    if not n or n.user_id != current_user.id:
        return jsonify({'error': 'Not found'}), 404
    n.read = True
    db.session.commit()
    return jsonify({'success': True})
