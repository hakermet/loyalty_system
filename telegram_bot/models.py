from django.db import models
from loyalty.models import Customer
from django.utils import timezone

class DiscountCode(models.Model):
    """Модель для зберігання згенерованих кодів знижок"""
    code = models.CharField(max_length=10, unique=True, verbose_name="Код")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клієнт")
    is_used = models.BooleanField(default=False, verbose_name="Використано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Використано о")
    expires_at = models.DateTimeField(verbose_name="Діє до")
    
    class Meta:
        verbose_name = "Код знижки"
        verbose_name_plural = "Коди знижок"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.customer.first_name} ({self.customer.phone_number})"
    
    def is_expired(self):
        """Перевірка чи не закінчився термін дії коду"""
        return timezone.now() > self.expires_at
    
    def mark_as_used(self):
        """Позначити код як використаний"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
