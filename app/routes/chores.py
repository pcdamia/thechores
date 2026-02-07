from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Chore, ChoreTracker, ChoreHistory, User, Notification
from datetime import datetime, date

chores_bp = Blueprint('chores', __name__)

@chores_bp.route('/')
@login_required
def list_chores():
    if not current_user.is_admin:
        from flask import flash, redirect, url_for
        flash('Only admins can manage chores.', 'error')
        return redirect(url_for('dashboard'))
    chores = Chore.query.all()
    users = User.query.all()
    return render_template('chores.html', chores=chores, users=users)

@chores_bp.route('/api', methods=['GET'])
def get_chores():
    """Get chores. ?all=1 returns every chore (for dashboard dropdown); otherwise exclude completed-today."""
    all_chores = request.args.get('all') == '1'
    if all_chores:
        chores = Chore.query.all()
        return jsonify([chore.to_dict() for chore in chores])
    today = date.today()
    completed_today_ids = db.session.query(ChoreTracker.chore_id).filter(
        ChoreTracker.date == today,
        ChoreTracker.status == 'completed',
        ChoreTracker.approved_by_id.isnot(None)  # Only count as completed if approved
    ).subquery()
    chores = Chore.query.filter(Chore.id.notin_(completed_today_ids)).all()
    return jsonify([chore.to_dict() for chore in chores])

@chores_bp.route('/api', methods=['POST'])
@login_required
def create_chore():
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can create chores'}), 403
    data = request.json
    
    # Restrict assignment: only admin can assign to other users
    assigned_user_id = data.get('assigned_user_id')
    if assigned_user_id and not current_user.is_admin:
        # Non-admin users can only assign to themselves
        if assigned_user_id != current_user.id:
            assigned_user_id = current_user.id
    
    chore = Chore(
        task=data.get('task'),
        frequency=data.get('frequency'),
        assigned_user_id=assigned_user_id,
        assigned_by_id=current_user.id if current_user.is_admin else None,  # Track who assigned the chore
        reward=float(data.get('reward', 0)),
        room_id=data.get('room_id')
    )
    db.session.add(chore)
    db.session.commit()
    return jsonify(chore.to_dict()), 201

@chores_bp.route('/api/<int:chore_id>', methods=['GET'])
@login_required
def get_chore(chore_id):
    chore = db.session.get(Chore, chore_id)
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    return jsonify(chore.to_dict())

