from sqlalchemy.orm import relationship
from src.extensions import db # Import db from extensions.py
from datetime import date, datetime

class RecurringTransaction(db.Model):
    __tablename__ = 'recurring_transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'income' or 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    frequency = db.Column(db.String(50), nullable=False)  # e.g., 'daily', 'weekly', 'monthly', 'yearly'
    interval = db.Column(db.Integer, nullable=False, default=1) # e.g., every 1 month, every 2 weeks
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True) # Optional: if the recurrence has an end
    next_due_date = db.Column(db.Date, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', backref=db.backref('recurring_transactions', lazy='dynamic'))
    category = relationship('Category') # Assuming Category model is defined elsewhere

    def __repr__(self):
        return f'<RecurringTransaction {self.id} {self.description} - {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'description': self.description,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'frequency': self.frequency,
            'interval': self.interval,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }