import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.transaction import Transaction, Category
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.transaction import transaction_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(transaction_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create database tables and default categories
with app.app_context():
    db.create_all()
    
    # Create default categories if they don't exist
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
