"""URL configuration for AuctionLive project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/auctions/", include("apps.auctions.urls")),
    path("api/bids/", include("apps.bids.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/watchlist/", include("apps.watchlist.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
