from flask import Blueprint, request, Response, jsonify, g, current_app, session
from src.models.user import User
from src.models.transaction import Transaction, Category
from src.routes.auth import login_required
from datetime import datetime, date
from sqlalchemy import and_, or_, func
from src.extensions import db
import csv
import io
from weasyprint import HTML

transaction_bp = Blueprint('transaction', __name__)

# --- Refactored Helper Function ---
def _get_filtered_transactions_query(user_id):
    """
    Returns a SQLAlchemy query object for transactions based on request args.
    This reduces code duplication across multiple routes.
    """
    query = Transaction.query.filter_by(user_id=user_id)

    category_id = request.args.get('category_id', type=int)
    transaction_type = request.args.get('type')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if transaction_type and transaction_type in ['income', 'expense']:
        query = query.filter_by(transaction_type=transaction_type)
    
    if start_date_str:
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Transaction.date >= start_date_obj)
        except ValueError:
            # Silently ignore invalid date format for filtering
            pass
    
    if end_date_str:
        try:
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(Transaction.date <= end_date_obj)
        except ValueError:
            # Silently ignore invalid date format
            pass
            
    return query

# --- Routes ---

@transaction_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all categories"""
    try:
        categories = Category.query.all()
        return jsonify([category.to_dict() for category in categories]), 200
    except Exception as e:
        current_app.logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Failed to get categories'}), 500

@transaction_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's transactions with optional filtering"""
    try:
        user_id = session['user_id']
        limit = request.args.get('limit', 50, type=int)
        
        query = _get_filtered_transactions_query(user_id)
        
        transactions = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).all()
        
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting transactions: {e}")
        return jsonify({'error': 'Failed to get transactions'}), 500

@transaction_bp.route('/transactions', methods=['POST'])
@login_required
def create_transaction():
    """Create a new transaction"""
    try:
        data = request.json
        user_id = session['user_id']
        
        if not data or not data.get('amount') or not data.get('transaction_type'):
            return jsonify({'error': 'Amount and transaction type are required'}), 400
        
        amount = float(data['amount'])
        transaction_type = data['transaction_type'].lower()
        description = data.get('description', '').strip()
        category_id = data.get('category_id')
        
        if transaction_type not in ['income', 'expense']:
            return jsonify({'error': 'Transaction type must be "income" or "expense"'}), 400
        
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
        
        if category_id:
            category = Category.query.get(category_id)
            if not category:
                return jsonify({'error': 'Invalid category ID'}), 400
        
        transaction_date = date.today()
        if data.get('date'):
            try:
                transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
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
        current_app.logger.error(f"Error creating transaction: {e}")
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
        current_app.logger.error(f"Error getting transaction {transaction_id}: {e}")
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
        
        if 'amount' in data:
            amount = float(data['amount'])
            if amount <= 0: return jsonify({'error': 'Amount must be positive'}), 400
            transaction.amount = amount
        
        if 'description' in data:
            transaction.description = data['description'].strip()
        
        if 'transaction_type' in data:
            transaction_type = data['transaction_type'].lower()
            if transaction_type not in ['income', 'expense']: return jsonify({'error': 'Invalid transaction type'}), 400
            transaction.transaction_type = transaction_type
        
        if 'category_id' in data:
            category_id = data['category_id']
            if category_id:
                category = Category.query.get(category_id)
                if not category: return jsonify({'error': 'Invalid category ID'}), 400
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
        current_app.logger.error(f"Error updating transaction {transaction_id}: {e}")
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
        current_app.logger.error(f"Error deleting transaction {transaction_id}: {e}")
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
        
        recent_transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
            .limit(10).all()
        
        total_income = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, transaction_type='income').scalar() or 0
        
        total_expense = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, transaction_type='expense').scalar() or 0
        
        balance = total_income - total_expense
        
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
        current_app.logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500

