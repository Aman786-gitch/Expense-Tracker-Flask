from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from dotenv import load_dotenv

load_dotenv()
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import calendar
import os


app = Flask(
    __name__,
    template_folder='app/templates',
    static_folder='app/static'
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

if not app.config['SECRET_KEY']:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set."
    )
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/expense_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


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
    user_id = db.Column(
    db.Integer,
    db.ForeignKey('user.id'),
    nullable=False
    )

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(
    db.Integer,
    db.ForeignKey('user.id'),
    nullable=False
)



def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))

        return route_function(*args, **kwargs)

    return wrapper



@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Check that all fields are filled
        if not name or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('register'))

        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))

        # Check whether the email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()

        except Exception:
            db.session.rollback()
            app.logger.exception('Registration failed')
            flash('Unable to create account. Please try again.', 'error')
            return redirect(url_for('register'))

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name

            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()

    # Start a clean session so the logout message
    # does not carry over to another account.
    session['_flashes'] = []

    flash('You are logged out successfully!', 'success')
    return redirect(url_for('login'))




@app.route('/')
def home():
    return redirect(url_for('dashboard'))


@app.route('/add-expense', methods=['GET'])
@login_required
def add_expenses_form():
    return render_template('add_expense.html')

@app.route('/add-expense', methods=['POST'])
@login_required
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
        notes=notes,
        user_id=session['user_id']
    )

    # Save to database
    db.session.add(expense)
    db.session.commit()

    flash('Expense added successfully!', 'success')

    return redirect(url_for('view_expenses'))


@app.route('/set-budget', methods=['GET', 'POST'])
@login_required
def set_budget():

    user_id = session.get('user_id')

    if request.method == 'POST':

        amount = request.form.get('amount', '').strip()

        try:
            amount = float(amount)

            if amount <= 0:
                flash('Budget must be greater than 0!', 'error')
                return redirect(url_for('set_budget'))

        except (ValueError, TypeError):
            flash('Please enter a valid budget amount!', 'error')
            return redirect(url_for('set_budget'))

        current_month = date.today().month
        current_year = date.today().year

        # Find this user's budget for the current month
        budget = Budget.query.filter_by(
            user_id=user_id,
            month=current_month,
            year=current_year
        ).first()

        if budget:
            # Update existing budget
            budget.amount = amount
        else:
            # Create a budget belonging to the logged-in user
            budget = Budget(
                amount=amount,
                month=current_month,
                year=current_year,
                user_id=user_id
            )
            db.session.add(budget)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Failed to save monthly budget')
            flash('Unable to save the budget. Please try again.', 'error')
            return redirect(url_for('set_budget'))

        flash('Monthly budget saved successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('set_budget.html')



@app.route('/expenses')
@login_required
def view_expenses():

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    month = request.args.get('month', '').strip()

    # Fetch only the logged-in user's expenses
    query = Expenses.query.filter_by(
        user_id=session['user_id']
    )

    # Apply search filter
    if search:
        query = query.filter(
            Expenses.title.ilike(f'%{search}%')
        )

    # Apply category filter
    if category:
        query = query.filter(
            Expenses.category == category
        )

    # Apply month filter
    if month:
        try:
            month_number = int(month)

            if 1 <= month_number <= 12:
                query = query.filter(
                    db.extract(
                        'month', Expenses.expense_date
                    ) == month_number
                )
            else:
                flash('Please select a valid month.', 'error')
                return redirect(url_for('view_expenses'))

        except ValueError:
            flash('Please select a valid month.', 'error')
            return redirect(url_for('view_expenses'))

    expenses = query.order_by(
        Expenses.expense_date.desc()
    ).all()

    # Categories belonging to the logged-in user
    categories = db.session.query(
        Expenses.category
    ).filter_by(
        user_id=session['user_id']
    ).distinct().all()

    categories = [cat[0] for cat in categories]

    return render_template(
        'expenses.html',
        data=expenses,
        search=search,
        category=category,
        month=month,
        categories=categories
    )



@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):

    # Find the expense belonging to the logged-in user only
    expense = Expenses.query.filter_by(
        id=expense_id,
        user_id=session['user_id']
    ).first_or_404()

    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        amount = request.form.get('amount', '').strip()
        category = request.form.get('category', '').strip()
        expense_date = request.form.get('expense_date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not title or not category or not expense_date:
            flash('Please fill in all required fields.', 'error')
            return redirect(
                url_for('edit_expense', expense_id=expense.id)
            )

        try:
            amount = float(amount)

            if amount <= 0:
                raise ValueError

        except ValueError:
            flash('Please enter a valid amount greater than 0.', 'error')
            return redirect(
                url_for('edit_expense', expense_id=expense.id)
            )

        try:
            expense_date = date.fromisoformat(expense_date)
        except ValueError:
            flash('Please enter a valid date.', 'error')
            return redirect(
                url_for('edit_expense', expense_id=expense.id)
            )

        expense.title = title
        expense.amount = amount
        expense.category = category
        expense.expense_date = expense_date
        expense.notes = notes

        db.session.commit()

        flash('Expense updated successfully!', 'success')
        return redirect(url_for('view_expenses'))

    return render_template('edit_expense.html', expense=expense)



@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):

    # Only allow deletion of the current user's expense
    expense = Expenses.query.filter_by(
        id=expense_id,
        user_id=session['user_id']
    ).first_or_404()

    db.session.delete(expense)
    db.session.commit()

    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('view_expenses'))



