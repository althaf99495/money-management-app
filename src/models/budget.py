# d:\money-management-app\src\models\budget.py
from sqlalchemy.orm import relationship
from src.extensions import db # Import db from extensions.py
from datetime import date

class Budget(db.Model):
    __tablename__ = 'budget'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    # Period for the budget, e.g., 'monthly', 'yearly', 'weekly'
    period = db.Column(db.String(50), nullable=False, default='monthly')
    # The month and year this budget applies to (for monthly budgets)
    # For simplicity, we'll store the first day of the month.
    budget_month = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = relationship('User', backref=db.backref('budgets', lazy='dynamic'))
    category = relationship('Category') # Assuming Category model exists

    def __repr__(self):
        return f'<Budget {self.id} for {self.category.name if self.category else "N/A"} - {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else 'N/A',
            'amount': self.amount,
            'period': self.period,
            'budget_month': self.budget_month.strftime('%Y-%m') if self.budget_month else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
