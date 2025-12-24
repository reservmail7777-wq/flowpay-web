import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this'

# --- НАСТРОЙКА БАЗЫ ДАННЫХ (SQLite для Mac, PostgreSQL для Render) ---
# Render предоставляет URL базы через переменную DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    # Фикс для SQLAlchemy, так как Render дает префикс postgres://, а нужно postgresql://
    database_url = database_url.replace("postgres://", "postgresql://", 1)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or ('sqlite:///' + os.path.join(basedir, 'database.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False) # В будущем лучше хэшировать
    balance_usdt = db.Column(db.Float, default=0.0)
    balance_uah = db.Column(db.Float, default=0.0)
    currency_in = db.Column(db.String(10), default='UAH')
    currency_out = db.Column(db.String(10), default='UAH')

class DepositRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), default='24.12.2025')
    wallet = db.Column(db.String(120), default='0x09E99EBCee0344FC2C8BE6D03760e4BDeE643C90')
    status = db.Column(db.String(50), default='Ожидается подтверждение платежа')

# Инициализация базы данных
with app.app_context():
    db.create_all()

# --- СЕКРЕТНЫЙ МАРШРУТ ДЛЯ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ---
@app.route('/admin-create-user', methods=['GET', 'POST'])
def admin_create_user():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username') # В модели User нет username, но можно использовать для логов

        if User.query.filter_by(email=email).first():
            message = "Ошибка: Пользователь с такой почтой уже существует!"
        else:
            new_user = User(email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            message = f"Успех! Пользователь {email} создан. Можете передать ему пароль."
    
    return f'''
        <div style="max-width: 400px; margin: 50px auto; font-family: sans-serif;">
            <h2>Добавить пользователя</h2>
            {f'<p style="color: green;">{message}</p>' if message else ''}
            <form method="post">
                <input type="email" name="email" placeholder="Email (Логин)" required style="width:100%; padding:10px; margin-bottom:10px;"><br>
                <input type="text" name="password" placeholder="Пароль" required style="width:100%; padding:10px; margin-bottom:10px;"><br>
                <button type="submit" style="width:100%; padding:10px; cursor:pointer;">Создать аккаунт</button>
            </form>
            <br><a href="/">На главную</a>
        </div>
    '''

# --- ОСНОВНЫЕ МАРШРУТЫ ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        error = "Неверная почта или пароль"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=user)

@app.route('/wallets')
def wallets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('wallets.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        user.currency_in = request.form.get('base_currency_in')
        user.currency_out = request.form.get('base_currency_out')
        db.session.commit()
        return redirect(url_for('settings'))

    commissions = {'in': '5.7%', 'out': '2.0%'}
    return render_template('settings.html', user=user, commissions=commissions)

@app.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('sales.html', user=user)

@app.route('/buy')
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('buy.html', user=user)

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        amount_val = request.form.get('amount')
        if amount_val:
            amount = float(amount_val)
            if amount >= 500:
                new_request = DepositRequest(user_id=user.id, amount=amount)
                db.session.add(new_request)
                db.session.commit()
        return redirect(url_for('balance'))

    history = DepositRequest.query.filter_by(user_id=user.id).order_by(DepositRequest.id.desc()).all()
    
    deposit_info = {
        'address': 'TRrqqVmgoRhiRPaGUPgtZcWKeDCGLjyy9Y',
        'network': 'Сеть TRC 20',
        'limit': '500 USDT'
    }
    
    return render_template('balance.html', user=user, info=deposit_info, history=history)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('history.html', user=user)

@app.route('/disputes')
def disputes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('disputes.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # На Render порт задается через переменную PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)