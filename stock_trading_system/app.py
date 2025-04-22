from flask import Flask, flash, render_template, redirect, request, url_for
from database import db
from models import User, Stock, Transaction, Order, PriceHistory, MarketHours, Holiday
from price_generator import update_stock_price
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, time, date
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock_trading.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret'
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    # Create admin user if not exists.
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            full_name="Administrator",
            username="admin",
            email="admin@example.com",
            password=generate_password_hash("yourpassword"),
            cash=10000
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route('/')
def index():
    stocks = Stock.query.all()
    schedule = MarketHours.query.all()
    holidays = Holiday.query.all()
    chart_stock = stocks[0] if stocks else None
    labels = []
    data_points = []
    #date and time
    now = datetime.now()
    date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
    if chart_stock:
        # Fetch the price history for the selected stock, ordered by timestamp.
        history = PriceHistory.query.filter_by(stock_id=chart_stock.id).order_by(PriceHistory.timestamp).all()
        for record in history:
            # Format timestamp as HH:mm (you can adjust the format as needed)
            labels.append(record.timestamp.strftime('%H:%M'))
            data_points.append(record.price)
    return render_template('index.html', date_time=date_time, stocks=stocks, chart_stock=chart_stock, labels=labels, data_points=data_points, schedule = schedule, holidays=holidays)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        new_user = User(
            full_name=request.form['full_name'],
            username=request.form['username'],
            email=request.form['email'],
            password=hashed_password,
            cash=10000
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/portfolio')
@login_required
def portfolio():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    orders = Order.query.filter_by(user_id=current_user.id, status='pending').all()
    #date and time
    now = datetime.now()
    date_time = now.strftime("%d/%m/%Y, %H:%M:%S")

    holdings_dict = {}
    for txn in transactions:
        stock = Stock.query.get(txn.stock_id)
        if stock:
            holdings_dict.setdefault(stock.id, {'ticker': stock.ticker, 'quantity': 0})
            if txn.type == 'buy':
                holdings_dict[stock.id]['quantity'] += txn.quantity
            elif txn.type == 'sell':
                holdings_dict[stock.id]['quantity'] -= txn.quantity
                
    portfolio_holdings = []
    for stock_id, data in holdings_dict.items():
        if data['quantity'] > 0:
            portfolio_holdings.append({
                'id': stock_id,
                'ticker': data['ticker'],
                'quantity': data['quantity']
            })
            
    return render_template('portfolio.html',
                           transactions=transactions,
                           orders=orders,
                           cash=current_user.cash,
                           portfolio=portfolio_holdings, date_time=date_time)

def is_market_open():
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    day_of_week_now = now.weekday()
    schedule = MarketHours.query.filter_by(day_of_week=day_of_week_now).first()
    holiday = Holiday.query.filter_by(holiday_date=today).first()
   
    if holiday:
        return False
    
    #default schedule
    if schedule:
        if schedule.opening_time <= current_time <= schedule.closing_time:
            return True
    elif 0 <= day_of_week_now <= 4:
        if time(8, 0) <= current_time <= time(20, 0):
            return True
    return False

@app.route('/buy', methods=['POST'])
@login_required
def buy():
    if is_market_open():
        stock = Stock.query.filter_by(id=request.form['stock_id']).first()
        quantity = int(request.form['quantity'])
        cost = stock.current_price * quantity
        if current_user.cash >= cost:
            current_user.cash -= cost
            order = Order(user_id=current_user.id, stock_id=stock.id, quantity=quantity, type='buy', status='executed')
            db.session.add(order)
            transaction = Transaction(user_id=current_user.id, stock_id=stock.id, quantity=quantity, price=stock.current_price, type='buy')
            db.session.add(transaction)
            db.session.commit()
        return redirect(url_for('portfolio'))
    else:
        flash('It is not market hours.', 'error')
        return redirect(url_for('index'))

@app.route('/sell', methods=['POST'])
@login_required
def sell():
    if is_market_open():
        stock = Stock.query.filter_by(id=request.form['stock_id']).first()
        quantity = int(request.form['quantity'])
        order = Order(user_id=current_user.id, stock_id=stock.id, quantity=quantity, type='sell', status='executed')
        db.session.add(order)
        transaction = Transaction(user_id=current_user.id, stock_id=stock.id, quantity=quantity, price=stock.current_price, type='sell')
        current_user.cash += stock.current_price * quantity
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('portfolio'))
    else:
        flash('It is not market hours.', 'error')
        return redirect(url_for('index'))

