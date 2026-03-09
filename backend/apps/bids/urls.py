"""URL patterns for bids app."""

from django.urls import path

from . import views

app_name = "bids"

urlpatterns = [
    path("", views.PlaceBidView.as_view(), name="place-bid"),
    path("my-bids/", views.UserBidsView.as_view(), name="my-bids"),
    path(
        "auction/<int:auction_id>/",
        views.AuctionBidsView.as_view(),
        name="auction-bids",
    ),
    path(
        "auction/<int:auction_id>/history/",
        views.BidHistoryView.as_view(),
        name="bid-history",
    ),
    path("auto-bid/", views.AutoBidCreateView.as_view(), name="auto-bid-create"),
    path("auto-bid/list/", views.AutoBidListView.as_view(), name="auto-bid-list"),
    path(
        "auto-bid/<int:pk>/",
        views.AutoBidDeactivateView.as_view(),
        name="auto-bid-deactivate",
    ),
]
