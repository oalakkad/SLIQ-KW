from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAdminUser, AllowAny
from dashboard.mixins import AdminLoggingMixin

from .models import Cart, CartItem, Wishlist, Order, OrderItem, DiscountCode, DiscountUsage
from payments.models import CheckoutPayment
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToWishlistSerializer,
    WishlistSerializer,
    OrderSerializer,
    DiscountCodeSerializer,
    DiscountUsageSerializer,
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework import status

# ------------------------------
# Utility: Get or create a cart
# ------------------------------
def _get_cart(request):
    """Return the authenticated user's cart or a guest cart bound to session_id."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.save()
        session_id = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_id=session_id, user=None)
    return cart


# ------------------------------
# Cart Views
# ------------------------------
class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        cart = _get_cart(self.request)
        return Cart.objects.prefetch_related("items__product").get(id=cart.id)


class AddToCartView(generics.CreateAPIView):
    """
    Expects body like:
    {
      "product_id": 123,
      "quantity": 1,
      "addons": [
        {"category_id": 12, "addon_id": 44, "option_ids": [301,302], "custom_name": "Sara"}
      ]
    }
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["cart"] = _get_cart(self.request)
        return ctx

    def perform_create(self, serializer):
        serializer.save()


class UpdateCartItemView(generics.UpdateAPIView):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = _get_cart(self.request)
        return CartItem.objects.filter(cart=cart)


class RemoveCartItemView(generics.DestroyAPIView):
    queryset = CartItem.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = _get_cart(self.request)
        return CartItem.objects.filter(cart=cart)


# ------------------------------
# Wishlist (auth-only)
# ------------------------------
class WishlistView(generics.ListAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product")


class AddToWishlistView(generics.CreateAPIView):
    serializer_class = AddToWishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        Wishlist.objects.get_or_create(user=self.request.user, product=product)


class RemoveFromWishlistView(generics.DestroyAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)


class ClearWishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        Wishlist.objects.filter(user=request.user).delete()
        return Response({"detail": "Wishlist cleared."}, status=status.HTTP_204_NO_CONTENT)


# ------------------------------
# Orders
# ------------------------------
class OrderListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  # only logged-in users see history

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")


class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class CreateOrderFromCartAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cart = _get_cart(request)
        cart_items = CartItem.objects.filter(cart=cart).select_related("product")
        if not cart_items.exists():
            return Response({"detail": "No items in cart."}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(
            (Decimal(item.product.price) + (item.unit_extra_price or Decimal("0.000"))) * item.quantity
            for item in cart_items
        )

        # --- discount handling ---
        discount = None
        discount_amount = Decimal("0.000")
        discount_code = request.data.get("discount_code")
        if discount_code:
            try:
                discount = DiscountCode.objects.get(code__iexact=discount_code, active=True)
                if discount.is_valid(request.user if request.user.is_authenticated else None):
                    discount_amount = discount.discount_for_cart(cart)
            except DiscountCode.DoesNotExist:
                pass

        delivery_fee = Decimal("2.000")
        total_price = (subtotal - discount_amount + delivery_fee).quantize(Decimal("0.001"))

        if request.user.is_authenticated:
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                discount=discount,
                discount_amount=discount_amount,
                status="pending",
            )
        else:
            guest_data = request.data.get("guest", {})
            order = Order.objects.create(
                user=None,
                total_price=total_price,
                discount=discount,
                discount_amount=discount_amount,
                status="pending",
                guest_name=guest_data.get("name"),
                guest_email=guest_data.get("email"),
                guest_phone=guest_data.get("phone"),
            )

        for item in cart_items:
            unit_price = Decimal(item.product.price) + (item.unit_extra_price or Decimal("0.000"))
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_purchase=unit_price,
                addons=item.addons,
            )

        cart_items.delete()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ------------------------------
# Admin Orders
# ------------------------------
class OrderAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = Order.objects.select_related("user", "discount").prefetch_related("items__product").all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__first_name", "user__last_name", "user__email", "status", "discount__code"]
    pagination_class = None
    filterset_fields = ["status", "user", "discount"]
    ordering_fields = ["created_at", "total_price", "discount_amount"]
    ordering = ["-created_at"]

    def perform_update(self, serializer):
        return serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

class DiscountCodeAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    """
    Admin viewset to manage discount codes.
    """
    queryset = DiscountCode.objects.prefetch_related("products", "categories").all()
    serializer_class = DiscountCodeSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "description"]
    filterset_fields = ["expiry_date", "active", "discount_type"]
    ordering_fields = ["created_at", "expiry_date", "value"]
    ordering = ["-created_at"]

    def perform_update(self, serializer):
        return serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


class DiscountUsageAdminViewSet(AdminLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """
    Admin viewset to list discount usage records.
    (Read-only, admin shouldn't create usages manually.)
    """
    queryset = DiscountUsage.objects.select_related("discount", "order", "user").all()
    serializer_class = DiscountUsageSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["discount__code", "order__id", "user__email"]
    filterset_fields = ["discount", "user"]
    ordering_fields = ["used_at"]
    ordering = ["-used_at"]

@api_view(["POST"])
@permission_classes([AllowAny])
def apply_discount(request):
    code = request.data.get("code", "").strip()
    cart_id = request.data.get("cart_id")

    if not code:
        return Response({"error": "Discount code required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        discount = DiscountCode.objects.get(code__iexact=code, active=True)
    except DiscountCode.DoesNotExist:
        return Response({"error": "Invalid code."}, status=status.HTTP_404_NOT_FOUND)

    if not discount.is_valid(request.user if request.user.is_authenticated else None):
        return Response({"error": "Code expired or inactive."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cart = Cart.objects.get(id=cart_id)
    except Cart.DoesNotExist:
        return Response({"error": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

    discount_amount = discount.discount_for_cart(cart)

    # ✅ persist discount on session CheckoutPayment (if any)
    session_id = request.session.session_key
    if not session_id:
        request.session.save()
        session_id = request.session.session_key

    cp = CheckoutPayment.objects.filter(session_id=session_id, status="initiated").last()
    if cp:
        cp.discount = discount
        cp.save(update_fields=["discount"])

    # fallback to session store if cp not yet created
    request.session["applied_discount_id"] = discount.id
    request.session.modified = True

    return Response(
        {
            "code": discount.code,
            "amount": str(discount_amount.quantize(Decimal("0.000"))),
        },
        status=status.HTTP_200_OK,
    )