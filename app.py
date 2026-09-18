from flask import Flask , render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date

app = Flask(
    __name__,
    template_folder='app/templates',
    static_folder='app/static'
)
app.config['SECRET_KEY'] = 'dev-secret-key'

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
    return redirect(url_for('dashboard'))


@app.route('/add-expense', methods=['GET'])
def add_expenses_form():
    return render_template('add_expense.html')

@app.route('/add-expense', methods=['POST'])
def add_expense():

    # Get values from the form
    title = request.form.get('title', '').strip()
    amount = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    expense_date = request.form.get('expense_date', '').strip()
    notes = request.form.get('notes', '').strip()

    # Check title
    if not title:
        flash('Expense title is required!', 'error')
        return redirect(url_for('add_expenses_form'))

    # Check category
    if not category:
        flash('Category is required!', 'error')
        return redirect(url_for('add_expenses_form'))

    # Check amount
    try:
        amount = float(amount)

        if amount <= 0:
            flash('Amount must be greater than 0!', 'error')
            return redirect(url_for('add_expenses_form'))

    except ValueError:
        flash('Please enter a valid amount!', 'error')
        return redirect(url_for('add_expenses_form'))

    # Check date
    try:
        expense_date = date.fromisoformat(expense_date)

    except ValueError:
        flash('Please enter a valid date!', 'error')
        return redirect(url_for('add_expenses_form'))

    # Create expense object
    expense = Expenses(
        title=title,
        amount=amount,
        category=category,
        expense_date=expense_date,
        notes=notes
    )

    # Save to database
    db.session.add(expense)
    db.session.commit()

    flash('Expense added successfully!', 'success')

    return redirect(url_for('view_expenses'))

@app.route('/expenses')
def view_expenses():
    expenses = Expenses.query.all()
    return render_template('expenses.html', data=expenses)

@app.route('/edit_expense/<int:expense_id>', methods=['GET','POST'])
def edit_expense(expense_id):
    expense = Expenses.query.get_or_404(expense_id)

    if request.method == 'POST':
        expense.title = request.form['title']
        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.expense_date = request.form['expense_date']
        expense.notes = request.form['notes']

        db.session.commit()
        return redirect(url_for('view_expenses'))

    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expenses.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()

    flash('Expense deleted successfully!', 'success')

    return redirect(url_for('view_expenses'))

@app.route('/dashboard')
def dashboard():

    count = Expenses.query.count()

    average_expense = db.session.query(
        db.func.avg(Expenses.amount)
    ).scalar() or 0

    total=db.session.query(
        db.func.sum(Expenses.amount)
    ).scalar() or 0

    highest_expense = db.session.query(
        db.func.max(Expenses.amount)
    ).scalar() or 0

    recent_expenses = Expenses.query.order_by(
    Expenses.expense_date.desc()
    ).limit(5).all()

    category_summary = db.session.query(
    Expenses.category,
    db.func.sum(Expenses.amount)
    ).group_by(Expenses.category).all()

    current_month = date.today().month
    current_year = date.today().year

    monthly_expense = db.session.query(
        db.func.sum(Expenses.amount)
    ).filter(
        db.extract('month', Expenses.expense_date) == current_month,
        db.extract('year', Expenses.expense_date) == current_year
    ).scalar() or 0

    return render_template(
        'dashboard.html',
        count=count,
        total=total,
        average_expense=average_expense,
        highest_expense=highest_expense,
        monthly_expense=monthly_expense,
        recent_expenses=recent_expenses,
        category_summary=category_summary
    )



if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)