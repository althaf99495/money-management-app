from src.extensions import db # Import db from extensions.py
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# db = SQLAlchemy() # Moved to main.py

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with transactions
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the user's password"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def get_balance(self):
        """Calculate current balance from transactions"""
        total_income = sum(t.amount for t in self.transactions if t.transaction_type == 'income')
        total_expense = sum(t.amount for t in self.transactions if t.transaction_type == 'expense')
        return total_income - total_expense
