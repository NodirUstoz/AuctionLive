"""
Celery tasks for auction processing: ending auctions, sending notifications,
and broadcasting updates via WebSocket channels.
"""

import logging

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_ending_auctions(self):
    """
    Check for auctions that are about to end (within 60 seconds)
    and broadcast countdown updates to connected clients.
    """
    from .models import Auction, AuctionStatus

    threshold = timezone.now() + timezone.timedelta(seconds=60)
    ending_soon = Auction.objects.filter(
        status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED],
        end_time__lte=threshold,
        end_time__gt=timezone.now(),
    )

    channel_layer = get_channel_layer()
    for auction in ending_soon:
        try:
            async_to_sync(channel_layer.group_send)(
                f"auction_{auction.id}",
                {
                    "type": "auction_update",
                    "data": {
                        "type": "ending_soon",
                        "auction_id": auction.id,
                        "time_remaining": auction.time_remaining,
                        "current_price": str(auction.current_price),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting ending soon for auction {auction.id}: {e}")

    return f"Checked {ending_soon.count()} ending auctions"


@shared_task(bind=True, max_retries=3)
def process_ended_auctions(self):
    """
    Find auctions whose end_time has passed and process their completion.
    Determines winners, updates statuses, and triggers notifications.
    """
    from .models import Auction, AuctionStatus
    from apps.notifications.services import NotificationService
    from apps.payments.models import Escrow

    ended_auctions = Auction.objects.filter(
        status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED],
        end_time__lte=timezone.now(),
    )

    channel_layer = get_channel_layer()
    processed = 0

    for auction in ended_auctions:
        try:
            final_status = auction.end_auction()
            processed += 1

            # Broadcast auction ended to WebSocket group
            update_data = {
                "type": "auction_ended",
                "auction_id": auction.id,
                "status": final_status,
                "final_price": str(auction.winning_bid) if auction.winning_bid else None,
                "winner": auction.winner.username if auction.winner else None,
            }

            async_to_sync(channel_layer.group_send)(
                f"auction_{auction.id}",
                {"type": "auction_update", "data": update_data},
            )

            # Send notifications
            if final_status == AuctionStatus.SOLD:
                # Notify winner
                NotificationService.create_notification(
                    user=auction.winner,
                    notification_type="auction_won",
                    title=f"You won: {auction.title}",
                    message=(
                        f"Congratulations! You won the auction for "
                        f'"{auction.title}" with a bid of ${auction.winning_bid}.'
                    ),
                    auction=auction,
                )

                # Create escrow
                Escrow.objects.create(
                    auction=auction,
                    buyer=auction.winner,
                    seller=auction.seller,
                    amount=auction.winning_bid,
                    status="pending",
                )

                # Notify seller
                NotificationService.create_notification(
                    user=auction.seller,
                    notification_type="auction_sold",
                    title=f"Auction sold: {auction.title}",
                    message=(
                        f'Your auction "{auction.title}" has been sold '
                        f"for ${auction.winning_bid} to {auction.winner.username}."
                    ),
                    auction=auction,
                )

                # Update seller profile stats
                if hasattr(auction.seller, "seller_profile"):
                    auction.seller.seller_profile.update_stats(auction.winning_bid)

                # Update bidder profile stats
                if hasattr(auction.winner, "bidder_profile"):
                    auction.winner.bidder_profile.record_win(auction.winning_bid)

            elif final_status == AuctionStatus.FAILED:
                NotificationService.create_notification(
                    user=auction.seller,
                    notification_type="auction_failed",
                    title=f"Auction ended: {auction.title}",
                    message=(
                        f'Your auction "{auction.title}" ended without '
                        f"meeting the reserve price."
                    ),
                    auction=auction,
                )

            # Notify all watchers
            notify_watchers_auction_ended.delay(auction.id, final_status)

        except Exception as e:
            logger.error(f"Error processing ended auction {auction.id}: {e}")

    return f"Processed {processed} ended auctions"


@shared_task
def notify_watchers_auction_ended(auction_id, final_status):
    """Notify all watchers of an auction that it has ended."""
    from .models import Auction
    from apps.watchlist.models import WatchlistItem
    from apps.notifications.services import NotificationService

    try:
        auction = Auction.objects.get(id=auction_id)
        watchers = WatchlistItem.objects.filter(auction=auction).select_related("user")

        for item in watchers:
            if item.user != auction.winner and item.user != auction.seller:
                NotificationService.create_notification(
                    user=item.user,
                    notification_type="watched_auction_ended",
                    title=f"Watched auction ended: {auction.title}",
                    message=(
                        f'The auction "{auction.title}" you were watching has ended.'
                    ),
                    auction=auction,
                )
    except Auction.DoesNotExist:
        logger.warning(f"Auction {auction_id} not found for watcher notification")


@shared_task
def broadcast_bid_update(auction_id, bid_data):
    """Broadcast a new bid to all WebSocket clients watching an auction."""
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"auction_{auction_id}",
            {
                "type": "new_bid",
                "data": bid_data,
            },
        )
    except Exception as e:
        logger.error(f"Error broadcasting bid for auction {auction_id}: {e}")
