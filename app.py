from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from flask import send_file
from io import BytesIO

from sqlalchemy import func
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'qwerty'  # Change this to a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    accounts = db.relationship('Account', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='account', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    category = db.relationship('Category')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=remember)
        return redirect(url_for('dashboard'))
        
    return render_template('auth/login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
            
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(
            username=username,
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
@login_required
def dashboard():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    recent_transactions = Transaction.query.join(Account).filter(
        Account.user_id == current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()
    
    # Calculate summary data
    total_balance = sum(account.balance for account in accounts)
    
    # Calculate monthly totals
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    last_month_start = datetime(today.year if today.month > 1 else today.year - 1,
                              today.month - 1 if today.month > 1 else 12, 1)
    last_month_end = start_of_month - timedelta(days=1)
    
    # Current month calculations
    monthly_income = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= start_of_month
    ).scalar() or 0
    
    monthly_expenses = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_of_month
    ).scalar() or 0
    
    # Last month calculations
    last_month_income = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date.between(last_month_start, last_month_end)
    ).scalar() or 0
    
    last_month_expenses = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date.between(last_month_start, last_month_end)
    ).scalar() or 0

    # Calculate last month's ending balance
    last_month_balance = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.date <= last_month_end
    ).scalar() or 0

    # Calculate percentage changes
    balance_change = ((total_balance - last_month_balance) / last_month_balance * 100) if last_month_balance > 0 else 0
    income_change = ((monthly_income - last_month_income) / last_month_income * 100) if last_month_income > 0 else 0
    expense_change = ((monthly_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses > 0 else 0
    
    # Savings calculation
    savings_goal = 1000.0  # Set your default savings goal
    savings_progress = total_balance  # Or calculate based on your business logic
    
    # Get budget alerts
    budget_alerts = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.start_date <= datetime.utcnow(),
        Budget.end_date >= datetime.utcnow()
    ).all()

    # Calculate budget statistics for each budget
    for budget in budget_alerts:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == budget.category_id,
            Transaction.type == 'expense',
            Transaction.date.between(budget.start_date, budget.end_date)
        ).scalar() or 0
        
        budget.spent = spent
        budget.percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        budget.remaining = budget.amount - spent
        
        if budget.percentage > 90:
            budget.alert_status = 'danger'
        elif budget.percentage > 70:
            budget.alert_status = 'warning'
        else:
            budget.alert_status = None

    # Calculate expense by category for pie chart
    category_totals = db.session.query(
        Category.name,
        func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Category.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_of_month
    ).group_by(Category.name).all()

    category_labels = [cat[0] for cat in category_totals]
    category_data = [float(cat[1]) if cat[1] else 0 for cat in category_totals]

    # Prepare chart data for income vs expenses
    chart_labels = []
    income_data = []
    expense_data = []
    
    # Get last 7 days of data for initial chart
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        chart_labels.append(date.strftime('%Y-%m-%d'))
        
        daily_income = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
            Account.user_id == current_user.id,
            Transaction.type == 'income',
            func.date(Transaction.date) == date.date()
        ).scalar() or 0
        
        daily_expense = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
            Account.user_id == current_user.id,
            Transaction.type == 'expense',
            func.date(Transaction.date) == date.date()
        ).scalar() or 0
        
        income_data.append(float(daily_income))
        expense_data.append(float(daily_expense))

    # Get all categories for the quick transaction modal
    categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('dashboard.html',
                         accounts=accounts,
                         total_balance=total_balance,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         income_change=income_change,
                         expense_change=expense_change,
                         balance_change=balance_change,
                         savings_goal=savings_goal,
                         savings_progress=savings_progress,
                         recent_transactions=recent_transactions,
                         budget_alerts=budget_alerts,
                         chart_labels=chart_labels,
                         income_data=income_data,
                         expense_data=expense_data,
                         category_labels=category_labels,
                         category_data=category_data,
                         categories=categories,
                         abs=abs)
