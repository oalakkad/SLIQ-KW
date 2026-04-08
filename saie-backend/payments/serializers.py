# payments/serializers.py

from rest_framework import serializers
from .models import Payment
from orders.serializers import OrderSerializer  # reuse to show order info if needed


class PaymentSerializer(serializers.ModelSerializer):
    # Nested order info (read-only)
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "currency",
            "status",
            "invoice_id",
            "payment_id",
            "method_id",
            "gateway_response",
            "paid_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "paid_at"]