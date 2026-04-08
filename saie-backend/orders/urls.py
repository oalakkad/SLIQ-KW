from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CartView, AddToCartView, UpdateCartItemView, RemoveCartItemView, WishlistView, AddToWishlistView, RemoveFromWishlistView,ClearWishlistView, OrderListCreateAPIView, OrderDetailAPIView, CreateOrderFromCartAPIView, OrderAdminViewSet, DiscountCodeAdminViewSet, DiscountUsageAdminViewSet, apply_discount

router = DefaultRouter()
router.register(r'admin/orders', OrderAdminViewSet, basename='admin-orders')
router.register(r"admin/discounts", DiscountCodeAdminViewSet, basename="admin-discounts")
router.register(r"admin/discount-usages", DiscountUsageAdminViewSet, basename="admin-discount-usages")

urlpatterns = [
    path('cart/', CartView.as_view(), name='user-cart'),
    path('cart/items/add/', AddToCartView.as_view(), name='cart-add-item'),
    path('cart/items/<int:pk>/update/', UpdateCartItemView.as_view(), name='cart-update-item'),
    path('cart/items/<int:pk>/delete/', RemoveCartItemView.as_view(), name='cart-remove-item'),

    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/items/add/', AddToWishlistView.as_view(), name='wishlist-add-item'),
    path('wishlist/items/<int:pk>/delete/', RemoveFromWishlistView.as_view(), name='wishlist-remove-item'),
    path('wishlist/clear/', ClearWishlistView.as_view(), name='wishlist-clear'),

    path('orders/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('orders/checkout/', CreateOrderFromCartAPIView.as_view(), name='order-checkout'),

    path("discounts/apply/", apply_discount, name="apply-discount"),
]


urlpatterns += router.urls
