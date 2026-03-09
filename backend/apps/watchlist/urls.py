"""URL patterns for watchlist app."""

from django.urls import path

from . import views

app_name = "watchlist"

urlpatterns = [
    path("", views.WatchlistListView.as_view(), name="watchlist-list"),
    path("add/", views.WatchlistAddView.as_view(), name="watchlist-add"),
    path("toggle/", views.WatchlistToggleView.as_view(), name="watchlist-toggle"),
    path(
        "<int:pk>/",
        views.WatchlistRemoveView.as_view(),
        name="watchlist-remove",
    ),
]
