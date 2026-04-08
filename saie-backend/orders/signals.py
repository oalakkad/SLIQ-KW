from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Order
from full_auth.settings import EMAIL_HOST_USER


def _send_order_email(order: Order, subject: str, message: str):
    """Helper to send email to either user or guest."""
    recipient = None
    if order.user and order.user.email:
        recipient = order.user.email
        name = f"{order.user.first_name} {order.user.last_name}".strip()
    elif order.guest_email:
        recipient = order.guest_email
        name = order.guest_name or "Guest"
    else:
        return  # no recipient, skip

    # Personalize the message
    personalized_message = f"Hello {name},\n\n{message}"

    send_mail(
        subject,
        personalized_message,
        EMAIL_HOST_USER,
        [recipient],
        fail_silently=False,
    )


@receiver(post_save, sender=Order)
def send_order_created_email(sender, instance, created, **kwargs):
    if created:
        subject = f"Your order #{instance.id} has been placed!"
        message = f"Thank you for your order. The current status is: {instance.status}."
        _send_order_email(instance, subject, message)


@receiver(pre_save, sender=Order)
def send_order_status_change_email(sender, instance, **kwargs):
    if not instance.pk:
        return  # new order handled in post_save

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if previous.status != instance.status:
        subject = f"Your order #{instance.id} status has changed"
        message = f"Your order status is now: {instance.status}."
        _send_order_email(instance, subject, message)