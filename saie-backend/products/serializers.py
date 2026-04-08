from rest_framework import serializers
from .models import Product, ProductImage, Category, AddonCategory, Addon, AddonOption


# Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_ar', 'slug', 'parent']

# Product Image Serializer
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text']

# Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        source='categories'
    )
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_ar', 'slug',
            'description', 'description_ar',
            'price', 'stock_quantity', 'image',
            'is_new_arrival', 'is_best_seller',
            'categories', 'category_ids', 'images',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        categories = validated_data.pop('categories', [])
        product = Product.objects.create(**validated_data)
        if categories:
            product.categories.set(categories)
        return product

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if categories is not None:
            instance.categories.set(categories)
        return instance

# Serializer to assign a ProductImage as thumbnail to a Product
class ProductThumbnailAssignSerializer(serializers.ModelSerializer):
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductImage.objects.all(), write_only=True
    )

    class Meta:
        model = Product
        fields = ['id', 'image', 'image_id']

    def update(self, instance, validated_data):
        product_image = validated_data.pop('image_id')
        instance.image = product_image.image  # Directly assign same file
        instance.save()
        return instance

class AddonOptionSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=10, decimal_places=3, source='extra_price'
    )

    class Meta:
        model = AddonOption
        fields = ['id', 'name', 'name_ar', 'price']


class AddonSerializer(serializers.ModelSerializer):
    options = AddonOptionSerializer(many=True, required=False)

    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=AddonCategory.objects.all(),
        many=True,
        source='categories',
        required=False
    )

    # ✅ NEW: specific products mapping
    specific_product_ids = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True,
        source='specific_products',
        required=False
    )

    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Addon
        fields = [
            'id', 'name', 'name_ar', 'price',
            'requires_custom_name', 'allow_multiple_options',
            'categories', 'category_ids',
            'specific_product_ids',   # ✅ NEW
            'options'
        ]

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        categories = [c for c in validated_data.pop('categories', []) if c is not None]

        # ✅ NEW
        specific_products = validated_data.pop('specific_products', [])

        addon = Addon.objects.create(**validated_data)

        if categories:
            addon.categories.set(categories)

        # ✅ NEW
        if specific_products:
            addon.specific_products.set(specific_products)

        # Create options
        for opt in options_data:
            AddonOption.objects.create(addon=addon, **opt)

        return addon

    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)
        categories = validated_data.pop('categories', None)

        # ✅ NEW
        specific_products = validated_data.pop('specific_products', None)

        # Update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update categories if provided
        if categories is not None:
            instance.categories.set([c for c in categories if c is not None])

        # ✅ NEW
        if specific_products is not None:
            instance.specific_products.set(specific_products)

        # Replace options if provided
        if options_data is not None:
            instance.options.all().delete()
            for opt in options_data:
                AddonOption.objects.create(addon=instance, **opt)

        return instance


class AddonCategorySerializer(serializers.ModelSerializer):
    addons = AddonSerializer(many=True, read_only=True)

    # READ linked products (admin UI)
    products = serializers.StringRelatedField(many=True, read_only=True)

    # WRITE linked products
    product_ids = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True,
        source='products',
        write_only=True,
        required=False
    )

    class Meta:
        model = AddonCategory
        fields = [
            'id',
            'name',
            'name_ar',
            'addons',
            'products',
            'product_ids',
        ]

class PublicAddonOptionSerializer(serializers.ModelSerializer):
    # expose extra_price as price for UI consistency
    price = serializers.DecimalField(max_digits=10, decimal_places=3, source='extra_price')

    class Meta:
        model = AddonOption
        fields = ['id', 'name', 'name_ar', 'price']


class PublicAddonSerializer(serializers.ModelSerializer):
    options = PublicAddonOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Addon
        fields = [
            'id',
            'name',
            'name_ar',
            'price',
            'allow_multiple_options',
            'requires_custom_name',
            'options',
        ]


class PublicAddonCategorySerializer(serializers.ModelSerializer):
    # This uses the M2M from Addon → AddonCategory (related_name='addons')
    addons = serializers.SerializerMethodField()

    def get_addons(self, obj):
        addons = getattr(obj, "addons_filtered", obj.addons.all())
        return PublicAddonSerializer(addons, many=True).data

    class Meta:
        model = AddonCategory
        fields = ['id', 'name', 'name_ar', 'addons']
