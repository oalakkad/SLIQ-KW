from django.urls import path
from .views import ContactMessageCreateView, AdminStatsView, SiteSettingsView, proxy_instagram_image, HomeImagesListView, HomeImageUpdateView

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("site-settings/", SiteSettingsView.as_view(), name="site-settings"),
    path("proxy-image/", proxy_instagram_image, name="proxy_instagram_image"),
    path("home-images/", HomeImagesListView.as_view(), name="home-images-list"),
    path("home-images/<str:key>/", HomeImageUpdateView.as_view(), name="home-images-update"),
]
