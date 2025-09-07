# 100% Безкоштовні хостинги для Django

## 🆓 Перевірені безкоштовні варіанти

### 1. Railway ⭐⭐⭐⭐⭐ (НАЙКРАЩИЙ)

**Переваги:**
- ✅ 100% безкоштовний план
- ✅ Автоматичне розгортання з GitHub
- ✅ PostgreSQL база даних включена
- ✅ SSL сертифікати автоматично
- ✅ Простий інтерфейс
- ✅ Підтримка Python/Django
- ✅ Змінні оточення
- ✅ Логи в реальному часі

**Обмеження:**
- 🔸 500 годин на місяць (достатньо для малих проектів)
- 🔸 1 GB RAM
- 🔸 1 GB диск

**Покрокова інструкція:**

1. **Реєстрація:**
   - Йдіть на [railway.app](https://railway.app)
   - Увійдіть через GitHub

2. **Створення проекту:**
   ```
   New Project → Deploy from GitHub repo → Вибрати ваш репозиторій
   ```

3. **Додавання бази даних:**
   ```
   Add Service → Database → PostgreSQL
   ```

4. **Налаштування змінних оточення:**
   ```
   Settings → Variables → Add Variable
   
   DJANGO_SETTINGS_MODULE=loyalty_system.settings_production
   SECRET_KEY=your-secret-key-here
   CHECKBOX_LOGIN=struyska45ch
   CHECKBOX_PASSWORD=6589695541
   CHECKBOX_LICENSE_KEY=your-license-key
   TELEGRAM_BOT_TOKEN=your-bot-token
   ```

5. **Налаштування команд:**
   ```
   Settings → Deploy
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn loyalty_system.wsgi:application --bind 0.0.0.0:$PORT
   ```

6. **Створення Worker для бота:**
   ```
   Add Service → Empty Service
   Start Command: python run_bot.py
   ```

---

### 2. Render ⭐⭐⭐⭐

**Переваги:**
- ✅ 100% безкоштовний план
- ✅ PostgreSQL база даних
- ✅ SSL автоматично
- ✅ GitHub інтеграція
- ✅ Статичні файли

**Обмеження:**
- 🔸 750 годин на місяць
- 🔸 512 MB RAM
- 🔸 Засинає після 15 хвилин неактивності

**Покрокова інструкція:**

1. **Реєстрація:**
   - [render.com](https://render.com)
   - Підключіть GitHub

2. **Створення Web Service:**
   ```
   New → Web Service → Connect Repository
   
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn loyalty_system.wsgi:application
   ```

3. **Додавання PostgreSQL:**
   ```
   New → PostgreSQL → Free Plan
   ```

4. **Змінні оточення:**
   ```
   Environment Variables:
   DATABASE_URL (автоматично з PostgreSQL)
   SECRET_KEY=your-secret-key
   CHECKBOX_LOGIN=struyska45ch
   CHECKBOX_PASSWORD=6589695541
   CHECKBOX_LICENSE_KEY=your-license-key
   TELEGRAM_BOT_TOKEN=your-bot-token
   ```

5. **Background Worker для бота:**
   ```
   New → Background Worker
   Start Command: python run_bot.py
   ```

---

### 3. PythonAnywhere ⭐⭐⭐

**Переваги:**
- ✅ Спеціалізований на Python
- ✅ Веб-консоль
- ✅ MySQL база даних
- ✅ Файловий менеджер

**Обмеження:**
- 🔸 Тільки 1 веб-додаток
- 🔸 Обмежений CPU
- 🔸 Немає HTTPS на безкоштовному плані
- 🔸 Складніше налаштування

**Покрокова інструкція:**

1. **Реєстрація:**
   - [pythonanywhere.com](https://pythonanywhere.com)
   - Beginner Account (безкоштовний)

2. **Завантаження коду:**
   ```bash
   # В консолі PythonAnywhere
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

3. **Віртуальне середовище:**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 mysite
   pip install -r requirements.txt
   ```

4. **Налаштування Web App:**
   ```
   Web → Add a new web app → Manual configuration → Python 3.10
   
   Source code: /home/yourusername/your-repo
   Working directory: /home/yourusername/your-repo
   WSGI configuration file: Edit → Вставити конфігурацію
   ```

5. **WSGI конфігурація:**
   ```python
   import os
   import sys
   
   path = '/home/yourusername/your-repo'
   if path not in sys.path:
       sys.path.insert(0, path)
   
   os.environ['DJANGO_SETTINGS_MODULE'] = 'loyalty_system.settings'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

---

### 4. Vercel ⭐⭐⭐ (Обмежено)

**Переваги:**
- ✅ Швидке розгортання
- ✅ GitHub інтеграція
- ✅ SSL автоматично

**Обмеження:**
- 🔸 Serverless функції (не підходить для постійних процесів)
- 🔸 Немає бази даних
- 🔸 Обмеження на тривалість виконання
- ❌ НЕ підходить для Telegram бота

---

### 5. Glitch ⭐⭐

**Переваги:**
- ✅ Онлайн редактор
- ✅ Швидкий старт

**Обмеження:**
- 🔸 Засинає після 5 хвилин
- 🔸 Обмежені ресурси
- 🔸 Складно налаштувати Django

---

## 🏆 РЕКОМЕНДАЦІЇ

### Для вашого проекту найкраще:

**1-й вибір: Railway**
- Найпростіше налаштування
- Найкращі можливості
- Стабільна робота

**2-й вибір: Render**
- Хороша альтернатива
- Трохи більше обмежень
- Засинає при неактивності

**3-й вибір: PythonAnywhere**
- Для навчання та тестування
- Більше ручного налаштування

## 📋 Підготовка проекту для безкоштовного хостингу

### 1. Оновіть requirements.txt
```txt
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
python-decouple==3.8
```

### 2. Створіть Procfile (для деяких хостингів)
```
web: gunicorn loyalty_system.wsgi:application
worker: python run_bot.py
```

### 3. Оновіть settings_production.py
```python
import os
import dj_database_url
from decouple import config

# Безпека
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# База даних
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# Статичні файли
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... інші middleware
]
```

### 4. Створіть .env файл
```env
SECRET_KEY=your-very-long-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.railway.app,your-domain.onrender.com
DATABASE_URL=postgresql://user:pass@host:port/dbname
TELEGRAM_BOT_TOKEN=your-bot-token
CHECKBOX_LOGIN=struyska45ch
CHECKBOX_PASSWORD=6589695541
CHECKBOX_LICENSE_KEY=your-license-key
```

## 🚀 Швидкий старт з Railway (Рекомендовано)

### Крок за кроком:

1. **Підготуйте GitHub репозиторій:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

2. **Railway розгортання:**
   - Йдіть на railway.app
   - "New Project" → "Deploy from GitHub repo"
   - Виберіть ваш репозиторій
   - Додайте PostgreSQL сервіс
   - Налаштуйте змінні оточення
   - Створіть Worker для Telegram бота

3. **Перевірка:**
   - Відкрийте згенерований URL
   - Перейдіть на `/admin/`
   - Протестуйте Telegram бота

## 🔧 Налагодження проблем

### Проблема: "Application failed to start"
**Рішення:**
1. Перевірте логи в панелі хостингу
2. Переконайтеся, що всі змінні оточення налаштовані
3. Перевірте requirements.txt
4. Переконайтеся, що gunicorn встановлено

### Проблема: "Database connection failed"
**Рішення:**
1. Перевірте DATABASE_URL
2. Запустіть міграції через панель хостингу
3. Переконайтеся, що PostgreSQL сервіс створено

### Проблема: "Static files not loading"
**Рішення:**
1. Додайте WhiteNoise в MIDDLEWARE
2. Налаштуйте STATIC_ROOT
3. Запустіть collectstatic

## 💡 Поради для економії ресурсів

1. **Оптимізуйте код:**
   - Використовуйте кешування
   - Мінімізуйте запити до БД
   - Стискайте статичні файли

2. **Налаштуйте логування:**
   - Обмежте рівень логів
   - Використовуйте ротацію логів

3. **Моніторинг:**
   - Відстежуйте використання ресурсів
   - Налаштуйте алерти

## 🎯 Висновок

**Для вашого проекту системи лояльності рекомендую Railway:**
- Найпростіше налаштування
- Підтримка і Django, і Telegram бота
- Достатньо ресурсів для малого/середнього бізнесу
- 100% безкоштовно

**Альтернатива - Render**, якщо Railway не підійде.

**Уникайте Vercel та Glitch** для цього типу проектів - вони не підходять для постійно працюючих додатків з базою даних.