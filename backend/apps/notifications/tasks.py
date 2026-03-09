"""
Celery tasks for notification processing.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, notification_id):
    """Send email for a specific notification."""
    from .models import Notification
    from .services import NotificationService

    try:
        notification = Notification.objects.get(id=notification_id)
        if not notification.email_sent:
            NotificationService.send_email_for_notification(notification)
    except Notification.DoesNotExist:
        logger.warning(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"Error sending notification email {notification_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_ending_soon_notifications():
    """
    Send notifications for auctions ending within the next 5 minutes
    to users who are watching or have bid on them.
    """
    from apps.auctions.models import Auction, AuctionStatus
    from apps.bids.models import Bid
    from apps.watchlist.models import WatchlistItem
    from .services import NotificationService

    threshold_start = timezone.now()
    threshold_end = threshold_start + timezone.timedelta(minutes=5)

    ending_soon = Auction.objects.filter(
        status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED],
        end_time__range=(threshold_start, threshold_end),
    )

    notified_count = 0

    for auction in ending_soon:
        # Get unique users who should be notified (bidders + watchers)
        bidder_ids = set(
            Bid.objects.filter(auction=auction, is_valid=True)
            .values_list("bidder_id", flat=True)
            .distinct()
        )
        watcher_ids = set(
            WatchlistItem.objects.filter(auction=auction)
            .values_list("user_id", flat=True)
        )

        user_ids = bidder_ids | watcher_ids
        # Don't notify the seller
        user_ids.discard(auction.seller_id)

        # Check if we already sent an ending-soon notification recently
        from .models import Notification

        already_notified = set(
            Notification.objects.filter(
                auction=auction,
                notification_type="auction_ending",
                created_at__gte=threshold_start - timezone.timedelta(minutes=10),
            ).values_list("user_id", flat=True)
        )

        from django.contrib.auth import get_user_model

        User = get_user_model()

        for user_id in user_ids - already_notified:
            try:
                user = User.objects.get(id=user_id)
                minutes_left = int(
                    (auction.end_time - timezone.now()).total_seconds() / 60
                )
                NotificationService.create_notification(
                    user=user,
                    notification_type="auction_ending",
                    title=f"Auction ending soon: {auction.title}",
                    message=(
                        f'The auction "{auction.title}" is ending in '
                        f"approximately {minutes_left} minutes. "
                        f"Current price: ${auction.current_price}."
                    ),
                    auction=auction,
                )
                notified_count += 1
            except User.DoesNotExist:
                continue

    logger.info(f"Sent {notified_count} ending-soon notifications")
    return f"Sent {notified_count} ending-soon notifications"
