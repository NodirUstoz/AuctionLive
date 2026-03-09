"""
Watchlist model for users to track auctions they're interested in.
"""

from django.conf import settings
from django.db import models


class WatchlistItem(models.Model):
    """A single watchlist entry linking a user to an auction."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watchlist_items",
    )
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="watchlist_items",
    )
    notify_on_bid = models.BooleanField(
        default=True,
        help_text="Notify when a new bid is placed.",
    )
    notify_on_ending = models.BooleanField(
        default=True,
        help_text="Notify when the auction is about to end.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "auction")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} watching {self.auction.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Increment watchers count on the auction
            from apps.auctions.models import Auction

            Auction.objects.filter(pk=self.auction_id).update(
                watchers_count=models.F("watchers_count") + 1
            )

    def delete(self, *args, **kwargs):
        auction_id = self.auction_id
        super().delete(*args, **kwargs)
        # Decrement watchers count on the auction
        from apps.auctions.models import Auction

        Auction.objects.filter(pk=auction_id).update(
            watchers_count=models.F("watchers_count") - 1
        )
