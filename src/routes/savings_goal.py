from flask import Blueprint, request, jsonify, session, current_app
from src.models.savings_goal import SavingsGoal
from src.extensions import db
from src.routes.auth import login_required
from datetime import datetime, date
from sqlalchemy import case

savings_goal_bp = Blueprint('savings_goal', __name__, url_prefix='/api/savings-goals')

@savings_goal_bp.route('', methods=['POST'])
@login_required
def create_savings_goal():
    data = request.json
    user_id = session['user_id']

    required_fields = ['name', 'target_amount']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields (name, target_amount)'}), 400

    try:
        # Ensure 'name' is handled if its value is null in the payload
        name_payload = data.get('name') # 'name' is in required_fields, so key should exist
        name = str(name_payload).strip() if name_payload is not None else ""

        target_amount = float(data['target_amount'])
        current_amount = float(data.get('current_amount', 0.0))
        target_date_str = data.get('target_date')
        description_payload = data.get('description')
        description = str(description_payload).strip() if description_payload is not None else ""
        priority = data.get('priority', 'medium').lower()

        if priority not in ['low', 'medium', 'high']:
            return jsonify({'error': "Invalid priority. Must be 'low', 'medium', or 'high'."}), 400

        if not name:
            return jsonify({'error': 'Goal name cannot be empty'}), 400
        if target_amount <= 0:
            return jsonify({'error': 'Target amount must be positive'}), 400
        if current_amount < 0:
            return jsonify({'error': 'Current amount cannot be negative'}), 400
        if current_amount > target_amount:
            return jsonify({'error': 'Current amount cannot exceed target amount initially'}), 400

        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid target_date format. Use YYYY-MM-DD.'}), 400

        new_goal = SavingsGoal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            description=description,
            priority=priority
        )
        db.session.add(new_goal)
        db.session.commit()
        return jsonify({'message': 'Savings goal created successfully', 'savings_goal': new_goal.to_dict()}), 201
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating savings goal: {e}")
        return jsonify({'error': 'Failed to create savings goal'}), 500

@savings_goal_bp.route('', methods=['GET'])
@login_required
def get_savings_goals():
    user_id = session['user_id']
    # Define custom order for priority: high, then medium, then low
    priority_order = case(
        (SavingsGoal.priority == 'high', 1),
        (SavingsGoal.priority == 'medium', 2),
        (SavingsGoal.priority == 'low', 3),
        else_=4 # Should not happen with validation
    )
    goals = SavingsGoal.query.filter_by(user_id=user_id).order_by(priority_order.asc(), SavingsGoal.target_date.asc(), SavingsGoal.created_at.desc()).all()
    return jsonify([goal.to_dict() for goal in goals]), 200

@savings_goal_bp.route('/<int:goal_id>', methods=['PUT'])
@login_required
def update_savings_goal(goal_id):
    data = request.json
    user_id = session['user_id']
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({'error': 'Savings goal not found or not authorized'}), 404

    try:
        if 'name' in data:
            name_payload = data.get('name')
            goal.name = str(name_payload).strip() if name_payload is not None else ""
            if not goal.name:
                 return jsonify({'error': 'Goal name cannot be empty'}), 400
        if 'target_amount' in data: goal.target_amount = float(data['target_amount'])
        if 'current_amount' in data: goal.current_amount = float(data['current_amount']) # Allow direct update for flexibility
        if 'target_date' in data:
            goal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data['target_date'] else None
        if 'description' in data:
            desc_payload = data.get('description')
            goal.description = str(desc_payload).strip() if desc_payload is not None else ""
        if 'priority' in data:
            priority_payload = data.get('priority')
            goal.priority = str(priority_payload).lower() if priority_payload else 'medium'
            if goal.priority not in ['low', 'medium', 'high']:
                return jsonify({'error': "Invalid priority. Must be 'low', 'medium', or 'high'."}), 400

        if not goal.name: # Re-check name after potential update
            return jsonify({'error': 'Goal name cannot be empty after update'}), 400
        if goal.target_amount <= 0: return jsonify({'error': 'Target amount must be positive'}), 400
        if goal.current_amount < 0: return jsonify({'error': 'Current amount cannot be negative'}), 400
        # We might allow current_amount > target_amount if they over-save or adjust target later

        db.session.commit()
        return jsonify({'message': 'Savings goal updated successfully', 'savings_goal': goal.to_dict()}), 200
    except ValueError:
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating savings goal {goal_id}: {e}")
        return jsonify({'error': 'Failed to update savings goal'}), 500

@savings_goal_bp.route('/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_savings_goal(goal_id):
    user_id = session['user_id']
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({'error': 'Savings goal not found or not authorized'}), 404

    try:
        db.session.delete(goal)
        db.session.commit()
        return jsonify({'message': 'Savings goal deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting savings goal {goal_id}: {e}")
        return jsonify({'error': 'Failed to delete savings goal'}), 500

@savings_goal_bp.route('/<int:goal_id>/contribute', methods=['POST'])
@login_required
def contribute_to_savings_goal(goal_id):
    data = request.json
    user_id = session['user_id']
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({'error': 'Savings goal not found or not authorized'}), 404

    try:
        amount = float(data.get('amount', 0.0))
        if amount <= 0:
            return jsonify({'error': 'Contribution amount must be positive'}), 400

        goal.current_amount += amount
        # Optional: Create a transaction record here if desired for full financial tracking
        # For now, just updating the goal's current_amount.

        db.session.commit()
        return jsonify({'message': 'Contribution successful', 'savings_goal': goal.to_dict()}), 200
    except ValueError:
        return jsonify({'error': 'Invalid contribution amount'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error contributing to savings goal {goal_id}: {e}")
        return jsonify({'error': 'Failed to contribute to savings goal'}), 500