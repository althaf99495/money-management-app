from flask import Blueprint, jsonify, request, session
from src.models.user import User, db
from src.models.transaction import Transaction, Category
from src.routes.auth import login_required
from datetime import datetime, date
from sqlalchemy import and_, or_, func

transaction_bp = Blueprint('transaction', __name__)

@transaction_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all categories"""
    try:
        categories = Category.query.all()
        return jsonify([category.to_dict() for category in categories]), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get categories'}), 500

@transaction_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's transactions with optional filtering"""
    try:
        user_id = session['user_id']
        
        # Get query parameters for filtering
        category_id = request.args.get('category_id', type=int)
        transaction_type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 50, type=int)
        
        # Build query
        query = Transaction.query.filter_by(user_id=user_id)
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if transaction_type and transaction_type in ['income', 'expense']:
            query = query.filter_by(transaction_type=transaction_type)
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Transaction.date >= start_date_obj)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Transaction.date <= end_date_obj)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        # Order by date descending and limit results
        transactions = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).all()
        
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get transactions'}), 500

@transaction_bp.route('/transactions', methods=['POST'])
@login_required
def create_transaction():
    """Create a new transaction"""
    try:
        data = request.json
        user_id = session['user_id']
        
        # Validate required fields
        if not data or not data.get('amount') or not data.get('transaction_type'):
            return jsonify({'error': 'Amount and transaction type are required'}), 400
        
        amount = float(data['amount'])
        transaction_type = data['transaction_type'].lower()
        description = data.get('description', '').strip()
        category_id = data.get('category_id')
        
        # Validate transaction type
        if transaction_type not in ['income', 'expense']:
            return jsonify({'error': 'Transaction type must be "income" or "expense"'}), 400
        
        # Validate amount
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
        
        # Validate category if provided
        if category_id:
            category = Category.query.get(category_id)
            if not category:
                return jsonify({'error': 'Invalid category ID'}), 400
        
        # Parse date if provided, otherwise use today
        transaction_date = date.today()
        if data.get('date'):
            try:
                transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create transaction
        transaction = Transaction(
            amount=amount,
            description=description,
            transaction_type=transaction_type,
            date=transaction_date,
            user_id=user_id,
            category_id=category_id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction': transaction.to_dict()
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create transaction'}), 500

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@login_required
def get_transaction(transaction_id):
    """Get a specific transaction"""
    try:
        user_id = session['user_id']
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        return jsonify(transaction.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get transaction'}), 500

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
@login_required
def update_transaction(transaction_id):
    """Update a transaction"""
    try:
        data = request.json
        user_id = session['user_id']
        
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Update fields if provided
        if 'amount' in data:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
            transaction.amount = amount
        
        if 'description' in data:
            transaction.description = data['description'].strip()
        
        if 'transaction_type' in data:
            transaction_type = data['transaction_type'].lower()
            if transaction_type not in ['income', 'expense']:
                return jsonify({'error': 'Transaction type must be "income" or "expense"'}), 400
            transaction.transaction_type = transaction_type
        
        if 'category_id' in data:
            category_id = data['category_id']
            if category_id:
                category = Category.query.get(category_id)
                if not category:
                    return jsonify({'error': 'Invalid category ID'}), 400
            transaction.category_id = category_id
        
        if 'date' in data:
            try:
                transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully',
            'transaction': transaction.to_dict()
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update transaction'}), 500

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        user_id = session['user_id']
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        db.session.delete(transaction)
        db.session.commit()
        
        return jsonify({'message': 'Transaction deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete transaction'}), 500

@transaction_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard_data():
    """Get dashboard data including balance and recent transactions"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get recent transactions (last 10)
        recent_transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
            .limit(10).all()
        
        # Calculate totals
        total_income = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, transaction_type='income').scalar() or 0
        
        total_expense = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, transaction_type='expense').scalar() or 0
        
        balance = total_income - total_expense
        
        # Get spending by category (expenses only)
        category_spending = db.session.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense'
        ).group_by(Category.name).all()
        
        return jsonify({
            'balance': balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'recent_transactions': [t.to_dict() for t in recent_transactions],
            'category_spending': [{'category': name, 'amount': float(total)} for name, total in category_spending]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get dashboard data'}), 500

