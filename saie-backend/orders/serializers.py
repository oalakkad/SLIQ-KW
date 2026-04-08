# from datetime import timezone
from django.utils import timezone
from rest_framework import serializers
from decimal import Decimal
from .models import Cart, CartItem, Wishlist, Order, OrderItem, DiscountCode, DiscountUsage
from products.models import Product
from products.serializers import ProductSerializer
from django.contrib.auth import get_user_model
from users.models import Address

# ⬇️ Adjust imports below to match your actual add-on models / relations
from products.models import AddonCategory, Addon, AddonOption  # <-- ensure these exist / adjust names

User = get_user_model()


class ProductSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'name_ar', 'price', 'image', 'slug']


class CartItemSerializer(serializers.ModelSerializer):
    # READ
    product = ProductSimpleSerializer(read_only=True)

    # WRITE
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    # stays as your raw normalized payload for writes
    addons = serializers.ListField(child=serializers.DictField(), required=False)
    unit_extra_price = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    unit_price = serializers.SerializerMethodField(read_only=True)
    line_total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_id', 'quantity',
            'addons', 'unit_extra_price', 'unit_price', 'line_total',
        ]
        extra_kwargs = {'quantity': {'required': True}}

    # ----- formatting helper (for response) -----
    def _fmt3(self, value) -> str:
        d = Decimal(str(value or 0)).quantize(Decimal('0.001'))
        return f"{d:.3f}"

    # ----- enrich addons for GET without changing write -----
    def _addons_detail_from_raw(self, raw_addons):
        """
        Turn stored normalized addons (ids) into rich details with names & prices.
        Does not affect validation / create logic.
        """
        details = []
        if not raw_addons:
            return details

        # Collect ids
        cat_ids, addon_ids, option_ids = set(), set(), set()
        for sel in raw_addons:
            try:
                cat_ids.add(int(sel.get('category_id')))
                addon_ids.add(int(sel.get('addon_id')))
                for oid in (sel.get('option_ids') or []):
                    option_ids.add(int(oid))
            except (TypeError, ValueError):
                # if data is malformed, just skip enriching (shouldn't happen due to your validator)
                continue

        cats = {c.id: c for c in AddonCategory.objects.filter(id__in=cat_ids)}
        addons = {a.id: a for a in Addon.objects.filter(id__in=addon_ids)}
        options_by_id = {o.id: o for o in AddonOption.objects.filter(id__in=option_ids)}

        for sel in raw_addons:
            try:
                cat_id = int(sel.get('category_id'))
                addon_id = int(sel.get('addon_id'))
                opt_ids = [int(i) for i in (sel.get('option_ids') or [])]
            except (TypeError, ValueError):
                continue

            custom_name = (sel.get('custom_name') or '').strip() or None
            cat = cats.get(cat_id)
            addon = addons.get(addon_id)

            # Build base block even if something missing, to avoid breaking response
            base_price = Decimal(str(getattr(addon, 'price', 0) or 0))
            subtotal = Decimal('0.000') + base_price

            # Only include options that belong to this addon
            valid_opts = []
            for oid in opt_ids:
                opt = options_by_id.get(oid)
                if opt and getattr(opt, 'addon_id', None) == addon_id:
                    valid_opts.append(opt)

            options_out = []
            for opt in valid_opts:
                extra = Decimal(str(getattr(opt, 'extra_price', 0) or 0))
                subtotal += extra
                options_out.append({
                    'id': opt.id,
                    'name': getattr(opt, 'name', ''),
                    'name_ar': getattr(opt, 'name_ar', ''),
                    'extra_price': self._fmt3(extra),
                })

            details.append({
                'category': {
                    'id': cat.id if cat else cat_id,
                    'name': getattr(cat, 'name', ''),
                    'name_ar': getattr(cat, 'name_ar', ''),
                },
                'addon': {
                    'id': addon.id if addon else addon_id,
                    'name': getattr(addon, 'name', ''),
                    'name_ar': getattr(addon, 'name_ar', ''),
                    'base_price': self._fmt3(base_price),
                    'allow_multiple_options': getattr(addon, 'allow_multiple_options', False),
                    'requires_custom_name': getattr(addon, 'requires_custom_name', False),
                    'custom_name': custom_name,
                },
                'options': options_out,
                'selection_subtotal': self._fmt3(subtotal),  # base + options extras
            })

        return details

    # ----- computed fields -----
    def get_unit_price(self, obj):
        base = Decimal(obj.product.price)
        extra = obj.unit_extra_price or Decimal('0.000')
        return f"{(base + extra):.3f}"

    def get_line_total(self, obj):
        return f"{(Decimal(self.get_unit_price(obj)) * obj.quantity):.3f}"

    # ----- ONLY CHANGE TO GET: override to_representation -----
    def to_representation(self, obj):
        """
        Keep the write contract intact (client sends raw normalized `addons`),
        but on read, replace `addons` with fully-detailed objects.
        """
        data = super().to_representation(obj)
        raw = obj.addons or []
        data['addons'] = self._addons_detail_from_raw(raw)
        return data

    # ----- helpers (unchanged) -----
    def _canonicalize_addons(self, addons_list):
        if not addons_list:
            return []
        norm = []
        for raw in addons_list:
            try:
                category_id = int(raw.get('category_id'))
                addon_id = int(raw.get('addon_id'))
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid addon payload: category_id/addon_id must be integers.")
            option_ids = raw.get('option_ids', [])
            if not isinstance(option_ids, list):
                raise serializers.ValidationError("option_ids must be a list.")
            option_ids = sorted(int(x) for x in option_ids)
            custom_name = (raw.get('custom_name') or None)
            norm.append({
                'category_id': category_id,
                'addon_id': addon_id,
                'option_ids': option_ids,
                'custom_name': custom_name,
            })
        norm.sort(key=lambda x: (x['category_id'], x['addon_id'], tuple(x['option_ids'])))
        return norm

    def _validate_and_price_addons(self, product: Product, addons_list):
        """
        Allowed AddonCategories are those linked to any Category the product belongs to.
        Addon must belong to that AddonCategory.
        Options must belong to that Addon.
        """
        if not addons_list:
            return Decimal('0.000')

        unit_extra = Decimal('0.000')

        # Categories of this product
        product_cats = product.categories.all()  # Category queryset

        # Allowed addon category ids (AddonCategory linked to any of these Categories)
        allowed_addon_cat_ids = set(
            AddonCategory.objects
            .filter(product_categories__in=product_cats)
            .distinct()
            .values_list('id', flat=True)
        )

        for item in addons_list:
            category_id = int(item['category_id'])
            addon_id = int(item['addon_id'])
            option_ids = item.get('option_ids', [])
            custom_name = (item.get('custom_name') or '').strip()

            # Category allowed?
            if category_id not in allowed_addon_cat_ids:
                raise serializers.ValidationError(
                    f"Addon category {category_id} is not allowed for this product."
                )

            # Addon must be linked to that AddonCategory (M2M)
            try:
                addon = Addon.objects.get(id=addon_id, categories__id=category_id)
            except Addon.DoesNotExist:
                raise serializers.ValidationError(
                    f"Addon {addon_id} is not part of addon category {category_id}."
                )

            # Multiple/single
            if not addon.allow_multiple_options and len(option_ids) > 1:
                raise serializers.ValidationError(f"Addon {addon_id} allows only one option.")

            # Custom name requirement
            if addon.requires_custom_name and not custom_name:
                raise serializers.ValidationError(f"Addon {addon_id} requires custom_name.")

            # Base addon price
            unit_extra += Decimal(str(addon.price or 0))

            # Options must be children of this addon; price = extra_price
            valid_opts = list(AddonOption.objects.filter(addon=addon, id__in=option_ids))
            if len(valid_opts) != len(option_ids):
                raise serializers.ValidationError(f"One or more options are invalid for addon {addon_id}.")

            for opt in valid_opts:
                unit_extra += Decimal(str(opt.extra_price or 0))

        return unit_extra.quantize(Decimal('0.001'))

    # ----- validation / create (unchanged) -----
    def validate(self, attrs):
        """
        - If PATCH only changes quantity, skip addon validation (no 'product'/'addons' in attrs).
        - If addons and/or product are changing, normalize + validate + price them.
        """
        changing_product = 'product' in attrs
        changing_addons = 'addons' in attrs

        if not (changing_product or changing_addons):
            # quantity-only update → nothing special to validate
            return attrs

        # Resolve product from payload if provided; otherwise from instance
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        if product is None:
            raise serializers.ValidationError("Product is required when changing addons or product.")

        # Use provided addons if present; else reuse instance addons for re-pricing
        addons_in = attrs['addons'] if 'addons' in attrs else (getattr(self.instance, 'addons', []) or [])
        addons_norm = self._canonicalize_addons(addons_in)
        attrs['addons'] = addons_norm

        # Recompute unit extra price for this selection
        attrs['_unit_extra_price'] = self._validate_and_price_addons(product, addons_norm)
        return attrs
    
    
    def update(self, instance, validated_data):
        """
        Ensure recomputed unit_extra_price is saved when addons/product change.
        Quantity-only PATCH should not touch addons/pricing.
        """
        # Quantity can always be updated
        if 'quantity' in validated_data:
            instance.quantity = validated_data['quantity']

        # If product is changing, set it
        if 'product' in validated_data:
            instance.product = validated_data['product']

        # If addons are changing, set them and apply recomputed price from validate()
        if 'addons' in validated_data:
            instance.addons = validated_data['addons']
            extra = validated_data.pop('_unit_extra_price', None)
            if extra is not None:
                instance.unit_extra_price = extra
        # If only product changed (no addons in payload) but we still computed price in validate()
        elif 'product' in validated_data and '_unit_extra_price' in validated_data:
            instance.unit_extra_price = validated_data['_unit_extra_price']

        instance.save()
        return instance

    def create(self, validated_data):
        cart = self.context.get('cart')
        if cart is None:
            raise RuntimeError("Cart not provided in serializer context.")

        product = validated_data['product']
        quantity = validated_data['quantity']
        addons = validated_data.get('addons', [])
        unit_extra_price = validated_data.pop('_unit_extra_price', Decimal('0.000'))

        # Merge with same product + identical addons selection
        existing_qs = CartItem.objects.filter(cart=cart, product=product)
        for item in existing_qs:
            if (item.addons or []) == addons:
                item.quantity += quantity
                item.save(update_fields=['quantity'])
                return item

        return CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            addons=addons,
            unit_extra_price=unit_extra_price,
        )


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_id', 'created_at', 'items']


