# Локальне розгортання системи лояльності

## 🖥️ Системні вимоги

### Мінімальні вимоги:
- **ОС**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **RAM**: 4 GB (рекомендовано 8 GB)
- **Диск**: 2 GB вільного місця
- **Інтернет**: Стабільне з'єднання для API Checkbox

### Необхідне ПЗ:
1. **Python 3.9+** (рекомендовано 3.11)
2. **Git** для клонування репозиторію
3. **Текстовий редактор** (VS Code, PyCharm, Sublime)

## 📋 Покрокова інструкція

### Крок 1: Встановлення Python

**Windows:**
1. Завантажте з [python.org](https://python.org/downloads/)
2. Під час встановлення обов'язково поставте галочку "Add Python to PATH"
3. Перевірте: `python --version`

```

### Крок 2: Клонування проекту

```bash
# Клонуйте репозиторій
git clone <your-repository-url>
cd Tg_system

# Або скопіюйте папку проекту
```

### Крок 3: Створення віртуального середовища

**Windows:**
```cmd
# Створення
python -m venv venv

# Активація
venv\Scripts\activate

# Перевірка
where python
```


### Крок 4: Встановлення залежностей

```bash
# Оновлення pip
python -m pip install --upgrade pip

# Встановлення залежностей
pip install -r requirements.txt
```

### Крок 5: Налаштування змінних оточення

1. **Створіть файл `.env`** в корені проекту:
```bash
cp .env.example .env
```

2. **Відредагуйте `.env`** з вашими даними:
```env
# Django
SECRET_KEY=your-very-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# База даних (SQLite для локального розвитку)
DATABASE_URL=sqlite:///db.sqlite3

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Checkbox API
CHECKBOX_API_URL=https://api.checkbox.ua/api/v1
CHECKBOX_LOGIN=struyska45ch
CHECKBOX_PASSWORD=6589695541
CHECKBOX_LICENSE_KEY=your-license-key

# CORS (для локального розвитку)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Крок 6: Налаштування бази даних

```bash
# Створення міграцій
python manage.py makemigrations

# Застосування міграцій
python manage.py migrate

# Створення суперкористувача
python manage.py createsuperuser
```

### Крок 7: Збір статичних файлів

```bash
python manage.py collectstatic --noinput
```

### Крок 8: Запуск системи

**Варіант 1: Окремі термінали (рекомендовано для розробки)**

*Термінал 1 - Django сервер:*
```bash
python manage.py runserver 0.0.0.0:8000
```

*Термінал 2 - Telegram Bot:*
```bash
python run_bot.py
```

**Варіант 2: Один процес (для тестування)**
```bash
# Створіть start.py
python start.py
```

## 🔧 Файл start.py для одночасного запуску

```python
import subprocess
import sys
import threading
import time

def run_django():
    """Запуск Django сервера"""
    subprocess.run([sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'])

def run_bot():
    """Запуск Telegram бота"""
    time.sleep(3)  # Чекаємо запуску Django
    subprocess.run([sys.executable, 'run_bot.py'])

if __name__ == '__main__':
    print("🚀 Запуск системи лояльності...")
    
    # Запуск Django в окремому потоці
    django_thread = threading.Thread(target=run_django)
    django_thread.daemon = True
    django_thread.start()
    
    # Запуск бота в основному потоці
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n⏹️ Зупинка системи...")
        sys.exit(0)
```

## 🌐 Доступ до системи

Після запуску система буде доступна за адресами:

- **Django Admin**: http://localhost:8000/admin/
- **API**: http://localhost:8000/api/
- **Веб-інтерфейс касира**: http://localhost:8000/cashier/
- **Telegram Bot**: Працює в фоновому режимі

## 🔍 Тестування системи

### 1. Перевірка Django
```bash
# Відкрийте браузер
http://localhost:8000/admin/

# Увійдіть з обліковими даними суперкористувача
```

### 2. Перевірка API
```bash
# Тест API
curl http://localhost:8000/api/customers/

# Або через браузер
http://localhost:8000/api/
```

### 3. Перевірка Telegram Bot
- Знайдіть вашого бота в Telegram
- Надішліть команду `/start`
- Перевірте відповідь

### 4. Тест Checkbox API
```bash
# Запустіть тест
python test_checkbox.py
```

## 🛠️ Налагодження проблем

### Проблема: "ModuleNotFoundError"
**Рішення:**
```bash
# Переконайтеся, що віртуальне середовище активовано
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Переустановіть залежності
pip install -r requirements.txt
```

### Проблема: "Port already in use"
**Рішення:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9

# Або використайте інший порт
python manage.py runserver 8001
```

### Проблема: "Database locked"
**Рішення:**
```bash
# Зупиніть всі процеси Django
# Видаліть db.sqlite3
rm db.sqlite3

# Створіть базу заново
python manage.py migrate
python manage.py createsuperuser
```

### Проблема: Telegram Bot не відповідає
**Перевірте:**
1. Правильність токена в `.env`
2. Інтернет з'єднання
3. Логи в терміналі
4. Чи не заблокований бот іншим процесом

## 📱 Розробка та налагодження

### Корисні команди:
```bash
# Перегляд логів Django
python manage.py runserver --verbosity=2

# Інтерактивна оболонка Django
python manage.py shell

# Перевірка моделей
python manage.py check

# Створення тестових даних
python manage.py loaddata fixtures/test_data.json
```

### Структура логів:
```
logs/
├── django.log          # Логи Django
├── telegram_bot.log    # Логи Telegram бота
└── checkbox_api.log    # Логи Checkbox API
```

## 🔒 Безпека для локального розвитку

1. **Ніколи не комітьте `.env`** файл
2. **Використовуйте різні ключі** для розробки та production
3. **Обмежте доступ** до admin панелі
4. **Регулярно оновлюйте** залежності

## 📊 Моніторинг

### Перевірка статусу:
```bash
# Процеси Python
ps aux | grep python

# Використання портів
netstat -tulpn | grep :8000

# Логи в реальному часі
tail -f logs/django.log
```

## 🚀 Готово!

Ваша система лояльності тепер працює локально!

**Наступні кроки:**
1. Протестуйте всі функції
2. Додайте тестових користувачів
3. Перевірте інтеграцію з Checkbox
4. Налаштуйте Telegram бота
5. При необхідності розгорніть на сервері

**Підтримка:**
- Перевіряйте логи при проблемах
- Використовуйте Django admin для налагодження
- Тестуйте API через браузер або Postman