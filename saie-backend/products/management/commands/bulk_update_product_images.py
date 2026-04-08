from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

# ⬇️ Adjust these imports to match your project
from products.models import Product, ProductImage

EXCLUDED_IDS = {39, 40, 41, 42, 43, 44, 45, 46, 47}
MEDIA_BASE = "http://localhost:8000/media/"
MAIN_PATTERN = MEDIA_BASE + "product-images/{slug}1.jpg"
GALLERY_PATTERN = MEDIA_BASE + "product-images/{slug}-gallery1.jpg"


class Command(BaseCommand):
    help = (
        "Update main image and add gallery1 image for all products except certain IDs. "
        "Main image -> product-images/{slug}1.jpg; "
        "New gallery -> product-images/{slug}-gallery1.jpg."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without saving.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        qs = Product.objects.exclude(id__in=EXCLUDED_IDS)

        updated_main = 0
        added_gallery = 0
        skipped = 0

        for product in qs.iterator():
            slug = getattr(product, "slug", None)
            name = getattr(product, "name", "") or ""

            if not slug:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipping id={product.id}: no slug"))
                continue

            # Build target URLs
            new_main_url = MAIN_PATTERN.format(slug=slug)
            new_gallery_url = GALLERY_PATTERN.format(slug=slug)

            # 1) Update main image if different
            main_changed = False
            current_main_url = getattr(product, "image", "") or ""
            if current_main_url != new_main_url:
                main_changed = True
                if not dry_run:
                    product.image = new_main_url
                    # Save only the changed field to be efficient/safe
                    product.save(update_fields=["image"])
                updated_main += 1

            # 2) Add gallery1 if it doesn't already exist
            #    We consider it present if any ProductImage for this product endswith the same file name.
            exists = ProductImage.objects.filter(
                Q(product=product) & Q(image__endswith=f"{slug}-gallery1.jpg")
            ).exists()

            gallery_added_now = False
            if not exists:
                if not dry_run:
                    ProductImage.objects.create(
                        product=product,
                        image=new_gallery_url,
                        alt_text=name or slug.replace("-", " ").title(),
                    )
                added_gallery += 1
                gallery_added_now = True

            # log per-product summary
            if main_changed or gallery_added_now:
                self.stdout.write(
                    f"[id={product.id} slug={slug}] "
                    f"{'MAIN→updated' if main_changed else 'MAIN→ok'}, "
                    f"{'GALLERY1→added' if gallery_added_now else 'GALLERY1→exists'}"
                )

        if dry_run:
            # Rollback dry-run changes
            transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Main updated: {updated_main}, gallery1 added: {added_gallery}, skipped (no slug): {skipped}."
            + (" (dry-run)" if dry_run else "")
        ))
