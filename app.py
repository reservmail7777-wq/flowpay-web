import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this'

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or ('sqlite:///' + os.path.join(basedir, 'database.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance_usdt = db.Column(db.Float, default=0.0)
    balance_uah = db.Column(db.Float, default=0.0)
    currency_in = db.Column(db.String(10), default='UAH')
    currency_out = db.Column(db.String(10), default='UAH')
    commission_in = db.Column(db.String(20), default='5.7%')
    commission_out = db.Column(db.String(20), default='2.0%')

class DepositRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), default='06.01.2026')
    wallet = db.Column(db.String(120), default='0x09E99EBCee0344FC2C8BE6D03760e4BDeE643C90')
    status = db.Column(db.String(50), default='Ожидается подтверждение платежа')

# --- ИНИЦИАЛИЗАЦИЯ И ИСПРАВЛЕНИЕ БАЗЫ ---
with app.app_context():
    db.create_all()
    try:
        # Добавляем колонки, если их нет (исправляет ошибку из вашего лога)
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS commission_in VARCHAR(20) DEFAULT \'5.7%\''))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS commission_out VARCHAR(20) DEFAULT \'2.0%\''))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Database update notice: {e}")

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ---
def get_current_user():
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

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
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('dashboard.html', user=user)

@app.route('/wallets')
def wallets():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('wallets.html', user=user)

@app.route('/history')
def history():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('history.html', user=user)

@app.route('/sales')
def sales():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('sales.html', user=user)

@app.route('/buy')
def buy():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('buy.html', user=user)

@app.route('/disputes')
def disputes():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    return render_template('disputes.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    if request.method == 'POST':
        user.currency_in = request.form.get('base_currency_in')
        user.currency_out = request.form.get('base_currency_out')
        db.session.commit()
        return redirect(url_for('settings'))
    commissions = {'in': user.commission_in, 'out': user.commission_out}
    return render_template('settings.html', user=user, commissions=commissions)

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    if request.method == 'POST':
        amount = request.form.get('amount')
        if amount and float(amount) >= 500:
            db.session.add(DepositRequest(user_id=user.id, amount=float(amount)))
            db.session.commit()
        return redirect(url_for('balance'))
    history_list = DepositRequest.query.filter_by(user_id=user.id).order_by(DepositRequest.id.desc()).all()
    return render_template('balance.html', user=user, history=history_list)

@app.route('/admin-create-user', methods=['GET', 'POST'])
def admin_create_user():
    message = None
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        if User.query.filter_by(email=email).first():
            message = "Ошибка: Пользователь уже существует!"
        else:
            new_user = User(
                email=email, password=password,
                currency_in=request.form.get('currency_in', 'UAH'),
                currency_out=request.form.get('currency_out', 'UAH'),
                balance_usdt=float(request.form.get('balance_usdt') or 0.0),
                balance_uah=float(request.form.get('balance_fiat') or 0.0),
                commission_in=request.form.get('comm_in') or "5.7%",
                commission_out=request.form.get('comm_out') or "2.0%"
            )
            db.session.add(new_user)
            db.session.commit()
            message = f"Успех! Пользователь {email} создан."
    
    currencies = ['UAH', 'RUB', 'KGS', 'TJS', 'KZT', 'AED', 'USD', 'EUR']
    options = "".join([f'<option value="{c}">{c}</option>' for c in currencies])
    return f'''
        <div style="max-width: 500px; margin: 40px auto; font-family: sans-serif; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background: #fdfdfd;">
            <h2 style="text-align:center;">Регистрация</h2>{f'<p style="color:green;text-align:center;">{message}</p>' if message else ''}
            <form method="post">
                Email: <input type="email" name="email" required style="width:100%;margin-bottom:10px;">
                Pass: <input type="text" name="password" required style="width:100%;margin-bottom:10px;">
                <div style="display:flex;gap:10px;">
                    <input type="text" name="comm_in" placeholder="In % (5.7%)" style="flex:1;">
                    <input type="text" name="comm_out" placeholder="Out % (2.0%)" style="flex:1;">
                </div><br>
                <div style="display:flex;gap:10px;">
                    <input type="number" step="0.01" name="balance_usdt" placeholder="USDT" style="flex:1;">
                    <input type="number" step="0.01" name="balance_fiat" placeholder="Fiat" style="flex:1;">
                </div><br>
                <select name="currency_in">{options}<option value="USDT">USDT</option></select>
                <select name="currency_out">{options}</select><br><br>
                <button type="submit" style="width:100%;padding:10px;background:#007bff;color:white;border:none;">СОЗДАТЬ</button>
            </form>
        </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)