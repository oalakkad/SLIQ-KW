from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from .serializers import ContactMessageSerializer, SiteSettingsSerializer, HomeImageSerializer
from .models import SiteSettings, HomeImage
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db.models import Sum, Value, DecimalField
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from django.db.models.functions import Coalesce
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import unquote

# 🔁 Adjust this to your order model + revenue field
from orders.models import Order
REVENUE_FIELD = "total"  # e.g. "total", "total_amount", "grand_total", etc.

class ContactMessageCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]  # Adjust if you require auth

    def perform_create(self, serializer):
        instance = serializer.save()
        # Optional: send an email notification
        try:
            send_mail(
                subject=f"[Contact] {instance.subject}",
                message=(
                    f"From: {instance.name} <{instance.email}>\n"
                    f"Phone: {instance.phone}\n\n"
                    f"{instance.message}"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)],
                fail_silently=True,
            )
        except Exception:
            # Don't block the API if email fails
            pass

    def create(self, request, *args, **kwargs):
        # Return a small message payload
        response = super().create(request, *args, **kwargs)
        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        User = get_user_model()

        # Users (active only; change to .count() if you want all)
        users_count = User.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()

        # Orders (all orders; filter by paid/completed if your model has a status)
        orders_qs = Order.objects.all()
        # Example if your Order has a `status` field:
        # orders_qs = orders_qs.filter(status__in=["paid", "completed", "delivered"])

        orders_count = orders_qs.count()

        # Revenue
        total_revenue = orders_qs.aggregate(
        total_revenue=Coalesce(Sum('total_price'), Value(0), output_field=DecimalField(max_digits=12, decimal_places=2)))['total_revenue']

        # If total_revenue is Decimal, DRF will stringify by default; casting is optional:
        return Response(
            {
                "users_count": users_count,
                "orders_count": orders_count,
                "total_revenue": str(total_revenue),
            }
        )

class SiteSettingsView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        obj = SiteSettings.get_solo()
        serializer = SiteSettingsSerializer(obj, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        obj = SiteSettings.get_solo()
        serializer = SiteSettingsSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class HomeImagesListView(generics.ListAPIView):
    queryset = HomeImage.objects.all().order_by('key')
    serializer_class = HomeImageSerializer
    permission_classes = [permissions.AllowAny]

class HomeImageUpdateView(generics.UpdateAPIView):
    queryset = HomeImage.objects.all()
    serializer_class = HomeImageSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'key'

@csrf_exempt
def proxy_instagram_image(request):
    url = request.GET.get("url")
    if not url:
        return HttpResponse("Missing url", status=400)

    try:
        # Decode URL (in case it was encoded)
        url = unquote(url)

        # Fetch from Instagram CDN
        resp = requests.get(url, stream=True, headers={"User-Agent": "Mozilla/5.0"})

        if resp.status_code != 200:
            return HttpResponse(f"Failed to fetch image: {resp.status_code}", status=resp.status_code)

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return HttpResponse(resp.content, content_type=content_type)

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
