from django.shortcuts import render

# Create your views here.
from rest_framework import generics, viewsets, filters
from django_filters import rest_framework
from rest_framework.permissions import IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, ProductImage, AddonCategory, Addon, AddonOption
from .serializers import ProductSerializer, CategorySerializer, ProductImageSerializer, ProductThumbnailAssignSerializer, AddonCategorySerializer, AddonSerializer, AddonOptionSerializer, PublicAddonCategorySerializer
from .permissions import IsAdminOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dashboard.mixins import AdminLoggingMixin
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q

class ProductFilter(rest_framework.FilterSet):
    category_slug = rest_framework.CharFilter(field_name='categories__slug', lookup_expr='iexact')

    class Meta:
        model = Product
        fields = ['is_best_seller', 'is_new_arrival', 'category_slug']

# 🛍️ Public: List all products (with optional filters)
class ProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_best_seller', 'is_new_arrival', 'categories']
    filterset_class = ProductFilter
    search_fields = ['name', 'name_ar', 'description']
    ordering_fields = ['price', 'created_at']
    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get("ordering")

        if ordering == "featured":
            # bring best sellers first, then new arrivals, then newest
            return queryset.order_by("-is_best_seller", "-is_new_arrival", "-created_at")
        elif ordering == "price-lth":
            return queryset.order_by("price")
        elif ordering == "price-htl":
            return queryset.order_by("-price")

        # default ordering
        return queryset.order_by("-created_at")

# 🔍 Public: View single product by ID or slug
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]


# 📦 Public: List all categories
class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


# 🧰 Admin: Manage products with full CRUD
class ProductAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 🔻 Disable pagination just for this viewset
    pagination_class = None

    # Allow search by user info or status
    search_fields = [
        "name",
        "name_ar",
        "slug",
        "description",
        "description_ar",
        "categories__name",
        "categories__name_ar",
    ]

    def get_parser_classes(self):
        # Only the upload endpoint requires multipart
        if self.action == 'upload_images':
            return (MultiPartParser, FormParser)
        return super().get_parser_classes()

    # ✅ 1. DELETE /admin/products/{productId}/images/{imageId}/
    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[^/.]+)')
    def delete_product_image(self, request, pk=None, image_id=None):
        product = self.get_object()
        try:
            image = product.images.get(pk=image_id)
            image.delete()  # This deletes the DB row and the file from storage
            return Response({'status': 'image deleted'}, status=status.HTTP_204_NO_CONTENT)
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    # ✅ 2. POST /admin/products/{productId}/set-thumbnail/
    @action(detail=True, methods=['post'], url_path='set-thumbnail')
    def set_thumbnail(self, request, pk=None):
        product = self.get_object()
        image_id = request.data.get('image_id')

        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_image = product.images.get(pk=image_id)
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

        # Copy the image to the thumbnail field
        serializer = ProductThumbnailAssignSerializer(instance=product, data={'image_id': product_image.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'status': 'thumbnail assigned',
            'thumbnail_url': product.image.url
        })

    # ✅ 3. POST /admin/products/{id}/upload-images/
    # ✅ Atomic upload + optional thumbnail set
    @action(detail=True, methods=['post'], url_path='upload-images', parser_classes=[MultiPartParser, FormParser])
    @transaction.atomic
    def upload_images(self, request, pk=None):
        product = self.get_object()
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # optional 0-based index of the chosen thumbnail among 'files'
        try:
            thumb_idx_raw = request.data.get('thumbnail_index', None)
            thumbnail_index = int(thumb_idx_raw) if thumb_idx_raw is not None else None
        except (TypeError, ValueError):
            thumbnail_index = None

        created_images = []
        for f in files:
            img = ProductImage.objects.create(product=product, image=f)
            created_images.append({'id': img.id, 'image': img.image.url, 'alt_text': img.alt_text})

        if thumbnail_index is not None and 0 <= thumbnail_index < len(created_images):
            chosen_id = created_images[thumbnail_index]['id']
            serializer = ProductThumbnailAssignSerializer(instance=product, data={'image_id': chosen_id})
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response({'status': 'images uploaded', 'images': created_images}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["get"], url_path="products")
    def list_products(self, request, pk=None):
        addon = self.get_object()
        products = addon.specific_products.all().order_by("id")
        return Response(ProductSerializer(products, many=True).data)
    
    @action(detail=True, methods=["post"], url_path="products/set")
    def set_products(self, request, pk=None):
        addon = self.get_object()
        ids = request.data.get("product_ids", [])

        addon.specific_products.set(
            Product.objects.filter(id__in=ids)
        )

        return Response({"status": "updated"})
        

# 🧰 Admin: Manage categories
class CategoryAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_ar', 'slug']
    ordering_fields = ['name', 'id']
    ordering = ['name']

# 🧰 Admin: Manage Product Images
class ProductImageAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['alt_text', 'product__name']
    ordering_fields = ['id', 'product']
    ordering = ['id']

# Menu Categories
class CategoryWithProductsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.all()
        data = []

        for category in categories:
            products = Product.objects.filter(categories=category)[:12]
            product_data = ProductSerializer(products, many=True, context={'request': request}).data
            category_data = CategorySerializer(category, context={'request': request}).data
            category_data["products"] = product_data
            data.append(category_data)

        return Response(data)

class AddonCategoryAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = AddonCategory.objects.prefetch_related('products', 'addons')
    serializer_class = AddonCategorySerializer
    permission_classes = [IsAdminUser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_ar']

    # GET /admin/addon-categories/{id}/product-categories/
    @action(detail=True, methods=["get"], url_path="product-categories")
    def list_product_categories(self, request, pk=None):
        addon_cat = self.get_object()
        cats = addon_cat.product_categories.all().order_by("id")
        # Reuse your existing CategorySerializer (read-only list)
        return Response(CategorySerializer(cats, many=True, context={'request': request}).data)

    # POST /admin/addon-categories/{id}/product-categories/set/
    # body: { "category_ids": [1,2,3] }
    @action(detail=True, methods=["post"], url_path="product-categories/set")
    def set_product_categories(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("category_ids", [])
        if not isinstance(ids, list):
            return Response({"error": "category_ids must be a list of IDs"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            addon_cat.product_categories.set(Category.objects.filter(id__in=ids))
        # Return the SAME payload shape as your existing admin endpoints
        return Response(self.get_serializer(addon_cat, context={'request': request}).data)

    # POST /admin/addon-categories/{id}/product-categories/add/
    # body: { "category_ids": [4,5] }
    @action(detail=True, methods=["post"], url_path="product-categories/add")
    def add_product_categories(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("category_ids", [])
        if not isinstance(ids, list):
            return Response({"error": "category_ids must be a list of IDs"}, status=status.HTTP_400_BAD_REQUEST)

        to_add = Category.objects.filter(id__in=ids)
        with transaction.atomic():
            addon_cat.product_categories.add(*to_add)
        return Response(self.get_serializer(addon_cat, context={'request': request}).data)

    # POST /admin/addon-categories/{id}/product-categories/remove/
    # body: { "category_ids": [2] }
    @action(detail=True, methods=["post"], url_path="product-categories/remove")
    def remove_product_categories(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("category_ids", [])
        if not isinstance(ids, list):
            return Response({"error": "category_ids must be a list of IDs"}, status=status.HTTP_400_BAD_REQUEST)

        to_remove = Category.objects.filter(id__in=ids)
        with transaction.atomic():
            addon_cat.product_categories.remove(*to_remove)
        return Response(self.get_serializer(addon_cat, context={'request': request}).data)
    

    # GET /admin/addon-categories/{id}/products/
    @action(detail=True, methods=["get"], url_path="products")
    def list_products(self, request, pk=None):
        addon_cat = self.get_object()
        products = addon_cat.products.all().order_by("id")
        return Response(
            ProductSerializer(products, many=True, context={'request': request}).data
        )
    
    # POST /admin/addon-categories/{id}/products/set/
    @action(detail=True, methods=["post"], url_path="products/set")
    def set_products(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("product_ids", [])

        if not isinstance(ids, list):
            return Response(
                {"error": "product_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            addon_cat.products.set(Product.objects.filter(id__in=ids))

        return Response(self.get_serializer(addon_cat).data)
    
    # POST /admin/addon-categories/{id}/products/add/
    @action(detail=True, methods=["post"], url_path="products/add")
    def add_products(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("product_ids", [])

        if not isinstance(ids, list):
            return Response(
                {"error": "product_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            addon_cat.products.add(*Product.objects.filter(id__in=ids))

        return Response(self.get_serializer(addon_cat).data)
    
    # POST /admin/addon-categories/{id}/products/remove/
    @action(detail=True, methods=["post"], url_path="products/remove")
    def remove_products(self, request, pk=None):
        addon_cat = self.get_object()
        ids = request.data.get("product_ids", [])

        if not isinstance(ids, list):
            return Response(
                {"error": "product_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            addon_cat.products.remove(*Product.objects.filter(id__in=ids))

        return Response(self.get_serializer(addon_cat).data)


class AddonAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = Addon.objects.all()
    serializer_class = AddonSerializer
    permission_classes = [IsAdminUser]


class AddonOptionAdminViewSet(AdminLoggingMixin, viewsets.ModelViewSet):
    queryset = AddonOption.objects.all()
    serializer_class = AddonOptionSerializer
    permission_classes = [IsAdminUser]

class ProductAddonsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        # Gather all addon categories linked to any of the product's categories
        addon_categories = AddonCategory.objects.filter(
            Q(products=product) |
            Q(product_categories__in=product.categories.all())
        ).distinct()

        serializer = AddonCategorySerializer(addon_categories, many=True)
        return Response(serializer.data)
    
class ProductAddonCategoriesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug: str):
        product = get_object_or_404(
            Product.objects.prefetch_related('categories'),
            slug=slug
        )

        product_cats = product.categories.all()

        # Fetch addon categories normally (category-based)
        addon_categories = (
            AddonCategory.objects.filter(
                product_categories__in=product_cats
            )
            .distinct()
            .order_by('id')
            .prefetch_related(
                'addons__options',
                'addons__specific_products'
            )
        )

        # Apply ADDON-level override logic
        result = []

        for cat in addon_categories:
            filtered_addons = cat.addons.filter(
                Q(specific_products=product) |
                Q(specific_products__isnull=True)
            ).distinct()

            # Attach filtered addons dynamically
            cat.addons_filtered = filtered_addons
            result.append(cat)

        serializer = PublicAddonCategorySerializer(
            result,
            many=True,
            context={'request': request}
        )

        return Response(serializer.data)
    
class ProductSitemapAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = (
            Product.objects
            .filter(stock_quantity__gt=0)  # optional, see note below
            .values('slug', 'updated_at')
        )

        return Response(products)
    
class CategorySitemapAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = (
            Category.objects
            .values('slug')
        )

        # categories don’t have updated_at, so we fake stability
        data = [
            {
                'slug': c['slug'],
                'updated_at': None
            }
            for c in categories
        ]

        return Response(data)