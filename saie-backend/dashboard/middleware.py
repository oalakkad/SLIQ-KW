import json
from django.utils.timezone import now
from .models import AdminActivityLog

class AdminActivityLoggingMiddleware:
    """
    Middleware to log all admin dashboard requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log requests from authenticated staff or superusers
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            try:
                # Determine resource type and id
                resource_type = request.resolver_match.view_name if request.resolver_match else "unknown"
                resource_id = None
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    resource_id = response.data.get('id')  # e.g., after create/update

                AdminActivityLog.objects.create(
                    admin=request.user,
                    action=f"{request.method} {request.path}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=self.get_client_ip(request),
                    created_at=now()
                )
            except Exception:
                # Avoid breaking the request if logging fails
                pass

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