@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            type = request.form.get('type')
            account_id = int(request.form.get('account_id'))
            category_id = int(request.form.get('category_id'))
            description = request.form.get('description')
            date_str = request.form.get('date')
            
            # Validate inputs
            if not all([amount, type, account_id, category_id, description, date_str]):
                return jsonify({'error': 'All fields are required'}), 400
            
            # Parse date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
            
            # Verify account ownership
            account = Account.query.get_or_404(account_id)
            if account.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized access'}), 403
            
            # Check sufficient funds for expense
            if type == 'expense' and account.balance < amount:
                return jsonify({'error': 'Insufficient funds'}), 400
            
            # Update account balance
            if type == 'expense':
                account.balance -= amount
            else:
                account.balance += amount
            
            # Create transaction
            transaction = Transaction(
                amount=amount,
                type=type,
                account_id=account_id,
                category_id=category_id,
                description=description,
                date=date
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({'message': 'Transaction added successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # GET request handling
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(
        user_id=current_user.id,
        parent_id=None  # This ensures we only get main categories
    ).order_by(Category.name).all()
    
    # Build base query for transactions belonging to user's accounts
    base_query = Transaction.query.join(Account).filter(Account.user_id == current_user.id)
    
    # Apply filters
    account_filter = request.args.get('account_filter')
    if account_filter and account_filter != 'all':
        base_query = base_query.filter(Transaction.account_id == account_filter)
    
    category_filter = request.args.get('category_filter')
    if category_filter and category_filter != 'all':
        base_query = base_query.filter(Transaction.category_id == category_filter)
    
    type_filter = request.args.get('type_filter')
    if type_filter and type_filter != 'all':
        base_query = base_query.filter(Transaction.type == type_filter)
    
    # Handle date filtering
    date_range = request.args.get('date_range', 'all')
    today = datetime.now().date()
    
    if date_range == 'today':
        base_query = base_query.filter(func.date(Transaction.date) == today)
    elif date_range == 'week':
        week_start = today - timedelta(days=today.weekday())
        base_query = base_query.filter(func.date(Transaction.date) >= week_start)
    elif date_range == 'month':
        month_start = today.replace(day=1)
        base_query = base_query.filter(func.date(Transaction.date) >= month_start)
    elif date_range == 'custom':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date:
            base_query = base_query.filter(func.date(Transaction.date) >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            base_query = base_query.filter(func.date(Transaction.date) <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Execute query and calculate totals based on filtered results
    transactions = base_query.order_by(Transaction.date.desc()).all()
    
    # Calculate totals from filtered transactions
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
    net_balance = total_income - total_expenses
    
    return render_template('transactions.html',
                         transactions=transactions,
                         accounts=accounts,
                         categories=categories,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_balance=net_balance)
@app.route('/accounts', methods=['GET', 'POST'])
@login_required
def accounts():
    if request.method == 'POST':
        name = request.form.get('name')
        initial_balance = float(request.form.get('initial_balance', 0))
        
        account = Account(name=name, balance=initial_balance, user_id=current_user.id)
        db.session.add(account)
        db.session.commit()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('accounts'))
    
    # Get all accounts for the current user
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Calculate monthly income and expenses
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    
    monthly_income = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= start_of_month
    ).scalar() or 0
    
    monthly_expenses = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_of_month
    ).scalar() or 0
    
    # Get all categories for transaction modal
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    return render_template('accounts.html', 
                         accounts=accounts,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         categories=categories)
@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name')
        type = request.form.get('type')
        parent_id = request.form.get('parent_id')
        
        # Check if this is a subcategory
        if parent_id:
            parent = Category.query.filter_by(id=parent_id, user_id=current_user.id).first()
            if not parent:
                flash('Parent category not found.', 'danger')
                return redirect(url_for('categories'))
            
            # Use parent's type for subcategory
            type = parent.type
            
            # Check if subcategory already exists
            existing_subcategory = Category.query.filter_by(
                name=name,
                parent_id=parent_id,
                user_id=current_user.id
            ).first()
            
            if existing_subcategory:
                flash('A subcategory with this name already exists under this parent category.', 'danger')
                return redirect(url_for('categories'))
        else:
            # Check if main category already exists
            existing_category = Category.query.filter_by(
                name=name,
                type=type,
                user_id=current_user.id,
                parent_id=None
            ).first()
            
            if existing_category:
                flash('A category with this name already exists.', 'danger')
                return redirect(url_for('categories'))
        
        try:
            category = Category(
                name=name,
                type=type,
                parent_id=parent_id,
                user_id=current_user.id
            )
            db.session.add(category)
            db.session.commit()
            flash(f'{"Sub" if parent_id else ""}Category created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the category.', 'danger')
            print(f"Error creating category: {str(e)}")
        
        return redirect(url_for('categories'))
    
    # Get all categories
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    # Calculate monthly totals
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    
    for category in categories:
        monthly_total = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == category.id,
            Transaction.date >= start_of_month
        ).scalar() or 0
        
        category.monthly_total = monthly_total
        
        # Get current budget if exists
        current_budget = Budget.query.filter(
            Budget.category_id == category.id,
            Budget.start_date <= today,
            Budget.end_date >= today
        ).first()
        
        if current_budget and current_budget.amount > 0:
            category.budget_percentage = (monthly_total / current_budget.amount) * 100
        else:
            category.budget_percentage = 0
    
    return render_template('categories.html', categories=categories)
@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        category_id = int(request.form.get('category_id'))
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        
        budget = Budget(
            amount=amount,
            category_id=category_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(budget)
        db.session.commit()
        
        flash('Budget set successfully!', 'success')
        return redirect(url_for('budgets'))
    
    # Get all budgets and categories
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id, type='expense').all()
    
    # Calculate total budget and spent amounts
    total_budget = sum(budget.amount for budget in budgets)
    total_spent = 0
    active_budgets_count = 0

    # Process budget data for display
    for budget in budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == budget.category_id,
            Transaction.type == 'expense',
            Transaction.date.between(budget.start_date, budget.end_date)
        ).scalar() or 0
        
        budget.spent = spent
        budget.percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        budget.remaining = budget.amount - spent
        
        if budget.percentage > 90:
            budget.alert_status = 'danger'
        elif budget.percentage > 70:
            budget.alert_status = 'warning'
        else:
            budget.alert_status = None
            
        if budget.start_date <= datetime.utcnow() <= budget.end_date:
            active_budgets_count += 1
            total_spent += spent

    # Calculate available budget
    available_budget = total_budget - total_spent
    
    # Prepare chart data
    budget_labels = [budget.category.name for budget in budgets]
    budget_amounts = [budget.amount for budget in budgets]
    spent_amounts = [budget.spent for budget in budgets]
    
    # Prepare category distribution data
    category_totals = db.session.query(
        Category.name,
        func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Category.user_id == current_user.id,
        Transaction.type == 'expense'
    ).group_by(Category.name).all()
    
    category_labels = [cat[0] for cat in category_totals]
    category_amounts = [float(cat[1]) if cat[1] else 0 for cat in category_totals]
    
    return render_template('budgets.html',
                         budgets=budgets,
                         categories=categories,
                         total_budget=total_budget,
                         available_budget=available_budget,
                         total_spent=total_spent,
                         active_budgets_count=active_budgets_count,
                         budget_labels=budget_labels,
                         budget_amounts=budget_amounts,
                         spent_amounts=spent_amounts,
                         category_labels=category_labels,
                         category_amounts=category_amounts)
