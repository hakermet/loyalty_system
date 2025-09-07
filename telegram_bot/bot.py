import logging
import os
import sys

# Додаємо поточну директорію до sys.path для imghdr
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loyalty_system.settings')
django.setup()

from loyalty.models import Customer, Purchase
from telegram_bot.models import DiscountCode
from telegram_bot.admin_config import is_admin
from checkbox_integration.api import get_customer_level, calculate_discount
from django.utils import timezone
from django.db import models
import string
import random
import pytz

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Токен вашого бота (зберігайте в змінних середовища в продакшені)
from django.conf import settings

TOKEN = settings.TELEGRAM_BOT_TOKEN

# Функція для конвертації часу в український часовий пояс
def format_ukraine_time(datetime_obj):
    """Конвертує UTC час в український часовий пояс та форматує"""
    ukraine_tz = pytz.timezone('Europe/Kiev')
    if datetime_obj.tzinfo is None:
        # Якщо час без часового поясу, вважаємо його UTC
        utc_time = pytz.utc.localize(datetime_obj)
    else:
        utc_time = datetime_obj.astimezone(pytz.utc)
    
    ukraine_time = utc_time.astimezone(ukraine_tz)
    return ukraine_time.strftime('%d.%m.%Y %H:%M')

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    
    # Перевіряємо, чи користувач вже зареєстрований
    try:
        customer = Customer.objects.get(telegram_id=str(user.id))
        level, discount = get_customer_level(customer.total_spent)
        
        # Оновлюємо знижку клієнта, якщо вона змінилася
        if customer.current_discount != discount:
            customer.current_discount = discount
            customer.save()
        
        keyboard = [
            [InlineKeyboardButton("🛒 Швидка покупка", callback_data="oneclick")],
            [InlineKeyboardButton("💰 Моя знижка", callback_data="discount")],
            [InlineKeyboardButton("📊 Рівні знижок", callback_data="levels")],
            [InlineKeyboardButton("📋 Історія покупок", callback_data="history")],
            [InlineKeyboardButton("⚙️ Налаштування профілю", callback_data="profile_settings")],
            [InlineKeyboardButton("📖 Допомога", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"Вітаємо, {customer.first_name}! 👋\n\n"
            f"💎 Ваш рівень: {level}\n"
            f"💰 Ваша знижка: {discount}%\n"
            f"🛒 Загальна сума покупок: {customer.total_spent} грн",
            reply_markup=reply_markup
        )
    except Customer.DoesNotExist:
        # Якщо користувач не зареєстрований, пропонуємо реєстрацію
        keyboard = [
            [InlineKeyboardButton("✅ Зареєструватися", callback_data="register")],
            [InlineKeyboardButton("📊 Рівні знижок", callback_data="levels")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "🎉 **Вітаємо в системі лояльності нашого магазину!**\n\n"
            "💎 Отримуйте знижки від 1% до 10% залежно від суми покупок\n"
            "🛒 Накопичуйте бонуси з кожною покупкою\n"
            "📈 Підвищуйте свій рівень для більших знижок\n\n"
            "Для початку роботи зареєструйтеся в системі! 👇",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def register_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    # Запитуємо дозвіл на використання номера телефону
    keyboard = [
        [KeyboardButton("📱 Поділитися номером телефону", request_contact=True)],
        [KeyboardButton("🏠 Головне меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    query.message.reply_text(
        text="📱 Для реєстрації в системі лояльності нам потрібен ваш номер телефону.\n\n"
             "Натисніть кнопку нижче, щоб автоматично поділитися номером з вашого Telegram акаунту:\n\n"
             "🔒 Ваші дані захищені та використовуються тільки для системи знижок.",
        reply_markup=reply_markup
    )
    context.user_data['registration_step'] = 'phone_consent'

def handle_message(update: Update, context: CallbackContext):
    # Обробка кнопки "Головне меню"
    if update.message.text == "🏠 Головне меню":
        # Очищаємо дані реєстрації
        context.user_data.clear()
        start(update, context)
        return
    
    # Обробка контакту для реєстрації
    if update.message.contact and 'registration_step' in context.user_data and context.user_data['registration_step'] == 'phone_consent':
        contact = update.message.contact
        phone = contact.phone_number
        
        # Додаємо + якщо його немає
        if not phone.startswith('+'):
            phone = '+' + phone
            
        context.user_data['phone'] = phone
        
        # Автоматично отримуємо ім'я та прізвище з контакту
        first_name = contact.first_name if contact.first_name else ""
        last_name = contact.last_name if contact.last_name else ""
        
        context.user_data['name'] = first_name
        context.user_data['lastname'] = last_name
        
        # Приховуємо клавіатуру з кнопкою контакту
        from telegram import ReplyKeyboardRemove
        
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Якщо є ім'я в контакті, одразу завершуємо реєстрацію
        if first_name:
            # Створюємо нового клієнта
            user = update.effective_user
            new_customer = Customer(
                telegram_id=str(user.id),
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                current_discount=1  # Початкова знижка 1% за реєстрацію
            )
            new_customer.save()
            
            # Очищуємо дані реєстрації
            context.user_data.clear()
            
            update.message.reply_text(
                f"🎉 Вітаємо, {first_name}!\n\n"
                f"✅ Ваш номер: {phone}\n"
                f"👤 Ім'я: {first_name}\n"
                f"👤 Прізвище: {last_name if last_name else 'не вказано'}\n\n"
                "Ви успішно зареєстровані! Тепер ви можете користуватися всіма функціями бота.\n\n"
                f"💰 Ваш рівень знижки: Starter ({new_customer.current_discount}%)\n"
                "🛒 Використовуйте кнопку 'Швидка покупка' для здійснення покупок.",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Показуємо головне меню
            start(update, context)
        else:
            # Якщо немає імені в контакті, просимо ввести
            context.user_data['registration_step'] = 'name'
            
            update.message.reply_text(
                f"✅ Дякуємо! Ваш номер {phone} збережено.\n\n"
                "Тепер, будь ласка, введіть ваше ім'я:",
                reply_markup=ReplyKeyboardRemove()
            )
            
            update.message.reply_text(
                "Введіть ваше ім'я:",
                reply_markup=reply_markup
            )
        return
    
    if 'registration_step' in context.user_data:
        if context.user_data['registration_step'] == 'phone_consent':
            # Якщо користувач надіслав текст замість контакту
            keyboard = [
                [KeyboardButton("📱 Поділитися номером телефону", request_contact=True)],
                [KeyboardButton("🏠 Головне меню")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            update.message.reply_text(
                "📱 Будь ласка, натисніть кнопку \"Поділитися номером телефону\" для автоматичного отримання номера з вашого Telegram акаунту.",
                reply_markup=reply_markup
            )
            return
        
        elif context.user_data['registration_step'] == 'name':
            # Обробка імені
            name = update.message.text.strip()
            if not name:
                keyboard = [
                    [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(
                    "Будь ласка, введіть ваше ім'я",
                    reply_markup=reply_markup
                )
                return
            
            context.user_data['name'] = name
            context.user_data['registration_step'] = 'last_name'
            
            keyboard = [
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Тепер, будь ласка, введіть ваше прізвище (або натисніть /skip, щоб пропустити)",
                reply_markup=reply_markup
            )
        
        elif context.user_data['registration_step'] == 'last_name':
            # Обробка прізвища та завершення реєстрації
            last_name = update.message.text.strip()
            if update.message.text == '/skip':
                last_name = None
            
            user = update.effective_user
            
            # Створюємо нового клієнта
            customer = Customer(
                telegram_id=str(user.id),
                first_name=context.user_data['name'],
                last_name=last_name,
                phone_number=context.user_data['phone'],
                current_discount=1,  # Початкова знижка 1% за реєстрацію
                total_spent=0
            )
            customer.save()
            
            # Очищаємо дані реєстрації
            context.user_data.clear()
            
            keyboard = [
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                f"🎉 Вітаємо, {customer.first_name}! Ви успішно зареєструвалися в нашій системі лояльності.\n\n"
                f"💎 Ваш рівень: Starter\n"
                f"💰 Ваша знижка: {customer.current_discount}%\n\n"
                f"Робіть покупки та підвищуйте свій рівень для отримання більших знижок!",
                reply_markup=reply_markup
            )
    
    # Обробка адміністративних дій
    if 'admin_action' in context.user_data:
        admin_action = context.user_data['admin_action']
        
        if admin_action == 'search_user':
            # Пошук користувача
            search_query = update.message.text.strip()
            
            # Пошук за номером телефону або ім'ям
            customers = Customer.objects.filter(
                models.Q(phone_number__icontains=search_query) |
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query)
            )[:10]  # Обмежуємо до 10 результатів
            
            keyboard = []
            
            if customers.exists():
                for customer in customers:
                    keyboard.append([InlineKeyboardButton(
                        f"👤 {customer.first_name} {customer.last_name or ''} ({customer.phone_number})",
                        callback_data=f"admin_user_details_{customer.id}"
                    )])
            
            keyboard.extend([
                [InlineKeyboardButton("🔍 Новий пошук", callback_data="admin_search_user")],
                [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if customers.exists():
                search_text = f"🔍 **Результати пошуку для '{search_query}':**\n\nЗнайдено {customers.count()} користувачів:\n\nНатисніть на користувача для перегляду деталей:"
            else:
                search_text = f"🔍 **Результати пошуку для '{search_query}':**\n\n❌ Користувачів не знайдено.\n\nСпробуйте інший запит або перевірте правильність введених даних."
            
            update.message.reply_text(search_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data.pop('admin_action', None)
            return
        
        elif admin_action.startswith('edit_'):
            # Редагування полів користувача
            field_type = admin_action.split('_')[1]  # name, lastname, phone, spent
            user_id = context.user_data.get('edit_user_id')
            
            if not user_id:
                return
            
            try:
                customer = Customer.objects.get(id=user_id)
                new_value = update.message.text.strip()
                
                if field_type == 'name':
                    if not new_value:
                        update.message.reply_text("❌ Ім'я не може бути порожнім")
                        return
                    customer.first_name = new_value
                    success_msg = f"✅ Ім'я змінено на '{new_value}'"
                    
                elif field_type == 'lastname':
                    customer.last_name = new_value if new_value else None
                    success_msg = f"✅ Прізвище змінено на '{new_value}'"
                    
                elif field_type == 'phone':
                    if not new_value.startswith('+380') or len(new_value) != 13:
                        update.message.reply_text("❌ Неправильний формат номера. Використовуйте формат +380XXXXXXXXX")
                        return
                    customer.phone_number = new_value
                    success_msg = f"✅ Номер телефону змінено на '{new_value}'"
                    
                elif field_type == 'spent':
                    try:
                        spent_amount = float(new_value)
                        if spent_amount < 0:
                            update.message.reply_text("❌ Сума не може бути від'ємною")
                            return
                        customer.total_spent = spent_amount
                        success_msg = f"✅ Загальна сума покупок змінена на {spent_amount:.2f} грн"
                    except ValueError:
                        update.message.reply_text("❌ Введіть правильну суму (число)")
                        return
                
                customer.save()
                
                keyboard = [
                    [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                    [InlineKeyboardButton("✏️ Продовжити редагування", callback_data=f"admin_edit_user_{user_id}")],
                    [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                update.message.reply_text(success_msg, reply_markup=reply_markup)
                
                # Очищаємо дані редагування
                context.user_data.pop('admin_action', None)
                context.user_data.pop('edit_user_id', None)
                
            except Customer.DoesNotExist:
                update.message.reply_text("❌ Користувача не знайдено")
                context.user_data.pop('admin_action', None)
                context.user_data.pop('edit_user_id', None)
            
            return
    
    # Обробка дій зміни профілю клієнта
    if 'profile_action' in context.user_data:
        profile_action = context.user_data['profile_action']
        customer_id = context.user_data.get('customer_id')
        
        if not customer_id:
            update.message.reply_text("❌ Помилка: дані сесії втрачено")
            context.user_data.clear()
            return
        
        try:
            customer = Customer.objects.get(id=customer_id)
            
            if profile_action == 'change_phone' and update.message.contact:
                # Зміна номера телефону через контакт
                contact = update.message.contact
                new_phone = contact.phone_number
                
                # Додаємо + якщо його немає
                if not new_phone.startswith('+'):
                    new_phone = '+' + new_phone
                
                # Валідація номера телефону
                if len(new_phone) < 10 or len(new_phone) > 15:
                    update.message.reply_text("❌ Неправильний формат номера телефону. Спробуйте ще раз.")
                    return
                
                # Перевіряємо, чи не використовується цей номер іншим користувачем
                existing_customer = Customer.objects.filter(phone_number=new_phone).exclude(id=customer.id).first()
                if existing_customer:
                    update.message.reply_text("❌ Цей номер телефону вже використовується іншим користувачем.")
                    return
                
                old_phone = customer.phone_number
                customer.phone_number = new_phone
                customer.save()
                
                keyboard = [
                    [InlineKeyboardButton("⚙️ Налаштування профілю", callback_data="profile_settings")],
                    [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                from telegram import ReplyKeyboardRemove
                update.message.reply_text(
                    f"✅ **Номер телефону успішно змінено!**\n\n"
                    f"Старий номер: {old_phone}\n"
                    f"Новий номер: {new_phone}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='Markdown'
                )
                
                update.message.reply_text(
                    "Що бажаєте зробити далі?",
                    reply_markup=reply_markup
                )
                
                # Очищаємо дані профілю
                context.user_data.pop('profile_action', None)
                context.user_data.pop('customer_id', None)
                
            elif profile_action == 'change_name' and update.message.text and update.message.text != "🏠 Головне меню":
                # Зміна імені
                new_name = update.message.text.strip()
                
                if len(new_name) < 1 or len(new_name) > 50:
                    update.message.reply_text("❌ Ім'я повинно містити від 1 до 50 символів. Спробуйте ще раз:")
                    return
                
                # Перевіряємо, що ім'я містить тільки літери, пробіли та дефіси
                import re
                if not re.match(r"^[a-zA-Zа-яА-ЯіІїЇєЄ\s\-']+$", new_name):
                    update.message.reply_text("❌ Ім'я може містити тільки літери, пробіли, дефіси та апострофи. Спробуйте ще раз:")
                    return
                
                old_name = customer.first_name
                customer.first_name = new_name
                customer.save()
                
                keyboard = [
                    [InlineKeyboardButton("⚙️ Налаштування профілю", callback_data="profile_settings")],
                    [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                from telegram import ReplyKeyboardRemove
                update.message.reply_text(
                    f"✅ **Ім'я успішно змінено!**\n\n"
                    f"Старе ім'я: {old_name}\n"
                    f"Нове ім'я: {new_name}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='Markdown'
                )
                
                update.message.reply_text(
                    "Що бажаєте зробити далі?",
                    reply_markup=reply_markup
                )
                
                # Очищаємо дані профілю
                context.user_data.pop('profile_action', None)
                context.user_data.pop('customer_id', None)
                
            elif profile_action == 'change_lastname' and update.message.text and update.message.text != "🏠 Головне меню":
                # Зміна прізвища
                new_lastname = update.message.text.strip()
                
                if len(new_lastname) > 50:
                    update.message.reply_text("❌ Прізвище не повинно перевищувати 50 символів. Спробуйте ще раз:")
                    return
                
                # Перевіряємо, що прізвище містить тільки літери, пробіли та дефіси (якщо не порожнє)
                if new_lastname and not re.match(r"^[a-zA-Zа-яА-ЯіІїЇєЄ\s\-']+$", new_lastname):
                    update.message.reply_text("❌ Прізвище може містити тільки літери, пробіли, дефіси та апострофи. Спробуйте ще раз:")
                    return
                
                old_lastname = customer.last_name or 'Не вказано'
                customer.last_name = new_lastname if new_lastname else None
                customer.save()
                
                keyboard = [
                    [InlineKeyboardButton("⚙️ Налаштування профілю", callback_data="profile_settings")],
                    [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                from telegram import ReplyKeyboardRemove
                update.message.reply_text(
                    f"✅ **Прізвище успішно змінено!**\n\n"
                    f"Старе прізвище: {old_lastname}\n"
                    f"Нове прізвище: {new_lastname or 'Не вказано'}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='Markdown'
                )
                
                update.message.reply_text(
                    "Що бажаєте зробити далі?",
                    reply_markup=reply_markup
                )
                
                # Очищаємо дані профілю
                context.user_data.pop('profile_action', None)
                context.user_data.pop('customer_id', None)
                
        except Customer.DoesNotExist:
            update.message.reply_text("❌ Помилка: користувача не знайдено")
            context.user_data.clear()
        
        return

def skip_command(update: Update, context: CallbackContext):
    if 'registration_step' in context.user_data and context.user_data['registration_step'] == 'last_name':
        user = update.effective_user
        
        # Створюємо нового клієнта без прізвища
        customer = Customer(
            telegram_id=str(user.id),
            first_name=context.user_data['name'],
            last_name=None,
            phone_number=context.user_data['phone'],
            current_discount=1,  # Початкова знижка 1% за реєстрацію
            total_spent=0
        )
        customer.save()
        
        # Очищаємо дані реєстрації
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"🎉 Вітаємо, {customer.first_name}! Ви успішно зареєструвалися в нашій системі лояльності.\n\n"
            f"💎 Ваш рівень: Starter\n"
            f"💰 Ваша знижка: {customer.current_discount}%\n\n"
            f"Робіть покупки та підвищуйте свій рівень для отримання більших знижок!",
            reply_markup=reply_markup
        )

def my_discount(update: Update, context: CallbackContext):
    user = update.effective_user
    
    try:
        customer = Customer.objects.get(telegram_id=str(user.id))
        # Визначаємо поточний рівень клієнта
        level, discount = get_customer_level(customer.total_spent)
        
        # Оновлюємо знижку клієнта, якщо вона змінилася
        if customer.current_discount != discount:
            customer.current_discount = discount
            customer.save()
        
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"💎 Ваш рівень: {level}\n"
            f"💰 Ваша знижка: {discount}%\n"
            f"🛒 Загальна сума покупок: {customer.total_spent} грн",
            reply_markup=reply_markup
        )
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("Зареєструватися", callback_data="register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Ви ще не зареєстровані в нашій системі лояльності.\n"
            "Для отримання знижок, будь ласка, зареєструйтеся.",
            reply_markup=reply_markup
        )

def show_discount_levels(update: Update, context: CallbackContext):
    """Показує всі рівні знижок"""
    keyboard = [
        [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    levels_text = (
        "📊 **Рівні знижок:**\n\n"
        "🔹 **Starter** (0 - 1 999 грн) - 1%\n"
        "🔸 **Regular** (2 000 - 4 999 грн) - 3%\n"
        "🔸 **Pro** (5 000 - 9 999 грн) - 5%\n"
        "🔶 **Elite** (10 000 - 19 999 грн) - 7%\n"
        "💎 **VIP** (20 000 грн і більше) - 10%\n\n"
        "Ваш рівень визначається загальною сумою всіх покупок!"
    )
    
    update.message.reply_text(levels_text, reply_markup=reply_markup, parse_mode='Markdown')
def one_click_process(update: Update, context: CallbackContext):
    user = update.effective_user
    
    try:
        customer = Customer.objects.get(telegram_id=str(user.id))
        
        # Генеруємо унікальний код для касира
        import random
        import string
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        update.message.reply_text(
            f"✅ Ваш код для касира: {unique_code}\n\n"
            f"Покажіть цей код касиру для застосування вашої знижки {customer.current_discount}%\n\n"
            f"Після оплати ваша знижка буде автоматично оновлена."
        )
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("Зареєструватися", callback_data="register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Ви ще не зареєстровані в нашій системі лояльності.\n"
            "Для отримання знижок, будь ласка, зареєструйтеся.",
            reply_markup=reply_markup
        )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "register":
        register_callback(update, context)
    elif query.data == "main_menu":
        # Повертаємося до головного меню
        user = update.effective_user
        try:
            customer = Customer.objects.get(telegram_id=str(user.id))
            level, discount = get_customer_level(customer.total_spent)
            
            # Оновлюємо знижку клієнта, якщо вона змінилася
            if customer.current_discount != discount:
                customer.current_discount = discount
                customer.save()
            
            keyboard = [
                [InlineKeyboardButton("🛒 Швидка покупка", callback_data="oneclick")],
                [InlineKeyboardButton("💰 Моя знижка", callback_data="discount")],
                [InlineKeyboardButton("📊 Рівні знижок", callback_data="levels")],
                [InlineKeyboardButton("📋 Історія покупок", callback_data="history")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.message.reply_text(
                f"Головне меню 🏠\n\n"
                f"💎 Ваш рівень: {level}\n"
                f"💰 Ваша знижка: {discount}%\n"
                f"🛒 Загальна сума покупок: {customer.total_spent} грн",
                reply_markup=reply_markup
            )
        except Customer.DoesNotExist:
            keyboard = [
                [InlineKeyboardButton("Зареєструватися", callback_data="register")],
                [InlineKeyboardButton("📊 Рівні знижок", callback_data="levels")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                "Вітаємо в системі лояльності нашого магазину! 🎉\n\n"
                "Для отримання знижок, будь ласка, зареєструйтеся.",
                reply_markup=reply_markup
            )
    elif query.data == "levels":
        # Показуємо рівні знижок
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        levels_text = (
            "📊 **Рівні знижок:**\n\n"
            "🔹 **Starter** (0 - 1 999 грн) - 1%\n"
            "🔸 **Regular** (2 000 - 4 999 грн) - 3%\n"
            "🔸 **Pro** (5 000 - 9 999 грн) - 5%\n"
            "🔶 **Elite** (10 000 - 19 999 грн) - 7%\n"
            "💎 **VIP** (20 000 грн і більше) - 10%\n\n"
            "Ваш рівень визначається загальною сумою всіх покупок!"
        )
        
        query.message.reply_text(levels_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "help":
        # Показуємо допомогу
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        help_text = (
            "📖 **Інструкція користувача**\n\n"
            "🚀 **Початок роботи:**\n"
            "• Натисніть /start для початку\n"
            "• Зареєструйтеся для отримання знижок\n\n"
            "💎 **Рівні знижок:**\n"
            "• 🔹 Starter (0-1999 грн) - 1%\n"
            "• 🔶 Regular (2000-4999 грн) - 3%\n"
            "• 🔶 Pro (5000-9999 грн) - 5%\n"
            "• 🟡 Elite (10000-19999 грн) - 7%\n"
            "• 💎 VIP (20000+ грн) - 10%\n\n"
            "🛒 **Як здійснити покупку:**\n"
            "1. Натисніть \"Швидка покупка\"\n"
            "2. Покажіть код касиру\n"
            "3. Отримайте знижку!\n\n"
            "🔧 **Команди:**\n"
            "• /start - головне меню\n"
            "• /help - ця інструкція\n"
            "• /discount - моя знижка\n"
            "• /history - історія покупок\n"
            "• /oneclick - швидка покупка"
        )
        
        query.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_stats":
        # Статистика системи
        from telegram_bot.models import DiscountCode
        from django.utils import timezone
        
        total_customers = Customer.objects.count()
        total_purchases = Purchase.objects.count()
        active_codes = DiscountCode.objects.filter(is_used=False, expires_at__gt=timezone.now()).count()
        total_spent = sum(customer.total_spent for customer in Customer.objects.all())
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        stats_text = (
            "📊 **Статистика системи**\n\n"
            f"👥 Всього клієнтів: {total_customers}\n"
            f"🛒 Всього покупок: {total_purchases}\n"
            f"🎫 Активних кодів: {active_codes}\n"
            f"💰 Загальна сума покупок: {total_spent:.2f} грн"
        )
        
        query.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_customers":
        # Список клієнтів
        customers = Customer.objects.order_by('-total_spent')[:10]
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        customers_text = "👥 **Топ-10 клієнтів:**\n\n"
        for i, customer in enumerate(customers, 1):
            level, discount = get_customer_level(customer.total_spent)
            customers_text += f"{i}. {customer.first_name} {customer.last_name}\n"
            customers_text += f"   📱 {customer.phone_number}\n"
            customers_text += f"   💎 {level} ({discount}%) - {customer.total_spent:.2f} грн\n\n"
        
        query.message.reply_text(customers_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_codes":
        # Активні коди
        from telegram_bot.models import DiscountCode
        from django.utils import timezone
        
        active_codes = DiscountCode.objects.filter(
            is_used=False, 
            expires_at__gt=timezone.now()
        ).order_by('-created_at')[:10]
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        codes_text = "🎫 **Активні коди знижок:**\n\n"
        for code in active_codes:
            codes_text += f"🔹 **{code.code}**\n"
            codes_text += f"   👤 {code.customer.first_name} {code.customer.last_name}\n"
            codes_text += f"   ⏰ Діє до: {code.expires_at.strftime('%H:%M %d.%m.%Y')}\n\n"
        
        if not active_codes:
            codes_text += "Немає активних кодів"
        
        query.message.reply_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_purchases":
        # Останні покупки
        purchases = Purchase.objects.order_by('-purchase_date')[:10]
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        purchases_text = "💰 **Останні покупки:**\n\n"
        for purchase in purchases:
            purchases_text += f"🛒 {purchase.amount:.2f} грн (знижка {purchase.discount_applied}%)\n"
            purchases_text += f"   👤 {purchase.customer.first_name} {purchase.customer.last_name}\n"
            purchases_text += f"   📅 {format_ukraine_time(purchase.purchase_date)}\n\n"
        
        if not purchases:
            purchases_text += "Немає покупок"
        
        query.message.reply_text(purchases_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_analytics":
        # Детальна аналітика
        from datetime import datetime, timedelta
        from django.db.models import Count, Sum, Avg
        from django.utils import timezone
        
        # Статистика за останній місяць
        last_month = timezone.now() - timedelta(days=30)
        monthly_customers = Customer.objects.filter(registration_date__gte=last_month).count()
        monthly_purchases = Purchase.objects.filter(purchase_date__gte=last_month).count()
        monthly_revenue = Purchase.objects.filter(purchase_date__gte=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Топ клієнти
        top_customers = Customer.objects.order_by('-total_spent')[:5]
        
        # Середній чек
        avg_purchase = Purchase.objects.aggregate(Avg('amount'))['amount__avg'] or 0
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        analytics_text = (
            "📈 **Детальна аналітика**\n\n"
            "📅 **За останній місяць:**\n"
            f"👥 Нових клієнтів: {monthly_customers}\n"
            f"🛒 Покупок: {monthly_purchases}\n"
            f"💰 Дохід: {monthly_revenue:.2f} грн\n\n"
            f"📊 **Середній чек:** {avg_purchase:.2f} грн\n\n"
            "🏆 **Топ-5 клієнтів:**\n"
        )
        
        for i, customer in enumerate(top_customers, 1):
            analytics_text += f"{i}. {customer.first_name} {customer.last_name} - {customer.total_spent:.2f} грн\n"
        
        query.message.reply_text(analytics_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_clear_db":
        # Очищення бази даних користувачів
        if not is_admin(query.from_user.id):
            query.answer("❌ У вас немає прав адміністратора.")
            return
        
        keyboard = [
            [InlineKeyboardButton("✅ Так, очистити", callback_data="admin_clear_confirm")],
            [InlineKeyboardButton("❌ Скасувати", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        warning_text = (
            "⚠️ **УВАГА!**\n\n"
            "Ви збираєтеся **ПОВНІСТЮ ОЧИСТИТИ** базу даних користувачів!\n\n"
            "Це дія **НЕЗВОРОТНА** і видалить:\n"
            "• Всіх зареєстрованих клієнтів\n"
            "• Всю історію покупок\n"
            "• Всі коди знижок\n\n"
            "**Ви впевнені, що хочете продовжити?**"
        )
        
        query.message.reply_text(warning_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_clear_confirm":
        # Підтвердження очищення бази даних
        if not is_admin(query.from_user.id):
            query.answer("❌ У вас немає прав адміністратора.")
            return
        
        try:
            # Імпорт моделі DiscountCode
            from telegram_bot.models import DiscountCode
            
            # Підрахунок записів перед видаленням
            customers_count = Customer.objects.count()
            purchases_count = Purchase.objects.count()
            codes_count = DiscountCode.objects.count()
            
            # Очищення бази даних
            Purchase.objects.all().delete()
            DiscountCode.objects.all().delete()
            Customer.objects.all().delete()
            
            keyboard = [
                [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            success_text = (
                "✅ **База даних успішно очищена!**\n\n"
                "Видалено:\n"
                f"👥 Клієнтів: {customers_count}\n"
                f"🛒 Покупок: {purchases_count}\n"
                f"🎫 Кодів знижок: {codes_count}\n\n"
                "Система готова до роботи з чистою базою даних."
            )
            
            query.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            keyboard = [
                [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            error_text = (
                "❌ **Помилка при очищенні бази даних!**\n\n"
                f"Деталі помилки: {str(e)}\n\n"
                "Спробуйте ще раз або зверніться до розробника."
            )
            
            query.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_user_management":
        # Управління користувачами
        keyboard = [
            [InlineKeyboardButton("🔍 Пошук користувача", callback_data="admin_search_user")],
            [InlineKeyboardButton("📝 Список всіх користувачів", callback_data="admin_all_users")],
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        management_text = (
            "👤 **Управління користувачами**\n\n"
            "🔍 Пошук користувача - знайти за номером телефону або ім'ям\n"
            "📝 Список всіх користувачів - перегляд з можливістю редагування\n\n"
            "Оберіть дію:"
        )
        
        query.message.reply_text(management_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_search_user":
        # Пошук користувача
        keyboard = [
            [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        search_text = (
            "🔍 **Пошук користувача**\n\n"
            "Введіть номер телефону (у форматі +380XXXXXXXXX) або ім'я користувача для пошуку:\n\n"
            "Приклад: +380501234567 або Іван"
        )
        
        query.message.reply_text(search_text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['admin_action'] = 'search_user'
    elif query.data == "admin_all_users":
        # Список всіх користувачів з пагінацією
        page = context.user_data.get('users_page', 0)
        users_per_page = 5
        start_index = page * users_per_page
        end_index = start_index + users_per_page
        
        all_customers = Customer.objects.order_by('-registration_date')
        total_customers = all_customers.count()
        customers = all_customers[start_index:end_index]
        
        keyboard = []
        
        # Додаємо кнопки для кожного користувача
        for customer in customers:
            keyboard.append([InlineKeyboardButton(
                f"👤 {customer.first_name} {customer.last_name or ''} ({customer.phone_number})",
                callback_data=f"admin_user_details_{customer.id}"
            )])
        
        # Кнопки навігації
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Попередня", callback_data="admin_users_prev"))
        if end_index < total_customers:
            nav_buttons.append(InlineKeyboardButton("Наступна ➡️", callback_data="admin_users_next"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        users_text = (
            f"📝 **Список користувачів** (сторінка {page + 1})\n\n"
            f"Показано {start_index + 1}-{min(end_index, total_customers)} з {total_customers} користувачів\n\n"
            "Натисніть на користувача для перегляду деталей:"
        )
        
        query.message.reply_text(users_text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['users_page'] = page
    elif query.data == "admin_users_prev":
        # Попередня сторінка користувачів
        current_page = context.user_data.get('users_page', 0)
        context.user_data['users_page'] = max(0, current_page - 1)
        # Повторно викликаємо admin_all_users
        query.data = "admin_all_users"
        return handle_callback_query(update, context)
    elif query.data == "admin_users_next":
        # Наступна сторінка користувачів
        current_page = context.user_data.get('users_page', 0)
        context.user_data['users_page'] = current_page + 1
        # Повторно викликаємо admin_all_users
        query.data = "admin_all_users"
        return handle_callback_query(update, context)
    elif query.data.startswith("admin_user_details_"):
        # Деталі користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            level, discount = get_customer_level(customer.total_spent)
            
            # Отримуємо статистику покупок
            purchases_count = Purchase.objects.filter(customer=customer).count()
            last_purchase = Purchase.objects.filter(customer=customer).order_by('-purchase_date').first()
            
            keyboard = [
                [InlineKeyboardButton("✏️ Редагувати", callback_data=f"admin_edit_user_{user_id}")],
                [InlineKeyboardButton("🗑️ Видалити", callback_data=f"admin_delete_user_{user_id}")],
                [InlineKeyboardButton("📝 Список користувачів", callback_data="admin_all_users")],
                [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            details_text = (
                f"👤 **Деталі користувача**\n\n"
                f"🆔 ID: {customer.id}\n"
                f"👤 Ім'я: {customer.first_name}\n"
                f"👤 Прізвище: {customer.last_name or 'Не вказано'}\n"
                f"📱 Телефон: {customer.phone_number}\n"
                f"💰 Загальна сума покупок: {customer.total_spent:.2f} грн\n"
                f"💎 Рівень: {level} ({discount}%)\n"
                f"🛒 Кількість покупок: {purchases_count}\n"
                f"📅 Дата реєстрації: {customer.registration_date.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            if last_purchase:
                details_text += f"🛍️ Остання покупка: {format_ukraine_time(last_purchase.purchase_date)} ({last_purchase.amount:.2f} грн)\n"
            else:
                details_text += "🛍️ Покупок ще не було\n"
            
            query.message.reply_text(details_text, reply_markup=reply_markup, parse_mode='Markdown')
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_edit_user_name_"):
        # Редагування імені користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            edit_text = (
                f"✏️ **Редагування імені**\n\n"
                f"Поточне ім'я: {customer.first_name}\n\n"
                "Введіть нове ім'я користувача:"
            )
            
            query.message.reply_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data['admin_action'] = 'edit_name'
            context.user_data['edit_user_id'] = user_id
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_edit_user_lastname_"):
        # Редагування прізвища користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            edit_text = (
                f"✏️ **Редагування прізвища**\n\n"
                f"Поточне прізвище: {customer.last_name or 'Не вказано'}\n\n"
                "Введіть нове прізвище користувача (або залиште порожнім для видалення):"
            )
            
            query.message.reply_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data['admin_action'] = 'edit_lastname'
            context.user_data['edit_user_id'] = user_id
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_edit_user_phone_"):
        # Редагування телефону користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            edit_text = (
                f"✏️ **Редагування номера телефону**\n\n"
                f"Поточний номер: {customer.phone_number}\n\n"
                "Введіть новий номер телефону у форматі +380XXXXXXXXX:"
            )
            
            query.message.reply_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data['admin_action'] = 'edit_phone'
            context.user_data['edit_user_id'] = user_id
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_edit_user_spent_"):
        # Редагування загальної суми покупок
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            edit_text = (
                f"✏️ **Редагування загальної суми покупок**\n\n"
                f"Поточна сума: {customer.total_spent:.2f} грн\n\n"
                "Введіть нову загальну суму покупок (число):"
            )
            
            query.message.reply_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data['admin_action'] = 'edit_spent'
            context.user_data['edit_user_id'] = user_id
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_edit_user_"):
        # Редагування користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("✏️ Змінити ім'я", callback_data=f"admin_edit_user_name_{user_id}")],
                [InlineKeyboardButton("✏️ Змінити прізвище", callback_data=f"admin_edit_user_lastname_{user_id}")],
                [InlineKeyboardButton("📱 Змінити телефон", callback_data=f"admin_edit_user_phone_{user_id}")],
                [InlineKeyboardButton("💰 Змінити суму покупок", callback_data=f"admin_edit_user_spent_{user_id}")],
                [InlineKeyboardButton("👤 Деталі користувача", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            edit_text = (
                f"✏️ **Редагування користувача**\n\n"
                f"👤 {customer.first_name} {customer.last_name or ''}\n"
                f"📱 {customer.phone_number}\n"
                f"💰 {customer.total_spent:.2f} грн\n\n"
                "Оберіть що хочете змінити:"
            )
            
            query.message.reply_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_delete_user_"):
        # Підтвердження видалення користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            
            keyboard = [
                [InlineKeyboardButton("✅ Так, видалити", callback_data=f"admin_confirm_delete_{user_id}")],
                [InlineKeyboardButton("❌ Скасувати", callback_data=f"admin_user_details_{user_id}")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            delete_text = (
                f"🗑️ **Видалення користувача**\n\n"
                f"⚠️ **УВАГА!** Ви збираєтесь видалити користувача:\n\n"
                f"👤 {customer.first_name} {customer.last_name or ''}\n"
                f"📱 {customer.phone_number}\n"
                f"💰 {customer.total_spent:.2f} грн\n\n"
                "❗ Ця дія незворотна! Всі дані користувача та його покупки будуть видалені.\n\n"
                "Ви впевнені?"
            )
            
            query.message.reply_text(delete_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data.startswith("admin_confirm_delete_"):
        # Остаточне видалення користувача
        user_id = int(query.data.split("_")[-1])
        try:
            customer = Customer.objects.get(id=user_id)
            customer_name = f"{customer.first_name} {customer.last_name or ''}"
            customer_phone = customer.phone_number
            
            # Видаляємо всі пов'язані дані
            Purchase.objects.filter(customer=customer).delete()
            from telegram_bot.models import DiscountCode
            DiscountCode.objects.filter(customer=customer).delete()
            
            # Видаляємо самого користувача
            customer.delete()
            
            keyboard = [
                [InlineKeyboardButton("📝 Список користувачів", callback_data="admin_all_users")],
                [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            success_text = (
                f"✅ **Користувача видалено**\n\n"
                f"👤 {customer_name}\n"
                f"📱 {customer_phone}\n\n"
                "Користувач та всі пов'язані дані успішно видалені з системи."
            )
            
            query.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Customer.DoesNotExist:
            query.message.reply_text("❌ Користувача не знайдено")
    elif query.data == "admin_settings":
        # Налаштування системи
        keyboard = [
            [InlineKeyboardButton("💎 Рівні знижок", callback_data="admin_discount_levels")],
            [InlineKeyboardButton("⏰ Час дії кодів", callback_data="admin_code_expiry")],
            [InlineKeyboardButton("📊 Мінімальна сума", callback_data="admin_min_amount")],
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = (
            "⚙️ **Налаштування системи**\n\n"
            "Поточні налаштування:\n"
            "💎 Рівні знижок: Starter(1%), Regular(3%), Pro(5%), Elite(7%), VIP(10%)\n"
            "⏰ Час дії кодів: 30 хвилин\n"
            "📊 Мінімальна сума: 0 грн\n\n"
            "Оберіть що хочете налаштувати:"
        )
        
        query.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_export":
        # Експорт даних
        import csv
        import io
        from datetime import datetime
        
        # Створюємо CSV файл з даними клієнтів
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Імя', 'Прізвище', 'Телефон', 'Загальна сума', 'Дата реєстрації', 'Рівень'])
        
        for customer in Customer.objects.all():
            level, discount = get_customer_level(customer.total_spent)
            writer.writerow([
                customer.id,
                customer.first_name,
                customer.last_name,
                customer.phone_number,
                customer.total_spent,
                customer.registration_date.strftime('%Y-%m-%d'),
                level
            ])
        
        keyboard = [
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        export_text = (
            "📤 **Експорт даних**\n\n"
            f"📊 Експортовано {Customer.objects.count()} клієнтів\n"
            f"📅 Дата експорту: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "📋 Дані готові до завантаження"
        )
        
        # Відправляємо файл
        csv_content = output.getvalue().encode('utf-8')
        context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(csv_content),
            filename=f"customers_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            caption=export_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif query.data == "admin_broadcast":
        # Розсилка повідомлень
        from datetime import timedelta
        from django.utils import timezone
        
        keyboard = [
            [InlineKeyboardButton("📢 Всім клієнтам", callback_data="broadcast_all")],
            [InlineKeyboardButton("💎 VIP клієнтам", callback_data="broadcast_vip")],
            [InlineKeyboardButton("🆕 Новим клієнтам", callback_data="broadcast_new")],
            [InlineKeyboardButton("🔧 Панель адміністратора", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        broadcast_text = (
            "🔔 **Розсилка повідомлень**\n\n"
            f"👥 Всього клієнтів: {Customer.objects.count()}\n"
            f"💎 VIP клієнтів: {Customer.objects.filter(total_spent__gte=20000).count()}\n"
            f"🆕 Нових клієнтів (за тиждень): {Customer.objects.filter(registration_date__gte=timezone.now() - timedelta(days=7)).count()}\n\n"
            "Оберіть цільову аудиторію:"
        )
        
        query.message.reply_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "broadcast_all":
        # Розсилка всім клієнтам
        customers = Customer.objects.all()
        keyboard = [
            [InlineKeyboardButton("🔔 Розсилка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        broadcast_text = (
            "📢 **Розсилка всім клієнтам**\n\n"
            f"👥 Буде відправлено {customers.count()} клієнтам\n\n"
            "⚠️ Функція розсилки буде доступна в наступному оновленні.\n"
            "Зараз ви можете зв'язатися з клієнтами індивідуально."
        )
        
        query.message.reply_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "broadcast_vip":
        # Розсилка VIP клієнтам
        vip_customers = Customer.objects.filter(total_spent__gte=20000)
        keyboard = [
            [InlineKeyboardButton("🔔 Розсилка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        broadcast_text = (
            "💎 **Розсилка VIP клієнтам**\n\n"
            f"👑 Буде відправлено {vip_customers.count()} VIP клієнтам\n\n"
            "⚠️ Функція розсилки буде доступна в наступному оновленні.\n"
            "Зараз ви можете зв'язатися з VIP клієнтами індивідуально."
        )
        
        query.message.reply_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "broadcast_new":
        # Розсилка новим клієнтам
        from datetime import timedelta
        from django.utils import timezone
        
        new_customers = Customer.objects.filter(registration_date__gte=timezone.now() - timedelta(days=7))
        keyboard = [
            [InlineKeyboardButton("🔔 Розсилка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        broadcast_text = (
            "🆕 **Розсилка новим клієнтам**\n\n"
            f"👶 Буде відправлено {new_customers.count()} новим клієнтам\n\n"
            "⚠️ Функція розсилки буде доступна в наступному оновленні.\n"
            "Зараз ви можете зв'язатися з новими клієнтами індивідуально."
        )
        
        query.message.reply_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_discount_levels":
        # Налаштування рівнів знижок
        keyboard = [
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="admin_settings")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        levels_text = (
            "💎 **Рівні знижок**\n\n"
            "📊 Поточні рівні:\n"
            "🥉 Starter: 0-999 грн (1% знижка)\n"
            "🥈 Regular: 1000-4999 грн (3% знижка)\n"
            "🥇 Pro: 5000-9999 грн (5% знижка)\n"
            "💎 Elite: 10000-19999 грн (7% знижка)\n"
            "👑 VIP: 20000+ грн (10% знижка)\n\n"
            "⚠️ Зміна рівнів знижок буде доступна в наступному оновленні."
        )
        
        query.message.reply_text(levels_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_code_expiry":
        # Налаштування часу дії кодів
        keyboard = [
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="admin_settings")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        expiry_text = (
            "⏰ **Час дії кодів**\n\n"
            "📅 Поточне налаштування: 30 хвилин\n\n"
            "ℹ️ Коди знижок діють протягом 30 хвилин після генерації.\n"
            "Після закінчення цього часу код стає недійсним.\n\n"
            "⚠️ Зміна часу дії кодів буде доступна в наступному оновленні."
        )
        
        query.message.reply_text(expiry_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_min_amount":
        # Налаштування мінімальної суми
        keyboard = [
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="admin_settings")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        min_amount_text = (
            "📊 **Мінімальна сума**\n\n"
            "💰 Поточне налаштування: 0 грн\n\n"
            "ℹ️ Мінімальна сума покупки для отримання знижки.\n"
            "Зараз знижка застосовується до будь-якої суми.\n\n"
            "⚠️ Зміна мінімальної суми буде доступна в наступному оновленні."
        )
        
        query.message.reply_text(min_amount_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "admin_panel":
        # Повернення до панелі адміністратора
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"), InlineKeyboardButton("📈 Аналітика", callback_data="admin_analytics")],
            [InlineKeyboardButton("👥 Список клієнтів", callback_data="admin_customers"), InlineKeyboardButton("🎫 Активні коди", callback_data="admin_codes")],
            [InlineKeyboardButton("👤 Управління користувачами", callback_data="admin_user_management")],
            [InlineKeyboardButton("💰 Останні покупки", callback_data="admin_purchases"), InlineKeyboardButton("⚙️ Налаштування", callback_data="admin_settings")],
            [InlineKeyboardButton("📤 Експорт даних", callback_data="admin_export"), InlineKeyboardButton("🔔 Розсилка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🗑️ Очистити базу", callback_data="admin_clear_db")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_text = (
            "🔧 **Панель адміністратора**\n\n"
            "📊 Керування системою лояльності\n"
            "Оберіть дію:"
        )
        
        query.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "oneclick":
        # Викликаємо функцію швидкого процесу
        user = update.effective_user
        try:
            customer = Customer.objects.get(telegram_id=str(user.id))
            level, discount = get_customer_level(customer.total_spent)
            
            # Генеруємо унікальний код для касира
            import random
            import string
            from datetime import timedelta
            from django.utils import timezone
            from telegram_bot.models import DiscountCode
            
            # Генеруємо унікальний код
            while True:
                unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not DiscountCode.objects.filter(code=unique_code).exists():
                    break
            
            # Зберігаємо код в базі даних (діє 30 хвилин)
            expires_at = timezone.now() + timedelta(minutes=30)
            discount_code = DiscountCode.objects.create(
                code=unique_code,
                customer=customer,
                expires_at=expires_at
            )
            
            keyboard = [
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Надсилаємо нове повідомлення замість редагування
            query.message.reply_text(
                f"✅ Ваш код для касира: **{unique_code}**\n\n"
                f"Покажіть цей код касиру для застосування вашої знижки {discount}%\n\n"
                f"Після оплати ваша знижка буде автоматично оновлена.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Customer.DoesNotExist:
            # Якщо користувач не зареєстрований
            keyboard = [
                [InlineKeyboardButton("Зареєструватися", callback_data="register")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                "Ви ще не зареєстровані в нашій системі лояльності.\n"
                "Для отримання знижок, будь ласка, зареєструйтеся.",
                reply_markup=reply_markup
            )
    elif query.data == "discount":
        # Обробка кнопки "Моя знижка"
        user = update.effective_user
        try:
            customer = Customer.objects.get(telegram_id=str(user.id))
            level, discount = get_customer_level(customer.total_spent)
            
            keyboard = [
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.message.reply_text(
                f"💎 Ваш рівень: {level}\n"
                f"💰 Ваша знижка: {discount}%\n"
                f"🛒 Загальна сума покупок: {customer.total_spent} грн",
                reply_markup=reply_markup
            )
        except Customer.DoesNotExist:
            keyboard = [
                [InlineKeyboardButton("Зареєструватися", callback_data="register")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                "Ви ще не зареєстровані в нашій системі лояльності.\n"
                "Для отримання знижок, будь ласка, зареєструйтеся.",
                reply_markup=reply_markup
            )
    elif query.data == "history":
        # Обробка кнопки "Історія покупок"
        user = update.effective_user
        try:
            customer = Customer.objects.get(telegram_id=str(user.id))
            purchases = Purchase.objects.filter(customer=customer).order_by('-purchase_date')[:5]  # Останні 5 покупок
            
            keyboard = [
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if purchases:
                message = "📋 **Ваші останні покупки:**\n\n"
                for i, purchase in enumerate(purchases, 1):
                    message += f"🧾 **Покупка #{i}**\n"
                    message += f"📅 Дата: {format_ukraine_time(purchase.purchase_date)}\n"
                    message += f"💰 Сума: {purchase.amount} грн\n"
                    message += f"🎯 Застосована знижка: {purchase.discount_applied}%\n"
                    
                    # Додаємо фіскальний номер чеку, якщо він є
                    if purchase.fiscal_receipt_number:
                        message += f"🧾 Фіскальний номер: `{purchase.fiscal_receipt_number}`\n"
                    
                    # Додаємо товари з покупки
                    from loyalty.models import PurchaseItem
                    items = PurchaseItem.objects.filter(purchase=purchase)
                    if items:
                        message += "🛒 **Товари:**\n"
                        for item in items:
                            message += f"  • {item.name} x{item.quantity} = {item.total_price} грн\n"
                    
                    message += "\n"
                
                query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                query.message.reply_text("У вас ще немає історії покупок.", reply_markup=reply_markup)
        except Customer.DoesNotExist:
            keyboard = [
                [InlineKeyboardButton("Зареєструватися", callback_data="register")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                "Ви ще не зареєстровані в нашій системі лояльності.\n"
                "Для отримання знижок, будь ласка, зареєструйтеся.",
                reply_markup=reply_markup
            )



def purchase_history(update: Update, context: CallbackContext):
    user = update.effective_user
    
    try:
        customer = Customer.objects.get(telegram_id=str(user.id))
        purchases = Purchase.objects.filter(customer=customer).order_by('-purchase_date')[:10]  # Останні 10 покупок
        
        if purchases:
            message = "Ваші останні покупки:\n\n"
            for i, purchase in enumerate(purchases, 1):
                message += f"🧾 Покупка #{i}\n"
                message += f"📅 Дата: {format_ukraine_time(purchase.purchase_date)}\n"
                message += f"💰 Сума: {purchase.amount} грн\n"
                message += f"🎯 Застосована знижка: {purchase.discount_applied}%\n"
                
                # Додаємо фіскальний номер чеку, якщо він є
                if purchase.fiscal_receipt_number:
                    message += f"🧾 Фіскальний номер: {purchase.fiscal_receipt_number}\n"
                
                # Додаємо товари з покупки
                from loyalty.models import PurchaseItem
                items = PurchaseItem.objects.filter(purchase=purchase)
                if items:
                    message += "🛒 Товари:\n"
                    for item in items:
                        message += f"  • {item.name} x{item.quantity} = {item.total_price} грн\n"
                
                message += "\n"
            
            update.message.reply_text(message)
        else:
            update.message.reply_text("У вас ще немає історії покупок.")
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("Зареєструватися", callback_data="register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Ви ще не зареєстровані в нашій системі лояльності.\n"
            "Для отримання знижок, будь ласка, зареєструйтеся.",
            reply_markup=reply_markup
        )

def one_click_process(update: Update, context: CallbackContext):
    user = update.effective_user
    
    try:
        customer = Customer.objects.get(telegram_id=str(user.id))
        
        # Генеруємо унікальний код для касира
        import random
        import string
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        update.message.reply_text(
            f"✅ Ваш код для касира: {unique_code}\n\n"
            f"Покажіть цей код касиру для застосування вашої знижки {customer.current_discount}%\n\n"
            f"Після оплати ваша знижка буде автоматично оновлена."
        )
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("Зареєструватися", callback_data="register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Ви ще не зареєстровані в нашій системі лояльності.\n"
            "Для отримання знижок, будь ласка, зареєструйтеся.",
            reply_markup=reply_markup
        )

def admin_command(update: Update, context: CallbackContext):
    """Команда для адміністраторів"""
    user = update.effective_user
    
    if not is_admin(user.id):
        update.message.reply_text("❌ У вас немає прав адміністратора.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Список клієнтів", callback_data="admin_customers")],
        [InlineKeyboardButton("🎫 Активні коди", callback_data="admin_codes")],
        [InlineKeyboardButton("💰 Останні покупки", callback_data="admin_purchases")],
        [InlineKeyboardButton("🗑️ Очистити базу", callback_data="admin_clear_db")],
        [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = (
        "🔧 **Панель адміністратора**\n\n"
        "Оберіть дію:"
    )
    
    update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')

def help_command(update: Update, context: CallbackContext):
    """Відображає інструкцію користувача"""
    keyboard = [
        [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = (
        "📖 **Інструкція користувача**\n\n"
        "🚀 **Початок роботи:**\n"
        "• Натисніть /start для початку\n"
        "• Зареєструйтеся для отримання знижок\n\n"
        "💎 **Рівні знижок:**\n"
        "• 🔹 Starter (0-1999 грн) - 1%\n"
        "• 🔶 Regular (2000-4999 грн) - 3%\n"
        "• 🔶 Pro (5000-9999 грн) - 5%\n"
        "• 🟡 Elite (10000-19999 грн) - 7%\n"
        "• 💎 VIP (20000+ грн) - 10%\n\n"
        "🛒 **Як здійснити покупку:**\n"
        "1. Натисніть \"Швидка покупка\"\n"
        "2. Покажіть код касиру\n"
        "3. Отримайте знижку!\n\n"
        "⚙️ **Команди:**\n"
        "• `/start` - головне меню та початок роботи\n"
        "• `/help` - довідка та інструкція користувача\n"
        "• `/discount` - перегляд поточної знижки та рівня\n"
        "• `/history` - історія всіх покупок\n"
        "• `/oneclick` - швидка покупка з QR-кодом\n"
        "• `/skip` - пропустити крок при реєстрації\n\n"
        "💡 **Підказка:** Використовуйте кнопки меню для зручної навігації!"
    )
    
    update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def profile_settings(update: Update, context: CallbackContext):
    """Меню налаштувань профілю для клієнта"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    try:
        customer = Customer.objects.get(telegram_id=user_id)
        
        keyboard = [
            [InlineKeyboardButton("📱 Змінити номер телефону", callback_data="change_phone")],
            [InlineKeyboardButton("👤 Змінити ім'я", callback_data="change_name")],
            [InlineKeyboardButton("👤 Змінити прізвище", callback_data="change_lastname")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"⚙️ **Налаштування профілю**\n\n"
            f"**Поточні дані:**\n"
            f"👤 Ім'я: {customer.first_name}\n"
            f"👤 Прізвище: {customer.last_name or 'Не вказано'}\n"
            f"📱 Телефон: {customer.phone_number}\n\n"
            f"Оберіть, що хочете змінити:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("Зареєструватися", callback_data="register")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Ви не зареєстровані в системі лояльності.\n\n"
            "Для доступу до налаштувань профілю спочатку зареєструйтеся:",
            reply_markup=reply_markup
        )

def change_phone(update: Update, context: CallbackContext):
    """Початок процесу зміни номера телефону"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    try:
        customer = Customer.objects.get(telegram_id=user_id)
        
        # Встановлюємо дію для обробки в handle_message
        context.user_data['profile_action'] = 'change_phone'
        context.user_data['customer_id'] = customer.id
        
        keyboard = [
            [KeyboardButton("📱 Поділитися новим номером", request_contact=True)],
            [KeyboardButton("🏠 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        query.message.reply_text(
            f"📱 **Зміна номера телефону**\n\n"
            f"Поточний номер: {customer.phone_number}\n\n"
            f"Натисніть кнопку нижче, щоб поділитися новим номером телефону:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Помилка: користувача не знайдено.",
            reply_markup=reply_markup
        )

def change_name(update: Update, context: CallbackContext):
    """Початок процесу зміни імені"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    try:
        customer = Customer.objects.get(telegram_id=user_id)
        
        # Встановлюємо дію для обробки в handle_message
        context.user_data['profile_action'] = 'change_name'
        context.user_data['customer_id'] = customer.id
        
        keyboard = [
            [KeyboardButton("🏠 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        query.message.reply_text(
            f"👤 **Зміна імені**\n\n"
            f"Поточне ім'я: {customer.first_name}\n\n"
            f"Введіть нове ім'я:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Помилка: користувача не знайдено.",
            reply_markup=reply_markup
        )

def change_lastname(update: Update, context: CallbackContext):
    """Початок процесу зміни прізвища"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    try:
        customer = Customer.objects.get(telegram_id=user_id)
        
        # Встановлюємо дію для обробки в handle_message
        context.user_data['profile_action'] = 'change_lastname'
        context.user_data['customer_id'] = customer.id
        
        keyboard = [
            [KeyboardButton("🏠 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        query.message.reply_text(
            f"👤 **Зміна прізвища**\n\n"
            f"Поточне прізвище: {customer.last_name or 'Не вказано'}\n\n"
            f"Введіть нове прізвище:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Customer.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        
        query.edit_message_text(
            "❌ Помилка: користувача не знайдено.",
            reply_markup=reply_markup
        )

def main():
    # Використовуємо Updater для версії 13.15
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Додаємо обробники команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("skip", skip_command))
    dispatcher.add_handler(CommandHandler("discount", my_discount))
    dispatcher.add_handler(CommandHandler("history", purchase_history))
    dispatcher.add_handler(CommandHandler("oneclick", one_click_process))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    # Обробник кнопок
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    # Обробник контактів
    dispatcher.add_handler(MessageHandler(Filters.contact, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Запускаємо бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()