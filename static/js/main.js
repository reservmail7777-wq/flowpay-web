/**
 * main.js - Логика управления интерфейсом FlowPay
 */

// 1. Открытие модального окна
function openModal() {
    const modal = document.getElementById('walletModal');
    if (modal) {
        modal.style.display = 'flex';
        // На случай если до этого выводилась ошибка, сбрасываем контент окна
        resetModalContent();
    }
}

// 2. Закрытие модального окна
function closeModal() {
    const modal = document.getElementById('walletModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 3. Логика "Сохранения" с проверкой депозита
function saveWallet() {
    const modalBody = document.querySelector('.modal-body');
    const modalFooter = document.querySelector('.modal-footer');
    
    // Эффект тряски окна при ошибке
    const modalWindow = document.querySelector('.modal-window');
    modalWindow.classList.add('shake-animation');
    
    // Удаляем класс анимации через 0.4с, чтобы можно было повторить
    setTimeout(() => {
        modalWindow.classList.remove('shake-animation');
    }, 400);

    // Заменяем содержимое формы на сообщение об ошибке
    modalBody.innerHTML = `
        <div class="error-container" style="text-align: center; padding: 30px 10px;">
            <div style="font-size: 50px; margin-bottom: 20px;">⚠️</div>
            <h3 style="color: #ff4d4f; margin-bottom: 15px; font-weight: 700;">ДОСТУП ОГРАНИЧЕН</h3>
            <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 25px;">
                Для добавления платежных реквизитов необходимо внести <br> 
                <span style="color: #fff; font-weight: 600;">страховой депозит</span> в размере <span style="color: #fff; font-weight: 600;">500 USDT</span>.
            </p>
            <button onclick="closeModal()" class="btn-save" style="width: 100%; max-width: 200px;">ПОНЯТНО</button>
        </div>
    `;

    // Скрываем стандартный футер с кнопками, так как теперь есть кнопка "Понятно"
    if (modalFooter) {
        modalFooter.style.display = 'none';
    }
}

// 4. Сброс формы к исходному состоянию (чтобы ошибка не висела вечно)
function resetModalContent() {
    const modalFooter = document.querySelector('.modal-footer');
    const modalBody = document.querySelector('.modal-body');
    
    // Возвращаем футер, если он был скрыт
    if (modalFooter) {
        modalFooter.style.display = 'grid';
    }
    
    // Если нужно, чтобы при повторном открытии форма снова была доступна, 
    // здесь можно было бы восстановить innerHTML формы.
    // Но сейчас, после ошибки, проще закрыть и открыть заново.
}