@transaction_bp.route('/transactions/download/csv', methods=['GET'])
@login_required
def download_transactions_csv():
    """Download user's transactions as a CSV file with optional filtering"""
    try:
        user_id = session['user_id']
        query = _get_filtered_transactions_query(user_id)
        transactions = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()

        if not transactions:
            return jsonify({"message": "No transactions found for the selected criteria."}), 404

        total_income_val = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expense_val = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        net_balance_val = total_income_val - total_expense_val

        output = io.StringIO()
        csv_writer = csv.writer(output)
        
        headers = ['Date', 'Description', 'Amount', 'Type', 'Category']
        csv_writer.writerow(headers)
        
        for t in transactions:
            category_name = t.category.name if t.category else ''
            csv_writer.writerow([
                t.date.strftime('%Y-%m-%d') if t.date else '',
                t.description,
                t.amount,
                t.transaction_type,
                category_name
            ])
        
        # Add summary rows
        csv_writer.writerow([]) # Empty row for spacing
        csv_writer.writerow(['Summary:'])
        csv_writer.writerow(['Total Income:', f'{total_income_val:.2f}'])
        csv_writer.writerow(['Total Expenses:', f'{total_expense_val:.2f}'])
        csv_writer.writerow(['Net Balance:', f'{net_balance_val:.2f}'])
            
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=transactions.csv"}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading CSV: {e}")
        return jsonify({'error': 'Failed to download transactions as CSV'}), 500

@transaction_bp.route('/transactions/download/pdf', methods=['GET'])
@login_required
def download_transactions_pdf():
    """Download user's transactions as a PDF file with optional filtering"""
    try:
        user_id = session['user_id']
        query = _get_filtered_transactions_query(user_id)
        transactions = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()

        if not transactions:
            return jsonify({"message": "No transactions found for the selected criteria."}), 404

        # Calculate totals
        total_income_val = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expense_val = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        net_balance_val = total_income_val - total_expense_val

        # Prepare filter information for the header
        report_date = date.today().strftime('%Y-%m-%d')
        filters_applied = []
        start_date_filter = request.args.get('start_date')
        end_date_filter = request.args.get('end_date')
        type_filter = request.args.get('type')
        category_id_filter = request.args.get('category_id', type=int)

        if start_date_filter or end_date_filter:
            period_str = "All Dates"
            if start_date_filter and end_date_filter:
                period_str = f"{start_date_filter} to {end_date_filter}"
            elif start_date_filter:
                period_str = f"From {start_date_filter}"
            elif end_date_filter:
                period_str = f"Up to {end_date_filter}"
            filters_applied.append(f"Period: {period_str}")
        if type_filter:
            filters_applied.append(f"Type: {type_filter.capitalize()}")
        if category_id_filter:
            category_filter_obj = Category.query.get(category_id_filter)
            if category_filter_obj:
                filters_applied.append(f"Category: {category_filter_obj.name}")

        filter_html = "<ul>" + "".join(f"<li>{f}</li>" for f in filters_applied) + "</ul>" if filters_applied else "<p>None</p>"

        html_string = f"""<html><head><title>Transaction Report</title>
<style>body{{font-family:sans-serif; font-size: 10pt;}} 
h1{{text-align:center;}}
table{{width:100%; border-collapse:collapse; margin-top: 15px; margin-bottom: 15px;}} 
th,td{{border:1px solid #ddd; padding:6px; text-align:left;}} 
th{{background-color: #f2f2f2;}}
.header-info, .summary-section {{margin-bottom: 20px; padding:10px; border: 1px solid #eee;}}
.header-info p, .summary-section p {{margin: 5px 0;}}
</style></head><body>
<h1>Transaction Report</h1>
<div class="header-info"><p><strong>Report Generated:</strong> {report_date}</p><p><strong>Filters Applied:</strong></p>{filter_html}</div>
<table border='1'><tr><th>Date</th><th>Description</th><th>Amount (INR)</th><th>Type</th><th>Category</th></tr>"""
        for t in transactions:
            category_name = t.category.name if t.category else ''
            html_string += f"<tr><td>{t.date.strftime('%Y-%m-%d') if t.date else ''}</td><td>{t.description or ''}</td><td>{t.amount:.2f}</td><td>{t.transaction_type}</td><td>{category_name}</td></tr>"
        html_string += f"""</table>
<div class="summary-section"><h3>Summary</h3>
<p><strong>Total Transactions:</strong> {len(transactions)}</p>
<p><strong>Total Income:</strong> {total_income_val:.2f} INR</p>
<p><strong>Total Expenses:</strong> {total_expense_val:.2f} INR</p>
<p><strong>Net Balance:</strong> {net_balance_val:.2f} INR</p>
</div></body></html>"""

        pdf_bytes = HTML(string=html_string).write_pdf()

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename=transactions.pdf"}
        )

    except Exception as e:
        current_app.logger.error(f"Error downloading PDF: {e}")
        return jsonify({'error': 'Failed to download transactions as PDF'}), 500