from flask import Blueprint, request, jsonify, session, current_app
from src.models.recurring_transaction import RecurringTransaction
from src.models.transaction import Transaction, Category # For creating actual transactions
from src.extensions import db # Import db from extensions.py
from src.routes.auth import login_required
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta # For easier date calculations

recurring_transaction_bp = Blueprint('recurring_transaction', __name__, url_prefix='/api/recurring-transactions')

def calculate_next_due_date(start_date, frequency, interval, current_next_due=None):
    """Calculates the next due date based on frequency and interval."""
    base_date = current_next_due or start_date
    
    if frequency == 'daily':
        return base_date + timedelta(days=interval)
    elif frequency == 'weekly':
        return base_date + timedelta(weeks=interval)
    elif frequency == 'monthly':
        return base_date + relativedelta(months=interval)
    elif frequency == 'yearly':
        return base_date + relativedelta(years=interval)
    else:
        raise ValueError("Invalid frequency")

@recurring_transaction_bp.route('', methods=['POST'])
@login_required
def create_recurring_transaction():
    data = request.json
    user_id = session['user_id']

    required_fields = ['description', 'amount', 'transaction_type', 'frequency', 'interval', 'start_date_str']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        start_date = datetime.strptime(data['start_date_str'], '%Y-%m-%d').date()
        end_date_str = data.get('end_date_str')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        if end_date and end_date < start_date:
            return jsonify({'error': 'End date cannot be before start date'}), 400

        frequency = data['frequency'].lower()
        if frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
            return jsonify({'error': 'Invalid frequency type'}), 400
        
        interval = int(data['interval'])
        if interval <= 0:
            return jsonify({'error': 'Interval must be positive'}), 400

        # Calculate initial next_due_date and determine if active
        calculated_next_due = start_date
        today = date.today()
        is_active_from_start = True

        while calculated_next_due < today:
            if end_date and calculated_next_due > end_date: # This check is mostly for start_date itself being past end_date
                is_active_from_start = False
                break
            try:
                potential_next = calculate_next_due_date(start_date, frequency, interval, current_next_due=calculated_next_due)
            except ValueError:
                return jsonify({'error': 'Invalid frequency for date calculation'}), 400

            if potential_next <= calculated_next_due:
                current_app.logger.error(f"Create: Next due date calculation did not advance: {calculated_next_due} -> {potential_next}")
                return jsonify({'error': 'Internal error calculating next due date progression.'}), 500
            calculated_next_due = potential_next

            if end_date and calculated_next_due > end_date:
                is_active_from_start = False # Advanced past end_date
                break
        
        if end_date and calculated_next_due > end_date: # Final check
            is_active_from_start = False

        if not is_active_from_start:
            return jsonify({'error': 'Recurring transaction has no valid future occurrences based on start/end dates.'}), 400

        new_recurring = RecurringTransaction(
            user_id=user_id,
            description=data['description'],
            amount=amount,
            transaction_type=str(data['transaction_type']).lower(),
            category_id=data.get('category_id'),
            frequency=frequency,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            next_due_date=calculated_next_due,
            is_active=True # If we reach here, it's created as active
        )
        db.session.add(new_recurring)
        db.session.commit()
        return jsonify({'message': 'Recurring transaction created', 'recurring_transaction': new_recurring.to_dict()}), 201

    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating recurring transaction: {e}")
        return jsonify({'error': 'Failed to create recurring transaction'}), 500

@recurring_transaction_bp.route('', methods=['GET'])
@login_required
def get_recurring_transactions():
    user_id = session['user_id']
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = RecurringTransaction.query.filter_by(user_id=user_id)
    if active_only:
        query = query.filter_by(is_active=True)
        
    recurring_txns = query.order_by(RecurringTransaction.next_due_date).all()
    return jsonify([rt.to_dict() for rt in recurring_txns]), 200

