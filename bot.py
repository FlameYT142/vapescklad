import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import (
    BOT_TOKEN, EMPLOYEES, MANAGER_USERNAME,
    is_employee, is_owner, is_admin, get_employee_info, get_employee_name
)
from sheets import (
    get_all_products, get_product_by_name, get_product_by_row,
    add_product, update_product_quantity, increase_product_quantity, decrease_product_quantity,
    add_movement, get_movements,
    get_report_stock, get_report_sales_today, get_report_by_employee, get_report_revenue
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BRATSK_TZ = ZoneInfo("Asia/Irkutsk")

user_states = {}


# ============================================
# ГЛАВНОЕ МЕНЮ
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        await update.message.reply_text(
            "🏪 *VAPECITY*\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "⛔ *Доступ ограничен*\n\n"
            "Этот бот предназначен только для сотрудников склада.\n\n"
            "Если вы хотите приобрести товар — напишите нашему менеджеру:\n\n"
            f"👤 {MANAGER_USERNAME}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📞 Свяжитесь с менеджером для покупки",
            parse_mode='Markdown'
        )
        return
    
    info = get_employee_info(user_id)
    role_emoji = "👑" if info['role'] == 'owner' else "🛠️"
    role_name = "Владелец" if info['role'] == 'owner' else "Администратор"
    
    keyboard = [
        [KeyboardButton("📦 Остатки"), KeyboardButton("➕ Принять товар")],
        [KeyboardButton("➖ Оформить продажу"), KeyboardButton("📊 Отчёты")],
        [KeyboardButton("🔍 Инвентаризация")],
    ]
    
    if is_owner(user_id):
        keyboard.append([KeyboardButton("⚙️ Админ-панель")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🏪 *СКЛАД VAPECITY*\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {info['username']}\n"
        f"{role_emoji} {role_name}\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================
# 📦 ОСТАТКИ
# ============================================
async def show_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    report = get_report_stock()
    await update.message.reply_text(report, parse_mode='Markdown')


# ============================================
# ➕ ПРИНЯТЬ ТОВАР
# ============================================
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    products = get_all_products()
    
    keyboard = []
    for p in products[:20]:
        keyboard.append([InlineKeyboardButton(
            f"{p['name']} ({p['quantity']} шт.)",
            callback_data=f"add_existing_{p['row']}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Новый товар", callback_data="add_new")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    await update.message.reply_text(
        "➕ *ПРИНЯТЬ ТОВАР*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите товар из списка или создайте новый:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============================================
# ➖ ОФОРМИТЬ ПРОДАЖУ
# ============================================
async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    products = get_all_products()
    
    if not products:
        await update.message.reply_text("📭 Склад пуст. Нечего продавать.")
        return
    
    keyboard = []
    for p in products[:20]:
        if p['quantity'] > 0:
            keyboard.append([InlineKeyboardButton(
                f"{p['name']} ({p['quantity']} шт.) - {p['price']:.2f} ₽",
                callback_data=f"sell_product_{p['row']}"
            )])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    await update.message.reply_text(
        "➖ *ОФОРМИТЬ ПРОДАЖУ*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите товар:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============================================
# 📊 ОТЧЁТЫ
# ============================================
async def show_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("📦 Остатки", callback_data="report_stock")],
        [InlineKeyboardButton("📅 Продажи за сегодня", callback_data="report_today")],
        [InlineKeyboardButton("👥 По сотрудникам", callback_data="report_employees")],
        [InlineKeyboardButton("💰 Общая выручка", callback_data="report_revenue")],
    ]
    
    await update.message.reply_text(
        "📊 *ОТЧЁТЫ*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите отчёт:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============================================
# 🔍 ИНВЕНТАРИЗАЦИЯ
# ============================================
async def inventory_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    await update.message.reply_text(
        "🔍 *ИНВЕНТАРИЗАЦИЯ*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите название товара, который хотите пересчитать:",
        parse_mode='Markdown'
    )
    
    user_states[user_id] = {'state': 'inventory_wait_name'}


# ============================================
# ⚙️ АДМИН-ПАНЕЛЬ
# ============================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("⛔ Доступ только для владельца.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 Сотрудники", callback_data="admin_employees")],
        [InlineKeyboardButton("📊 Движения", callback_data="admin_movements")],
    ]
    
    await update.message.reply_text(
        "⚙️ *АДМИН-ПАНЕЛЬ*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============================================
# ОБРАБОТКА ТЕКСТА
# ============================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not is_employee(user_id):
        return
    
    if text == "📦 Остатки":
        await show_stock(update, context)
        return
    elif text == "➕ Принять товар":
        await add_product_start(update, context)
        return
    elif text == "➖ Оформить продажу":
        await sell_start(update, context)
        return
    elif text == "📊 Отчёты":
        await show_reports(update, context)
        return
    elif text == "🔍 Инвентаризация":
        await inventory_start(update, context)
        return
    elif text == "⚙️ Админ-панель":
        await admin_panel(update, context)
        return
    
    state_data = user_states.get(user_id, {})
    state = state_data.get('state')
    
    if not state:
        return
    
    employee_name = get_employee_name(user_id)
    
    # ИНВЕНТАРИЗАЦИЯ: НАЗВАНИЕ
    if state == 'inventory_wait_name':
        product = get_product_by_name(text)
        if not product:
            await update.message.reply_text(f"❌ Товар '{text}' не найден.")
            return
        
        user_states[user_id] = {
            'state': 'inventory_wait_quantity',
            'product_row': product['row'],
            'product_name': product['name'],
            'product_quantity': product['quantity']
        }
        
        await update.message.reply_text(
            f"📦 Товар: *{product['name']}*\n"
            f"📊 В системе: *{product['quantity']} шт.*\n\n"
            f"Введите фактическое количество:",
            parse_mode='Markdown'
        )
        return
    
    # ИНВЕНТАРИЗАЦИЯ: КОЛИЧЕСТВО
    if state == 'inventory_wait_quantity':
        try:
            actual = int(text)
            product_row = state_data['product_row']
            product_name = state_data['product_name']
            system_qty = state_data['product_quantity']
            
            diff = actual - system_qty
            
            if diff == 0:
                text_result = (
                    f"✅ *Расхождений нет!*\n\n"
                    f"📦 {product_name}\n"
                    f"📊 В системе: {system_qty} шт.\n"
                    f"📝 Фактически: {actual} шт."
                )
            else:
                diff_text = f"+{diff}" if diff > 0 else str(diff)
                text_result = (
                    f"⚠️ *Обнаружено расхождение!*\n\n"
                    f"📦 {product_name}\n"
                    f"📊 В системе: {system_qty} шт.\n"
                    f"📝 Фактически: {actual} шт.\n"
                    f"📉 Расхождение: *{diff_text} шт.*\n\n"
                    f"_Изменения не применены._"
                )
            
            await update.message.reply_text(text_result, parse_mode='Markdown')
            user_states.pop(user_id, None)
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        return
    
    # ДОБАВЛЕНИЕ: НАЗВАНИЕ НОВОГО
    if state == 'add_wait_name':
        user_states[user_id] = {
            'state': 'add_new_wait_price',
            'name': text
        }
        await update.message.reply_text(
            f"✅ Название: *{text}*\n\nВведите цену товара (₽):",
            parse_mode='Markdown'
        )
        return
    
    # ДОБАВЛЕНИЕ: ЦЕНА
    if state == 'add_new_wait_price':
        try:
            price = float(text.replace(',', '.'))
            user_states[user_id]['price'] = price
            user_states[user_id]['state'] = 'add_new_wait_quantity'
            
            await update.message.reply_text(
                f"✅ Цена: *{price:.2f} ₽*\n\nВведите количество:",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        return
    
    # ДОБАВЛЕНИЕ: КОЛИЧЕСТВО
    if state == 'add_new_wait_quantity':
        try:
            quantity = int(text)
            name = user_states[user_id]['name']
            price = user_states[user_id]['price']
            
            row = add_product(name, price, quantity)
            
            if row:
                add_movement(employee_name, name, quantity, 'Приход', price * quantity)
                
                await update.message.reply_text(
                    f"✅ *Товар добавлен!*\n\n"
                    f"📦 {name}\n"
                    f"💰 {price:.2f} ₽\n"
                    f"📊 {quantity} шт.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Ошибка добавления.")
            
            user_states.pop(user_id, None)
        except ValueError:
            await update.message.reply_text("❌ Введите целое число.")
        return
    
    # ДОБАВЛЕНИЕ К СУЩЕСТВУЮЩЕМУ
    if state == 'add_wait_quantity':
        try:
            quantity = int(text)
            row = state_data['product_row']
            name = state_data['product_name']
            price = state_data['product_price']
            
            new_qty = increase_product_quantity(row, quantity)
            add_movement(employee_name, name, quantity, 'Приход', price * quantity)
            
            await update.message.reply_text(
                f"✅ *Приход оформлен!*\n\n"
                f"📦 {name}\n"
                f"➕ +{quantity} шт.\n"
                f"📊 Теперь: {new_qty} шт.",
                parse_mode='Markdown'
            )
            
            user_states.pop(user_id, None)
        except ValueError:
            await update.message.reply_text("❌ Введите целое число.")
        return
    
    # ПРОДАЖА: КОЛИЧЕСТВО
    if state == 'sell_wait_quantity':
        try:
            quantity = int(text)
            max_qty = state_data['product_quantity']
            
            if quantity > max_qty:
                await update.message.reply_text(f"❌ На складе только {max_qty} шт.")
                return
            
            user_states[user_id]['state'] = 'sell_wait_client'
            user_states[user_id]['sell_quantity'] = quantity
            
            await update.message.reply_text(
                f"✅ Количество: *{quantity} шт.*\n\nВведите клиента (username или ID):",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        return
    
    # ПРОДАЖА: КЛИЕНТ
    if state == 'sell_wait_client':
        client = text.strip()
        
        if client.isdigit():
            client_display = f"ID: {client}"
        else:
            if not client.startswith('@'):
                client = '@' + client
            client_display = client
        
        user_states[user_id]['client'] = client_display
        user_states[user_id]['state'] = 'sell_wait_payment'
        
        keyboard = [
            [InlineKeyboardButton("💵 Наличные", callback_data="pay_cash")],
            [InlineKeyboardButton("💳 Карта", callback_data="pay_card")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        
        await update.message.reply_text(
            f"✅ Клиент: *{client_display}*\n\nВыберите способ оплаты:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # ПРОДАЖА: КОММЕНТАРИЙ
    if state == 'sell_wait_comment':
        comment = text.strip()
        await finalize_sale(update, context, user_id, comment)
        return


# ============================================
# ЗАВЕРШЕНИЕ ПРОДАЖИ
# ============================================
async def finalize_sale(update_or_query, context, user_id, comment=''):
    state_data = user_states.get(user_id, {})
    
    if not state_data:
        return
    
    employee_name = get_employee_name(user_id)
    row = state_data['product_row']
    name = state_data['product_name']
    price = state_data['product_price']
    quantity = state_data['sell_quantity']
    client = state_data.get('client', '-')
    payment = state_data.get('payment', '-')
    
    new_qty = decrease_product_quantity(row, quantity)
    total = price * quantity
    
    full_comment = f"Клиент: {client} | Оплата: {payment}"
    if comment:
        full_comment += f" | {comment}"
    
    add_movement(employee_name, name, quantity, 'Продажа', total, full_comment)
    
    user_states.pop(user_id, None)
    
    result_text = (
        f"✅ *ПРОДАЖА ОФОРМЛЕНА!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Товар: *{name}*\n"
        f"🔢 Количество: *{quantity} шт.*\n"
        f"💰 Цена: *{price:.2f} ₽*\n"
        f"💵 Сумма: *{total:.2f} ₽*\n"
        f"👤 Клиент: {client}\n"
        f"💳 Оплата: {payment}\n"
    )
    
    if comment:
        result_text += f"📝 Комментарий: {comment}\n"
    
    result_text += f"\n📊 Остаток: *{new_qty} шт.*"
    
    if hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_text(result_text, parse_mode='Markdown')
    else:
        await update_or_query.edit_message_text(result_text, parse_mode='Markdown')


# ============================================
# ОБРАБОТКА КНОПОК
# ============================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if not is_employee(user_id):
        return
    
    employee_name = get_employee_name(user_id)
    
    # ОТМЕНА
    if data == "cancel":
        user_states.pop(user_id, None)
        await query.edit_message_text("❌ Действие отменено.")
        return
    
    # НОВЫЙ ТОВАР
    if data == "add_new":
        user_states[user_id] = {'state': 'add_wait_name'}
        await query.edit_message_text(
            "➕ *НОВЫЙ ТОВАР*\n\nВведите название товара:",
            parse_mode='Markdown'
        )
        return
    
    # ДОБАВЛЕНИЕ К СУЩЕСТВУЮЩЕМУ
    if data.startswith("add_existing_"):
        row = int(data.split("_")[2])
        product = get_product_by_row(row)
        
        if not product:
            await query.edit_message_text("❌ Товар не найден.")
            return
        
        user_states[user_id] = {
            'state': 'add_wait_quantity',
            'product_row': row,
            'product_name': product['name'],
            'product_price': product['price']
        }
        
        await query.edit_message_text(
            f"📦 Товар: *{product['name']}*\n"
            f"💰 Цена: {product['price']:.2f} ₽\n"
            f"📊 Сейчас: {product['quantity']} шт.\n\n"
            f"Введите количество для прихода:",
            parse_mode='Markdown'
        )
        return
    
    # ПРОДАЖА
    if data.startswith("sell_product_"):
        row = int(data.split("_")[2])
        product = get_product_by_row(row)
        
        if not product:
            await query.edit_message_text("❌ Товар не найден.")
            return
        
        user_states[user_id] = {
            'state': 'sell_wait_quantity',
            'product_row': row,
            'product_name': product['name'],
            'product_price': product['price'],
            'product_quantity': product['quantity']
        }
        
        await query.edit_message_text(
            f"📦 Товар: *{product['name']}*\n"
            f"💰 Цена: {product['price']:.2f} ₽\n"
            f"📊 На складе: {product['quantity']} шт.\n\n"
            f"Введите количество:",
            parse_mode='Markdown'
        )
        return
    
    # ОПЛАТА
    if data == "pay_cash":
        user_states[user_id]['payment'] = "Наличные"
        user_states[user_id]['state'] = 'sell_wait_comment'
        
        keyboard = [[InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_comment")]]
        
        await query.edit_message_text(
            "✅ Оплата: *Наличные*\n\nВведите комментарий (или пропустите):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if data == "pay_card":
        user_states[user_id]['payment'] = "Карта"
        user_states[user_id]['state'] = 'sell_wait_comment'
        
        keyboard = [[InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_comment")]]
        
        await query.edit_message_text(
            "✅ Оплата: *Карта*\n\nВведите комментарий (или пропустите):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if data == "skip_comment":
        await finalize_sale(query, context, user_id, '')
        return
    
    # ОТЧЁТЫ
    if data == "report_stock":
        report = get_report_stock()
        await query.edit_message_text(report, parse_mode='Markdown')
        return
    
    if data == "report_today":
        report = get_report_sales_today()
        await query.edit_message_text(report, parse_mode='Markdown')
        return
    
    if data == "report_employees":
        report = get_report_by_employee()
        await query.edit_message_text(report, parse_mode='Markdown')
        return
    
    if data == "report_revenue":
        report = get_report_revenue()
        await query.edit_message_text(report, parse_mode='Markdown')
        return
    
    # АДМИН-ПАНЕЛЬ
    if data == "admin_employees":
        if not is_owner(user_id):
            await query.edit_message_text("⛔ Доступ только для владельца.")
            return
        
        text = "👥 *СОТРУДНИКИ*\n━━━━━━━━━━━━━━━━━━━\n\n"
        for emp_id, info in EMPLOYEES.items():
            role_emoji = "👑" if info['role'] == 'owner' else "🛠️"
            text += f"{role_emoji} {info['username']}\n"
            text += f"   ID: `{emp_id}`\n"
            text += f"   Роль: {info['name']}\n\n"
        
        await query.edit_message_text(text, parse_mode='Markdown')
        return
    
    if data == "admin_movements":
        if not is_owner(user_id):
            await query.edit_message_text("⛔ Доступ только для владельца.")
            return
        
        movements = get_movements(20)
        
        if not movements:
            await query.edit_message_text("📭 История пуста.")
            return
        
        text = "📊 *ПОСЛЕДНИЕ ДВИЖЕНИЯ*\n━━━━━━━━━━━━━━━━━━━\n\n"
        for m in reversed(movements):
            text += f"• {m['date']} | {m['type']}\n"
            text += f"  {m['product']} × {m['quantity']} = {m['total']} ₽\n"
            text += f"  👤 {m['employee']}\n\n"
        
        await query.edit_message_text(text, parse_mode='Markdown')
        return


# ============================================
# ЗАПУСК
# ============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Бот Склад VapeCity запущен!")
    logger.info(f"👑 Владелец: @voloki4")
    logger.info(f"🛠️ Админы: @myhzxc, @Mementaaa")
    logger.info(f"👤 Менеджер: {MANAGER_USERNAME}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()