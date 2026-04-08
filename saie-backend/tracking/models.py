from django.db import models
from django.conf import settings
from products.models import Product

# Create your models here.

class RecentlyViewed(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recently_viewed_products'
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recently_viewed_by_users'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)