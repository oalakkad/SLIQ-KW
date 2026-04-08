from django.conf import settings
from rest_framework.views import APIView
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from djoser.social.views import ProviderAuthView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from .models import Address
from .serializers import AddressSerializer, CustomerSerializer
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from dashboard.mixins import AdminLoggingMixin
from django.contrib.auth import get_user_model
User = get_user_model()

class CustomProviderAuthView(ProviderAuthView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 201:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            request.data['refresh'] = refresh_token

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access')

        if access_token:
            request.data['token'] = access_token

        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access')
        response.delete_cookie('refresh')

        return response

class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Set user to the logged-in user
        serializer.save(user=self.request.user)

class AddressRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_default_address(request, pk):
    user = request.user

    try:
        address = Address.objects.get(pk=pk, user=user)
    except Address.DoesNotExist:
        return Response({"detail": "Address not found."}, status=404)

    # Remove default flag from other addresses
    Address.objects.filter(user=user, is_default=True).update(is_default=False)

    # Set selected address as default
    address.is_default = True
    address.save()

    return Response({"detail": "Default address updated."})

class CustomerAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    """
    Admin ViewSet to manage customers: list, retrieve, update, and delete.
    """
    queryset = User.objects.filter(is_staff=False, is_superuser=False)
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    # Enable search, filtering, and ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Search fields: can search by name or email
    search_fields = ['first_name', 'last_name', 'email']

    # 🔻 Disable pagination just for this viewset
    pagination_class = None

    # Filter fields: e.g., active status
    filterset_fields = ['is_active']

    # Allow ordering by date joined or email
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']  # Default order: newest first

    def perform_update(self, serializer):
        """Handle updates and optionally log admin actions"""
        instance = serializer.save()
        # Optionally log activity if using AdminLoggingMixin
        self.log_activity("UPDATE", instance)
        return instance

    def perform_destroy(self, instance):
        """Handle deletion and optionally log admin actions"""
        # Optionally log activity if using AdminLoggingMixin
        self.log_activity("DELETE", instance)
        instance.delete()
