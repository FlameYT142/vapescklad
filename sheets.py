import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID, SHEET_PRODUCTS, SHEET_MOVEMENTS
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import json
import os

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BRATSK_TZ = ZoneInfo("Asia/Irkutsk")


def get_bratsk_time():
    return datetime.now(BRATSK_TZ)


def get_client():
    try:
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
        else:
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {e}")
        raise


def get_products_sheet():
    client = get_client()
    return client.open_by_key(SHEET_ID).worksheet(SHEET_PRODUCTS)


def get_movements_sheet():
    client = get_client()
    try:
        return client.open_by_key(SHEET_ID).worksheet(SHEET_MOVEMENTS)
    except gspread.WorksheetNotFound:
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.add_worksheet(title=SHEET_MOVEMENTS, rows=1000, cols=10)
        sheet.append_row(['Дата', 'Сотрудник', 'Товар', 'Кол-во', 'Тип', 'Сумма', 'Комментарий'])
        return sheet


# ============================================
# 📦 ТОВАРЫ
# ============================================
def get_all_products():
    try:
        sheet = get_products_sheet()
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return []
        
        products = []
        for i, row in enumerate(data[1:], start=2):
            if len(row) < 2 or not row[1].strip():
                continue
            
            name = row[1].strip()
            if not name:
                continue
            
            try:
                price_str = row[2].strip().replace(',', '.').replace(' ', '') if len(row) > 2 else '0'
                price = float(price_str) if price_str else 0
                
                quantity = 0
                if len(row) > 3 and row[3].strip():
                    try:
                        quantity = int(float(row[3].strip()))
                    except:
                        quantity = 0
                
                products.append({
                    'row': i,
                    'name': name,
                    'price': price,
                    'quantity': quantity,
                })
            except Exception as e:
                logger.warning(f"Ошибка товара строка {i}: {e}")
                continue
        
        return products
    except Exception as e:
        logger.error(f"❌ Ошибка получения товаров: {e}")
        return []


def get_product_by_name(name):
    products = get_all_products()
    for p in products:
        if p['name'].lower() == name.lower():
            return p
    return None


def get_product_by_row(row):
    products = get_all_products()
    for p in products:
        if p['row'] == row:
            return p
    return None


def update_product_quantity(row, new_quantity):
    try:
        sheet = get_products_sheet()
        sheet.update_cell(row, 4, str(new_quantity))
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления: {e}")
        return False


def add_product(name, price, quantity):
    try:
        sheet = get_products_sheet()
        data = sheet.get_all_values()
        
        row_number = 2
        for i, row in enumerate(data[1:], start=2):
            if len(row) < 2 or not row[1].strip():
                row_number = i
                break
            row_number = i + 1
        
        sheet.update_cell(row_number, 2, name)
        sheet.update_cell(row_number, 3, str(price))
        sheet.update_cell(row_number, 4, str(quantity))
        sheet.update_cell(row_number, 5, f"=C{row_number}*D{row_number}")
        
        return row_number
    except Exception as e:
        logger.error(f"❌ Ошибка добавления товара: {e}")
        return None


def increase_product_quantity(row, amount):
    try:
        sheet = get_products_sheet()
        current = sheet.cell(row, 4).value
        try:
            current_int = int(float(current)) if current else 0
        except:
            current_int = 0
        
        new_quantity = current_int + amount
        sheet.update_cell(row, 4, str(new_quantity))
        return new_quantity
    except Exception as e:
        logger.error(f"❌ Ошибка увеличения: {e}")
        return 0


def decrease_product_quantity(row, amount):
    try:
        sheet = get_products_sheet()
        current = sheet.cell(row, 4).value
        try:
            current_int = int(float(current)) if current else 0
        except:
            current_int = 0
        
        new_quantity = max(0, current_int - amount)
        sheet.update_cell(row, 4, str(new_quantity))
        return new_quantity
    except Exception as e:
        logger.error(f"❌ Ошибка уменьшения: {e}")
        return 0


