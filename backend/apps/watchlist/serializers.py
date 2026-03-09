"""
Watchlist serializers.
"""

from rest_framework import serializers

from apps.auctions.serializers import AuctionListSerializer

from .models import WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    """Serializer for watchlist items with nested auction data."""

    auction_detail = AuctionListSerializer(source="auction", read_only=True)

    class Meta:
        model = WatchlistItem
        fields = (
            "id",
            "auction",
            "auction_detail",
            "notify_on_bid",
            "notify_on_ending",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_auction(self, value):
        user = self.context["request"].user
        if WatchlistItem.objects.filter(user=user, auction=value).exists():
            raise serializers.ValidationError(
                "This auction is already in your watchlist."
            )
        return value


class WatchlistToggleSerializer(serializers.Serializer):
    """Serializer for toggling watchlist status."""

    auction_id = serializers.IntegerField()
