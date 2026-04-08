from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.fields.files import FieldFile
from products.models import Product, ProductImage  # <-- adjust

EXCLUDED_IDS = {39, 40, 41, 42, 43, 44, 45, 46, 47}

def get_storage_name(v) -> str:
    if isinstance(v, FieldFile):
        return v.name or ""
    return (v or "")

class Command(BaseCommand):
    help = "Make the gallery1 image identical to the product's main image."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview changes only.")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts["dry_run"]

        qs = Product.objects.exclude(id__in=EXCLUDED_IDS)

        changed = 0
        for p in qs.iterator():
            main = get_storage_name(p.image)
            if not main:
                continue

            # Find the gallery1 image (endswith -gallery1.jpg or id > gallery)
            gallery_qs = ProductImage.objects.filter(product=p).order_by("id")
            if gallery_qs.count() < 2:
                continue

            gallery1 = gallery_qs[1]  # second entry (images[1])
            g_name = get_storage_name(gallery1.image)

            if g_name != main:
                if not dry:
                    ProductImage.objects.filter(pk=gallery1.id).update(image=main)
                changed += 1
                self.stdout.write(f"[id={p.id}] gallery1 fixed → {main}")

        if dry:
            transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Gallery1 replaced with main image in {changed} products."
            + (" (dry-run)" if dry else "")
        ))
