from django.db import models

class Customer(models.Model):
    telegram_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    current_discount = models.FloatField(default=0)  # Поточна знижка у відсотках
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} ({self.phone_number})"

class Purchase(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='purchases')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = models.FloatField(default=0)  # Знижка, яка була застосована
    discount_earned = models.FloatField(default=0)   # Знижка, яка була нарахована
    purchase_date = models.DateTimeField(auto_now_add=True)
    receipt_id = models.CharField(max_length=100, unique=True)  # ID чеку з Checkbox
    fiscal_receipt_number = models.CharField(max_length=50, blank=True, null=True)  # Фіскальний номер чеку
    
    def __str__(self):
        return f"Purchase {self.receipt_id} by {self.customer}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)  # Назва товару
    quantity = models.DecimalField(max_digits=8, decimal_places=3, default=1)  # Кількість
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Ціна за одиницю
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # Загальна вартість товару
    
    def __str__(self):
        return f"{self.name} x{self.quantity} = {self.total_price} грн"