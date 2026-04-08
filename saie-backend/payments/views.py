# payments/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status as http_status, filters, viewsets

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction, connection
from django.views.decorators.csrf import csrf_exempt

from decimal import Decimal
import logging
import time

from django_filters.rest_framework import DjangoFilterBackend

from users.models import Address
from orders.models import (
    Cart, CartItem, Order, OrderItem,
    DiscountCode, DiscountUsage
)
from orders.serializers import OrderSerializer
from .models import Payment, CheckoutPayment
from .serializers import PaymentSerializer
from .myfatoorah import mf_post
from dashboard.mixins import AdminLoggingMixin

from django.db.models import signals
from orders import signals as order_signals

logger = logging.getLogger(__name__)

DELIVERY_FEE = Decimal("2.000")

# ------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------
def _ensure_session(request):
    """Ensure the request has a session key for guest carts."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_cart_for_request(request):
    """Return the Cart associated to the current request (auth user or guest)."""
    try:
        if request.user.is_authenticated:
            return Cart.objects.get(user=request.user)
        session_id = _ensure_session(request)
        return Cart.objects.get(session_id=session_id, user=None)
    except Cart.DoesNotExist:
        return None


def _compute_amount_from_request(request) -> Decimal:
    cart = _get_cart_for_request(request)
    if not cart:
        return Decimal("0.000")
    items = CartItem.objects.filter(cart=cart).select_related("product")
    if not items.exists():
        return Decimal("0.000")

    total = Decimal("0.000")
    for i in items:
        base = Decimal(i.product.price)
        extra = i.unit_extra_price or Decimal("0.000")
        total += (base + extra) * i.quantity

    return total.quantize(Decimal("0.000"))


def _get_checkout_payment_for_request(request, cp_id: int) -> CheckoutPayment:
    """
    Load a CheckoutPayment that belongs to the current actor:
      - If user is authenticated: cp.user == request.user
      - Else guest: cp.session_id == current session_id AND cp.user is null
    """
    if request.user.is_authenticated:
        return get_object_or_404(CheckoutPayment, pk=cp_id, user=request.user)
    session_id = _ensure_session(request)
    return get_object_or_404(
        CheckoutPayment,
        pk=cp_id,
        user__isnull=True,
        session_id=session_id,
    )


def _snapshot_cart_items_to_order(cart: Cart, order: Order) -> Decimal:
    """
    Copy items from cart → order in bulk, then clear the cart rows by PK.
    Returns subtotal of copied items.
    """
    t0 = time.time()
    qs = CartItem.objects.select_related("product").filter(cart=cart)

    cart_items = list(qs)
    if not cart_items:
        logger.info("[snapshot] cart empty (%.2fs)", time.time() - t0)
        return Decimal("0.000")

    subtotal = Decimal("0.000")
    order_rows = []
    cart_ids = []

    for ci in cart_items:
        base = Decimal(ci.product.price)
        extra = ci.unit_extra_price or Decimal("0.000")
        unit_price = (base + extra).quantize(Decimal("0.001"))
        subtotal += unit_price * ci.quantity

        order_rows.append(OrderItem(
            order=order,
            product=ci.product,
            quantity=ci.quantity,
            price_at_purchase=unit_price,
            addons=ci.addons,
        ))
        cart_ids.append(ci.id)

    # Bulk insert order items, then remove cart items by PK
    OrderItem.objects.bulk_create(order_rows, batch_size=100)
    CartItem.objects.filter(id__in=cart_ids).delete()

    logger.info("[snapshot] moved %d items in %.2fs (subtotal=%s)",
                len(order_rows), time.time() - t0, f"{subtotal:.3f}")
    return subtotal.quantize(Decimal("0.000"))


def _order_to_lite(order: Order):
    """
    TEMP: lightweight payload that won’t traverse deep relations.
    Enabled by settings.ORDERS_USE_LITE_SERIALIZER (default True) or ?full=1 to bypass.
    """
    # bare minimum to satisfy the success screen without heavy nested graphs
    return {
        "id": order.id,
        "status": order.status,
        "total_price": f"{order.total_price:.3f}",
        "discount_amount": f"{(order.discount_amount or Decimal('0.000')):.3f}",
        "discount": (
            {
                "id": order.discount_id,
                "code": getattr(order.discount, "code", None),
                "value": str(getattr(order.discount, "value", "")),
                "discount_type": getattr(order.discount, "discount_type", ""),
            }
            if order.discount_id else None
        ),
        "address_id": order.shipping_address_id,
        "address": {
            "id": getattr(order.shipping_address, "id", None) if order.shipping_address_id else None,
            "full_name": order.shipping_full_name,
            "address_line": order.shipping_line,
            "city": order.shipping_city,
            "postal_code": order.shipping_postal_code,
            "country": order.shipping_country,
            "phone": order.shipping_phone,
        },
        # keep items lightweight (no nested product serializer)
        "items": [
            {
                "id": oi.id,
                "product": {
                    "id": oi.product_id,
                    "name": getattr(oi.product, "name", ""),
                    "name_ar": getattr(oi.product, "name_ar", ""),
                    "price": str(getattr(oi.product, "price", "")),
                    "image": getattr(oi.product, "image", ""),
                    "slug": getattr(oi.product, "slug", ""),
                },
                "quantity": oi.quantity,
                "price_at_purchase": f"{oi.price_at_purchase:.3f}",
                "addons": oi.addons or [],
            }
            for oi in order.items.all()
        ],
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _should_use_lite(request) -> bool:
    # If the caller explicitly asks for full payload (?full=1) use the serializer path.
    if request.query_params.get("full") in {"1", "true", "True"}:
        return False
    return getattr(settings, "ORDERS_USE_LITE_SERIALIZER", True)


# ------------------------------------------------------------------------------------
# Start checkout intent
# ------------------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def start_checkout(request):
    """
    Starts a checkout payment-intent and sets the InvoiceAmount to the DISCOUNTED total.
    Accepts optional payload: {"discount_code": "CODE123"}
    Also picks up session-applied code if present.
    """
    session_id = _ensure_session(request)
    user = request.user if request.user.is_authenticated else None

    cart = _get_cart_for_request(request)
    if not cart or not cart.items.exists():
        return Response({"detail": "Cart is empty."}, status=http_status.HTTP_400_BAD_REQUEST)

    subtotal = _compute_amount_from_request(request)

    # Resolve discount
    disc = None
    payload_code = (request.data.get("discount_code") or "").strip()
    if payload_code:
        d = DiscountCode.objects.filter(code__iexact=payload_code, active=True).first()
        if d and d.is_valid(user):
            disc = d
    if not disc:
        disc_id = request.session.get("applied_discount_id")
        if disc_id:
            d = DiscountCode.objects.filter(id=disc_id, active=True).first()
            if d and d.is_valid(user):
                disc = d

    discount_amount = Decimal("0.000")
    if disc:
        discount_amount = disc.discount_for_cart(cart)

    amount = (
        subtotal
        - discount_amount
        + DELIVERY_FEE
    ).quantize(Decimal("0.001"))

    if amount < 0:
        amount = Decimal("0.000")

    cp = CheckoutPayment.objects.create(
        user=user,
        session_id=None if user else session_id,
        amount=amount,
        currency="KWD",
        status="initiated",
        address_id=request.data.get("address_id"),
        cart_snapshot=request.data.get("cart"),
        guest_name=(request.data.get("guest") or {}).get("name") if not user else None,
        guest_email=(request.data.get("guest") or {}).get("email") if not user else None,
        guest_phone=(request.data.get("guest") or {}).get("phone") if not user else None,
        discount=disc,
    )

    # Clear sticky discount from session
    if request.session.get("applied_discount_id"):
        try:
            del request.session["applied_discount_id"]
            request.session.modified = True
        except KeyError:
            pass

    return Response(
        {"checkoutPaymentId": cp.id, "amount": f"{amount:.3f}", "currency": cp.currency},
        status=http_status.HTTP_201_CREATED,
    )


# ------------------------------------------------------------------------------------
# Step 1: InitiatePayment (list methods)
# ------------------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def initiate_payment(request):
    cp_id = request.data.get("checkoutPaymentId")
    if not cp_id:
        return Response({"detail": "checkoutPaymentId is required"}, status=http_status.HTTP_400_BAD_REQUEST)

    cp = _get_checkout_payment_for_request(request, cp_id)
    payload = {"InvoiceAmount": float(cp.amount), "CurrencyIso": cp.currency}
    res = mf_post("InitiatePayment", payload)
    return Response(res["Data"])


# ------------------------------------------------------------------------------------
# Step 2: ExecutePayment (redirect URL)
# ------------------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def execute_payment(request):
    cp_id = request.data.get("checkoutPaymentId")
    method_id = request.data.get("paymentMethodId")

    try:
        method_id = int(method_id)
    except (TypeError, ValueError):
        return Response({"detail": "paymentMethodId must be integer"}, status=http_status.HTTP_400_BAD_REQUEST)

    cp = _get_checkout_payment_for_request(request, cp_id)

    # Customer identity for the gateway
    if request.user.is_authenticated:
        customer_name = (
            getattr(request.user, "full_name", None)
            or getattr(request.user, "name", None)
            or f"{getattr(request.user, 'first_name', '')} {getattr(request.user, 'last_name', '')}".strip()
            or "Customer"
        )
        customer_email = getattr(request.user, "email", "") or ""
    else:
        customer_name = getattr(cp, "guest_name", None) or "Customer"
        customer_email = getattr(cp, "guest_email", "") or ""

    payload = {
        "PaymentMethodId": method_id,
        "CustomerName": customer_name,
        "DisplayCurrencyIso": cp.currency,
        "CustomerEmail": customer_email,
        "InvoiceValue": float(cp.amount),
        "CallBackUrl": f"{settings.MYFATOORAH_CALLBACK_URL}?cpId={cp.id}",
        "ErrorUrl":    f"{settings.MYFATOORAH_CALLBACK_URL}?cpId={cp.id}",
    }
    res = mf_post("ExecutePayment", payload)

    cp.method_id = method_id
    cp.invoice_id = str(res["Data"].get("InvoiceId") or cp.invoice_id or "")
    cp.save(update_fields=["method_id", "invoice_id"])

    return Response({"paymentUrl": res["Data"]["PaymentURL"], "invoiceId": cp.invoice_id})


# ------------------------------------------------------------------------------------
# Step 3: Verify after redirect (TEMP PATCHED)
# ------------------------------------------------------------------------------------
# payments/views.py
@csrf_exempt
@api_view(["GET"])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    Step 3: Verify payment after MyFatoorah redirect.
    Creates an Order for both guest and authenticated users.
    Guest orders use flattened address fields from cart_snapshot.
    """
    log = logging.getLogger(__name__)
    t0 = time.time()

    payment_id = request.GET.get("paymentId")
    cp_id = request.GET.get("cpId")

    if not (payment_id and cp_id):
        return Response({"detail": "paymentId and cpId are required"}, status=400)

    cp = get_object_or_404(CheckoutPayment, pk=cp_id)
    log.info("[verify_payment] start cp=%s", cp_id)

    # ------------------ Step 1: Verify payment ------------------
    res = mf_post("GetPaymentStatus", {"Key": payment_id, "KeyType": "PaymentId"})
    data = res.get("Data", {})
    invoice_status = (data.get("InvoiceStatus") or "").lower()
    txn_statuses = [(t.get("TransactionStatus") or "").lower() for t in (data.get("InvoiceTransactions") or [])]
    succeeded = invoice_status in {"paid", "success"} or any(
        s.startswith("succ") or s == "captured" for s in txn_statuses
    )

    if not succeeded:
        cp.status = "failed"
        cp.payment_id = payment_id
        cp.invoice_id = data.get("InvoiceId") or cp.invoice_id
        cp.save(update_fields=["status", "payment_id", "invoice_id"])
        return Response({"paymentStatus": "failed"}, status=400)

    cp.status = "paid"
    cp.payment_id = payment_id
    cp.invoice_id = data.get("InvoiceId") or cp.invoice_id
    cp.paid_at = timezone.now()
    cp.save(update_fields=["status", "payment_id", "invoice_id", "paid_at"])

    log.info("[verify_payment] cp marked paid (%.2fs)", time.time() - t0)

    signals.post_save.disconnect(order_signals.send_order_created_email, sender=Order)

    try:
        with transaction.atomic():
            # ------------------ Step 2: Prepare shipping data ------------------
            addr = Address.objects.filter(id=cp.address_id).first()
            snap = cp.cart_snapshot or {}

            # Read guest shipping info (flat format)
            shipping_line = snap.get("address_line") or snap.get("address")
            shipping_city = snap.get("city")
            shipping_postal = snap.get("postal_code")
            shipping_country = snap.get("country")
            shipping_phone = snap.get("phone")

            # Read billing info (flat format)
            billing_line = snap.get("billing_address_line") or snap.get("billing_address")
            billing_city = snap.get("billing_city") or shipping_city
            billing_postal = snap.get("billing_postal_code") or shipping_postal
            billing_country = snap.get("billing_country") or shipping_country
            billing_phone = snap.get("billing_phone") or shipping_phone

            # ------------------ Step 3: Create the order ------------------
            order = Order.objects.create(
                user=cp.user,
                status="preparing",
                total_price=Decimal("0.000"),
                guest_name=cp.guest_name,
                guest_email=cp.guest_email,
                guest_phone=cp.guest_phone,
                shipping_address=addr if addr else None,
                shipping_full_name=getattr(addr, "full_name", cp.guest_name),
                shipping_line=shipping_line or getattr(addr, "address_line", None),
                shipping_city=shipping_city or getattr(addr, "city", None),
                shipping_postal_code=shipping_postal or getattr(addr, "postal_code", None),
                shipping_country=shipping_country or getattr(addr, "country", None),
                shipping_phone=shipping_phone or getattr(addr, "phone", cp.guest_phone),
                billing_line=billing_line,
                billing_city=billing_city,
                billing_postal_code=billing_postal,
                billing_country=billing_country,
                billing_phone=billing_phone,
            )

            # ------------------ Step 4: Snapshot cart items ------------------
            try:
                if cp.user:
                    cart = Cart.objects.get(user=cp.user)
                else:
                    cart = Cart.objects.get(session_id=cp.session_id, user=None)
                subtotal = _snapshot_cart_items_to_order(cart, order)
            except Cart.DoesNotExist:
                subtotal = Decimal("0.000")

            # ------------------ Step 5: Discount handling ------------------
            discount_amt = Decimal("0.000")
            if cp.discount and cp.discount.is_valid(order.user):
                discount_amt = cp.discount.discount_for_order(order)
                order.discount = cp.discount
                order.discount_amount = min(discount_amt, subtotal)
                DiscountUsage.objects.create(
                    discount=cp.discount, order=order, user=order.user
                )
            else:
                order.discount_amount = Decimal("0.000")

            order.delivery_fee = DELIVERY_FEE

            order.total_price = (
                subtotal
                - order.discount_amount
                + DELIVERY_FEE
            ).quantize(Decimal("0.001"))
            
            order.save(update_fields=["total_price", "discount", "discount_amount"])

            # ------------------ Step 6: Payment record ------------------
            Payment.objects.create(
                order=order,
                amount=order.total_price,
                currency=cp.currency,
                status="paid",
                invoice_id=cp.invoice_id,
                payment_id=payment_id,
                method_id=cp.method_id,
                gateway_response=res,
                paid_at=timezone.now(),
            )

            cp.order = order
            cp.save(update_fields=["order"])

    finally:
        signals.post_save.connect(order_signals.send_order_created_email, sender=Order)

    # ------------------ Step 7: Return ------------------
    order = (
        Order.objects.select_related("shipping_address", "user", "discount")
        .prefetch_related("items__product")
        .get(id=cp.order_id)
    )

    log.info("[verify_payment] done cp=%s → order=%s (%.2fs)", cp.id, order.id, time.time() - t0)

    return Response(
        {"paymentStatus": "paid", "order": OrderSerializer(order).data},
        status=http_status.HTTP_200_OK,
    )


# ------------------------------------------------------------------------------------
# Admin Payments
# ------------------------------------------------------------------------------------
class PaymentAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    """
    Admin viewset to list/search Payments
    """
    queryset = Payment.objects.select_related("order", "order__user").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "order__user__first_name", "order__user__last_name", "order__user__email",
        "invoice_id", "payment_id", "status"
    ]
    filterset_fields = ["status", "currency", "method_id", "order"]
    ordering_fields = ["created_at", "amount", "paid_at"]
    ordering = ["-created_at"]

    def perform_update(self, serializer):
        return serializer.save()

    def perform_destroy(self, instance):
        instance.delete()