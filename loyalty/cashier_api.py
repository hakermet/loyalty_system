from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from telegram_bot.models import DiscountCode
from .models import Customer, Purchase
from checkbox_integration.api import get_customer_level, CheckboxAPI
import json
from decimal import Decimal

@api_view(['POST'])
@permission_classes([AllowAny])
def process_discount_code(request):
    """API для обробки коду знижки від касира"""
    code = request.data.get('code')
    receipt_id = request.data.get('receipt_id')
    amount = request.data.get('amount')
    
    if not code or not receipt_id or not amount:
        return Response({
            "success": False,
            "error": "Необхідно вказати код, ID чеку та суму покупки"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Знаходимо код знижки
        discount_code = DiscountCode.objects.get(code=code.upper())
        
        # Перевіряємо чи код не використаний
        if discount_code.is_used:
            return Response({
                "success": False,
                "error": "Код вже використано"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Перевіряємо чи код не закінчився
        if discount_code.is_expired():
            return Response({
                "success": False,
                "error": "Термін дії коду закінчився"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        customer = discount_code.customer
        
        # Перевірити, чи не використовувався цей чек раніше
        if Purchase.objects.filter(receipt_id=receipt_id).exists():
            return Response({
                "success": False,
                "error": f'Чек з ID "{receipt_id}" вже був використаний раніше'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Отримуємо поточний рівень та знижку клієнта
        old_level, current_discount = get_customer_level(customer.total_spent)
        
        # Розраховуємо суму зі знижкою
        amount = float(amount)
        discount_amount = amount * (current_discount / 100)
        final_amount = amount - discount_amount
        
        # Позначаємо код як використаний
        discount_code.mark_as_used()
        
        # Оновлюємо загальну суму покупок клієнта
        customer.total_spent += amount
        
        # Визначаємо новий рівень та знижку після покупки
        new_level, new_discount = get_customer_level(customer.total_spent)
        
        # Оновлюємо знижку клієнта відповідно до нового рівня
        customer.current_discount = new_discount
        customer.save()
        
        # Зберігаємо інформацію про покупку
        purchase = Purchase.objects.create(
            customer=customer,
            amount=amount,
            discount_applied=current_discount,
            discount_earned=0,
            receipt_id=receipt_id
        )
        
        # Формуємо відповідь
        response_data = {
            "success": True,
            "customer_name": f"{customer.first_name} {customer.last_name}",
            "phone_number": customer.phone_number,
            "original_amount": amount,
            "discount_percentage": current_discount,
            "discount_amount": round(discount_amount, 2),
            "final_amount": round(final_amount, 2),
            "old_level": old_level,
            "new_level": new_level,
            "new_discount": new_discount,
            "total_spent": customer.total_spent,
            "level_upgraded": old_level != new_level
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except DiscountCode.DoesNotExist:
        return Response({
            "success": False,
            "error": "Код не знайдено"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "success": False,
            "error": f"Помилка обробки: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def validate_discount_code(request, code):
    """API для перевірки валідності коду знижки"""
    try:
        discount_code = DiscountCode.objects.get(code=code.upper())
        customer = discount_code.customer
        level, discount = get_customer_level(customer.total_spent)
        
        return Response({
            "valid": not discount_code.is_used and not discount_code.is_expired(),
            "customer_name": f"{customer.first_name} {customer.last_name}",
            "phone_number": customer.phone_number,
            "discount_percentage": discount,
            "level": level,
            "expires_at": discount_code.expires_at,
            "is_used": discount_code.is_used,
            "is_expired": discount_code.is_expired()
        }, status=status.HTTP_200_OK)
        
    except DiscountCode.DoesNotExist:
        return Response({
            "valid": False,
            "error": "Код не знайдено"
        }, status=status.HTTP_404_NOT_FOUND)

@csrf_exempt
@require_http_methods(["POST"])
def process_phone_purchase(request):
    """Обробка покупки за номером телефону"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number', '').strip()
        amount = data.get('amount')
        receipt_id = data.get('receipt_id', '').strip()
        
        if not phone_number or not amount or not receipt_id:
            return JsonResponse({
                'success': False,
                'error': 'Всі поля обов\'язкові для заповнення'
            })
        
        # Знайти клієнта за номером телефону
        try:
            customer = Customer.objects.get(phone_number=phone_number)
        except Customer.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Клієнт з таким номером телефону не знайдений в системі лояльності'
            })
        
        # Перевірити, чи не використовувався цей чек раніше
        if Purchase.objects.filter(receipt_id=receipt_id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Чек з ID "{receipt_id}" вже був використаний раніше'
            })
        
        amount = Decimal(str(amount))
        
        # Отримати поточну знижку клієнта
        discount_percentage = customer.current_discount
        discount_amount = amount * (Decimal(str(discount_percentage)) / Decimal('100'))
        final_amount = amount - discount_amount
        
        # Створити запис про покупку
        purchase = Purchase.objects.create(
            customer=customer,
            amount=amount,
            discount_applied=discount_percentage,
            receipt_id=receipt_id
        )
        
        # Оновити загальну суму витрат клієнта
        customer.total_spent += amount
        
        # Розрахувати новий рівень та знижку
        old_level, old_discount = get_customer_level(customer.total_spent - amount)
        new_level, new_discount = get_customer_level(customer.total_spent)
        
        # Оновити знижку клієнта відповідно до нового рівня
        customer.current_discount = new_discount
        customer.save()
        
        # Оновити знижку, яка була нарахована
        purchase.discount_earned = new_discount - discount_percentage
        purchase.save()
        
        level_upgraded = old_level != new_level
        
        return JsonResponse({
            'success': True,
            'customer_name': f"{customer.first_name} {customer.last_name or ''}".strip(),
            'phone_number': customer.phone_number,
            'original_amount': float(amount),
            'discount_percentage': discount_percentage,
            'discount_amount': float(discount_amount),
            'final_amount': float(final_amount),
            'old_level': old_level,
            'new_level': new_level,
            'new_discount': new_discount,
            'level_upgraded': level_upgraded,
            'total_spent': float(customer.total_spent)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Невірний формат JSON'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Помилка обробки покупки: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def validate_phone_number(request, phone_number):
    """Перевірка номера телефону та отримання інформації про клієнта"""
    try:
        customer = Customer.objects.get(phone_number=phone_number)
        level, discount = get_customer_level(customer.total_spent)
        
        return JsonResponse({
            'valid': True,
            'customer_name': f"{customer.first_name} {customer.last_name or ''}".strip(),
            'phone_number': customer.phone_number,
            'level': level,
            'discount_percentage': customer.current_discount,
            'total_spent': float(customer.total_spent)
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'error': 'Клієнт з таким номером телефону не знайдений в системі лояльності'
        })

@csrf_exempt
@require_http_methods(["POST"])
def process_receipt_auto(request):
    """Автоматична обробка чеку за ID - синхронізація суми з Checkbox API"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        receipt_id = data.get('receipt_id')
        
        if not phone_number or not receipt_id:
            return JsonResponse({
                'success': False,
                'message': 'Необхідно вказати номер телефону та ID чеку'
            })
        
        # Перевіряємо, чи не використовувався цей чек раніше
        if Purchase.objects.filter(receipt_id=receipt_id).exists():
            return JsonResponse({
                'success': False,
                'message': 'Цей чек вже був використаний в системі лояльності'
            })
        
        # Інтеграція з реальним Checkbox API
        from checkbox_integration.api import CheckboxAPI
        
        try:
            # Ініціалізуємо API Checkbox
            print(f"🔍 ATTEMPTING TO GET RECEIPT: {receipt_id}")
            checkbox_api = CheckboxAPI()
            
            # Отримуємо реальні дані чеку з Checkbox API
            print(f"📡 CALLING CHECKBOX API...")
            receipt_info = checkbox_api.get_receipt(receipt_id)
            
            if not receipt_info:
                print(f"❌ NO RECEIPT DATA FROM API")
                return JsonResponse({
                    'success': False,
                    'message': 'Не вдалося отримати інформацію про чек з Checkbox API. Перевірте ID чеку.'
                })
            
            print(f"✅ RECEIPT DATA RECEIVED: {receipt_info}")
            
            # Перевіряємо статус чеку
            if receipt_info.get('status') != 'DONE':
                print(f"⚠️ RECEIPT STATUS NOT DONE: {receipt_info.get('status')}")
                return JsonResponse({
                    'success': False,
                    'message': 'Чек ще не завершений або має некоректний статус'
                })
                
        except Exception as e:
            # Якщо API недоступний, повертаємо помилку
            print(f"🚨 CHECKBOX API ERROR: {str(e)}")
            print(f"📋 RECEIPT_ID: {receipt_id}")
            print(f"📞 PHONE_NUMBER: {phone_number}")
            
            return JsonResponse({
                'success': False,
                'message': f'Помилка при отриманні даних чеку через Checkbox API: {str(e)}'
            })
        
        # Отримуємо суму покупки з чеку
        amount = Decimal(str(receipt_info.get('total', 0)))
        print(f"💰 RECEIPT AMOUNT: {amount}")
        if amount <= 0:
            print(f"❌ INVALID AMOUNT: {amount}")
            return JsonResponse({
                'success': False,
                'message': 'Некоректна сума в чеку'
            })
        
        try:
            # Знаходимо клієнта за номером телефону
            print(f"🔍 SEARCHING FOR CUSTOMER: {phone_number}")
            customer = Customer.objects.get(phone_number=phone_number)
            print(f"✅ CUSTOMER FOUND: {customer.first_name} {customer.last_name}")
            
            # Отримуємо поточний рівень та знижку клієнта
            old_level, old_discount = get_customer_level(customer.total_spent)
            
            # Розраховуємо знижку
            discount_amount = amount * (Decimal(str(old_discount)) / 100)
            final_amount = amount - discount_amount
            
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
                discount_applied=old_discount,
                discount_earned=0,
                receipt_id=receipt_id,
                fiscal_receipt_number=receipt_info.get('fiscal_receipt_number')
            )
            purchase.save()
            
            # Зберігаємо товари з чеку
            from .models import PurchaseItem
            for item in receipt_info.get('items', []):
                # Пропускаємо знижки та інші не-товарні позиції
                if item['unit_price'] > 0:
                    PurchaseItem.objects.create(
                        purchase=purchase,
                        name=item['name'],
                        quantity=item['quantity'],
                        unit_price=Decimal(str(item['unit_price'])),
                        total_price=Decimal(str(item['total_price']))
                    )
            
            # Формуємо повідомлення про результат
            level_up_message = ''
            if old_level != new_level:
                level_up_message = f' 🎉 Вітаємо! Ви досягли нового рівня: {new_level}!'
            
            return JsonResponse({
                'success': True,
                'message': f'Чек успішно оброблено! Сума: {amount} грн. Знижка {old_discount}%: -{discount_amount:.2f} грн. До сплати: {final_amount:.2f} грн. Ваш рівень: {new_level}. Ваша знижка: {new_discount}%. Загальна сума покупок: {customer.total_spent} грн{level_up_message}',
                'receipt_data': {
                    'original_amount': amount,
                    'discount_percentage': old_discount,
                    'discount_amount': discount_amount,
                    'final_amount': final_amount,
                    'customer_level': new_level,
                    'customer_discount': new_discount,
                    'total_spent': float(customer.total_spent)
                }
            })
            
        except Customer.DoesNotExist:
            print(f"❌ CUSTOMER NOT FOUND: {phone_number}")
            return JsonResponse({
                'success': False,
                'message': 'Клієнт з таким номером телефону не зареєстрований в системі лояльності'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Некоректний формат JSON'
        })
    except Exception as e:
        print(f"🚨 GENERAL ERROR: {str(e)}")
        import traceback
        print(f"📋 TRACEBACK: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'message': f'Помилка обробки запиту: {str(e)}'
        })