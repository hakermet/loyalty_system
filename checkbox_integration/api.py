import requests
import json
import os
import qrcode
from io import BytesIO
from django.conf import settings
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loyalty_system.settings')
django.setup()

from loyalty.models import Customer, Purchase

# Налаштування API Checkbox з settings.py
CHECKBOX_API_URL = settings.CHECKBOX_API_URL
CHECKBOX_LOGIN = settings.CHECKBOX_LOGIN
CHECKBOX_PASSWORD = settings.CHECKBOX_PASSWORD
CHECKBOX_LICENSE_KEY = settings.CHECKBOX_LICENSE_KEY

class CheckboxAPI:
    def __init__(self):
        self.token = None
        self.login()
    
    def login(self):
        """Авторизація в API Checkbox - спробуємо різні методи"""
        
        # Різні методи авторизації для тестування
        auth_methods = [
            {
                'name': 'PIN-код авторизація',
                'url': f"{CHECKBOX_API_URL}/cashier/signinPinCode",
                'data': {"pin_code": CHECKBOX_PASSWORD}
            },
            {
                'name': 'Логін/пароль авторизація',
                'url': f"{CHECKBOX_API_URL}/cashier/signin",
                'data': {"login": CHECKBOX_LOGIN, "password": CHECKBOX_PASSWORD}
            },
            {
                'name': 'Альтернативна PIN авторизація',
                'url': f"{CHECKBOX_API_URL}/auth/signin",
                'data': {"pin_code": CHECKBOX_PASSWORD}
            },
            {
                'name': 'Базова авторизація',
                'url': f"{CHECKBOX_API_URL}/signin",
                'data': {"login": CHECKBOX_LOGIN, "password": CHECKBOX_PASSWORD}
            }
        ]
        
        base_headers = {
            "Content-Type": "application/json",
            "accept": "application/json",
            "X-License-Key": CHECKBOX_LICENSE_KEY,
            "X-Client-Name": "Loyalty-System",
            "X-Client-Version": "1.0.0"
        }
        
        for method in auth_methods:
            print(f"\n🔐 СПРОБА АВТОРИЗАЦІЇ: {method['name']}")
            print(f"   URL: {method['url']}")
            print(f"   Data: {method['data']}")
            print(f"   License Key: {CHECKBOX_LICENSE_KEY[:10]}...")
            
            try:
                response = requests.post(method['url'], json=method['data'], headers=base_headers, timeout=10)
                print(f"📊 RESPONSE STATUS: {response.status_code}")
                print(f"📄 RESPONSE HEADERS: {dict(response.headers)}")
                print(f"📝 RESPONSE BODY: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    self.token = result.get('access_token')
                    if self.token:
                        print(f"✅ УСПІШНА АВТОРИЗАЦІЯ: {method['name']}")
                        print(f"🔑 Token отримано")
                        return True
                    else:
                        print(f"❌ Токен не знайдено в відповіді")
                else:
                    print(f"❌ ПОМИЛКА АВТОРИЗАЦІЇ: Status {response.status_code}")
                    if response.status_code == 403:
                        print(f"🚫 FORBIDDEN: Перевірте credentials та license key")
                    elif response.status_code == 401:
                        print(f"🔒 UNAUTHORIZED: Невірний логін/пароль")
                    elif response.status_code == 404:
                        print(f"🔍 NOT FOUND: Перевірте API URL")
                        
            except requests.exceptions.Timeout:
                print(f"⏰ TIMEOUT для методу {method['name']}")
                continue
            except requests.exceptions.ConnectionError:
                print(f"🌐 CONNECTION ERROR для методу {method['name']}")
                continue
            except Exception as e:
                print(f"💥 ПОМИЛКА для методу {method['name']}: {str(e)}")
                continue
        
        print(f"❌ ВСІ МЕТОДИ АВТОРИЗАЦІЇ НЕ СПРАЦЮВАЛИ")
        return False
    
    def get_headers(self):
        """Отримання заголовків для запитів"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def get_receipt(self, receipt_id):
        """Отримання інформації про чек за його фіскальним номером через Checkbox API"""
        print(f"📋 Запит даних для чеку: {receipt_id}")
        
        if not self.token:
            print("🔐 Немає токену авторизації, спробуємо увійти...")
            if not self.login():
                print("❌ Не вдалося авторизуватися в Checkbox API")
                return None
        
        # Спробуємо різні методи отримання чеку
        methods = [
            f"{CHECKBOX_API_URL}/receipts/{receipt_id}",
            f"{CHECKBOX_API_URL}/cashier/receipts/{receipt_id}",
            f"{CHECKBOX_API_URL}/receipts/search?fiscal_number={receipt_id}",
            f"{CHECKBOX_API_URL}/cashier/receipts/search?fiscal_number={receipt_id}"
        ]
        
        headers = self.get_headers()
        
        for i, url in enumerate(methods, 1):
            try:
                print(f"🔍 Метод {i}: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                print(f"📊 Статус відповіді: {response.status_code}")
                print(f"📝 Відповідь: {response.text[:200]}...")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Успішно отримано дані чеку методом {i}")
                    
                    # Обробляємо різні формати відповіді
                    if isinstance(data, dict):
                        if 'results' in data and data['results']:
                            receipt = data['results'][0]
                        elif 'data' in data:
                            receipt = data['data']
                        else:
                            receipt = data
                    else:
                        receipt = data
                    
                    # Витягуємо суму з різних можливих полів
                    total_amount = (
                        receipt.get('total_sum') or 
                        receipt.get('total') or 
                        receipt.get('sum') or 
                        receipt.get('amount') or 
                        0
                    )
                    
                    return {
                        'id': receipt_id,
                        'total': float(total_amount) / 100 if total_amount > 1000 else float(total_amount),  # Конвертуємо копійки в гривні якщо потрібно
                        'created_at': receipt.get('created_at', '2024-01-01T12:00:00Z'),
                        'status': receipt.get('status', 'DONE'),
                        'raw_data': receipt
                    }
                    
                elif response.status_code == 401:
                    print("🔒 Токен застарів, спробуємо перелогінитися...")
                    if self.login():
                        headers = self.get_headers()
                        continue
                    else:
                        print("❌ Не вдалося перелогінитися")
                        break
                        
            except requests.exceptions.Timeout:
                print(f"⏰ Таймаут для методу {i}")
                continue
            except requests.exceptions.ConnectionError:
                print(f"🌐 Помилка з'єднання для методу {i}")
                continue
            except Exception as e:
                print(f"💥 Помилка для методу {i}: {str(e)}")
                continue
        
        print("❌ Всі методи не спрацювали, чек не знайдено")
        return None
    
    def apply_discount(self, receipt_id, discount_percentage):
        """Застосування знижки до чеку"""
        if not self.token:
            if not self.login():
                return False
        
        # Отримуємо інформацію про чек
        receipt = self.get_receipt(receipt_id)
        if not receipt:
            return False
        
        # Тут має бути логіка застосування знижки через API Checkbox
        # Це залежить від конкретного API Checkbox, тому це приблизна реалізація
        url = f"{CHECKBOX_API_URL}/receipts/{receipt_id}/discount"
        payload = {
            "discountType": "PERCENTAGE",
            "value": discount_percentage
        }
        
        response = requests.post(url, json=payload, headers=self.get_headers())
        return response.status_code == 200

def get_customer_level(total_spent):
    """Визначення рівня клієнта на основі накопиченої суми покупок"""
    if total_spent < 2000:
        return "Starter", 1  # Всі клієнти рівня Starter отримують 1% за реєстрацію
    elif total_spent < 5000:
        return "Regular", 3
    elif total_spent < 10000:
        return "Pro", 5
    elif total_spent < 20000:
        return "Elite", 7
    else:
        return "VIP", 10

def calculate_discount(amount):
    """Розрахунок знижки на основі суми покупки (для нарахування)"""
    # Тепер знижка нараховується тільки на основі рівня клієнта
    # Ця функція може бути використана для додаткових бонусів
    return 0  # Поки що не нараховуємо додаткові знижки за покупку

def process_purchase(phone_number, receipt_id):
    """Обробка покупки та нарахування знижки"""
    print(f"🛒 Обробка покупки для телефону: {phone_number}, чек: {receipt_id}")
    
    # Ініціалізуємо API
    api = CheckboxAPI()
    
    # Отримуємо інформацію про чек через справжній Checkbox API
    receipt_data = api.get_receipt(receipt_id)
    if not receipt_data:
        return {"success": False, "message": "Не вдалося отримати інформацію про чек через Checkbox API"}
    
    # Отримуємо суму покупки
    amount = float(receipt_data.get('total', 0))
    print(f"💰 Сума покупки: {amount} грн")
    
    try:
        # Знаходимо клієнта за номером телефону
        customer = Customer.objects.get(phone_number=phone_number)
        
        # Отримуємо поточний рівень та знижку клієнта
        old_level, old_discount = get_customer_level(customer.total_spent)
        
        # Застосовуємо поточну знижку клієнта
        current_discount = old_discount
        if current_discount > 0:
            api.apply_discount(receipt_id, current_discount)
        
        # Оновлюємо загальну суму покупок клієнта
        customer.total_spent += amount
        
        # Визначаємо новий рівень та знижку після покупки
        new_level, new_discount = get_customer_level(customer.total_spent)
        
        # Оновлюємо знижку клієнта відповідно до нового рівня
        customer.current_discount = new_discount
        customer.save()
        
        # Зберігаємо інформацію про покупку
        purchase = Purchase(
            customer=customer,
            amount=amount,
            discount_applied=current_discount,
            discount_earned=0,  # Тепер знижки не нараховуються за покупку
            receipt_id=receipt_id
        )
        purchase.save()
        
        # Формуємо повідомлення про результат
        message = f"Знижку {current_discount}% застосовано.\n"
        message += f"Ваш поточний рівень: {new_level}\n"
        message += f"Ваша знижка: {new_discount}%\n"
        message += f"Загальна сума покупок: {customer.total_spent} грн"
        
        if old_level != new_level:
            message += f"\n🎉 Вітаємо! Ви досягли нового рівня: {new_level}!"
        
        return {
            "success": True,
            "message": message
        }
    
    except Customer.DoesNotExist:
        # Клієнт не знайдений, генеруємо QR-код для реєстрації
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"https://t.me/your_bot_username?start={receipt_id}")
        qr.make(fit=True)
        
        img = qrcode.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = buffer.getvalue()
        
        return {
            "success": False,
            "message": "Клієнт не зареєстрований в системі лояльності",
            "qr_code": qr_code_base64
        }