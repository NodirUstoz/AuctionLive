"""
Bid models: Bid, AutoBid, BidHistory for tracking all bidding activity.
"""

from django.conf import settings
from django.db import models


class Bid(models.Model):
    """Individual bid on an auction."""

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="bids",
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_auto_bid = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    is_winning = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["auction", "-amount"]),
            models.Index(fields=["bidder", "-created_at"]),
        ]

    def __str__(self):
        return f"Bid ${self.amount} on {self.auction.title} by {self.bidder.username}"

    def save(self, *args, **kwargs):
        # Mark previous winning bid as not winning
        if self.is_winning:
            Bid.objects.filter(
                auction=self.auction, is_winning=True
            ).exclude(pk=self.pk).update(is_winning=False)
        super().save(*args, **kwargs)


class AutoBid(models.Model):
    """Auto-bidding configuration for a user on a specific auction."""

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="auto_bids",
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auto_bids",
    )
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    increment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount to increment each auto-bid by.",
    )
    is_active = models.BooleanField(default=True)
    total_bids_placed = models.PositiveIntegerField(default=0)
    last_bid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("auction", "bidder")
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"AutoBid by {self.bidder.username} on {self.auction.title} "
            f"(max: ${self.max_amount})"
        )

    @property
    def remaining_budget(self):
        """Calculate remaining auto-bid budget."""
        if self.last_bid_amount:
            return self.max_amount - self.last_bid_amount
        return self.max_amount

    def can_bid(self, current_price):
        """Check if auto-bid can still place bids."""
        next_bid = current_price + self.increment
        return self.is_active and next_bid <= self.max_amount

    def deactivate(self):
        """Deactivate the auto-bid."""
        self.is_active = False
        self.save(update_fields=["is_active"])


class BidHistory(models.Model):
    """Audit log for all bidding events."""

    EVENT_CHOICES = [
        ("bid_placed", "Bid Placed"),
        ("bid_retracted", "Bid Retracted"),
        ("auto_bid_placed", "Auto Bid Placed"),
        ("auto_bid_created", "Auto Bid Created"),
        ("auto_bid_deactivated", "Auto Bid Deactivated"),
        ("auto_bid_exhausted", "Auto Bid Budget Exhausted"),
        ("outbid", "Outbid"),
        ("auction_extended", "Auction Extended"),
    ]

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="bid_history",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bid_history",
    )
    bid = models.ForeignKey(
        Bid,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="history_entries",
    )
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bid History Entry"
        verbose_name_plural = "Bid History Entries"

    def __str__(self):
        return f"{self.event} - {self.auction.title} by {self.user.username}"
