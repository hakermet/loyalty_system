from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.db import models
from telegram_bot.models import DiscountCode
from telegram_bot.admin_config import ADMIN_IDS
import json
import csv
import requests
from django.conf import settings

def cashier_interface(request):
    """Веб-інтерфейс для касирів"""
    return render(request, 'cashier_interface.html')

@csrf_exempt
def login_view(request):
    """Сторінка входу"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('login')
            password = data.get('password')
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Успішний вхід!',
                    'redirect_url': '/cashier/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Невірний логін або пароль'
                })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Помилка обробки даних'
            })
    
    return render(request, 'login.html')



def logout_view(request):
    """Вихід з системи"""
    logout(request)
    return redirect('login')

@login_required
def admin_panel(request):
    """Адміністративна панель"""
    # Перевіряємо, чи користувач є адміністратором
    if not request.user.is_superuser:
        return redirect('login')
    
    return render(request, 'admin_panel.html')

@login_required
def admin_stats_api(request):
    """API для отримання статистики"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from loyalty.models import Customer, Purchase
    
    total_customers = Customer.objects.count()
    active_codes = DiscountCode.objects.filter(is_used=False).count()
    total_purchases = Purchase.objects.count()
    total_revenue = Purchase.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    return JsonResponse({
        'total_customers': total_customers,
        'active_codes': active_codes,
        'total_purchases': total_purchases,
        'total_revenue': float(total_revenue)
    })

@login_required
def admin_users_api(request):
    """API для управління користувачами"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from loyalty.models import Customer
    
    if request.method == 'GET':
        customers = Customer.objects.all().order_by('-total_spent')
        users_data = []
        for customer in customers:
            users_data.append({
                'id': customer.id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'phone_number': customer.phone_number,
                'total_spent': float(customer.total_spent),
                'current_discount': customer.current_discount
            })
        
        return JsonResponse({'users': users_data})
    
    elif request.method == 'DELETE':
        user_id = request.path.split('/')[-2]  # Отримуємо ID з URL
        try:
            customer = Customer.objects.get(id=user_id)
            customer.delete()
            return JsonResponse({'success': True})
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})

@login_required
def admin_codes_api(request):
    """API для управління кодами знижок"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'GET':
        codes = DiscountCode.objects.all().order_by('-created_at')
        codes_data = []
        for code in codes:
            codes_data.append({
                'code': code.code,
                'discount_percentage': code.discount_percentage,
                'is_used': code.is_used,
                'created_at': code.created_at.isoformat()
            })
        
        return JsonResponse({'codes': codes_data})
    
    elif request.method == 'DELETE':
        code_value = request.path.split('/')[-2]  # Отримуємо код з URL
        try:
            code = DiscountCode.objects.get(code=code_value)
            code.delete()
            return JsonResponse({'success': True})
        except DiscountCode.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Code not found'})

@login_required
def admin_generate_code_api(request):
    """API для генерації нового коду знижки"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        import string
        import random
        
        # Генеруємо унікальний код
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not DiscountCode.objects.filter(code=code).exists():
                break
        
        # Створюємо новий код зі знижкою 10%
        discount_code = DiscountCode.objects.create(
            code=code,
            discount_percentage=10
        )
        
        return JsonResponse({
            'success': True,
            'code': code,
            'discount_percentage': 10
        })

@login_required
def admin_analytics_api(request):
    """API для аналітики"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from loyalty.models import Customer, Purchase
    from django.utils import timezone
    from datetime import timedelta
    
    # Аналітика за останній місяць
    last_month = timezone.now() - timedelta(days=30)
    
    new_users = Customer.objects.filter(registration_date__gte=last_month).count()
    active_users = Customer.objects.filter(purchases__created_at__gte=last_month).distinct().count()
    avg_purchase = Purchase.objects.filter(created_at__gte=last_month).aggregate(avg=Avg('amount'))['avg'] or 0
    
    # Найпопулярніший рівень
    from checkbox_integration.api import get_customer_level
    levels_count = {}
    for customer in Customer.objects.all():
        level, _ = get_customer_level(customer.total_spent)
        levels_count[level] = levels_count.get(level, 0) + 1
    
    popular_level = max(levels_count.items(), key=lambda x: x[1])[0] if levels_count else 'Невідомо'
    
    return JsonResponse({
        'new_users': new_users,
        'active_users': active_users,
        'avg_purchase': float(avg_purchase),
        'popular_level': popular_level
    })

@login_required
def admin_export_api(request):
    """API для експорту даних"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from loyalty.models import Customer
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Ім\'я', 'Прізвище', 'Телефон', 'Витрачено', 'Знижка', 'Дата реєстрації'])
    
    for customer in Customer.objects.all():
        writer.writerow([
            customer.id,
            customer.first_name,
            customer.last_name,
            customer.phone_number,
            customer.total_spent,
            customer.current_discount,
            customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

@login_required
def admin_broadcast_api(request):
    """API для розсилки повідомлень"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            
            if not message.strip():
                return JsonResponse({'success': False, 'error': 'Empty message'})
            
            from loyalty.models import Customer
            
            # Отримуємо всіх користувачів з Telegram ID
            customers = Customer.objects.exclude(telegram_id__isnull=True).exclude(telegram_id='')
            sent_count = 0
            
            # Надсилаємо повідомлення через Telegram Bot API
            bot_token = settings.TELEGRAM_BOT_TOKEN
            
            for customer in customers:
                try:
                    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                    payload = {
                        'chat_id': customer.telegram_id,
                        'text': f'📢 Повідомлення від адміністрації:\n\n{message}',
                        'parse_mode': 'HTML'
                    }
                    
                    response = requests.post(url, json=payload, timeout=5)
                    if response.status_code == 200:
                        sent_count += 1
                except Exception as e:
                    print(f'Помилка надсилання повідомлення користувачу {customer.telegram_id}: {e}')
                    continue
            
            return JsonResponse({
                'success': True,
                'sent_count': sent_count,
                'total_users': customers.count()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
