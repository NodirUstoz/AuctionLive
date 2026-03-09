"""
Auction models: AuctionCategory, Auction, AuctionImage, AuctionStatus tracking.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuctionCategory(models.Model):
    """Hierarchical auction categories."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auction Category"
        verbose_name_plural = "Auction Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        """Return full category path e.g. 'Electronics > Phones'."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class AuctionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Approval"
    ACTIVE = "active", "Active"
    EXTENDED = "extended", "Extended"
    ENDED = "ended", "Ended"
    SOLD = "sold", "Sold"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed (Reserve not met)"


class Auction(models.Model):
    """Main auction model."""

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auctions",
    )
    category = models.ForeignKey(
        AuctionCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name="auctions",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    condition = models.CharField(
        max_length=20,
        choices=[
            ("new", "New"),
            ("like_new", "Like New"),
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        default="good",
    )

    # Pricing
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    reserve_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Minimum price that must be met for the auction to succeed.",
    )
    current_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    buy_now_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Price at which the item can be purchased immediately.",
    )
    min_bid_increment = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("1.00")
    )

    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    original_end_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Original end time before any extensions.",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=AuctionStatus.choices,
        default=AuctionStatus.DRAFT,
        db_index=True,
    )

    # Winner
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auctions_won",
    )
    winning_bid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    # Stats
    total_bids = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    watchers_count = models.PositiveIntegerField(default=0)

    # Shipping
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    shipping_details = models.TextField(blank=True)

    # Metadata
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "end_time"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.status in (AuctionStatus.ACTIVE, AuctionStatus.EXTENDED)
            and self.start_time <= now <= self.end_time
        )

    @property
    def time_remaining(self):
        """Return seconds remaining in the auction."""
        if not self.is_active:
            return 0
        remaining = (self.end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))

    @property
    def reserve_met(self):
        """Check if the reserve price has been met."""
        if self.reserve_price is None:
            return True
        return self.current_price >= self.reserve_price

    @property
    def minimum_bid(self):
        """Calculate the minimum allowed bid."""
        if self.current_price == Decimal("0.00"):
            return self.starting_price
        return self.current_price + self.min_bid_increment

    def extend_auction(self, minutes=None):
        """Extend auction time if a bid is placed near the end."""
        from django.conf import settings as django_settings

        if minutes is None:
            minutes = django_settings.AUCTION_EXTEND_MINUTES

        self.original_end_time = self.original_end_time or self.end_time
        self.end_time = timezone.now() + timezone.timedelta(minutes=minutes)
        self.status = AuctionStatus.EXTENDED
        self.save(update_fields=["end_time", "original_end_time", "status"])

    def end_auction(self):
        """Process auction ending."""
        from apps.bids.models import Bid

        highest_bid = (
            Bid.objects.filter(auction=self, is_valid=True)
            .order_by("-amount")
            .first()
        )

        if highest_bid and self.reserve_met:
            self.status = AuctionStatus.SOLD
            self.winner = highest_bid.bidder
            self.winning_bid = highest_bid.amount
        elif highest_bid and not self.reserve_met:
            self.status = AuctionStatus.FAILED
        else:
            self.status = AuctionStatus.ENDED

        self.save(update_fields=["status", "winner", "winning_bid"])
        return self.status

    def increment_views(self):
        """Increment view count atomically."""
        Auction.objects.filter(pk=self.pk).update(
            view_count=models.F("view_count") + 1
        )


class AuctionImage(models.Model):
    """Images associated with an auction."""

    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="auctions/%Y/%m/%d/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"Image for {self.auction.title}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per auction
        if self.is_primary:
            AuctionImage.objects.filter(
                auction=self.auction, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
