from django.db import models
from django.conf import settings

# Create your models here.

class SiteSettings(models.Model):
    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    bio_en = models.TextField(blank=True, default="A brand founded on bold femininity, offering effective and effortless products.")
    bio_ar = models.TextField(blank=True, default="علامة تجارية نسائية جريئة تدعمها منتجات عالية الجودة وفعالة وسهلة الاستخدام.")

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class AdminActivityLog(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.TextField()
    resource_type = models.CharField(max_length=100)
    resource_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"
