"""
Payment serializers.
"""

from rest_framework import serializers

from .models import Escrow, Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""

    payer_name = serializers.CharField(source="payer.username", read_only=True)
    payee_name = serializers.CharField(source="payee.username", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "auction",
            "auction_title",
            "payer_name",
            "payee_name",
            "amount",
            "shipping_cost",
            "total_amount",
            "platform_fee",
            "status",
            "status_display",
            "payment_method",
            "transaction_id",
            "paid_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "total_amount",
            "platform_fee",
            "transaction_id",
            "paid_at",
            "created_at",
        )


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating a payment."""

    auction_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=[("stripe", "Stripe"), ("bank_transfer", "Bank Transfer")]
    )


class EscrowSerializer(serializers.ModelSerializer):
    """Serializer for escrow records."""

    buyer_name = serializers.CharField(source="buyer.username", read_only=True)
    seller_name = serializers.CharField(source="seller.username", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Escrow
        fields = (
            "id",
            "auction",
            "auction_title",
            "buyer_name",
            "seller_name",
            "amount",
            "platform_fee",
            "status",
            "status_display",
            "funded_at",
            "released_at",
            "expires_at",
            "created_at",
        )
