from django.urls import path, re_path
from rest_framework.routers import DefaultRouter
from .views import (
    CustomProviderAuthView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    LogoutView,
    AddressListCreateView,
    AddressRetrieveUpdateDestroyView,
    set_default_address,
    CustomerAdminViewSet,
)

# Create a router for admin endpoints
router = DefaultRouter()
router.register(r'admin/customers', CustomerAdminViewSet, basename='admin-customers')

urlpatterns = [
    # Authentication & Token Endpoints
    re_path(
        r'^o/(?P<provider>\S+)/$',
        CustomProviderAuthView.as_view(),
        name='provider-auth'
    ),
    path('jwt/create/', CustomTokenObtainPairView.as_view()),
    path('jwt/refresh/', CustomTokenRefreshView.as_view()),
    path('jwt/verify/', CustomTokenVerifyView.as_view()),
    path('logout/', LogoutView.as_view()),

    # Address Endpoints
    path("addresses/", AddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/", AddressRetrieveUpdateDestroyView.as_view(), name="address-detail"),
    path("addresses/<int:pk>/set-default/", set_default_address, name="address-set-default"),
]

# Combine with router URLs
urlpatterns += router.urls
