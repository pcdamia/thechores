from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Event
from datetime import datetime

events_bp = Blueprint('events', __name__)


@events_bp.route('/')
@login_required
def list_events():
    """Events list page (similar to items)."""
    return render_template('events.html')


@events_bp.route('/api', methods=['GET'])
def get_events():
    """Get events - public endpoint for calendar"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Event.query
    if start_date:
        query = query.filter(Event.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Event.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    events = query.all()
    return jsonify([event.to_dict() for event in events])

@events_bp.route('/api', methods=['POST'])
@login_required
def create_event():
    data = request.json
    event = Event(
        title=data.get('title'),
        description=data.get('description'),
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date(),
        time=datetime.strptime(data['time'], '%H:%M').time() if data.get('time') else None,
        user_id=current_user.id if current_user.is_authenticated else None,
        event_type=data.get('event_type')
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201

@events_bp.route('/api/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    data = request.json
    event.title = data.get('title', event.title)
    event.description = data.get('description', event.description)
    event.event_type = data.get('event_type', event.event_type)
    if data.get('date'):
        event.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    if data.get('time'):
        event.time = datetime.strptime(data['time'], '%H:%M').time()
    event.updated_at = datetime.utcnow()
    event.updated_by_id = current_user.id

    db.session.commit()
    return jsonify(event.to_dict())

@events_bp.route('/api/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    db.session.delete(event)
    db.session.commit()
    return jsonify({'success': True})
