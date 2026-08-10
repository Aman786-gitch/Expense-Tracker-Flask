from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/db_name'
db = SQLAlchemy(app)

class Expenses(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(100), nullable=False)
    amount=db.Column(db.Decimal(10, 2), nullable=False)
    category=db.Column(db.String(50), nullable=False)
    expense_date=db.Column(db.Date, nullable=False)
    notes=db.Column(db.Text(120), nullable=True)
    created_at=db.Column(db.DateTime, default=db.func.current_timestamp())