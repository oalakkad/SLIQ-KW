# myapp/apps.py
from django.apps import AppConfig
from django.contrib.auth import get_user_model

class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "full_auth"
