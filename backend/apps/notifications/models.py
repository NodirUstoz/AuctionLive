"""
Notification model for tracking user notifications.
"""

from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    OUTBID = "outbid", "Outbid"
    AUCTION_WON = "auction_won", "Auction Won"
    AUCTION_SOLD = "auction_sold", "Auction Sold"
    AUCTION_ENDING = "auction_ending", "Auction Ending Soon"
    AUCTION_FAILED = "auction_failed", "Auction Failed"
    PAYMENT_RECEIVED = "payment_received", "Payment Received"
    PAYMENT_CONFIRMED = "payment_confirmed", "Payment Confirmed"
    ESCROW_RELEASED = "escrow_released", "Escrow Released"
    ESCROW_EXPIRED = "escrow_expired", "Escrow Expired"
    AUTO_BID_EXHAUSTED = "auto_bid_exhausted", "Auto Bid Exhausted"
    WATCHED_AUCTION_ENDED = "watched_auction_ended", "Watched Auction Ended"
    SYSTEM = "system", "System Notification"


class Notification(models.Model):
    """User notification record."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"

    def mark_read(self):
        """Mark this notification as read."""
        from django.utils import timezone

        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])
