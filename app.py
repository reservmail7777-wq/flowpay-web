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

# --- АДМИН-ПАНЕЛЬ: СПИСОК И УДАЛЕНИЕ ---
@app.route('/admin-users')
def admin_list_users():
    users = User.query.all()
    rows = ""
    for u in users:
        rows += f'''
        <tr>
            <td style="padding:12px; border-bottom:1px solid #eee;">{u.id}</td>
            <td style="padding:12px; border-bottom:1px solid #eee;"><b>{u.email}</b></td>
            <td style="padding:12px; border-bottom:1px solid #eee;">{u.balance_usdt} USDT / {u.balance_uah} Fiat</td>
            <td style="padding:12px; border-bottom:1px solid #eee;">
                <a href="/admin/delete-user/{u.id}" 
                   onclick="return confirm('Вы уверены, что хотите удалить {u.email}?')" 
                   style="color: #d9534f; text-decoration: none; font-weight: bold;">Удалить</a>
            </td>
        </tr>
        '''
    return f'''
        <div style="max-width: 900px; margin: 50px auto; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>Управление пользователями</h2>
                <a href="/admin-create-user" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">+ Создать пользователя</a>
            </div>
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <thead style="background: #f8f9fa;">
                    <tr>
                        <th style="padding:15px; text-align: left;">ID</th>
                        <th style="padding:15px; text-align: left;">Email</th>
                        <th style="padding:15px; text-align: left;">Балансы</th>
                        <th style="padding:15px; text-align: left;">Действие</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="margin-top: 20px;"><a href="/" style="color: #666;">← На главную</a></p>
        </div>
    '''

@app.route('/admin/delete-user/<int:user_id>')
def delete_user(user_id):
    user_to_delete = db.session.get(User, user_id)
    if user_to_delete:
        DepositRequest.query.filter_by(user_id=user_id).delete()
        db.session.delete(user_to_delete)
        db.session.commit()
    return redirect(url_for('admin_list_users'))

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
            return redirect(url_for('admin_list_users'))
    
    currencies = ['UAH', 'RUB', 'KGS', 'TJS', 'KZT', 'AED', 'USD', 'EUR']
    options = "".join([f'<option value="{c}">{c}</option>' for c in currencies])
    return f'''
        <div style="max-width: 500px; margin: 40px auto; font-family: sans-serif; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background: #fdfdfd; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2 style="text-align:center;">Регистрация</h2>{f'<p style="color:red;text-align:center;">{message}</p>' if message else ''}
            <form method="post">
                Email: <input type="email" name="email" required style="width:100%; padding:10px; margin-bottom:15px; border:1px solid #ccc; border-radius:5px;">
                Pass: <input type="text" name="password" required style="width:100%; padding:10px; margin-bottom:15px; border:1px solid #ccc; border-radius:5px;">
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <input type="text" name="comm_in" placeholder="In % (5.7%)" style="flex:1; padding:10px;">
                    <input type="text" name="comm_out" placeholder="Out % (2.0%)" style="flex:1; padding:10px;">
                </div>
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <input type="number" step="0.01" name="balance_usdt" placeholder="USDT" style="flex:1; padding:10px;">
                    <input type="number" step="0.01" name="balance_fiat" placeholder="Fiat" style="flex:1; padding:10px;">
                </div>
                <div style="display:flex; gap:10px; margin-bottom:20px;">
                    <select name="currency_in" style="flex:1; padding:10px;">{options}<option value="USDT">USDT</option></select>
                    <select name="currency_out" style="flex:1; padding:10px;">{options}</select>
                </div>
                <button type="submit" style="width:100%; padding:12px; background:#007bff; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">СОЗДАТЬ И ВЕРНУТЬСЯ</button>
            </form>
            <p style="text-align:center; margin-top:15px;"><a href="/admin-users" style="color:#666; text-decoration:none;">← К списку пользователей</a></p>
        </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)