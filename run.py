from flask import Flask , render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, template_folder='app/templates')

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/expense_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Expenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

@app.route('/')
def home():
    return 'Expense Tracker is connected to the database'


@app.route('/add-expense', methods=['GET'])
def add_expenses_form():
    return render_template('add_expense.html')

@app.route('/add-expense', methods=['POST'])
def add_expense():

    title = request.form['title']
    amount = request.form['amount']
    category = request.form['category']
    expense_date = request.form['expense_date']
    notes = request.form['notes']

    expense = Expenses(
        title=title,
        amount=amount,
        category=category,
        expense_date=expense_date,
        notes=notes
    )

    db.session.add(expense)
    db.session.commit()

    return 'Expense added successfully'


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)