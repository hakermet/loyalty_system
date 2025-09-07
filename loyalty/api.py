from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Customer, Purchase
from checkbox_integration.api import process_purchase

@api_view(['POST'])
def process_customer_purchase(request):
    """API для обробки покупки клієнта"""
    phone_number = request.data.get('phone_number')
    receipt_id = request.data.get('receipt_id')
    
    if not phone_number or not receipt_id:
        return Response({"error": "Необхідно вказати номер телефону та ID чеку"}, status=status.HTTP_400_BAD_REQUEST)
    
    result = process_purchase(phone_number, receipt_id)
    
    if result["success"]:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(result, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_customer_info(request, phone_number):
    """API для отримання інформації про клієнта"""
    try:
        customer = Customer.objects.get(phone_number=phone_number)
        data = {
            "id": customer.id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone_number": customer.phone_number,
            "current_discount": customer.current_discount,
            "total_spent": customer.total_spent
        }
        return Response(data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({"error": "Клієнт не знайдений"}, status=status.HTTP_404_NOT_FOUND)