"""
Bid serializers for placing bids, auto-bids, and bid history.
"""

from rest_framework import serializers

from .models import AutoBid, Bid, BidHistory


class BidSerializer(serializers.ModelSerializer):
    """Serializer for individual bids."""

    bidder_name = serializers.CharField(source="bidder.username", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)

    class Meta:
        model = Bid
        fields = (
            "id",
            "auction",
            "bidder_name",
            "amount",
            "is_auto_bid",
            "is_winning",
            "created_at",
            "auction_title",
        )
        read_only_fields = ("id", "bidder_name", "is_auto_bid", "is_winning", "created_at")


class PlaceBidSerializer(serializers.Serializer):
    """Serializer for placing a new bid."""

    auction_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be positive.")
        return value


class AutoBidSerializer(serializers.ModelSerializer):
    """Serializer for auto-bid configuration."""

    bidder_name = serializers.CharField(source="bidder.username", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    remaining_budget = serializers.ReadOnlyField()

    class Meta:
        model = AutoBid
        fields = (
            "id",
            "auction",
            "bidder_name",
            "auction_title",
            "max_amount",
            "increment",
            "is_active",
            "total_bids_placed",
            "last_bid_amount",
            "remaining_budget",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "bidder_name",
            "total_bids_placed",
            "last_bid_amount",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        auction = attrs.get("auction")
        max_amount = attrs.get("max_amount")
        increment = attrs.get("increment")

        if auction and max_amount:
            if max_amount <= auction.current_price:
                raise serializers.ValidationError(
                    {"max_amount": "Max amount must be greater than current price."}
                )

        if increment and auction:
            if increment < auction.min_bid_increment:
                raise serializers.ValidationError(
                    {
                        "increment": (
                            f"Increment must be at least "
                            f"${auction.min_bid_increment}."
                        )
                    }
                )

        return attrs


class CreateAutoBidSerializer(serializers.Serializer):
    """Serializer for creating auto-bid."""

    auction_id = serializers.IntegerField()
    max_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    increment = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_max_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max amount must be positive.")
        return value

    def validate_increment(self, value):
        if value <= 0:
            raise serializers.ValidationError("Increment must be positive.")
        return value


class BidHistorySerializer(serializers.ModelSerializer):
    """Serializer for bid history audit log."""

    user_name = serializers.CharField(source="user.username", read_only=True)
    event_display = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = BidHistory
        fields = (
            "id",
            "auction",
            "user_name",
            "event",
            "event_display",
            "amount",
            "metadata",
            "created_at",
        )
