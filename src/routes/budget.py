# d:\money-management-app\src\routes\budget.py
from flask import Blueprint, request, jsonify, session, current_app
from src.models.budget import Budget
from src.models.transaction import Transaction, Category # Assuming these are in transaction.py or a models file
from src.extensions import db # Import db from extensions.py
from src.routes.auth import login_required
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract

budget_bp = Blueprint('budget', __name__, url_prefix='/api/budgets')

@budget_bp.route('', methods=['POST'])
@login_required
def create_budget():
    data = request.json
    user_id = session['user_id']

    required_fields = ['category_id', 'amount', 'budget_month_str', 'period']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields (category_id, amount, budget_month_str, period)'}), 400

    try:
        category_id = int(data['category_id'])
        amount = float(data['amount'])
        budget_month_str = data['budget_month_str'] # Expected format: "YYYY-MM"
        period = data.get('period', 'monthly').lower()

        if amount <= 0:
            return jsonify({'error': 'Budget amount must be positive'}), 400

        # Convert "YYYY-MM" to a date object (first day of the month)
        try:
            budget_month_date = datetime.strptime(budget_month_str + "-01", '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid budget_month format. Use YYYY-MM.'}), 400
        
        # Check if category exists
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        # Optional: Check for existing budget for the same user, category, and month/period
        existing_budget = Budget.query.filter_by(
            user_id=user_id, 
            category_id=category_id, 
            budget_month=budget_month_date,
            period=period
        ).first()
        if existing_budget:
            return jsonify({'error': f'A {period} budget for this category in {budget_month_str} already exists.'}), 409


        new_budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period=period,
            budget_month=budget_month_date
        )
        db.session.add(new_budget)
        db.session.commit()
        return jsonify({'message': 'Budget created successfully', 'budget': new_budget.to_dict()}), 201
    except ValueError:
        return jsonify({'error': 'Invalid amount or category_id format'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating budget: {e}")
        return jsonify({'error': 'Failed to create budget'}), 500

@budget_bp.route('', methods=['GET'])
@login_required
def get_budgets():
    user_id = session['user_id']
    # Optionally filter by month/year: request.args.get('month_year', 'YYYY-MM')
    month_year_filter_str = request.args.get('month_year')

    query = Budget.query.filter_by(user_id=user_id)

    if month_year_filter_str:
        try:
            year, month = map(int, month_year_filter_str.split('-'))
            query = query.filter(
                extract('year', Budget.budget_month) == year,
                extract('month', Budget.budget_month) == month
            )
        except ValueError:
            return jsonify({'error': 'Invalid month_year filter format. Use YYYY-MM.'}), 400
            
    budgets = query.order_by(Budget.budget_month.desc(), Budget.category_id).all()
    return jsonify([budget.to_dict() for budget in budgets]), 200

@budget_bp.route('/<int:budget_id>', methods=['PUT'])
@login_required
def update_budget(budget_id):
    data = request.json
    user_id = session['user_id']
    budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()

    if not budget:
        return jsonify({'error': 'Budget not found or not authorized'}), 404

    try:
        if 'amount' in data:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'error': 'Budget amount must be positive'}), 400
            budget.amount = amount
        if 'category_id' in data:
            category_id = int(data['category_id'])
            category = Category.query.get(category_id)
            if not category:
                 return jsonify({'error': 'Category not found'}), 404
            budget.category_id = category_id
        if 'budget_month_str' in data:
            try:
                budget.budget_month = datetime.strptime(data['budget_month_str'] + "-01", '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid budget_month format. Use YYYY-MM.'}), 400
        if 'period' in data:
            budget.period = data['period'].lower()
        
        db.session.commit()
        return jsonify({'message': 'Budget updated successfully', 'budget': budget.to_dict()}), 200
    except ValueError:
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating budget {budget_id}: {e}")
        return jsonify({'error': 'Failed to update budget'}), 500

@budget_bp.route('/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    user_id = session['user_id']
    budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()

    if not budget:
        return jsonify({'error': 'Budget not found or not authorized'}), 404

    try:
        db.session.delete(budget)
        db.session.commit()
        return jsonify({'message': 'Budget deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting budget {budget_id}: {e}")
        return jsonify({'error': 'Failed to delete budget'}), 500

@budget_bp.route('/summary', methods=['GET'])
@login_required
def get_budget_summary():
    user_id = session['user_id']
    # Default to current month if not specified
    month_year_str = request.args.get('month_year', date.today().strftime('%Y-%m'))

    try:
        year, month = map(int, month_year_str.split('-'))
        start_of_month = date(year, month, 1)
        # Find the last day of the month
        if month == 12:
            end_of_month = date(year, month, 31)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
            
    except ValueError:
        return jsonify({'error': 'Invalid month_year format. Use YYYY-MM.'}), 400

    from sqlalchemy.orm import joinedload

    budgets = Budget.query.options(joinedload(Budget.category)).filter_by(user_id=user_id, period='monthly').filter(
        extract('year', Budget.budget_month) == year,
        extract('month', Budget.budget_month) == month
    ).all()

    summary = []
    for budget in budgets:
        # Sum expenses for this category in the given month
        total_spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_type == 'expense',
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month
        ).scalar() or 0.0

        summary.append({
            'budget_id': budget.id,
            'category_id': budget.category_id,
            'category_name': budget.category.name if getattr(budget, 'category', None) and getattr(budget.category, 'name', None) else 'N/A',
            'budgeted_amount': budget.amount,
            'spent_amount': total_spent,
            'remaining_amount': budget.amount - total_spent,
            'period': budget.period,
            'budget_month': budget.budget_month.strftime('%Y-%m')
        })
        
    return jsonify(summary), 200