# ----------------------------
# Wishlist
# ----------------------------
class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSimpleSerializer()

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'created_at']


class AddToWishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ['product']


# ----------------------------
# Orders
# ----------------------------
class OrderUserSerializer(serializers.ModelSerializer):
    """Minimal user info for authenticated orders."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    addons = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price_at_purchase", "addons"]

    def _fmt3(self, value) -> str:
        d = Decimal(str(value or 0)).quantize(Decimal("0.001"))
        return f"{d:.3f}"

    def _addons_detail_from_raw(self, raw_addons):
        """Return enriched addon details identical to CartItemSerializer."""
        if not raw_addons:
            return []

        cat_ids, addon_ids, option_ids = set(), set(), set()
        for sel in raw_addons:
            try:
                cat_ids.add(int(sel.get("category_id")))
                addon_ids.add(int(sel.get("addon_id")))
                for oid in (sel.get("option_ids") or []):
                    option_ids.add(int(oid))
            except (TypeError, ValueError):
                continue

        cats = {c.id: c for c in AddonCategory.objects.filter(id__in=cat_ids)}
        addons = {a.id: a for a in Addon.objects.filter(id__in=addon_ids)}
        opts = {o.id: o for o in AddonOption.objects.filter(id__in=option_ids)}

        details = []
        for sel in raw_addons:
            try:
                cat_id = int(sel.get("category_id"))
                addon_id = int(sel.get("addon_id"))
                opt_ids = [int(i) for i in (sel.get("option_ids") or [])]
            except (TypeError, ValueError):
                continue

            custom_name = (sel.get("custom_name") or "").strip() or None
            cat = cats.get(cat_id)
            addon = addons.get(addon_id)

            base_price = Decimal(str(getattr(addon, "price", 0) or 0))
            subtotal = Decimal("0.000") + base_price

            valid_opts = [
                o for o in opts.values() if getattr(o, "addon_id", None) == addon_id and o.id in opt_ids
            ]
            options_out = []
            for opt in valid_opts:
                extra = Decimal(str(getattr(opt, "extra_price", 0) or 0))
                subtotal += extra
                options_out.append({
                    "id": opt.id,
                    "name": getattr(opt, "name", ""),
                    "name_ar": getattr(opt, "name_ar", ""),
                    "extra_price": self._fmt3(extra),
                })

            details.append({
                "category": {
                    "id": cat.id if cat else cat_id,
                    "name": getattr(cat, "name", ""),
                    "name_ar": getattr(cat, "name_ar", ""),
                },
                "addon": {
                    "id": addon.id if addon else addon_id,
                    "name": getattr(addon, "name", ""),
                    "name_ar": getattr(addon, "name_ar", ""),
                    "base_price": self._fmt3(base_price),
                    "allow_multiple_options": getattr(addon, "allow_multiple_options", False),
                    "requires_custom_name": getattr(addon, "requires_custom_name", False),
                    "custom_name": custom_name,
                },
                "options": options_out,
                "selection_subtotal": self._fmt3(subtotal),
            })
        return details

    def get_addons(self, obj):
        return self._addons_detail_from_raw(obj.addons or [])


# -----------------------------------------
# Order Item Write Serializer
# -----------------------------------------
class OrderItemWriteSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    addons = serializers.ListField(child=serializers.DictField(), required=False)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price_at_purchase", "addons"]

    def validate(self, attrs):
        """Normalize addon payloads."""
        addons_in = attrs.get("addons", None)
        if addons_in is None:
            return attrs

        norm = []
        for raw in addons_in:
            try:
                category_id = int(raw.get("category_id"))
                addon_id = int(raw.get("addon_id"))
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid addon payload")

            option_ids = raw.get("option_ids", [])
            if not isinstance(option_ids, list):
                raise serializers.ValidationError("option_ids must be list")

            custom_name = (raw.get("custom_name") or "").strip() or None
            norm.append({
                "category_id": category_id,
                "addon_id": addon_id,
                "option_ids": sorted(int(x) for x in option_ids),
                "custom_name": custom_name,
            })
        attrs["addons"] = norm
        return attrs

    def create(self, validated_data):
        addons = validated_data.pop("addons", [])
        return OrderItem.objects.create(addons=addons, **validated_data)

    def update(self, instance, validated_data):
        addons = validated_data.pop("addons", None)
        if addons is not None:
            instance.addons = addons
        instance.product = validated_data.get("product", instance.product)
        instance.quantity = validated_data.get("quantity", instance.quantity)
        instance.price_at_purchase = validated_data.get("price_at_purchase", instance.price_at_purchase)
        instance.save()
        return instance


# -----------------------------------------
# Order Serializer (with get_discount + update)
# -----------------------------------------
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    items_write = OrderItemWriteSerializer(many=True, write_only=True)
    discount = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    discount_id = serializers.PrimaryKeyRelatedField(
        queryset=DiscountCode.objects.all(),
        source="discount",
        allow_null=True,
        required=False,
        write_only=True,
    )

    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="shipping_address",
        allow_null=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "guest_name", "guest_email", "guest_phone",
            "status", "total_price", "delivery_fee",
            "discount", "discount_id", "discount_amount",
            "address_id", "address",
            "shipping_full_name", "shipping_line", "shipping_city",
            "shipping_postal_code", "shipping_country", "shipping_phone",
            "created_at", "updated_at",
            "items", "items_write",
        ]

    # --------------------------
    # Getters
    # --------------------------
    def get_user(self, obj):
        if not obj.user:
            return None
        u = obj.user
        return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email}

    def get_discount(self, obj):
        if not obj.discount:
            return None
        disc = obj.discount
        return {
            "id": disc.id,
            "code": disc.code,
            "value": str(disc.value),
            "discount_type": disc.discount_type,
        }

    def get_address(self, obj):
        addr = obj.shipping_address
        if not addr:
            return {
                "full_name": obj.shipping_full_name,
                "address_line": obj.shipping_line,
                "city": obj.shipping_city,
                "postal_code": obj.shipping_postal_code,
                "country": obj.shipping_country,
                "phone": obj.shipping_phone,
            }
        return {
            "id": addr.id,
            "full_name": addr.full_name,
            "address_line": addr.address_line,
            "city": addr.city,
            "postal_code": addr.postal_code,
            "country": addr.country,
            "phone": addr.phone,
        }

    # --------------------------
    # Update
    # --------------------------
    def update(self, instance, validated_data):
        items_data = self.context["request"].data.get("items_write", None)

        # --- Basic fields ---
        instance.status = validated_data.get("status", instance.status)
        instance.total_price = validated_data.get("total_price", instance.total_price)

        # --- Discount handling ---
        if "discount" in validated_data:
            instance.discount = validated_data["discount"]
            if instance.discount:
                subtotal = sum(
                    Decimal(i.price_at_purchase) * i.quantity for i in instance.items.all()
                )
                discount_amount = instance.discount.discount_for_order(instance)
                instance.discount_amount = min(discount_amount, subtotal)
                delivery = instance.delivery_fee or Decimal("0.000")

                instance.total_price = (
                    subtotal
                    - instance.discount_amount
                    + delivery
                ).quantize(Decimal("0.001"))
            else:
                instance.discount_amount = Decimal("0.000")

        # --- Address update logic ---
        # 1. If Address FK provided, copy its values
        if "shipping_address" in validated_data:
            addr = validated_data["shipping_address"]
            instance.shipping_address = addr
            if addr:
                instance.shipping_full_name = addr.full_name
                instance.shipping_line = addr.address_line
                instance.shipping_city = addr.city
                instance.shipping_postal_code = addr.postal_code
                instance.shipping_country = addr.country
                instance.shipping_phone = addr.phone

        # 2. If direct flat fields provided, update them individually
        for field in [
            "shipping_full_name",
            "shipping_line",
            "shipping_city",
            "shipping_postal_code",
            "shipping_country",
            "shipping_phone",
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()

        # --- Items update ---
        if items_data:
            for item_data in items_data:
                item_id = item_data.get("id")
                addons_data = item_data.get("addons") or []
                if item_id:
                    try:
                        order_item = instance.items.get(id=item_id)
                        order_item.quantity = item_data.get("quantity", order_item.quantity)
                        order_item.price_at_purchase = item_data.get(
                            "price_at_purchase", order_item.price_at_purchase
                        )
                        order_item.product_id = item_data.get("product", order_item.product_id)
                        order_item.addons = addons_data
                        order_item.save()
                    except OrderItem.DoesNotExist:
                        OrderItem.objects.create(
                            order=instance,
                            product_id=item_data["product"],
                            quantity=item_data["quantity"],
                            price_at_purchase=item_data["price_at_purchase"],
                            addons=addons_data,
                        )
                else:
                    OrderItem.objects.create(
                        order=instance,
                        product_id=item_data["product"],
                        quantity=item_data["quantity"],
                        price_at_purchase=item_data["price_at_purchase"],
                        addons=addons_data,
                    )

        return instance

class DiscountCodeSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()  # 👈 declare computed field here

    class Meta:
        model = DiscountCode
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "value",
            "applies_to_all",
            "products",
            "categories",
            "usage_limit",
            "per_user_limit",
            "expiry_date",
            "active",
            "created_at",
            "status",   # 👈 now valid
        ]
        read_only_fields = ["id", "created_at"]

    def get_status(self, obj):
        if not obj.active:
            return "inactive"
        if obj.expiry_date and timezone.now() > obj.expiry_date:
            return "expired"
        return "active"


class DiscountUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountUsage
        fields = ["id", "discount", "order", "user", "used_at"]
        read_only_fields = ["id", "used_at"]