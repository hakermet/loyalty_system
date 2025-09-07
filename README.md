# 🎯 Система лояльності з Telegram ботом

Повнофункціональна система лояльності для бізнесу з інтеграцією Checkbox API та Telegram ботом для клієнтів.

## 🚀 Особливості

- **Django REST API** - Повний API для управління системою лояльності
- **Telegram бот** - Інтерактивний бот для клієнтів
- **Checkbox інтеграція** - Автоматичне отримання даних чеків
- **Веб-інтерфейс касира** - Зручний інтерфейс для персоналу
- **Адмін панель** - Повне управління системою
- **Система балів** - Нарахування та списання бонусних балів
- **QR коди** - Генерація QR кодів для клієнтів

## 📋 Структура проекту

```
loyalty_system/
├── loyalty/                 # Основний додаток системи лояльності
├── telegram_bot/           # Telegram бот
├── checkbox_integration/   # Інтеграція з Checkbox API
├── templates/             # HTML шаблони
├── requirements.txt       # Python залежності
├── docker-compose.yml     # Docker конфігурація
└── deployment файли       # Інструкції для розгортання
```

## 🛠 Технології

- **Backend**: Django 4.2, Django REST Framework
- **Database**: SQLite
- **Bot**: python-telegram-bot
- **API Integration**: Checkbox API
- **Deployment**: Docker, Gunicorn, Nginx
- **Frontend**: HTML, CSS, JavaScript

## 📱 Функціонал Telegram бота

- Реєстрація нових клієнтів
- Перегляд балансу бонусних балів
- Історія покупок та нарахувань
- Отримання QR коду клієнта
- Сканування чеків для нарахування балів
- Підтримка адміністратора

## 🌐 API Endpoints

- `/api/customers/` - Управління клієнтами
- `/api/purchases/` - Покупки та транзакції
- `/api/loyalty-points/` - Бонусні бали
- `/api/receipts/` - Обробка чеків
- `/cashier/` - Інтерфейс касира
- `/admin/` - Адмін панель Django

## 🚀 Швидкий старт

### Локальне розгортання

1. **Клонування репозиторію:**
   ```bash
   git clone https://github.com/hakermet/loyalty_system.git
   cd loyalty_system
   ```

2. **Встановлення залежностей:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Налаштування змінних оточення:**
   ```bash
   cp .env.example .env
   # Відредагуйте .env файл з вашими даними
   ```

4. **Міграції бази даних:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Запуск сервера:**
   ```bash
   python manage.py runserver
   python run_bot.py  # В окремому терміналі
   ```

### Docker розгортання

```bash
docker-compose up -d
```

## 📚 Документація

- [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md) - Локальне розгортання
- [DEPLOYMENT.md](DEPLOYMENT.md) - Розгортання на сервері
- [FREE_HOSTING_GUIDE.md](FREE_HOSTING_GUIDE.md) - Безкоштовні хостинги
- [INFINITYFREE_DEPLOYMENT.md](INFINITYFREE_DEPLOYMENT.md) - Альтернативні хостинги
- [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md) - Керівництво системи
- [USER_GUIDE.md](USER_GUIDE.md) - Керівництво користувача

## 🔧 Конфігурація

### Обов'язкові змінні оточення:

```env
SECRET_KEY=your-django-secret-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
CHECKBOX_LOGIN=your-checkbox-login
CHECKBOX_PASSWORD=your-checkbox-password
CHECKBOX_LICENSE_KEY=your-checkbox-license-key
# SQLite використовується автоматично - додаткові налаштування не потрібні
```

## 🌟 Рекомендовані хостинги

### Безкоштовні:
- **Railway** ⭐⭐⭐⭐⭐ (Найкращий)
- **Render** ⭐⭐⭐⭐
- **PythonAnywhere** ⭐⭐⭐

### Платні:
- **DigitalOcean**
- **AWS**
- **Google Cloud**
- **Heroku**

## 📞 Підтримка

Якщо у вас виникли питання або проблеми:

1. Перевірте документацію в папці проекту
2. Переглянуте Issues на GitHub
3. Створіть новий Issue з детальним описом проблеми

## 📄 Ліцензія

Цей проект розповсюджується під ліцензією MIT.

## 🤝 Внесок у проект

Вітаються Pull Request'и та пропозиції по покращенню!

---

**Розроблено для малого та середнього бізнесу в Україні** 🇺🇦