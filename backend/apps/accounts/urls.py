"""URL patterns for accounts app."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.TokenRefreshAPIView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "profile/seller/",
        views.SellerProfileView.as_view(),
        name="seller-profile",
    ),
    path(
        "profile/bidder/",
        views.BidderProfileView.as_view(),
        name="bidder-profile",
    ),
    path(
        "change-password/",
        views.ChangePasswordView.as_view(),
        name="change-password",
    ),
]