@app.route('/reports')
@login_required
def reports():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    period = request.args.get('period', 'month')  # default to month
    account_id = request.args.get('account_id')
    category_id = request.args.get('category_id')
    
    # Initialize variables
    transactions = []
    total_income = 0
    total_expenses = 0
    net_change = 0
    average_transaction = 0
    trend_data = {'labels': [], 'income': [], 'expenses': []}
    category_data = {'labels': [], 'values': []}
    balance_data = {'labels': [], 'values': []}
    account_data = {'labels': [], 'values': []}

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Build base query
        query = Transaction.query.join(Account).filter(
            Account.user_id == current_user.id,
            Transaction.date.between(start_date, end_date)
        )

        # Apply additional filters
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        # Get transactions
        transactions = query.order_by(Transaction.date).all()

        if transactions:
            # Calculate summary statistics
            total_income = sum(t.amount for t in transactions if t.type == 'income')
            total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
            net_change = total_income - total_expenses
            average_transaction = (total_income + total_expenses) / len(transactions)

            # Prepare trend data (income vs expenses over time)
            dates = sorted(set(t.date.date() for t in transactions))
            for date in dates:
                day_transactions = [t for t in transactions if t.date.date() == date]
                trend_data['labels'].append(date.strftime('%Y-%m-%d'))
                trend_data['income'].append(sum(t.amount for t in day_transactions if t.type == 'income'))
                trend_data['expenses'].append(sum(t.amount for t in day_transactions if t.type == 'expense'))

            # Prepare category distribution data
            category_totals = {}
            for t in transactions:
                if t.type == 'expense':  # Only showing expenses in category chart
                    cat_name = t.category.name
                    if cat_name not in category_totals:
                        category_totals[cat_name] = 0
                    category_totals[cat_name] += t.amount
            
            category_data['labels'] = list(category_totals.keys())
            category_data['values'] = list(category_totals.values())

            # Prepare daily balance trend
            running_balance = 0
            balance_by_date = {}
            for date in dates:
                day_transactions = [t for t in transactions if t.date.date() == date]
                for t in day_transactions:
                    if t.type == 'income':
                        running_balance += t.amount
                    else:
                        running_balance -= t.amount
                balance_by_date[date] = running_balance

            balance_data['labels'] = [date.strftime('%Y-%m-%d') for date in dates]
            balance_data['values'] = list(balance_by_date.values())

            # Prepare account distribution data
            account_totals = {}
            for t in transactions:
                acc_name = t.account.name
                if acc_name not in account_totals:
                    account_totals[acc_name] = 0
                account_totals[acc_name] += 1  # Counting number of transactions

            account_data['labels'] = list(account_totals.keys())
            account_data['values'] = list(account_totals.values())

    # Get all accounts and categories for filters
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()

    selected_account_id = int(account_id) if account_id else None
    selected_category_id = int(category_id) if category_id else None

    return render_template('reports.html',
                         transactions=transactions,
                         start_date=start_date if start_date else datetime.now(),
                         end_date=end_date if end_date else datetime.now(),
                         period=period,
                         accounts=accounts,
                         categories=categories,
                         selected_account_id=selected_account_id,
                         selected_category_id=selected_category_id,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_change=net_change,
                         average_transaction=average_transaction,
                         trend_data=trend_data,
                         category_data=category_data,
                         balance_data=balance_data,
                         account_data=account_data)
    return render_template('reports.html')