@recurring_transaction_bp.route('/<int:rt_id>', methods=['PUT'])
@login_required
def update_recurring_transaction(rt_id):
    data = request.json
    user_id = session['user_id']
    rt = RecurringTransaction.query.filter_by(id=rt_id, user_id=user_id).first()

    if not rt:
        return jsonify({'error': 'Recurring transaction not found'}), 404

    try:
        if 'description' in data: rt.description = data['description']
        if 'amount' in data: rt.amount = float(data['amount'])
        if 'transaction_type' in data: rt.transaction_type = data['transaction_type'].lower()
        if 'category_id' in data: rt.category_id = data.get('category_id')

        date_params_changed = False
        if 'frequency' in data:
            rt.frequency = data['frequency'].lower()
            if rt.frequency not in ['daily', 'weekly', 'monthly', 'yearly']: return jsonify({'error': 'Invalid frequency type'}), 400
            date_params_changed = True
        if 'interval' in data:
            rt.interval = int(data['interval'])
            if rt.interval <=0: return jsonify({'error': 'Interval must be positive'}), 400
            date_params_changed = True
        if 'start_date_str' in data:
            rt.start_date = datetime.strptime(data['start_date_str'], '%Y-%m-%d').date()
            date_params_changed = True
        if 'end_date_str' in data:
            rt.end_date = datetime.strptime(data['end_date_str'], '%Y-%m-%d').date() if data['end_date_str'] else None
            date_params_changed = True
            if rt.end_date and rt.end_date < rt.start_date: return jsonify({'error': 'End date cannot be before start date'}), 400

        user_set_active_status = data.get('is_active')

        if date_params_changed:
            # Recalculate next_due_date based on potentially new start_date, frequency, interval
            calculated_next_due = rt.start_date
            today = date.today()
            can_be_active = True

            while calculated_next_due < today:
                if rt.end_date and calculated_next_due > rt.end_date:
                    can_be_active = False
                    break
                try:
                    potential_next = calculate_next_due_date(rt.start_date, rt.frequency, rt.interval, current_next_due=calculated_next_due)
                except ValueError:
                    return jsonify({'error': 'Invalid frequency for date calculation during update'}), 400

                if potential_next <= calculated_next_due:
                    current_app.logger.error(f"Update: Next due date calculation did not advance: {calculated_next_due} -> {potential_next}")
                    return jsonify({'error': 'Internal error calculating next due date progression during update.'}), 500
                calculated_next_due = potential_next

                if rt.end_date and calculated_next_due > rt.end_date:
                    can_be_active = False # Advanced past end_date
                    break
            
            if rt.end_date and calculated_next_due > rt.end_date: # Final check
                can_be_active = False

            rt.next_due_date = calculated_next_due # Update next_due_date
            rt.is_active = can_be_active # Set active status based on calculation

        # Apply user's explicit is_active choice if provided
        if user_set_active_status is not None:
            if not bool(user_set_active_status): # If user wants to deactivate
                rt.is_active = False
            elif date_params_changed and not rt.is_active : # User wants to activate, but calculation made it inactive
                pass # It remains inactive due to date constraints
            else: # User wants to activate and it's possible, or no date params changed
                rt.is_active = True

        db.session.commit()
        return jsonify({'message': 'Recurring transaction updated', 'recurring_transaction': rt.to_dict()}), 200
    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating recurring transaction {rt_id}: {e}")
        return jsonify({'error': 'Failed to update recurring transaction'}), 500

@recurring_transaction_bp.route('/<int:rt_id>', methods=['DELETE'])
@login_required
def delete_recurring_transaction(rt_id):
    user_id = session['user_id']
    rt = RecurringTransaction.query.filter_by(id=rt_id, user_id=user_id).first()

    if not rt:
        return jsonify({'error': 'Recurring transaction not found'}), 404

    try:
        # Instead of deleting, we can mark as inactive
        # db.session.delete(rt)
        rt.is_active = False
        db.session.commit()
        return jsonify({'message': 'Recurring transaction deactivated'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating recurring transaction {rt_id}: {e}")
        return jsonify({'error': 'Failed to deactivate recurring transaction'}), 500

# Note: Logic for automatically generating transactions from due recurring_transactions
# would typically be in a separate scheduled task or triggered by an event (e.g., user login).
# For simplicity, it's not included directly in these CRUD routes.
# You would query RecurringTransaction where next_due_date <= today and is_active == True,
# create a Transaction, and then update next_due_date for the RecurringTransaction.