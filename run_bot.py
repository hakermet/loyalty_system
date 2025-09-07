import os
import sys
import django
import asyncio

# Додаємо поточну директорію до Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loyalty_system.settings')
django.setup()

from telegram_bot.bot import main

if __name__ == '__main__':
    main()