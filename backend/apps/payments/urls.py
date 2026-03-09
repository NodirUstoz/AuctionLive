"""URL patterns for payments app."""

from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.CreatePaymentView.as_view(), name="create-payment"),
    path("list/", views.UserPaymentsView.as_view(), name="user-payments"),
    path("<int:pk>/", views.PaymentDetailView.as_view(), name="payment-detail"),
    path(
        "<int:pk>/confirm/",
        views.ConfirmPaymentView.as_view(),
        name="confirm-payment",
    ),
    path("escrows/", views.UserEscrowsView.as_view(), name="user-escrows"),
]
