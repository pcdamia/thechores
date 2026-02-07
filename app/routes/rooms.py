from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models import db, Room, Chore, ChoreTracker, ChoreHistory
from datetime import datetime, date, timedelta

rooms_bp = Blueprint('rooms', __name__)

@rooms_bp.route('/')
@login_required
def list_rooms():
    rooms = Room.query.all()
    chores = Chore.query.all()
    return render_template('rooms.html', rooms=rooms, chores=chores)

@rooms_bp.route('/api', methods=['GET'])
@login_required
def get_rooms():
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms])

@rooms_bp.route('/api', methods=['POST'])
@login_required
def create_room():
    data = request.json
    room = Room(
        name=data.get('name'),
        last_deep_cleaned=datetime.strptime(data['last_deep_cleaned'], '%Y-%m-%d').date() if data.get('last_deep_cleaned') else None,
        last_cleaned=datetime.strptime(data['last_cleaned'], '%Y-%m-%d').date() if data.get('last_cleaned') else None
    )
    
    # Add associated chores
    if data.get('chore_ids'):
        chores = Chore.query.filter(Chore.id.in_(data['chore_ids'])).all()
        room.chores = chores
    
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201

@rooms_bp.route('/api/<int:room_id>', methods=['GET'])
@login_required
def get_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    return jsonify(room.to_dict())


@rooms_bp.route('/api/<int:room_id>/detail', methods=['GET'])
@login_required
def get_room_detail(room_id):
    """Room detail for modal: assignable chores, last cleanings per chore, assignment table (trackers)."""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    chore_ids = [c.id for c in room.chores]
    assignable_chores = [
        {'id': c.id, 'task': c.task, 'assigned_user_name': c.assigned_user.name if c.assigned_user else None}
        for c in room.chores
    ]
    last_cleanings = []
    for c in room.chores:
        last = (
            ChoreTracker.query.filter_by(chore_id=c.id, status='completed')
            .order_by(ChoreTracker.date.desc())
            .first()
        )
        if last:
            last_cleanings.append({
                'chore_id': c.id,
                'chore_task': c.task,
                'last_completed_date': last.date.isoformat() if last.date else None,
            })
    cutoff = date.today() - timedelta(days=30)
    trackers = (
        ChoreTracker.query.filter(ChoreTracker.chore_id.in_(chore_ids), ChoreTracker.date >= cutoff)
        .order_by(ChoreTracker.date.desc())
        .all()
    )
    assignments = []
    for t in trackers:
        c = t.chore
        assignments.append({
            'id': t.id,
            'chore_id': t.chore_id,
            'chore_task': c.task if c else None,
            'assigned_to': c.assigned_user.name if c and c.assigned_user else None,
            'date_assigned': t.date.isoformat() if t.date else None,
            'status': t.status,
        })
    return jsonify({
        'room': room.to_dict(),
        'assignable_chores': assignable_chores,
        'last_cleanings': last_cleanings,
        'assignments': assignments,
    })

@rooms_bp.route('/api/<int:room_id>', methods=['PUT'])
@login_required
def update_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    data = request.json
    room.name = data.get('name', room.name)
    if data.get('last_deep_cleaned'):
        room.last_deep_cleaned = datetime.strptime(data['last_deep_cleaned'], '%Y-%m-%d').date()
    if data.get('last_cleaned'):
        room.last_cleaned = datetime.strptime(data['last_cleaned'], '%Y-%m-%d').date()
    
    # Update associated chores
    if 'chore_ids' in data:
        chores = Chore.query.filter(Chore.id.in_(data['chore_ids'])).all()
        room.chores = chores
    
    db.session.commit()
    return jsonify(room.to_dict())

@rooms_bp.route('/api/<int:room_id>', methods=['DELETE'])
@login_required
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    db.session.delete(room)
    db.session.commit()
    return jsonify({'success': True})

@rooms_bp.route('/api/<int:room_id>/mark-cleaned', methods=['POST'])
@login_required
def mark_cleaned(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    room.last_cleaned = datetime.now().date()
    db.session.commit()
    return jsonify(room.to_dict())

@rooms_bp.route('/api/<int:room_id>/mark-deep-cleaned', methods=['POST'])
@login_required
def mark_deep_cleaned(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    room.last_deep_cleaned = datetime.now().date()
    db.session.commit()
    return jsonify(room.to_dict())
