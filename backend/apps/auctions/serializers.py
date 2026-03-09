"""
Auction serializers for CRUD operations, categories, and images.
"""

from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Auction, AuctionCategory, AuctionImage, AuctionStatus


class AuctionCategorySerializer(serializers.ModelSerializer):
    """Serializer for auction categories."""

    children = serializers.SerializerMethodField()
    auction_count = serializers.SerializerMethodField()

    class Meta:
        model = AuctionCategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "icon",
            "is_active",
            "children",
            "auction_count",
        )

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return AuctionCategorySerializer(children, many=True).data

    def get_auction_count(self, obj):
        return obj.auctions.filter(
            status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
        ).count()


class AuctionImageSerializer(serializers.ModelSerializer):
    """Serializer for auction images."""

    class Meta:
        model = AuctionImage
        fields = ("id", "image", "alt_text", "is_primary", "order")


class AuctionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for auction listings."""

    seller_name = serializers.CharField(source="seller.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    time_remaining = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    minimum_bid = serializers.ReadOnlyField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "slug",
            "seller_name",
            "category_name",
            "condition",
            "starting_price",
            "current_price",
            "buy_now_price",
            "start_time",
            "end_time",
            "status",
            "total_bids",
            "view_count",
            "watchers_count",
            "primary_image",
            "time_remaining",
            "is_active",
            "minimum_bid",
            "featured",
            "created_at",
        )

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if not primary:
            primary = obj.images.first()
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None


class AuctionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for auction detail view."""

    seller = UserSerializer(read_only=True)
    category = AuctionCategorySerializer(read_only=True)
    images = AuctionImageSerializer(many=True, read_only=True)
    winner_name = serializers.CharField(
        source="winner.username", read_only=True, default=None
    )
    time_remaining = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    minimum_bid = serializers.ReadOnlyField()
    reserve_met = serializers.ReadOnlyField()
    is_watched = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "seller",
            "category",
            "title",
            "slug",
            "description",
            "condition",
            "starting_price",
            "reserve_price",
            "current_price",
            "buy_now_price",
            "min_bid_increment",
            "start_time",
            "end_time",
            "original_end_time",
            "status",
            "winner_name",
            "winning_bid",
            "total_bids",
            "view_count",
            "watchers_count",
            "shipping_cost",
            "shipping_details",
            "featured",
            "images",
            "time_remaining",
            "is_active",
            "minimum_bid",
            "reserve_met",
            "is_watched",
            "created_at",
            "updated_at",
        )

    def get_is_watched(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.watchlist_items.filter(user=request.user).exists()
        return False


class AuctionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating auctions."""

    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Auction
        fields = (
            "title",
            "category",
            "description",
            "condition",
            "starting_price",
            "reserve_price",
            "buy_now_price",
            "min_bid_increment",
            "start_time",
            "end_time",
            "shipping_cost",
            "shipping_details",
            "images",
        )

    def validate(self, attrs):
        start_time = attrs.get("start_time", timezone.now())
        end_time = attrs.get("end_time")

        if end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )

        if end_time and end_time <= timezone.now():
            raise serializers.ValidationError(
                {"end_time": "End time must be in the future."}
            )

        reserve_price = attrs.get("reserve_price")
        starting_price = attrs.get("starting_price")
        if reserve_price and starting_price and reserve_price < starting_price:
            raise serializers.ValidationError(
                {"reserve_price": "Reserve price must be >= starting price."}
            )

        buy_now = attrs.get("buy_now_price")
        if buy_now and starting_price and buy_now <= starting_price:
            raise serializers.ValidationError(
                {"buy_now_price": "Buy now price must be greater than starting price."}
            )

        return attrs

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        user = self.context["request"].user

        # Generate unique slug
        base_slug = slugify(validated_data["title"])
        slug = base_slug
        counter = 1
        while Auction.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        auction = Auction.objects.create(
            seller=user,
            slug=slug,
            current_price=validated_data["starting_price"],
            status=AuctionStatus.ACTIVE
            if validated_data.get("start_time", timezone.now()) <= timezone.now()
            else AuctionStatus.PENDING,
            **validated_data,
        )

        # Create images
        for i, image_data in enumerate(images_data):
            AuctionImage.objects.create(
                auction=auction,
                image=image_data,
                is_primary=(i == 0),
                order=i,
            )

        return auction


class SellerDashboardSerializer(serializers.Serializer):
    """Serializer for seller dashboard analytics."""

    active_auctions = serializers.IntegerField()
    total_auctions = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_bids_received = serializers.IntegerField()
    active_listings = AuctionListSerializer(many=True)
    recent_sales = AuctionListSerializer(many=True)
    pending_payments = serializers.IntegerField()
