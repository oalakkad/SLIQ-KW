from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductListAPIView,
    ProductDetailAPIView,
    CategoryListAPIView,
    ProductAdminViewSet,
    CategoryAdminViewSet,
    ProductImageAdminViewSet,
    CategoryWithProductsAPIView,
    AddonCategoryAdminViewSet,
    AddonAdminViewSet,
    AddonOptionAdminViewSet,
    ProductAddonCategoriesAPIView,
    ProductSitemapAPIView,
    CategorySitemapAPIView,
)
from django.conf import settings
from django.conf.urls.static import static

# Admin API router
router = DefaultRouter()
router.register(r'admin/products', ProductAdminViewSet, basename='admin-products')
router.register(r'admin/categories', CategoryAdminViewSet, basename='admin-categories')
router.register(r'admin/product-images', ProductImageAdminViewSet, basename='admin-product-images')

# Addon Admin Routers
router.register(r'admin/addon-categories', AddonCategoryAdminViewSet, basename='admin-addon-categories')
router.register(r'admin/addons', AddonAdminViewSet, basename='admin-addons')
router.register(r'admin/addon-options', AddonOptionAdminViewSet, basename='admin-addon-options')

urlpatterns = [
    path('products/sitemap/', ProductSitemapAPIView.as_view()),
    path('categories/sitemap/', CategorySitemapAPIView.as_view()),


    # Public APIs
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('menu-categories/', CategoryWithProductsAPIView.as_view(), name='menu-categories'),

    path('products/<slug:slug>/addons/', ProductAddonCategoriesAPIView.as_view(), name='product-addon-categories'),

    # Admin APIs
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)