from django.db import models
from decimal import Decimal
from django.utils import timezone
# Create your models here.
from products.models import Product
from django.conf import settings

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('on_delivery', 'On delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    delivery_fee = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    subtotal_price = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))

    # Guest info
    guest_email = models.EmailField(null=True, blank=True)
    guest_name = models.CharField(max_length=255, null=True, blank=True)
    guest_phone = models.CharField(max_length=50, null=True, blank=True)

    # Shipping Address
    shipping_address = models.ForeignKey(
        "users.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )

    # Address snapshot (preserved for both guests and users)
    shipping_full_name = models.CharField(max_length=255, null=True, blank=True)
    shipping_line = models.TextField(null=True, blank=True)
    shipping_city = models.CharField(max_length=100, null=True, blank=True)
    shipping_postal_code = models.CharField(max_length=20, null=True, blank=True)
    shipping_country = models.CharField(max_length=100, null=True, blank=True)
    shipping_phone = models.CharField(max_length=20, null=True, blank=True)

    # Optional billing (for future or invoices)
    billing_full_name = models.CharField(max_length=255, null=True, blank=True)
    billing_line = models.TextField(null=True, blank=True)
    billing_city = models.CharField(max_length=100, null=True, blank=True)
    billing_postal_code = models.CharField(max_length=20, null=True, blank=True)
    billing_country = models.CharField(max_length=100, null=True, blank=True)
    billing_phone = models.CharField(max_length=20, null=True, blank=True)

    discount = models.ForeignKey(
        "orders.DiscountCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=3)
    addons = models.JSONField(default=list, blank=True)

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "session_id")  # either-or, but not duplicate

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    addons = models.JSONField(default=list, blank=True)
    unit_extra_price = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class DiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)

    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="percent"
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Percentage (0–100) or fixed amount in KWD depending on type.",
    )

    applies_to_all = models.BooleanField(default=True)
    products = models.ManyToManyField(
        "products.Product",
        blank=True,
        related_name="discount_codes",
        help_text="Leave empty if applies_to_all is true.",
    )
    categories = models.ManyToManyField(
        "products.Category",
        blank=True,
        related_name="discount_codes",
        help_text="Leave empty if applies_to_all is true.",
    )

    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max total uses across all users"
    )
    per_user_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max uses per single user"
    )
    expiry_date = models.DateTimeField(null=True, blank=True)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, user=None) -> bool:
        if not self.active:
            return False
        from django.utils import timezone
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False
        if self.usage_limit is not None and self.usages.count() >= self.usage_limit:
            return False
        if user and self.per_user_limit is not None:
            if self.usages.filter(user=user).count() >= self.per_user_limit:
                return False
        return True

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()} {self.value})"

    # ------------------------
    # 🔑 FIXED DISCOUNT LOGIC
    # ------------------------
    def _eligible_product(self, product):
        if self.applies_to_all:
            return True
        if self.products.exists() and not self.products.filter(id=product.id).exists():
            return False
        if self.categories.exists() and not product.categories.filter(
            id__in=self.categories.values_list("id", flat=True)
        ).exists():
            return False
        return True

    def _compute(self, base: Decimal) -> Decimal:
        base = base.quantize(Decimal("0.001"))
        if base <= 0:
            return Decimal("0.000")
        if self.discount_type == "percent":
            amt = (base * self.value / Decimal("100")).quantize(Decimal("0.001"))
        else:
            amt = Decimal(self.value).quantize(Decimal("0.001"))
        return min(amt, base)

    def discount_for_cart(self, cart) -> Decimal:
        subtotal = Decimal("0.000")
        for item in cart.items.select_related("product"):
            if not self._eligible_product(item.product):
                continue
            unit_price = Decimal(item.product.price) + (item.unit_extra_price or Decimal("0.000"))
            subtotal += unit_price * item.quantity
        return self._compute(subtotal)

    def discount_for_order(self, order) -> Decimal:
        subtotal = Decimal("0.000")
        for item in order.items.select_related("product"):
            if not self._eligible_product(item.product):
                continue
            subtotal += Decimal(item.price_at_purchase) * item.quantity
        return self._compute(subtotal)


class DiscountUsage(models.Model):
    """
    Track each time a discount code is used (for limits & reporting).
    """
    discount = models.ForeignKey(
        DiscountCode, on_delete=models.CASCADE, related_name="usages"
    )
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="discount_usage"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.discount.code} used on Order {self.order_id}"