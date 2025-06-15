import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.extensions import db # Import db from the new extensions.py


# Now, import blueprints. These might import models, which in turn import 'db' from this file.
# Since 'db' is defined above, this will work.
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.transaction import transaction_bp
from src.routes.budget import budget_bp # Import the new budget blueprint
from src.routes.recurring_transaction import recurring_transaction_bp# Import new blueprint
from src.routes.savings_goal import savings_goal_bp # Import new blueprint

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Initialize db with the Flask app instance

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth') # auth_bp handles user creation (signup)
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(transaction_bp, url_prefix='/api')
app.register_blueprint(budget_bp) # FIX: Removed redundant url_prefix. The prefix is already in the blueprint file.
app.register_blueprint(recurring_transaction_bp) # FIX: Removed redundant url_prefix. The prefix is already in the blueprint file.
app.register_blueprint(savings_goal_bp)

# Create database tables and default categories
with app.app_context():
    # Import models here, after db is initialized and app_context is active,
    # to ensure they are registered with the correct db instance.
    from src.models.user import User
    from src.models.transaction import Transaction, Category # Import Category here
    from src.models.budget import Budget
    from src.models.recurring_transaction import RecurringTransaction
    from src.models.savings_goal import SavingsGoal
    
    db.create_all()
    
    # Create default categories if they don't exist
    # Category model is now correctly in scope here.
    default_categories = [
        {'name': 'Food', 'description': 'Food and dining expenses'},
        {'name': 'Bills', 'description': 'Utility bills and recurring payments'},
        {'name': 'Entertainment', 'description': 'Movies, games, and leisure activities'},
        {'name': 'Transportation', 'description': 'Gas, public transport, and travel'},
        {'name': 'Shopping', 'description': 'Clothing, electronics, and general shopping'},
        {'name': 'Healthcare', 'description': 'Medical expenses and health-related costs'},
        {'name': 'Salary', 'description': 'Regular income from employment'},
        {'name': 'Other', 'description': 'Miscellaneous transactions'}
    ]
    
    for cat_data in default_categories:
        existing_category = Category.query.filter_by(name=cat_data['name']).first()
        if not existing_category:
            category = Category(name=cat_data['name'], description=cat_data['description'])
            db.session.add(category)
    
    db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)