@chores_bp.route('/api/<int:chore_id>', methods=['PUT'])
@login_required
def update_chore(chore_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can edit chores'}), 403
    chore = db.session.get(Chore, chore_id)
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    
    data = request.json
    
    # Restrict assignment: only admin can assign to other users
    # Regular users can only assign to themselves
    assigned_user_id = data.get('assigned_user_id')
    if assigned_user_id is not None:
        if not current_user.is_admin:
            # Non-admin users can only assign to themselves or unassign
            if assigned_user_id and assigned_user_id != current_user.id:
                return jsonify({'error': 'You can only assign chores to yourself'}), 403
        # Admin can assign to anyone
    
    chore.task = data.get('task', chore.task)
    chore.frequency = data.get('frequency', chore.frequency)
    if assigned_user_id is not None:
        chore.assigned_user_id = assigned_user_id if assigned_user_id else None
        # Update assigned_by_id if admin is assigning to someone else
        if current_user.is_admin and assigned_user_id:
            chore.assigned_by_id = current_user.id
    chore.reward = float(data.get('reward', chore.reward))
    chore.room_id = data.get('room_id', chore.room_id)
    
    db.session.commit()
    return jsonify(chore.to_dict())

@chores_bp.route('/api/<int:chore_id>', methods=['DELETE'])
@login_required
def delete_chore(chore_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can delete chores'}), 403
    chore = db.session.get(Chore, chore_id)
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    
    db.session.delete(chore)
    db.session.commit()
    return jsonify({'success': True})

@chores_bp.route('/api/<int:chore_id>/complete', methods=['POST'])
@login_required
def complete_chore(chore_id):
    from app.models import ChoreHistory, Room
    chore = db.session.get(Chore, chore_id)
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    
    # Get room name if exists
    room_name = None
    if chore.room_id:
        room = db.session.get(Room, chore.room_id)
        if room:
            room_name = room.name
    elif chore.rooms and len(chore.rooms) > 0:
        room_name = chore.rooms[0].name
    
    # Get assigned user name
    assigned_user_name = None
    if chore.assigned_user:
        assigned_user_name = chore.assigned_user.name
    
    # Create history entry (permanent record)
    history = ChoreHistory(
        chore_id=chore_id,
        task=chore.task,
        frequency=chore.frequency,
        assigned_user_id=chore.assigned_user_id,
        assigned_user_name=assigned_user_name,
        room_id=chore.room_id,
        room_name=room_name,
        reward=chore.reward,
        completed_date=date.today()
    )
    db.session.add(history)
    
    # Create tracker entry for today
    tracker = ChoreTracker(
        chore_id=chore_id,
        date=date.today(),
        status='completed'
    )
    db.session.add(tracker)
    
    # Add reward to user's bank
    if chore.assigned_user:
        chore.assigned_user.bank += chore.reward
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Chore completed and reward added'})

@chores_bp.route('/tracker', methods=['GET'])
def get_tracker():
    """Get chore tracker entries - public endpoint for viewing"""
    trackers = ChoreTracker.query.order_by(ChoreTracker.date.desc()).all()
    return jsonify([tracker.to_dict() for tracker in trackers])

@chores_bp.route('/tracker/completed', methods=['GET'])
def get_completed_tracker():
    """Get completed chore history entries grouped by date"""
    from app.models import ChoreHistory
    # Get all completed chores from history (permanent record)
    completed_history = ChoreHistory.query.order_by(ChoreHistory.completed_date.desc()).all()
    
    # Group by date
    grouped = {}
    for history in completed_history:
        date_str = history.completed_date.isoformat() if history.completed_date else None
        if date_str:
            if date_str not in grouped:
                grouped[date_str] = []
            
            grouped[date_str].append({
                'id': history.id,
                'chore_id': history.chore_id,
                'task': history.task,
                'assigned_user_name': history.assigned_user_name,
                'reward': float(history.reward),
                'date': date_str,
                'room_name': history.room_name
            })
    
    return jsonify(grouped)

@chores_bp.route('/tracker', methods=['POST'])
@login_required
def create_tracker_entry():
    data = request.json
    tracker_date = datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else date.today()
    due_by = None
    if data.get('due_by_date'):
        due_by = datetime.strptime(data['due_by_date'], '%Y-%m-%d').date()
    tracker = ChoreTracker(
        chore_id=data.get('chore_id'),
        date=tracker_date,
        due_by_date=due_by,
        status=data.get('status', 'pending')
    )
    db.session.add(tracker)
    db.session.commit()
    return jsonify(tracker.to_dict()), 201

LATE_PENALTY_PER_DAY = 2  # tokens deducted per day late

@chores_bp.route('/tracker/<int:tracker_id>', methods=['PUT'])
@login_required
def update_tracker_entry(tracker_id):
    from app.models import ChoreHistory, Room
    tracker = db.session.get(ChoreTracker, tracker_id)
    if not tracker:
        return jsonify({'error': 'Tracker entry not found'}), 404

    data = request.json
    if 'due_by_date' in data:
        val = data.get('due_by_date')
        tracker.due_by_date = datetime.strptime(val, '%Y-%m-%d').date() if val else None
    if 'assigner_notes' in data:
        tracker.assigner_notes = data.get('assigner_notes')
    
    old_status = tracker.status
    if 'status' in data:
        new_status = data['status']
        tracker.status = new_status
        
        chore = tracker.chore
        if chore:
            # Handle pending_approval status - assignee marks as done, notify assigner
            if new_status == 'pending_approval' and old_status != 'pending_approval':
                # Notify the assigner that chore is pending approval
                assigner_id = chore.assigned_by_id
                if assigner_id and assigner_id != current_user.id:  # Don't notify if assigner is marking it themselves
                    assignee_name = chore.assigned_user.name if chore.assigned_user else 'Someone'
                    message = f'"{chore.task}" has been marked as completed by {assignee_name} and is pending your approval.'
                    link = f'/dashboard?highlight_chore={chore.id}'
                    notification = Notification(user_id=assigner_id, message=message, link=link)
                    db.session.add(notification)
                elif not assigner_id:
                    # If no assigner set, notify all admins
                    from app.models import User
                    admins = User.query.filter_by(is_admin=True).all()
                    assignee_name = chore.assigned_user.name if chore.assigned_user else 'Someone'
                    message = f'"{chore.task}" has been marked as completed by {assignee_name} and is pending approval.'
                    link = f'/dashboard?highlight_chore={chore.id}'
                    for admin in admins:
                        if admin.id != current_user.id:
                            notification = Notification(user_id=admin.id, message=message, link=link)
                            db.session.add(notification)
            
            # Handle completed status - only give reward if approved_by_id is set
            if new_status == 'completed' and tracker.approved_by_id:
                today = date.today()
                due_date = tracker.due_by_date or tracker.date
                days_late = max(0, (today - due_date).days)
                penalty = LATE_PENALTY_PER_DAY * days_late
                reward_to_add = max(0.0, float(chore.reward) - penalty)
                existing = ChoreHistory.query.filter_by(
                    chore_id=chore.id,
                    completed_date=today
                ).first()
                if not existing:
                    room_name = None
                    if chore.room_id:
                        room = db.session.get(Room, chore.room_id)
                        if room:
                            room_name = room.name
                    elif chore.rooms and len(chore.rooms) > 0:
                        room_name = chore.rooms[0].name
                    assigned_name = chore.assigned_user.name if chore.assigned_user else None
                    history = ChoreHistory(
                        chore_id=chore.id,
                        task=chore.task,
                        frequency=chore.frequency,
                        assigned_user_id=chore.assigned_user_id,
                        assigned_user_name=assigned_name,
                        room_id=chore.room_id,
                        room_name=room_name,
                        reward=reward_to_add,
                        completed_date=today
                    )
                    db.session.add(history)
                    if chore.assigned_user:
                        chore.assigned_user.bank += reward_to_add
            
            # Handle reinstatement - when status changes from pending_approval back to pending
            if new_status == 'pending' and old_status == 'pending_approval':
                # Notify the assignee that chore was reinstated
                assignee_id = chore.assigned_user_id
                if assignee_id and assignee_id != current_user.id:  # Don't notify if assignee is doing it themselves
                    assigner_name = chore.assigned_by.name if chore.assigned_by else 'Admin'
                    notes_text = f' Notes: {tracker.assigner_notes}' if tracker.assigner_notes else ''
                    message = f'"{chore.task}" has been reinstated by {assigner_name}.{notes_text}'
                    link = f'/dashboard?highlight_chore={chore.id}'
                    notification = Notification(user_id=assignee_id, message=message, link=link)
                    db.session.add(notification)
    
    tracker.updated_at = datetime.utcnow()
    tracker.updated_by_id = current_user.id

    db.session.commit()
    return jsonify(tracker.to_dict())

@chores_bp.route('/tracker/<int:tracker_id>/approve', methods=['POST'])
@login_required
def approve_chore_completion(tracker_id):
    """Approve a chore that's pending approval. Only the assigner can approve."""
    from app.models import ChoreHistory, Room
    tracker = db.session.get(ChoreTracker, tracker_id)
    if not tracker:
        return jsonify({'error': 'Tracker entry not found'}), 404
    
    chore = tracker.chore
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    
    # Check if current user is the assigner (or admin if assigned_by_id is not set)
    if chore.assigned_by_id:
        if chore.assigned_by_id != current_user.id:
            return jsonify({'error': 'Only the assigner can approve completion'}), 403
    elif not current_user.is_admin:
        return jsonify({'error': 'Only the assigner or admin can approve completion'}), 403
    
    # Check if status is pending_approval
    if tracker.status != 'pending_approval':
        return jsonify({'error': 'Chore is not pending approval'}), 400
    
    # Approve: set status to completed and approved_by_id
    tracker.status = 'completed'
    tracker.approved_by_id = current_user.id
    
    # Now give the reward
    today = date.today()
    due_date = tracker.due_by_date or tracker.date
    days_late = max(0, (today - due_date).days)
    penalty = LATE_PENALTY_PER_DAY * days_late
    reward_to_add = max(0.0, float(chore.reward) - penalty)
    
    existing = ChoreHistory.query.filter_by(
        chore_id=chore.id,
        completed_date=today
    ).first()
    if not existing:
        room_name = None
        if chore.room_id:
            room = db.session.get(Room, chore.room_id)
            if room:
                room_name = room.name
        elif chore.rooms and len(chore.rooms) > 0:
            room_name = chore.rooms[0].name
        assigned_name = chore.assigned_user.name if chore.assigned_user else None
        history = ChoreHistory(
            chore_id=chore.id,
            task=chore.task,
            frequency=chore.frequency,
            assigned_user_id=chore.assigned_user_id,
            assigned_user_name=assigned_name,
            room_id=chore.room_id,
            room_name=room_name,
            reward=reward_to_add,
            completed_date=today
        )
        db.session.add(history)
        if chore.assigned_user:
            chore.assigned_user.bank += reward_to_add
    
    tracker.updated_at = datetime.utcnow()
    tracker.updated_by_id = current_user.id
    
    db.session.commit()
    return jsonify(tracker.to_dict())

@chores_bp.route('/tracker/<int:tracker_id>/reinstate', methods=['POST'])
@login_required
def reinstate_chore(tracker_id):
    """Reinstate a chore that's pending approval. Only the assigner can reinstate."""
    tracker = db.session.get(ChoreTracker, tracker_id)
    if not tracker:
        return jsonify({'error': 'Tracker entry not found'}), 404
    
    chore = tracker.chore
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404
    
    # Check if current user is the assigner (or admin if assigned_by_id is not set)
    if chore.assigned_by_id:
        if chore.assigned_by_id != current_user.id:
            return jsonify({'error': 'Only the assigner can reinstate the chore'}), 403
    elif not current_user.is_admin:
        return jsonify({'error': 'Only the assigner or admin can reinstate the chore'}), 403
    
    # Check if status is pending_approval
    if tracker.status != 'pending_approval':
        return jsonify({'error': 'Chore is not pending approval'}), 400
    
    data = request.json
    notes = data.get('notes', '')
    
    # Reinstate: set status back to pending and add notes
    tracker.status = 'pending'
    tracker.assigner_notes = notes
    
    # Notify the assignee
    assignee_id = chore.assigned_user_id
    if assignee_id:
        assigner_name = current_user.name
        notes_text = f' Notes: {notes}' if notes else ''
        message = f'"{chore.task}" has been reinstated by {assigner_name}.{notes_text}'
        link = f'/dashboard?highlight_chore={chore.id}'
        notification = Notification(user_id=assignee_id, message=message, link=link)
        db.session.add(notification)
    
    tracker.updated_at = datetime.utcnow()
    tracker.updated_by_id = current_user.id
    
    db.session.commit()
    return jsonify(tracker.to_dict())
