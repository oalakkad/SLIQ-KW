from rest_framework import serializers
from .models import ContactMessage, SiteSettings, HomeImage

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "subject", "message", "created_at"]
        read_only_fields = ["id", "created_at"]

class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["id", "logo", "bio_en", "bio_ar", "brand_name", "instagram_url"]
        read_only_fields = ["id"]

class HomeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeImage
        fields = ["id", "key", "label", "image"]
        read_only_fields = ["id", "key", "label"]
