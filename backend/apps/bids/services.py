"""
Bidding service: core business logic for placing bids, auto-bidding,
and auction extension on last-second bids.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.auctions.models import Auction, AuctionStatus

from .models import AutoBid, Bid, BidHistory

logger = logging.getLogger(__name__)


class BidService:
    """Service class encapsulating all bidding logic."""

    @staticmethod
    @transaction.atomic
    def place_bid(auction_id, bidder, amount, is_auto=False):
        """
        Place a bid on an auction with full validation.
        Uses select_for_update to prevent race conditions.

        Args:
            auction_id: ID of the auction to bid on
            bidder: User placing the bid
            amount: Decimal bid amount
            is_auto: Whether this is an auto-bid

        Returns:
            Bid instance

        Raises:
            ValueError: If bid is invalid
        """
        # Lock the auction row to prevent concurrent bid issues
        try:
            auction = Auction.objects.select_for_update().get(id=auction_id)
        except Auction.DoesNotExist:
            raise ValueError("Auction not found.")

        # Validation checks
        if not auction.is_active:
            raise ValueError("This auction is no longer active.")

        if auction.seller == bidder:
            raise ValueError("You cannot bid on your own auction.")

        if amount < auction.minimum_bid:
            raise ValueError(
                f"Bid must be at least ${auction.minimum_bid}. "
                f"Current price is ${auction.current_price}."
            )

        # Check buy-now price
        if auction.buy_now_price and amount >= auction.buy_now_price:
            return BidService._process_buy_now(auction, bidder, auction.buy_now_price)

        # Create the bid
        bid = Bid.objects.create(
            auction=auction,
            bidder=bidder,
            amount=amount,
            is_auto_bid=is_auto,
            is_winning=True,
        )

        # Update auction state
        auction.current_price = amount
        auction.total_bids += 1
        auction.save(update_fields=["current_price", "total_bids"])

        # Record in bid history
        BidHistory.objects.create(
            auction=auction,
            user=bidder,
            bid=bid,
            event="auto_bid_placed" if is_auto else "bid_placed",
            amount=amount,
            metadata={"bid_id": bid.id},
        )

        # Update bidder profile
        if hasattr(bidder, "bidder_profile"):
            bidder.bidder_profile.increment_bids()

        # Notify previous highest bidder they've been outbid
        BidService._notify_outbid(auction, bid)

        # Check if auction should be extended (anti-sniping)
        BidService._check_auction_extension(auction)

        # Trigger auto-bids from other users
        BidService._process_auto_bids(auction, bidder)

        return bid

    @staticmethod
    @transaction.atomic
    def _process_buy_now(auction, bidder, price):
        """Handle buy-now purchase."""
        bid = Bid.objects.create(
            auction=auction,
            bidder=bidder,
            amount=price,
            is_winning=True,
        )

        auction.current_price = price
        auction.total_bids += 1
        auction.status = AuctionStatus.SOLD
        auction.winner = bidder
        auction.winning_bid = price
        auction.end_time = timezone.now()
        auction.save()

        BidHistory.objects.create(
            auction=auction,
            user=bidder,
            bid=bid,
            event="bid_placed",
            amount=price,
            metadata={"buy_now": True},
        )

        # Deactivate all auto-bids for this auction
        AutoBid.objects.filter(auction=auction, is_active=True).update(
            is_active=False
        )

        return bid

    @staticmethod
    def _check_auction_extension(auction):
        """
        Extend auction if a bid is placed within the threshold
        (anti-sniping protection).
        """
        threshold = settings.AUCTION_EXTEND_THRESHOLD_SECONDS
        time_remaining = auction.time_remaining

        if 0 < time_remaining <= threshold:
            auction.extend_auction()
            BidHistory.objects.create(
                auction=auction,
                user=auction.seller,
                event="auction_extended",
                metadata={
                    "previous_end": auction.original_end_time.isoformat()
                    if auction.original_end_time
                    else None,
                    "new_end": auction.end_time.isoformat(),
                },
            )
            logger.info(
                f"Auction {auction.id} extended due to last-second bid"
            )

    @staticmethod
    def _notify_outbid(auction, new_bid):
        """Notify the previously winning bidder that they've been outbid."""
        from apps.notifications.services import NotificationService

        previous_winning_bid = (
            Bid.objects.filter(
                auction=auction, is_valid=True, is_winning=False
            )
            .exclude(bidder=new_bid.bidder)
            .order_by("-amount")
            .first()
        )

        if previous_winning_bid:
            NotificationService.create_notification(
                user=previous_winning_bid.bidder,
                notification_type="outbid",
                title=f"You've been outbid on {auction.title}",
                message=(
                    f"Someone placed a bid of ${new_bid.amount} on "
                    f'"{auction.title}". Your bid was ${previous_winning_bid.amount}.'
                ),
                auction=auction,
            )

    @staticmethod
    def _process_auto_bids(auction, current_bidder):
        """
        Process auto-bids from other users after a new bid is placed.
        Finds the highest auto-bid that can outbid the current price.
        """
        active_auto_bids = (
            AutoBid.objects.filter(
                auction=auction,
                is_active=True,
            )
            .exclude(bidder=current_bidder)
            .order_by("-max_amount")
        )

        for auto_bid in active_auto_bids:
            next_bid_amount = auction.current_price + auto_bid.increment

            if next_bid_amount <= auto_bid.max_amount:
                try:
                    bid = BidService.place_bid(
                        auction_id=auction.id,
                        bidder=auto_bid.bidder,
                        amount=next_bid_amount,
                        is_auto=True,
                    )

                    auto_bid.total_bids_placed += 1
                    auto_bid.last_bid_amount = next_bid_amount
                    auto_bid.save(
                        update_fields=["total_bids_placed", "last_bid_amount"]
                    )

                    # Broadcast auto-bid via task
                    from apps.auctions.tasks import broadcast_bid_update

                    broadcast_bid_update.delay(
                        auction.id,
                        {
                            "type": "new_bid",
                            "bid": {
                                "id": bid.id,
                                "bidder": bid.bidder.username,
                                "amount": str(bid.amount),
                                "timestamp": bid.created_at.isoformat(),
                                "is_auto_bid": True,
                            },
                            "auction": {
                                "current_price": str(auction.current_price),
                                "total_bids": auction.total_bids,
                                "minimum_bid": str(auction.minimum_bid),
                            },
                        },
                    )
                    break  # Only one auto-bid responds at a time

                except ValueError as e:
                    logger.info(
                        f"Auto-bid {auto_bid.id} could not place bid: {e}"
                    )
            else:
                # Auto-bid exhausted
                auto_bid.deactivate()
                BidHistory.objects.create(
                    auction=auction,
                    user=auto_bid.bidder,
                    event="auto_bid_exhausted",
                    amount=auto_bid.max_amount,
                    metadata={"auto_bid_id": auto_bid.id},
                )

                from apps.notifications.services import NotificationService

                NotificationService.create_notification(
                    user=auto_bid.bidder,
                    notification_type="auto_bid_exhausted",
                    title=f"Auto-bid exhausted on {auction.title}",
                    message=(
                        f"Your auto-bid on \"{auction.title}\" has reached its "
                        f"maximum of ${auto_bid.max_amount}. The current price "
                        f"is ${auction.current_price}."
                    ),
                    auction=auction,
                )

    @staticmethod
    def setup_auto_bid(auction_id, bidder, max_amount, increment):
        """
        Set up or update an auto-bid for a user on an auction.

        Returns:
            AutoBid instance
        """
        try:
            auction = Auction.objects.get(id=auction_id)
        except Auction.DoesNotExist:
            raise ValueError("Auction not found.")

        if not auction.is_active:
            raise ValueError("This auction is no longer active.")

        if auction.seller == bidder:
            raise ValueError("You cannot auto-bid on your own auction.")

        if max_amount <= auction.current_price:
            raise ValueError("Max amount must be greater than the current price.")

        if increment < auction.min_bid_increment:
            raise ValueError(
                f"Increment must be at least ${auction.min_bid_increment}."
            )

        auto_bid, created = AutoBid.objects.update_or_create(
            auction=auction,
            bidder=bidder,
            defaults={
                "max_amount": max_amount,
                "increment": increment,
                "is_active": True,
            },
        )

        event = "auto_bid_created" if created else "auto_bid_created"
        BidHistory.objects.create(
            auction=auction,
            user=bidder,
            event=event,
            amount=max_amount,
            metadata={
                "auto_bid_id": auto_bid.id,
                "increment": str(increment),
            },
        )

        # Place initial auto-bid if current price is below max
        if auction.current_price < max_amount:
            initial_amount = max(
                auction.minimum_bid,
                auction.current_price + increment,
            )
            if initial_amount <= max_amount:
                try:
                    BidService.place_bid(
                        auction_id=auction.id,
                        bidder=bidder,
                        amount=min(initial_amount, max_amount),
                        is_auto=True,
                    )
                    auto_bid.total_bids_placed += 1
                    auto_bid.last_bid_amount = initial_amount
                    auto_bid.save(
                        update_fields=["total_bids_placed", "last_bid_amount"]
                    )
                except ValueError:
                    pass  # Initial bid could fail if someone beat us to it

        return auto_bid
