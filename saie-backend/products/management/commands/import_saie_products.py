import os
import json
import requests
from pathlib import Path
from tabulate import tabulate
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from products.models import Product, Category, ProductImage
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Import products and categories from saieclips JSON files'

    def add_arguments(self, parser):
        parser.add_argument('--import', action='store_true', help='Actually write to the DB')

    def handle(self, *args, **options):
        base_path = Path('data')  # or wherever your files are
        products_file = base_path / 'products.json'
        categories_file = base_path / 'categories.json'

        if not products_file.exists() or not categories_file.exists():
            self.stderr.write("Missing products.json or categories.json")
            return

        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)["data"]

        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)["data"]

        # Build category map
        category_map = {}
        for cat in categories:
            obj, _ = Category.objects.get_or_create(
                slug=slugify(cat["category_name"]),
                defaults={
                    "name": cat["category_name"],
                    "name_ar": cat.get("category_name_ar", "")
                }
            )
            category_map[cat["category_id"]] = obj

        self.stdout.write(self.style.NOTICE("Previewing first 10 products:"))
        preview = []
        for p in products[:10]:
            preview.append([
                p["product_id"],
                p["title"],
                p.get("sale_price", "0"),
                p["current_stock"],
                category_map.get(p["category"], "Unknown").name
            ])
        self.stdout.write(tabulate(preview, headers=["ID", "Name", "Price", "Stock", "Category"]))

        if not options["import"]:
            self.stdout.write(self.style.WARNING("Run with --import to save these to the DB"))
            return

        for p in products:
            slug = slugify(p["title"])
            category = category_map.get(p["category"])

            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": p["title"],
                    "name_ar": p.get("title_ar", ""),
                    "description": p.get("description", ""),
                    "description_ar": p.get("description_ar", ""),
                    "price": float(p.get("sale_price") or 0),
                    "stock_quantity": int(p.get("current_stock") or 0),
                    "is_new_arrival": p.get("is_new", False),
                    "is_best_seller": p.get("is_best_seller", False),
                }
            )
            if created:
                product.categories.add(category)
                self.stdout.write(self.style.SUCCESS(f"Created product: {product.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Skipped (already exists): {product.name}"))

            # Download and assign main image if not already set
            image_url = p.get("main_image")
            if image_url and not product.image:
                try:
                    img_data = requests.get(image_url).content
                    product.image.save(f"{slug}.jpg", ContentFile(img_data), save=True)
                    self.stdout.write(f"📸 Attached image to {product.name}")
                except Exception as e:
                    self.stderr.write(f"⚠️ Failed to download image for {product.name}: {e}")

            # Add to ProductImage gallery too
            if image_url and not ProductImage.objects.filter(product=product).exists():
                try:
                    img_data = requests.get(image_url).content
                    ProductImage.objects.create(
                        product=product,
                        image=ContentFile(img_data, name=f"{slug}-gallery.jpg"),
                        alt_text=product.name
                    )
                except Exception as e:
                    self.stderr.write(f"⚠️ Failed gallery image for {product.name}: {e}")