# ============================================
# 📝 ДВИЖЕНИЯ
# ============================================
def add_movement(employee, product_name, quantity, movement_type, total, comment=''):
    try:
        sheet = get_movements_sheet()
        now = get_bratsk_time()
        
        row = [
            now.strftime('%d.%m.%Y %H:%M'),
            employee,
            product_name,
            str(quantity),
            movement_type,
            f"{total:.2f}",
            comment or '-'
        ]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления движения: {e}")
        return False


def get_movements(limit=50):
    try:
        sheet = get_movements_sheet()
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return []
        
        movements = []
        for row in data[1:][-limit:]:
            if len(row) >= 6:
                movements.append({
                    'date': row[0],
                    'employee': row[1],
                    'product': row[2],
                    'quantity': row[3],
                    'type': row[4],
                    'total': row[5],
                    'comment': row[6] if len(row) > 6 else ''
                })
        
        return movements
    except Exception as e:
        logger.error(f"❌ Ошибка получения движений: {e}")
        return []


# ============================================
# 📊 ОТЧЁТЫ
# ============================================
def get_report_stock():
    products = get_all_products()
    
    if not products:
        return "📭 Склад пуст."
    
    text = "📦 *ОСТАТКИ НА СКЛАДЕ*\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    total_sum = 0
    for p in products:
        item_sum = p['price'] * p['quantity']
        total_sum += item_sum
        text += (
            f"• *{p['name']}*\n"
            f"  💰 {p['price']:.2f} ₽ × {p['quantity']} шт. = {item_sum:.2f} ₽\n\n"
        )
    
    text += "━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 *Общая сумма: {total_sum:.2f} ₽*\n"
    text += f"📦 *Всего товаров: {len(products)}*"
    
    return text


def get_report_sales_today():
    movements = get_movements(1000)
    today = get_bratsk_time().strftime('%d.%m.%Y')
    
    today_sales = [
        m for m in movements 
        if m['type'] == 'Продажа' and m['date'].startswith(today)
    ]
    
    if not today_sales:
        return f"📭 Сегодня продаж не было ({today})"
    
    total = sum(float(m['total']) for m in today_sales)
    count = sum(int(m['quantity']) for m in today_sales)
    
    text = f"📅 *ПРОДАЖИ ЗА {today}*\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    for m in today_sales:
        text += f"• {m['date'].split()[1]} | {m['employee']}\n"
        text += f"  {m['product']} × {m['quantity']} = {m['total']} ₽\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 *Выручка: {total:.2f} ₽*\n"
    text += f"📦 *Продано: {count} шт.*"
    
    return text


def get_report_by_employee():
    movements = get_movements(1000)
    sales = [m for m in movements if m['type'] == 'Продажа']
    
    if not sales:
        return "📭 Продаж пока не было."
    
    by_employee = {}
    for m in sales:
        emp = m['employee']
        if emp not in by_employee:
            by_employee[emp] = {'count': 0, 'total': 0}
        by_employee[emp]['count'] += int(m['quantity'])
        by_employee[emp]['total'] += float(m['total'])
    
    text = "👥 *ПРОДАЖИ ПО СОТРУДНИКАМ*\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    for emp, data in sorted(by_employee.items(), key=lambda x: x[1]['total'], reverse=True):
        text += (
            f"• *{emp}*\n"
            f"  📦 Продано: {data['count']} шт.\n"
            f"  💰 Выручка: {data['total']:.2f} ₽\n\n"
        )
    
    return text


def get_report_revenue():
    movements = get_movements(1000)
    sales = [m for m in movements if m['type'] == 'Продажа']
    
    if not sales:
        return "📭 Продаж пока не было."
    
    total = sum(float(m['total']) for m in sales)
    count = sum(int(m['quantity']) for m in sales)
    
    text = "💰 *ОБЩАЯ ВЫРУЧКА*\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📦 Продано: *{count} шт.*\n"
    text += f"💰 Выручка: *{total:.2f} ₽*\n"
    text += f"📊 Всего операций: *{len(sales)}*"
    
    return text