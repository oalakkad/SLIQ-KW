from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=3)
    stock_quantity = models.IntegerField()
    image = models.ImageField(upload_to='product-thumbnails/', blank=True, null=True)
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    categories = models.ManyToManyField(
        'Category',
        related_name='products',
        through='ProductCategory',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)

    class Meta:
        db_table = 'products_product_categories'
        unique_together = ('product', 'category')


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='product-images/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class AddonCategory(models.Model):
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    # Link to product categories (many-to-many)
    product_categories = models.ManyToManyField(
        Category,
        related_name='addon_categories',
        blank=True
    )

    # Apply addon category to specific products
    products = models.ManyToManyField(
        'Product',
        related_name='addon_categories',
        blank=True
    )

    def __str__(self):
        return self.name


class Addon(models.Model):
    categories = models.ManyToManyField(
        AddonCategory,
        related_name='addons',
        blank=True
    )
    specific_products = models.ManyToManyField(
        Product,
        related_name='specific_addons',
        blank=True
    )
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=3)
    requires_custom_name = models.BooleanField(default=False)
    allow_multiple_options = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class AddonOption(models.Model):
    addon = models.ForeignKey(
        Addon,
        on_delete=models.CASCADE,
        related_name='options'
    )
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    extra_price = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)

    def __str__(self):
        return f"{self.name} - {self.addon.name}"