@app.route('/dashboard')
@login_required
def dashboard():

    user_id = session.get('user_id')

    # Only this user's expenses
    user_expenses = Expenses.query.filter_by(user_id=user_id)

    count = user_expenses.count()

    average_expense = db.session.query(
        db.func.avg(Expenses.amount)
    ).filter(
        Expenses.user_id == user_id
    ).scalar() or 0

    total = db.session.query(
        db.func.sum(Expenses.amount)
    ).filter(
        Expenses.user_id == user_id
    ).scalar() or 0

    highest_expense = db.session.query(
        db.func.max(Expenses.amount)
    ).filter(
        Expenses.user_id == user_id
    ).scalar() or 0

    recent_expenses = user_expenses.order_by(
        Expenses.expense_date.desc(),
        Expenses.id.desc()
    ).limit(5).all()

    # Category chart: only the logged-in user's expenses
    category_summary = db.session.query(
        Expenses.category,
        db.func.sum(Expenses.amount)
    ).filter(
        Expenses.user_id == user_id
    ).group_by(
        Expenses.category
    ).all()

    current_month = date.today().month
    current_year = date.today().year

    # This user's spending in the current month
    monthly_expense = db.session.query(
        db.func.sum(Expenses.amount)
    ).filter(
        Expenses.user_id == user_id,
        db.extract('month', Expenses.expense_date) == current_month,
        db.extract('year', Expenses.expense_date) == current_year
    ).scalar() or 0

    # This user's budget for the current month
    budget = Budget.query.filter_by(
        user_id=user_id,
        month=current_month,
        year=current_year
    ).first()

    if budget:
        budget_amount = float(budget.amount)
        remaining_budget = budget_amount - float(monthly_expense)

        budget_percentage = (
            float(monthly_expense) / budget_amount * 100
        ) if budget_amount > 0 else 0
    else:
        budget_amount = 0
        remaining_budget = 0
        budget_percentage = 0

    # Monthly chart: only the logged-in user's expenses
    monthly_summary = db.session.query(
        db.extract(
            'month', Expenses.expense_date
        ).label('month'),
        db.func.sum(
            Expenses.amount
        ).label('total')
    ).filter(
        Expenses.user_id == user_id
    ).group_by(
        db.extract('month', Expenses.expense_date)
    ).order_by(
        db.extract('month', Expenses.expense_date)
    ).all()

    monthly_summary = [
        (calendar.month_name[int(month)], amount)
        for month, amount in monthly_summary
    ]

    return render_template(
        'dashboard.html',
        count=count,
        total=total,
        average_expense=average_expense,
        highest_expense=highest_expense,
        monthly_expense=monthly_expense,
        recent_expenses=recent_expenses,
        category_summary=category_summary,
        monthly_summary=monthly_summary,
        budget_amount=budget_amount,
        remaining_budget=remaining_budget,
        budget_percentage=budget_percentage
    )




if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)