"""
Payment views for creating, listing, and confirming payments.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.models import Auction

from .models import Escrow, Payment
from .serializers import (
    CreatePaymentSerializer,
    EscrowSerializer,
    PaymentSerializer,
)
from .services import PaymentService


class CreatePaymentView(APIView):
    """Create a payment for a won auction."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            auction = Auction.objects.get(
                id=serializer.validated_data["auction_id"]
            )
            payment = PaymentService.create_payment(
                auction=auction,
                payer=request.user,
                payment_method=serializer.validated_data["payment_method"],
            )
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED,
            )
        except Auction.DoesNotExist:
            return Response(
                {"detail": "Auction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PaymentDetailView(generics.RetrieveAPIView):
    """Get payment details."""

    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Payment.objects.filter(
            payer=self.request.user
        ) | Payment.objects.filter(payee=self.request.user)


class ConfirmPaymentView(APIView):
    """Confirm a payment has been processed."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        try:
            payment = PaymentService.confirm_payment(
                payment_id=pk, user=request.user
            )
            return Response(PaymentSerializer(payment).data)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserPaymentsView(generics.ListAPIView):
    """List payments for the authenticated user."""

    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return (
            Payment.objects.filter(payer=user)
            | Payment.objects.filter(payee=user)
        ).select_related("auction", "payer", "payee").order_by("-created_at")


class UserEscrowsView(generics.ListAPIView):
    """List escrows for the authenticated user."""

    serializer_class = EscrowSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return (
            Escrow.objects.filter(buyer=user)
            | Escrow.objects.filter(seller=user)
        ).select_related("auction", "buyer", "seller").order_by("-created_at")
