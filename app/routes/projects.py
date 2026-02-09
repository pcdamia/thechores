from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.models import db, Project, User, Notification, project_users
from app.utils import save_uploaded_file, delete_uploaded_file

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/')
@login_required
def list_projects():
    # Pass users as list of dicts so template can use tojson in JS; projects grid is loaded via API
    users = [{'id': u.id, 'name': u.name} for u in User.query.all()]
    return render_template('projects.html', users=users)

@projects_bp.route('/api', methods=['GET'])
@login_required
def get_projects():
    projects = Project.query.filter_by(completed=False).all()
    return jsonify([project.to_dict() for project in projects])

@projects_bp.route('/api/completed', methods=['GET'])
@login_required
def get_completed_projects():
    """Get completed projects grouped by date"""
    from datetime import date
    completed_projects = Project.query.filter_by(completed=True).order_by(Project.completed_date.desc()).all()
    
    # Group by date
    grouped = {}
    for project in completed_projects:
        date_str = project.completed_date.isoformat() if project.completed_date else None
        if date_str:
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(project.to_dict())
    
    return jsonify(grouped)

def _parse_user_ids(data):
    """Parse user_ids from request: single id or list of ids."""
    uid = data.get('user_id')
    uids = data.get('user_ids')
    if uids is not None:
        if isinstance(uids, list):
            return [int(x) for x in uids if x is not None]
        return [int(uids)]
    if uid is not None:
        return [int(uid)]
    return [current_user.id]

@projects_bp.route('/api', methods=['POST'])
@login_required
def create_project():
    data = request.json or {}
    user_ids = _parse_user_ids(data)
    primary = user_ids[0] if user_ids else current_user.id
    project = Project(
        name=data.get('name', ''),
        user_id=primary,
        description=data.get('description'),
        severity=data.get('severity'),
        reward=float(data.get('reward', 0))
    )
    db.session.add(project)
    db.session.flush()
    for uid in user_ids:
        db.session.execute(project_users.insert().values(project_id=project.id, user_id=uid))
    db.session.commit()
    return jsonify(project.to_dict()), 201

@projects_bp.route('/api/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(project.to_dict())

@projects_bp.route('/api/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.json or {}
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.severity = data.get('severity', project.severity)
    project.reward = float(data.get('reward', project.reward))
    if 'assignee_notes' in data:
        project.assignee_notes = data.get('assignee_notes')
    user_ids = data.get('user_ids')
    if user_ids is not None:
        uids = [int(x) for x in user_ids] if isinstance(user_ids, list) else [int(user_ids)]
        project.user_id = uids[0] if uids else project.user_id
        db.session.execute(project_users.delete().where(project_users.c.project_id == project_id))
        for uid in uids:
            db.session.execute(project_users.insert().values(project_id=project_id, user_id=uid))
    elif 'user_id' in data:
        uid = int(data['user_id'])
        project.user_id = uid
        db.session.execute(project_users.delete().where(project_users.c.project_id == project_id))
        db.session.execute(project_users.insert().values(project_id=project_id, user_id=uid))
    
    db.session.commit()
    return jsonify(project.to_dict())


@projects_bp.route('/api/<int:project_id>/request-details', methods=['POST'])
@login_required
def request_project_details(project_id):
    """Notify assignee(s) that this project needs more details/clarification."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    assignees = list(project.assigned_users) if project.assigned_users else ([project.user] if project.user else [])
    if not assignees:
        return jsonify({'error': 'No assignees to notify'}), 400
    message = f'Project "{project.name}" needs more details or clarification.'
    link = f'/projects/?highlight={project_id}'
    for u in assignees:
        n = Notification(user_id=u.id, message=message, link=link)
        db.session.add(n)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Assignees notified'})

@projects_bp.route('/api/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})

@projects_bp.route('/api/<int:project_id>/complete', methods=['POST'])
@login_required
def complete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    # Optional completed photo (multipart form)
    photo_path = None
    if request.files:
        f = request.files.get('photo')
        if f and f.filename:
            photo_path = save_uploaded_file(f, 'projects')
            if project.completed_photo:
                delete_uploaded_file(project.completed_photo)
            project.completed_photo = photo_path
    
    # Add reward to primary assignee's bank
    if project.user:
        project.user.bank += project.reward
    
    project.completed = True
    project.completed_date = date.today()
    project.completed_by_id = current_user.id
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Project completed and reward added', 'project': project.to_dict()})
