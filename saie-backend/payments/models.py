from django.db import models
from django.conf import settings
from orders.models import DiscountCode

class Payment(models.Model):
    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    ]

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=3)  # copy from order at time of checkout
    currency = models.CharField(max_length=3, default="KWD")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="initiated"
    )

    # MyFatoorah fields
    invoice_id = models.CharField(max_length=64, null=True, blank=True)
    payment_id = models.CharField(max_length=64, null=True, blank=True)
    method_id = models.IntegerField(null=True, blank=True)  # from Initiate/Execute flow
    gateway_response = models.JSONField(null=True, blank=True)  # raw last response (optional)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Order {self.order_id} - {self.status}"


class CheckoutPayment(models.Model):
    STATUS = [
        ("initiated", "Initiated"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    # Either user or session_id must be set
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=3)
    currency = models.CharField(max_length=3, default="KWD")
    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default="initiated"
    )

    address_id = models.IntegerField(null=True, blank=True)
    cart_snapshot = models.JSONField(null=True, blank=True)

    # Guest info (optional)
    guest_name = models.CharField(max_length=255, null=True, blank=True)
    guest_email = models.EmailField(null=True, blank=True)
    guest_phone = models.CharField(max_length=50, null=True, blank=True)

    invoice_id = models.CharField(max_length=64, null=True, blank=True)
    payment_id = models.CharField(max_length=64, null=True, blank=True)
    method_id = models.IntegerField(null=True, blank=True)

    discount = models.ForeignKey(
        DiscountCode, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="checkout_payments"
    )

    # Link to the real order after success
    order = models.OneToOneField(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="checkout_payment"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.user:
            return f"CheckoutPayment {self.id} for user {self.user_id} - {self.status}"
        return f"CheckoutPayment {self.id} (guest) - {self.status}"