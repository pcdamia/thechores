from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.auth import hash_password, verify_password, hash_security_answer, verify_security_answer

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    wants_json = request.headers.get('Accept') == 'application/json' or request.is_json
    
    if current_user.is_authenticated:
        if wants_json:
            return jsonify({'success': True, 'message': 'Already logged in'})
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and verify_password(password, user.password_hash):
            login_user(user)
            # If JSON request (from modal), return JSON response
            if wants_json:
                return jsonify({'success': True, 'message': 'Login successful'})
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            # If JSON request, return JSON error
            if wants_json:
                return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            flash('Invalid username or password', 'error')
    
    if wants_json:
        return jsonify({'success': False, 'error': 'GET request not allowed'}), 405
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('Only administrators can create new users', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        name = request.form.get('name', '').strip()
        is_admin = request.form.get('is_admin') == 'on'
        
        if not username or not password or not name:
            flash('Username, password, and name are required', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        # Validate security questions and answers
        sq1 = request.form.get('security_question_1', '').strip()
        sa1 = request.form.get('security_answer_1', '').strip()
        sq2 = request.form.get('security_question_2', '').strip()
        sa2 = request.form.get('security_answer_2', '').strip()
        sq3 = request.form.get('security_question_3', '').strip()
        sa3 = request.form.get('security_answer_3', '').strip()
        if not all([sq1, sa1, sq2, sa2, sq3, sa3]):
            flash('All three security questions and answers are required', 'error')
            return render_template('register.html')
        
        user = User(
            username=username,
            password_hash=hash_password(password),
            name=name,
            is_admin=is_admin,
            bank=0.0
        )
        
        # Set security questions
        user.security_question_1 = sq1
        user.security_answer_1_hash = hash_security_answer(sa1)
        user.security_question_2 = sq2
        user.security_answer_2_hash = hash_security_answer(sa2)
        user.security_question_3 = sq3
        user.security_answer_3_hash = hash_security_answer(sa3)
        
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('users.list_users'))
    
    return render_template('register.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash('User not found', 'error')
            return render_template('reset_password.html')
        
        # Redirect to security questions page
        return redirect(url_for('auth.reset_password_questions', username=username))
    
    return render_template('reset_password.html')

@auth_bp.route('/reset-password-questions/<username>', methods=['GET', 'POST'])
def reset_password_questions(username):
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.reset_password'))
    
    # Users without security answers set (e.g. legacy accounts) cannot reset via questions
    if not all([user.security_answer_1_hash, user.security_answer_2_hash, user.security_answer_3_hash]):
        flash('This account does not have security questions set. Please contact an administrator.', 'error')
        return redirect(url_for('auth.reset_password'))
    
    if request.method == 'POST':
        answer1 = request.form.get('security_answer_1')
        answer2 = request.form.get('security_answer_2')
        answer3 = request.form.get('security_answer_3')
        new_password = request.form.get('new_password')
        
        if not new_password or len(new_password.strip()) < 1:
            flash('New password is required', 'error')
            return render_template('reset_password_questions.html', user=user)
        
        if not (verify_security_answer(answer1, user.security_answer_1_hash) and
                verify_security_answer(answer2, user.security_answer_2_hash) and
                verify_security_answer(answer3, user.security_answer_3_hash)):
            flash('Incorrect security answers', 'error')
            return render_template('reset_password_questions.html', user=user)
        
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        flash('Password reset successfully', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password_questions.html', user=user)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    if not verify_password(current_password, current_user.password_hash):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('dashboard'))
    
    current_user.password_hash = hash_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('dashboard'))
