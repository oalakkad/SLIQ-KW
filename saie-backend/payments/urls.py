# payments/urls.py
from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'admin/payments', views.PaymentAdminViewSet, basename='admin-payments')

urlpatterns = [
    # New checkout flow (intent → execute → verify)
    path("payments/checkout/start/", views.start_checkout, name="payments-start-checkout"),
    path("payments/initiate/", views.initiate_payment, name="payments-initiate"),
    path("payments/execute/", views.execute_payment, name="payments-execute"),
    path("payments/verify/", views.verify_payment, name="payments-verify"),
]

urlpatterns += router.urls