def check_budget_limits(category_id, transaction_type, amount):
    if transaction_type == 'expense':
        current_date = datetime.utcnow()
        budget = Budget.query.filter(
            Budget.category_id == category_id,
            Budget.start_date <= current_date,
            Budget.end_date >= current_date
        ).first()
        
        if budget:
            # Calculate total expenses for this category in the budget period
            total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.category_id == category_id,
                Transaction.type == 'expense',
                Transaction.date.between(budget.start_date, budget.end_date)
            ).scalar() or 0
            
            total_expenses += amount
            
            if total_expenses > budget.amount:
                flash(f'Budget limit exceeded for category {budget.category.name}!', 'warning')
@app.route('/generate-pdf-report')
@login_required
def generate_pdf_report():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id')
    category_id = request.args.get('category_id')

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Build query
        query = Transaction.query.join(Account).filter(
            Account.user_id == current_user.id,
            Transaction.date.between(start_date, end_date)
        )

        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        transactions = query.order_by(Transaction.date).all()

        # Calculate summaries
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        net_change = total_income - total_expenses
        average_transaction = (total_income + total_expenses) / len(transactions) if transactions else 0

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']

        # Create content
        elements = []

        # Title
        elements.append(Paragraph(f"Financial Report", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", normal_style))
        elements.append(Spacer(1, 20))

        # Summary Table
        summary_data = [
            ['Summary', 'Amount'],
            ['Total Income', f"${total_income:.2f}"],
            ['Total Expenses', f"${total_expenses:.2f}"],
            ['Net Change', f"${net_change:.2f}"],
            ['Average Transaction', f"${average_transaction:.2f}"]
        ]

        summary_table = Table(summary_data, colWidths=[300, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Transactions Table
        elements.append(Paragraph("Transaction Details", heading_style))
        elements.append(Spacer(1, 20))

        # Table header
        transactions_data = [['Date', 'Description', 'Category', 'Account', 'Type', 'Amount']]
        
        # Add transaction rows
        for t in transactions:
            transactions_data.append([
                t.date.strftime('%Y-%m-%d'),
                t.description,
                t.category.name,
                t.account.name,
                t.type,
                f"${t.amount:.2f}"
            ])

        # Create table
        transactions_table = Table(transactions_data, colWidths=[80, 100, 80, 80, 70, 70])
        transactions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT')
        ]))
        elements.append(transactions_table)

        # Build PDF
        doc.build(elements)

        # Prepare response
        buffer.seek(0)
        filename = f"financial_report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.pdf"

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    flash('Please select a date range to generate the report.', 'warning')
    return redirect(url_for('reports'))
# API Routes for AJAX calls
@app.route('/api/transactions/search')
@login_required
def search_transactions():
    search_term = request.args.get('term', '')
    transactions = Transaction.query.join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.description.ilike(f'%{search_term}%')
    ).order_by(Transaction.date.desc()).all()
    
    return jsonify([{
        'id': t.id,
        'date': t.date.strftime('%Y-%m-%d'),
        'description': t.description,
        'amount': t.amount,
        'type': t.type,
        'account': t.account.name,
        'category': t.category.name
    } for t in transactions])