#deposit
@app.route('/deposit', methods=['POST'])
@login_required
def deposit():
    amount = float(request.form['amount'])
    if request.method == 'POST':
        current_user.cash = current_user.cash + amount
        db.session.commit()
        flash('Successfully deposited!', 'success')
        return redirect(url_for('portfolio'))
    else:
        flash('There was an error with your deposit.', 'error')
        return redirect(url_for('portfolio'))

#withdraw
@app.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form['amount'])
    if amount > current_user.cash:
        flash('Insufficient Funds.', 'error')
        return redirect(url_for('portfolio'))
    elif amount < current_user.cash:
        flash('Successfully withdrawn!', 'success')
        current_user.cash = current_user.cash - amount
        db.session.commit()
        return redirect(url_for('portfolio'))
    else:
        return redirect(url_for('portfolio'))

@app.route('/cancel_order/<int:order_id>')
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id, status='pending').first()
    if order:
        order.status = 'cancelled'
        db.session.commit()
    return redirect(url_for('portfolio'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    stocks = Stock.query.all()
    schedule = MarketHours.query.all()
    holidays= Holiday.query.all()
    return render_template('admin_dashboard.html', stocks=stocks, schedule=schedule, holidays=holidays)

@app.route('/admin/create_stock', methods=['GET', 'POST'])
@login_required
def create_stock():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        stock = Stock(
            company_name=request.form['company_name'],
            ticker=request.form['ticker'],
            volume=int(request.form['volume']),
            initial_price=float(request.form['initial_price']),
            current_price=float(request.form['initial_price']),
            opening_price=float(request.form['initial_price']),
            high=float(request.form['initial_price']),
            low=float(request.form['initial_price'])
        )
        db.session.add(stock)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('create_stock.html')

@app.route('/admin/remove_stock/<int:stock_id>', methods=['POST'])
@login_required
def remove_stock(stock_id):
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    stock = Stock.query.get(stock_id)
    if stock:
        db.session.delete(stock)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_hours/<int:id>', methods=['POST'])
def delete_hours(id):
     hours = MarketHours.query.get_or_404(id)
     if hours:
        db.session.delete(hours)
        db.session.commit()
     return redirect(url_for('admin_dashboard'))

@app.route('/delete_holiday/<int:id>', methods=['POST'])
def delete_holiday(id):
     day = Holiday.query.get_or_404(id)
     if day:
        db.session.delete(day)
        db.session.commit()
     return redirect(url_for('admin_dashboard'))

@app.route('/update_prices')
def update_prices():
    stocks = Stock.query.all()
    for stock in stocks:
        update_stock_price(stock)
    db.session.commit()
    return redirect(url_for('index'))

#market hours function
@app.route('/admin/hours', methods=['GET', 'POST'])
@login_required
def hours():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        day = int(request.form['day_of_week1'])
        open = request.form['opening_time1']
        close = request.form['closing_time1']
        open_time = datetime.strptime(open, '%H:%M:%s').time()
        close_time = datetime.strptime(close, '%H:%M:%s').time()

        new_schedule = MarketHours(day_of_week=day, opening_time=open_time, closing_time=close_time)
        db.session.add(new_schedule)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    schedule = MarketHours.query.all()
    return render_template('admin_dashboard.html', schedule=schedule)

#market holidays function
@app.route('/admin/add_holiday', methods=['GET', 'POST'])
@login_required
def add_holiday():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['holiday_name']
        date_st = request.form['holiday_date']
        date_object = datetime.strptime(date_st, '%Y-%m-%d').date()
        new_holiday = Holiday(holiday_date=date_object, holiday_name=name)
        db.session.add(new_holiday)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    holidays = Holiday.query.all()
    return render_template('admin_dashboard.html', holidays=holidays)

if __name__ == '__main__':
    app.run(debug=True)
