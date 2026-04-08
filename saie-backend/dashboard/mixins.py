from dashboard.models import AdminActivityLog

class AdminLoggingMixin:
    """
    Mixin to log detailed CRUD actions for admin dashboard ViewSets only.
    """

    def perform_create(self, serializer):
        instance = serializer.save()
        self.log_activity("CREATE", instance)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        self.log_activity("UPDATE", instance)
        return instance

    def perform_destroy(self, instance):
        self.log_activity("DELETE", instance)
        instance.delete()

    def log_activity(self, action, instance):
        """
        Logs detailed CRUD actions to AdminActivityLog.
        Only logs requests that target /api/admin/ endpoints (your dashboard).
        """
        request = self.request
        user = request.user

        # Only log dashboard API requests
        if not request.path.startswith("/api/admin/"):
            return

        if user.is_authenticated and (user.is_staff or user.is_superuser):
            AdminActivityLog.objects.create(
                admin=user,
                action=f"{action} {instance.__class__.__name__}: {instance}",
                resource_type=instance.__class__.__name__,
                resource_id=instance.id,
                ip_address=self.get_client_ip(request)
            )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