@app.route('/api/transactions/<int:transaction_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_transaction(transaction_id):
    # First verify the transaction belongs to the current user
    transaction = Transaction.query.join(Account).filter(
        Transaction.id == transaction_id,
        Account.user_id == current_user.id
    ).first_or_404()
    
    if request.method == 'GET':
        return jsonify({
            'id': transaction.id,
            'type': transaction.type,
            'amount': float(transaction.amount),
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'account_id': transaction.account_id,
            'category_id': transaction.category_id
        })
    
    elif request.method == 'DELETE':
        try:
            # Reverse the balance change
            if transaction.type == 'expense':
                transaction.account.balance += transaction.amount
            else:
                transaction.account.balance -= transaction.amount
                
            db.session.delete(transaction)
            db.session.commit()
            return jsonify({'message': 'Transaction deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            old_amount = transaction.amount
            old_type = transaction.type
            old_account = transaction.account
            
            # Get the new values
            new_amount = float(request.form.get('amount'))
            new_type = request.form.get('type')
            new_account_id = int(request.form.get('account_id'))
            new_category_id = int(request.form.get('category_id'))
            new_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            
            # If account is changing, verify new account belongs to user
            if new_account_id != transaction.account_id:
                new_account = Account.query.filter_by(
                    id=new_account_id, 
                    user_id=current_user.id
                ).first_or_404()
            else:
                new_account = old_account
            
            # Revert old transaction's effect on balance
            if old_type == 'expense':
                old_account.balance += old_amount
            else:
                old_account.balance -= old_amount
            
            # Apply new transaction's effect on balance
            if new_type == 'expense':
                if new_account.balance < new_amount:
                    return jsonify({'error': 'Insufficient funds'}), 400
                new_account.balance -= new_amount
            else:
                new_account.balance += new_amount
            
            # Update transaction details
            transaction.amount = new_amount
            transaction.type = new_type
            transaction.description = request.form.get('description')
            transaction.category_id = new_category_id
            transaction.account_id = new_account_id
            transaction.date = new_date
            
            db.session.commit()
            return jsonify({'message': 'Transaction updated successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_category(category_id):
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first_or_404()
    
    if request.method == 'DELETE':
        # Check if category has transactions
        if category.transactions:
            return jsonify({
                'error': 'Cannot delete category with transactions'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': 'Category deleted successfully'})
    
    elif request.method == 'PUT':
        category.name = request.form.get('name')
        db.session.commit()
        return jsonify({'message': 'Category updated successfully'})

@app.route('/api/budgets/<int:budget_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()
    
    if request.method == 'GET':
        return jsonify({
            'id': budget.id,
            'amount': budget.amount,
            'category_id': budget.category_id,
            'start_date': budget.start_date.strftime('%Y-%m-%d'),
            'end_date': budget.end_date.strftime('%Y-%m-%d')
        })
    
    elif request.method == 'DELETE':
        db.session.delete(budget)
        db.session.commit()
        return jsonify({'message': 'Budget deleted successfully'})
    
    elif request.method == 'PUT':
        budget.amount = float(request.form.get('amount'))
        budget.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        budget.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        db.session.commit()
        return jsonify({'message': 'Budget updated successfully'})

@app.route('/api/accounts/<int:account_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_account(account_id):
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()
    
    if request.method == 'DELETE':
        # Check if account has transactions
        if account.transactions:
            return jsonify({
                'error': 'Cannot delete account with transactions'
            }), 400
        
        db.session.delete(account)
        db.session.commit()
        return jsonify({'message': 'Account deleted successfully'})
    
    elif request.method == 'PUT':
        account.name = request.form.get('name')
        db.session.commit()
        return jsonify({'message': 'Account updated successfully'})

@app.route('/api/dashboard/chart-data')
@login_required
def dashboard_chart_data():
    period = request.args.get('period', 'weekly')
    today = datetime.utcnow()
    
    # Calculate date ranges
    if period == 'weekly':
        start_date = today - timedelta(days=7)
        date_format = '%Y-%m-%d'
        group_by = func.date(Transaction.date)
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
        date_format = '%Y-%m-%d'
        group_by = func.date(Transaction.date)
    else:  # yearly
        start_date = today - timedelta(days=365)
        date_format = '%Y-%m'
        group_by = func.strftime('%Y-%m', Transaction.date)

    # Query transactions
    transactions = db.session.query(
        group_by.label('date'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= today
    ).group_by('date', Transaction.type).all()

    # Process the data
    date_dict = {}
    
    # Initialize all dates in the range with zero values
    current_date = start_date
    while current_date <= today:
        if period == 'yearly':
            date_str = current_date.strftime(date_format)
        else:
            date_str = current_date.strftime(date_format)
            
        date_dict[date_str] = {'income': 0, 'expense': 0}
        
        if period == 'yearly':
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        else:
            current_date += timedelta(days=1)

    # Fill in actual values
    for t in transactions:
        if period == 'yearly':
            date_str = t.date
        else:
            date_str = t.date.strftime(date_format) if isinstance(t.date, datetime) else t.date
            
        if date_str in date_dict:
            date_dict[date_str][t.type] = float(t.total)

    # Sort dates and prepare response data
    sorted_dates = sorted(date_dict.keys())
    
    response_data = {
        'labels': sorted_dates,
        'income': [date_dict[date]['income'] for date in sorted_dates],
        'expenses': [date_dict[date]['expense'] for date in sorted_dates]
    }

    return jsonify(response_data)

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Context Processors
@app.context_processor
def utility_processor():
    def get_budget_progress(category_id):
        current_date = datetime.utcnow()
        budget = Budget.query.filter(
            Budget.category_id == category_id,
            Budget.start_date <= current_date,
            Budget.end_date >= current_date
        ).first()
        
        if not budget:
            return None
            
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == category_id,
            Transaction.type == 'expense',
            Transaction.date.between(budget.start_date, budget.end_date)
        ).scalar() or 0
        
        return {
            'amount': budget.amount,
            'spent': spent,
            'percentage': (spent / budget.amount * 100) if budget.amount > 0 else 0
        }
    
    return dict(get_budget_progress=get_budget_progress)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)