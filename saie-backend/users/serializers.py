from rest_framework import serializers
from .models import Address
from django.contrib.auth import get_user_model

User = get_user_model()

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']

class CustomerSerializer(serializers.ModelSerializer):
    addresses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'addresses']

    def get_addresses(self, obj):
        from .serializers import AddressSerializer  # avoid circular import
        addresses = Address.objects.filter(user=obj)
        return AddressSerializer(addresses, many=True).data
