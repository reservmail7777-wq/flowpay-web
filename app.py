import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text # Добавлено для выполнения SQL-запросов

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

# --- ИНИЦИАЛИЗАЦИЯ И АВТО-МИГРАЦИЯ ---
with app.app_context():
    db.create_all()
    # Этот блок проверяет наличие колонок и добавляет их, если их нет (решает ошибку 500 на Render)
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS commission_in VARCHAR(20) DEFAULT \'5.7%\''))
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS commission_out VARCHAR(20) DEFAULT \'2.0%\''))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Migration notice: {e}")

# --- АДМИН-МАРШРУТ ---
@app.route('/admin-create-user', methods=['GET', 'POST'])
def admin_create_user():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        c_in = request.form.get('currency_in', 'UAH')
        c_out = request.form.get('currency_out', 'UAH')
        b_usdt = float(request.form.get('balance_usdt') or 0.0)
        b_fiat = float(request.form.get('balance_fiat') or 0.0)
        comm_in = request.form.get('comm_in') or "5.7%"
        comm_out = request.form.get('comm_out') or "2.0%"

        if User.query.filter_by(email=email).first():
            message = "Ошибка: Пользователь с такой почтой уже существует!"
        else:
            new_user = User(
                email=email, password=password, 
                currency_in=c_in, currency_out=c_out,
                balance_usdt=b_usdt, balance_uah=b_fiat,
                commission_in=comm_in, commission_out=comm_out
            )
            db.session.add(new_user)
            db.session.commit()
            message = f"Успех! Пользователь {email} создан."
    
    currencies = ['UAH', 'RUB', 'KGS', 'TJS', 'KZT', 'AED', 'USD', 'EUR']
    options = "".join([f'<option value="{c}">{c}</option>' for c in currencies])

    return f'''
        <div style="max-width: 500px; margin: 40px auto; font-family: sans-serif; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background: #fdfdfd;">
            <h2 style="text-align: center;">Регистрация пользователя</h2>
            {f'<p style="color: white; background: #28a745; padding: 10px; border-radius: 5px; text-align: center;">{message}</p>' if message else ''}
            <form method="post">
                <label>Email:</label><input type="email" name="email" required style="width:100%; padding:10px; margin-bottom:15px; border: 1px solid #ccc; border-radius: 5px;">
                <label>Пароль:</label><input type="text" name="password" required style="width:100%; padding:10px; margin-bottom:15px; border: 1px solid #ccc; border-radius: 5px;">
                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <div style="flex: 1;"><label>Комиссия PayIn:</label><input type="text" name="comm_in" placeholder="5.7%" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;"></div>
                    <div style="flex: 1;"><label>Комиссия PayOut:</label><input type="text" name="comm_out" placeholder="2.0%" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;"></div>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <div style="flex: 1;"><label>Баланс USDT:</label><input type="number" step="0.01" name="balance_usdt" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;"></div>
                    <div style="flex: 1;"><label>Баланс Фиат:</label><input type="number" step="0.01" name="balance_fiat" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;"></div>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <div style="flex: 1;"><label>Валюта In:</label><select name="currency_in" style="width:100%; padding:10px;">{options}<option value="USDT">USDT</option></select></div>
                    <div style="flex: 1;"><label>Валюта Out:</label><select name="currency_out" style="width:100%; padding:10px;">{options}</select></div>
                </div>
                <button type="submit" style="width:100%; padding:12px; background: #007bff; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">СОЗДАТЬ АККАУНТ</button>
            </form>
        </div>
    '''

# --- ОСТАЛЬНЫЕ МАРШРУТЫ ---
@app.route('/')
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        error = "Неверная почта или пароль"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        user.currency_in = request.form.get('base_currency_in')
        user.currency_out = request.form.get('base_currency_out')
        db.session.commit()
        return redirect(url_for('settings'))
    commissions = {'in': user.commission_in, 'out': user.commission_out}
    return render_template('settings.html', user=user, commissions=commissions)

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST' and request.form.get('amount'):
        db.session.add(DepositRequest(user_id=user.id, amount=float(request.form.get('amount'))))
        db.session.commit()
        return redirect(url_for('balance'))
    history = DepositRequest.query.filter_by(user_id=user.id).order_by(DepositRequest.id.desc()).all()
    return render_template('balance.html', user=user, history=history)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)