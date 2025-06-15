from flask import Blueprint, jsonify, request, session
from src.models.user import User
from src.extensions import db # Import db from extensions.py
from src.routes.auth import login_required # Import login_required

user_bp = Blueprint('user', __name__, url_prefix='/user') # Changed url_prefix for clarity

# This blueprint is now for managing the logged-in user's profile.
# User creation is handled by /api/auth/signup.

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_user_profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_user_profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.json
    
    if 'username' in data:
        new_username = data['username'].strip()
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            return jsonify({'error': 'Username already exists'}), 409
        user.username = new_username
        session['username'] = new_username # Update session if username changes
        
    if 'email' in data:
        new_email = data['email'].strip().lower()
        if new_email != user.email and User.query.filter_by(email=new_email).first():
            return jsonify({'error': 'Email already exists'}), 409
        user.email = new_email
    
    # Password change should be a separate endpoint with current password verification
    # if 'password' in data: user.set_password(data['password'])

    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

# Deleting a user is a sensitive operation, often handled differently (e.g., admin only, or soft delete)
# For now, this endpoint is removed. User can logout. Full account deletion needs more consideration.
