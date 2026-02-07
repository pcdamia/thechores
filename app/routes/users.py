from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime
from app.models import db, User, Chore, ChoreTracker, ChoreHistory, Project, Event, project_users
from app.auth import hash_password, hash_security_answer
from app.utils import save_uploaded_file, delete_uploaded_file

users_bp = Blueprint('users', __name__)

STATUS_LABELS = {
    'at_school': 'At school',
    'at_work': 'At work',
    'overnight_stay': 'Overnight stay',
    'grocery_shopping': 'Grocery / food shopping',
}

@users_bp.route('/')
@login_required
def list_users():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    users_data = [{
        'id': u.id,
        'username': u.username,
        'name': u.name,
        'is_admin': u.is_admin,
        'bank': float(u.bank),
        'color_code': u.color_code or None,
        'profile_image': u.profile_image,
        'background_gradient': u.background_gradient,
        'status': u.status,
        'title': u.title or None,
    } for u in users]
    return render_template('users.html', users=users_data)

@users_bp.route('/api', methods=['GET'])
def get_users():
    """Get users - public endpoint for display purposes (profile images, names, status)"""
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'name': u.name,
        'is_admin': u.is_admin,
        'bank': float(u.bank),
        'profile_image': u.profile_image,
        'color_code': u.color_code or None,
        'background_gradient': u.background_gradient,
        'status': u.status,
        'title': u.title or None,
    } for u in users])

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        is_admin = request.form.get('is_admin') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('create_user.html')
        
        user = User(
            username=username,
            password_hash=hash_password(password),
            name=name,
            is_admin=is_admin,
            bank=0.0
        )
        
        user.security_question_1 = request.form.get('security_question_1')
        user.security_answer_1_hash = hash_security_answer(request.form.get('security_answer_1'))
        user.security_question_2 = request.form.get('security_question_2')
        user.security_answer_2_hash = hash_security_answer(request.form.get('security_answer_2'))
        user.security_question_3 = request.form.get('security_question_3')
        user.security_answer_3_hash = hash_security_answer(request.form.get('security_answer_3'))
        
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('users.list_users'))
    
    return render_template('create_user.html')

@users_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

@users_bp.route('/<int:user_id>/api', methods=['PATCH'])
@login_required
def update_user(user_id):
    """Update user (admin only). Fields: name, bank, is_admin, color_code."""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        val = data['name']
        if val is not None and str(val).strip():
            user.name = str(val).strip()
    if 'bank' in data:
        try:
            user.bank = float(data['bank'])
        except (TypeError, ValueError):
            pass
    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])
    if 'color_code' in data:
        val = data['color_code']
        user.color_code = val if (val and str(val).strip()) else None
    if 'status' in data:
        val = data['status']
        user.status = str(val).strip() if (val is not None and str(val).strip()) else None
    if 'title' in data:
        val = data['title']
        user.title = str(val).strip() if (val is not None and str(val).strip()) else None
    db.session.commit()
    return jsonify({
        'success': True,
        'name': user.name,
        'bank': float(user.bank),
        'is_admin': user.is_admin,
        'color_code': user.color_code,
        'status': user.status,
        'title': user.title,
    })


@users_bp.route('/<int:user_id>/detail', methods=['GET'])
@users_bp.route('/<int:user_id>/api/detail', methods=['GET'])
@login_required
def user_detail(user_id):
    """Get user with stats: last chore/project, upcoming chores/projects/events. Admin or self."""
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    today = date.today()
    # Last chore completed (ChoreHistory for this user)
    last_chore = ChoreHistory.query.filter_by(assigned_user_id=user_id).order_by(ChoreHistory.completed_date.desc()).first()
    last_chore_completed = last_chore.completed_date.isoformat() if last_chore and last_chore.completed_date else None
    last_chore_task = last_chore.task if last_chore else None
    # Last project completed (Project where user was assignee)
    last_proj = Project.query.filter(
        Project.completed == True,
        db.or_(Project.user_id == user_id, Project.id.in_(
            db.session.query(project_users.c.project_id).filter(project_users.c.user_id == user_id)
        ))
    ).order_by(Project.completed_date.desc()).first()
    last_project_completed = last_proj.completed_date.isoformat() if last_proj and last_proj.completed_date else None
    last_project_name = last_proj.name if last_proj else None
    # Upcoming chores: ChoreTracker pending where chore.assigned_user_id = user
    upcoming_trackers = ChoreTracker.query.join(Chore).filter(
        Chore.assigned_user_id == user_id,
        ChoreTracker.status == 'pending',
        ChoreTracker.date >= today
    ).order_by(ChoreTracker.date.asc()).limit(10).all()
    upcoming_chores = [{'id': t.id, 'task': t.chore.task if t.chore else None, 'date': t.date.isoformat() if t.date else None} for t in upcoming_trackers]
    # Upcoming projects (incomplete, assigned to user)
    proj_rows = db.session.query(project_users.c.project_id).filter(project_users.c.user_id == user_id).all()
    proj_ids = [r[0] for r in proj_rows]
    upcoming_projects = Project.query.filter(Project.completed == False, Project.id.in_(proj_ids)).order_by(Project.name).limit(10).all() if proj_ids else []
    upcoming_projects = [{'id': p.id, 'name': p.name} for p in upcoming_projects]
    # Upcoming events (user_id = user, date >= today)
    upcoming_events = Event.query.filter(Event.user_id == user_id, Event.date >= today).order_by(Event.date.asc()).limit(10).all()
    upcoming_events = [{'id': e.id, 'title': e.title, 'date': e.date.isoformat() if e.date else None} for e in upcoming_events]
    return jsonify({
        'id': user.id,
        'name': user.name,
        'username': user.username,
        'title': user.title,
        'status': user.status,
        'profile_image': user.profile_image,
        'color_code': user.color_code,
        'background_gradient': user.background_gradient,
        'bank': float(user.bank),
        'is_admin': user.is_admin,
        'last_chore_completed': last_chore_completed,
        'last_chore_task': last_chore_task,
        'last_project_completed': last_project_completed,
        'last_project_name': last_project_name,
        'upcoming_chores': upcoming_chores,
        'upcoming_projects': upcoming_projects,
        'upcoming_events': upcoming_events,
    })


@users_bp.route('/<int:user_id>/profile-image', methods=['POST'])
@login_required
def set_user_profile_image(user_id):
    """Set profile image for user. Admin can set any user's image; non-admin can only set own."""
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    f = request.files.get('profile_image') or request.files.get('file')
    if not f or not f.filename:
        return jsonify({'error': 'No file provided'}), 400
    path = save_uploaded_file(f, 'profiles')
    if not path:
        return jsonify({'error': 'Invalid or unsupported file'}), 400
    if user.profile_image:
        delete_uploaded_file(user.profile_image)
    user.profile_image = path
    db.session.commit()
    return jsonify({'success': True, 'profile_image': path})

@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    new_password = request.json.get('new_password', 'admin123')
    user.password_hash = hash_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Password reset for {user.username}'})
