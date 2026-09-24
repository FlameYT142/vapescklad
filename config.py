import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

# ============================================
# 👥 СОТРУДНИКИ
# ============================================
EMPLOYEES = {
    8494622112: {
        'role': 'owner',
        'username': '@voloki4',
        'name': 'Владелец'
    },
    1302410770: {
        'role': 'admin',
        'username': '@myhzxc',
        'name': 'Администратор'
    },
    1427959789: {
        'role': 'admin',
        'username': '@Mementaaa',
        'name': 'Администратор'
    },
}

# Менеджер для посторонних
MANAGER_USERNAME = '@smart_trader138'

# ============================================
# 📊 НАЗВАНИЯ ЛИСТОВ
# ============================================
SHEET_PRODUCTS = 'Склад'
SHEET_MOVEMENTS = 'Движения'

# ============================================
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================
def is_employee(user_id):
    return user_id in EMPLOYEES


def is_owner(user_id):
    return EMPLOYEES.get(user_id, {}).get('role') == 'owner'


def is_admin(user_id):
    return EMPLOYEES.get(user_id, {}).get('role') == 'admin'


def get_employee_info(user_id):
    return EMPLOYEES.get(user_id, {})


def get_employee_name(user_id):
    info = EMPLOYEES.get(user_id, {})
    return info.get('username', str(user_id))