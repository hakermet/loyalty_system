# Інструкції з розгортання системи лояльності на сервері

## Передумови

### Системні вимоги
- Ubuntu 20.04+ або CentOS 8+
- Python 3.8+
- PostgreSQL 12+
- Nginx
- SSL сертифікат (рекомендується)

## Крок 1: Підготовка сервера

### Оновлення системи
```bash
sudo apt update && sudo apt upgrade -y
```

### Встановлення необхідних пакетів
```bash
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib nginx git supervisor -y
```

## Крок 2: Налаштування бази даних

### Створення бази даних та користувача
```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE loyalty_system_db;
CREATE USER loyalty_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE loyalty_system_db TO loyalty_user;
ALTER USER loyalty_user CREATEDB;
\q
```

## Крок 3: Розгортання додатку

### Створення користувача для додатку
```bash
sudo adduser --system --group loyalty
sudo mkdir -p /var/www/loyalty_system
sudo chown loyalty:loyalty /var/www/loyalty_system
```

### Клонування проекту
```bash
sudo -u loyalty git clone https://github.com/your-username/loyalty-system.git /var/www/loyalty_system
cd /var/www/loyalty_system
```

### Створення віртуального середовища
```bash
sudo -u loyalty python3 -m venv venv
sudo -u loyalty ./venv/bin/pip install --upgrade pip
sudo -u loyalty ./venv/bin/pip install -r requirements.txt
```

## Крок 4: Налаштування змінних оточення

### Створення .env файлу
```bash
sudo -u loyalty cp .env.example .env
sudo -u loyalty nano .env
```

### Заповнення .env файлу
```env
SECRET_KEY=your-very-long-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

DB_NAME=loyalty_system_db
DB_USER=loyalty_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

TELEGRAM_BOT_TOKEN=your-telegram-bot-token

CHECKBOX_API_URL=https://api.checkbox.in.ua/api/v1
CHECKBOX_LOGIN=struyska45ch
CHECKBOX_PASSWORD=6589695541
CHECKBOX_LICENSE_KEY=525a77dbf8c8eb5659bfc3fe

CORS_ALLOWED_ORIGINS=https://your-domain.com
```

## Крок 5: Налаштування Django

### Міграції бази даних
```bash
sudo -u loyalty ./venv/bin/python manage.py migrate --settings=loyalty_system.settings_production
```

### Створення суперкористувача
```bash
sudo -u loyalty ./venv/bin/python manage.py createsuperuser --settings=loyalty_system.settings_production
```

### Збір статичних файлів
```bash
sudo -u loyalty ./venv/bin/python manage.py collectstatic --noinput --settings=loyalty_system.settings_production
```

## Крок 6: Налаштування Gunicorn

### Створення конфігураційного файлу Gunicorn
```bash
sudo nano /var/www/loyalty_system/gunicorn.conf.py
```

```python
bind = "127.0.0.1:8000"
workers = 3
user = "loyalty"
group = "loyalty"
raw_env = [
    "DJANGO_SETTINGS_MODULE=loyalty_system.settings_production",
]
pythonpath = "/var/www/loyalty_system"
chdir = "/var/www/loyalty_system"
daemon = False
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/var/www/loyalty_system/logs/gunicorn_access.log"
errorlog = "/var/www/loyalty_system/logs/gunicorn_error.log"
loglevel = "info"
```

## Крок 7: Налаштування Supervisor

### Django додаток
```bash
sudo nano /etc/supervisor/conf.d/loyalty_django.conf
```

```ini
[program:loyalty_django]
command=/var/www/loyalty_system/venv/bin/gunicorn loyalty_system.wsgi:application -c /var/www/loyalty_system/gunicorn.conf.py
directory=/var/www/loyalty_system
user=loyalty
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/loyalty_system/logs/django.log
```

### Telegram Bot
```bash
sudo nano /etc/supervisor/conf.d/loyalty_bot.conf
```

```ini
[program:loyalty_bot]
command=/var/www/loyalty_system/venv/bin/python telegram_bot/bot.py
directory=/var/www/loyalty_system
user=loyalty
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/loyalty_system/logs/bot.log
environment=DJANGO_SETTINGS_MODULE="loyalty_system.settings_production"
```

### Перезапуск Supervisor
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start loyalty_django
sudo supervisorctl start loyalty_bot
```

## Крок 8: Налаштування Nginx

### Створення конфігурації сайту
```bash
sudo nano /etc/nginx/sites-available/loyalty_system
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Static files
    location /static/ {
        alias /var/www/loyalty_system/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /var/www/loyalty_system/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;
}
```

### Активація сайту
```bash
sudo ln -s /etc/nginx/sites-available/loyalty_system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Крок 9: Налаштування SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Крок 10: Налаштування автоматичного резервного копіювання

### Створення скрипта резервного копіювання
```bash
sudo nano /var/www/loyalty_system/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/loyalty_system"
DATE=$(date +"%Y%m%d_%H%M%S")

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U loyalty_user loyalty_system_db > $BACKUP_DIR/db_backup_$DATE.sql

# Files backup
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz -C /var/www loyalty_system

# Remove old backups (older than 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### Додавання до crontab
```bash
sudo chmod +x /var/www/loyalty_system/backup.sh
sudo crontab -e
```

Додати рядок:
```
0 2 * * * /var/www/loyalty_system/backup.sh
```

## Крок 11: Моніторинг та логи

### Перевірка статусу сервісів
```bash
sudo supervisorctl status
sudo systemctl status nginx
sudo systemctl status postgresql
```

### Перегляд логів
```bash
# Django логи
tail -f /var/www/loyalty_system/logs/django.log

# Bot логи
tail -f /var/www/loyalty_system/logs/bot.log

# Nginx логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Крок 12: Оновлення додатку

### Скрипт для оновлення
```bash
sudo nano /var/www/loyalty_system/update.sh
```

```bash
#!/bin/bash
cd /var/www/loyalty_system

# Pull latest changes
sudo -u loyalty git pull origin main

# Install/update dependencies
sudo -u loyalty ./venv/bin/pip install -r requirements.txt

# Run migrations
sudo -u loyalty ./venv/bin/python manage.py migrate --settings=loyalty_system.settings_production

# Collect static files
sudo -u loyalty ./venv/bin/python manage.py collectstatic --noinput --settings=loyalty_system.settings_production

# Restart services
sudo supervisorctl restart loyalty_django
sudo supervisorctl restart loyalty_bot

echo "Update completed!"
```

```bash
sudo chmod +x /var/www/loyalty_system/update.sh
```

## Безпека

### Налаштування файрволу
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### Регулярні оновлення
```bash
sudo apt update && sudo apt upgrade -y
```

## Тестування

### Перевірка роботи API
```bash
curl -X GET https://your-domain.com/api/health/
```

### Перевірка роботи бота
Надішліть `/start` вашому боту в Telegram

## Підтримка

Для отримання допомоги або повідомлення про проблеми:
- Перевірте логи: `/var/www/loyalty_system/logs/`
- Перевірте статус сервісів: `sudo supervisorctl status`
- Перевірте конфігурацію Nginx: `sudo nginx -t`