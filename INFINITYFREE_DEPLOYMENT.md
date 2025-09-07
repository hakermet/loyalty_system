# Розгортання на InfinityFree

## Важливо! Обмеження InfinityFree

⚠️ **УВАГА**: InfinityFree має серйозні обмеження для Django проектів:
- Не підтримує Python/Django напряму
- Тільки PHP, HTML, CSS, JavaScript
- Немає доступу до командного рядка
- Немає можливості встановлювати Python пакети
- Немає підтримки WebSocket для Telegram Bot

## Альтернативні рішення

### 1. Heroku (Рекомендовано)
**Безкоштовний план з обмеженнями**

#### Кроки розгортання:
1. Створіть акаунт на [heroku.com](https://heroku.com)
2. Встановіть Heroku CLI
3. Створіть файл `Procfile`:
```
web: gunicorn loyalty_system.wsgi
worker: python run_bot.py
```
4. Створіть файл `runtime.txt`:
```
python-3.11.0
```
5. Оновіть `requirements.txt` додавши:
```
psycopg2-binary==2.9.7
dj-database-url==2.1.0
```
6. Команди для розгортання:
```bash
heroku login
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
heroku config:set DJANGO_SETTINGS_MODULE=loyalty_system.settings_production
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set CHECKBOX_LOGIN="struyska45ch"
heroku config:set CHECKBOX_PASSWORD="6589695541"
heroku config:set CHECKBOX_LICENSE_KEY="your-license-key"
heroku config:set TELEGRAM_BOT_TOKEN="your-bot-token"
git init
git add .
git commit -m "Initial commit"
heroku git:remote -a your-app-name
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
heroku ps:scale web=1 worker=1
```

### 2. Railway (Рекомендовано)
**Безкоштовний план з хорошою підтримкою Python**

#### Кроки розгортання:
1. Створіть акаунт на [railway.app](https://railway.app)
2. Підключіть GitHub репозиторій
3. Додайте PostgreSQL сервіс
4. Налаштуйте змінні оточення:
   - `DJANGO_SETTINGS_MODULE=loyalty_system.settings_production`
   - `SECRET_KEY=your-secret-key`
   - `CHECKBOX_LOGIN=struyska45ch`
   - `CHECKBOX_PASSWORD=6589695541`
   - `CHECKBOX_LICENSE_KEY=your-license-key`
   - `TELEGRAM_BOT_TOKEN=your-bot-token`
5. Railway автоматично розгорне проект

### 3. PythonAnywhere (Частково безкоштовно)
**Обмежений безкоштовний план**

#### Кроки розгортання:
1. Створіть акаунт на [pythonanywhere.com](https://pythonanywhere.com)
2. Завантажте файли через Files або Git
3. Створіть віртуальне середовище:
```bash
mkvirtualenv --python=/usr/bin/python3.10 mysite-virtualenv
pip install -r requirements.txt
```
4. Налаштуйте Web App в панелі управління
5. Налаштуйте WSGI файл
6. Додайте змінні оточення в `.env`

### 4. Render (Рекомендовано)
**Безкоштовний план з автоматичним розгортанням**

#### Кроки розгортання:
1. Створіть акаунт на [render.com](https://render.com)
2. Підключіть GitHub репозиторій
3. Створіть Web Service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn loyalty_system.wsgi:application`
4. Додайте PostgreSQL базу даних
5. Налаштуйте змінні оточення
6. Створіть Background Worker для бота:
   - Start Command: `python run_bot.py`

## Підготовка проекту для хмарного хостингу

### 1. Оновіть settings_production.py
```python
import os
import dj_database_url
from pathlib import Path

# Для Heroku/Railway/Render
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}

# Статичні файли для хмарного хостингу
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Додайте WhiteNoise middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Додати це
    # ... інші middleware
]
```

### 2. Оновіть requirements.txt
```
Django==4.2.7
djangorestframework==3.14.0
python-telegram-bot==20.7
requests==2.31.0
qrcode==7.4.2
Pillow==10.1.0
pytz==2023.3
gunicorn==21.2.0
whitenoise==6.6.0
dj-database-url==2.1.0
psycopg2-binary==2.9.7
django-cors-headers==4.3.1
```

### 3. Створіть Procfile (для Heroku)
```
web: gunicorn loyalty_system.wsgi
worker: python run_bot.py
```

### 4. Створіть runtime.txt (для Heroku)
```
python-3.11.0
```

## Рекомендації

1. **Найкращий варіант**: Railway або Render - найпростіше налаштування
2. **Альтернатива**: Heroku - більше можливостей, але складніше
3. **Для тестування**: PythonAnywhere - обмежений, але працює

## Важливі нотатки

- InfinityFree НЕ підходить для Django проектів
- Всі рекомендовані сервіси мають безкоштовні плани
- Telegram Bot потребує постійного з'єднання (worker process)
- Обов'язково налаштуйте змінні оточення для безпеки
- Використовуйте PostgreSQL замість SQLite для production

## Налаштування після розгортання

1. Запустіть міграції: `python manage.py migrate`
2. Створіть суперкористувача: `python manage.py createsuperuser`
3. Зберіть статичні файли: `python manage.py collectstatic`
4. Перевірте роботу API через admin панель
5. Протестуйте Telegram бота

## Підтримка

Якщо виникнуть проблеми:
1. Перевірте логи сервісу
2. Переконайтеся, що всі змінні оточення налаштовані
3. Перевірте, що база даних підключена
4. Переконайтеся, що worker process для бота запущений