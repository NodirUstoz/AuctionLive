"""URL patterns for auctions app."""

from django.urls import path

from . import views

app_name = "auctions"

urlpatterns = [
    path("", views.AuctionListView.as_view(), name="auction-list"),
    path("create/", views.AuctionCreateView.as_view(), name="auction-create"),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "categories/<slug:slug>/auctions/",
        views.CategoryAuctionsView.as_view(),
        name="category-auctions",
    ),
    path("featured/", views.FeaturedAuctionsView.as_view(), name="featured-auctions"),
    path(
        "seller-dashboard/",
        views.SellerDashboardView.as_view(),
        name="seller-dashboard",
    ),
    path("my-auctions/", views.MyAuctionsView.as_view(), name="my-auctions"),
    path("<int:pk>/", views.AuctionByIdView.as_view(), name="auction-by-id"),
    path("<slug:slug>/", views.AuctionDetailView.as_view(), name="auction-detail"),
]
