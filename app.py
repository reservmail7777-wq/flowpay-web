import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance_usdt = db.Column(db.Float, default=0.0)
    balance_uah = db.Column(db.Float, default=0.0)
    currency_in = db.Column(db.String(10), default='UAH')
    currency_out = db.Column(db.String(10), default='UAH')

class DepositRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), default='24.12.2025')
    wallet = db.Column(db.String(120), default='TRrqqVmgoRhiRPaGUPgtZcWKeDCGLjyy9Y')
    status = db.Column(db.String(50), default='Ожидается подтверждение платежа')

# После добавления модели выполните в консоли:
# with app.app_context():
#     db.create_all()

with app.app_context():
    db.create_all()

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
    
    # 1. ОБРАБОТКА НАЖАТИЯ "ПОДТВЕРДИТЬ"
    if request.method == 'POST':
        amount_val = request.form.get('amount')
        if amount_val:
            amount = float(amount_val)
            if amount >= 500:
                # Создаем новую запись в базе
                new_request = DepositRequest(user_id=user.id, amount=amount)
                db.session.add(new_request)
                db.session.commit()
        return redirect(url_for('balance')) # Перезагружаем страницу, чтобы увидеть новую строку

    # 2. ОТОБРАЖЕНИЕ СТРАНИЦЫ
    # Загружаем из базы все заявки текущего пользователя
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
    app.run(debug=True)