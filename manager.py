from app import app, db, User
import sys

def add_user():
    email = input("Введите Email пользователя: ")
    password = input("Введите Пароль: ")
    b_usdt = float(input("Введите баланс USDT (например, 100.50): ") or 0)
    b_uah = float(input("Введите баланс UAH: ") or 0)

    with app.app_context():
        # Проверяем, нет ли такого юзера
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"Ошибка: Пользователь {email} уже существует!")
            return

        new_user = User(
            email=email, 
            password=password, 
            balance_usdt=b_usdt, 
            balance_uah=b_uah
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"\n--- УСПЕХ ---")
        print(f"Пользователь {email} добавлен в базу данных.")

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\nСписок всех пользователей в базе:")
        print("-" * 50)
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Pass: {u.password} | USDT: {u.balance_usdt}")
        print("-" * 50)

if __name__ == "__main__":
    print("1. Добавить пользователя")
    print("2. Показать список пользователей")
    choice = input("Выберите действие: ")
    
    if choice == "1":
        add_user()
    elif choice == "2":
        list_users()
    else:
        print("Отмена.")