from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from app.models import db, User
from app.utils import save_uploaded_file, delete_uploaded_file
import os
import json

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def settings():
    return render_template('settings.html')

@settings_bp.route('/api', methods=['GET'])
@login_required
def get_settings():
    user = db.session.get(User, current_user.id)
    return jsonify({
        'name': user.name,
        'profile_image': user.profile_image,
        'background_image': user.background_image,
        'background_gradient': user.background_gradient,
        'background_position': user.background_position or 'centered',
        'color_scheme': user.color_scheme,
        'color_code': user.color_code
    })

@settings_bp.route('/api', methods=['PUT'])
@login_required
def update_settings():
    user = db.session.get(User, current_user.id)
    
    # Handle form data (for file uploads) or JSON
    if request.is_json:
        data = request.json
        profile_file = None
        background_file = None
        profile_crop = None
    else:
        data = request.form.to_dict()
        profile_file = request.files.get('profile_image')
        background_file = request.files.get('background_image')
        profile_crop_str = request.form.get('profile_crop')
        if profile_crop_str:
            import json
            try:
                profile_crop = json.loads(profile_crop_str)
            except:
                profile_crop = None
    
    if 'name' in data:
        user.name = data['name']
    if 'background_gradient' in data:
        user.background_gradient = data['background_gradient']
    if 'background_position' in data:
        user.background_position = data['background_position']
    if 'color_scheme' in data:
        user.color_scheme = data['color_scheme']
    if 'color_code' in data:
        val = data['color_code']
        user.color_code = val if (val and str(val).strip()) else None

    # Handle profile image upload
    if profile_file and profile_file.filename:
        # Delete old profile image
        if user.profile_image:
            delete_uploaded_file(user.profile_image)
        # Save new image with crop data
        filepath = save_uploaded_file(profile_file, 'profiles', profile_crop)
        if filepath:
            user.profile_image = filepath
    
    # Handle background image upload
    if background_file and background_file.filename:
        # Delete old background image
        if user.background_image:
            delete_uploaded_file(user.background_image)
        # Save new image
        filepath = save_uploaded_file(background_file, 'backgrounds')
        if filepath:
            user.background_image = filepath
    
    db.session.commit()
    # Refresh the user object to ensure changes are reflected
    db.session.refresh(user)
    
    return jsonify({'success': True, 'profile_image': user.profile_image, 'background_image': user.background_image})

@settings_bp.route('/api/quick-chores', methods=['GET'])
@login_required
def get_quick_chores():
    """Get user's selected quick chore IDs"""
    user = db.session.get(User, current_user.id)
    if user.quick_chores:
        try:
            chore_ids = json.loads(user.quick_chores)
            return jsonify({'chore_ids': chore_ids})
        except:
            return jsonify({'chore_ids': []})
    return jsonify({'chore_ids': []})

@settings_bp.route('/api/quick-chores', methods=['PUT'])
@login_required
def update_quick_chores():
    """Update user's selected quick chore IDs (max 8)"""
    user = db.session.get(User, current_user.id)
    data = request.json
    chore_ids = data.get('chore_ids', [])
    
    # Limit to 8 chores
    if len(chore_ids) > 8:
        return jsonify({'error': 'Maximum 8 quick chores allowed'}), 400
    
    # Validate that all IDs are integers
    try:
        chore_ids = [int(id) for id in chore_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid chore IDs'}), 400
    
    user.quick_chores = json.dumps(chore_ids)
    db.session.commit()
    
    return jsonify({'success': True, 'chore_ids': chore_ids})

@settings_bp.route('/api/quick-events', methods=['GET'])
@login_required
def get_quick_events():
    """Get user's selected quick event IDs"""
    user = db.session.get(User, current_user.id)
    if user.quick_events:
        try:
            event_ids = json.loads(user.quick_events)
            return jsonify({'event_ids': event_ids})
        except:
            return jsonify({'event_ids': []})
    return jsonify({'event_ids': []})

@settings_bp.route('/api/quick-events', methods=['PUT'])
@login_required
def update_quick_events():
    """Update user's selected quick event IDs (max 8)"""
    user = db.session.get(User, current_user.id)
    data = request.json
    event_ids = data.get('event_ids', [])
    
    # Limit to 8 events
    if len(event_ids) > 8:
        return jsonify({'error': 'Maximum 8 quick events allowed'}), 400
    
    # Validate that all IDs are integers
    try:
        event_ids = [int(id) for id in event_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid event IDs'}), 400
    
    user.quick_events = json.dumps(event_ids)
    db.session.commit()
    
    return jsonify({'success': True, 'event_ids': event_ids})

