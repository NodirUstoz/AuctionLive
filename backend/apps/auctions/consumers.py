"""
WebSocket consumer for live auction bidding.
Handles real-time bid placement, auction updates, and countdown synchronization.
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebSocketConsumer
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class AuctionConsumer(AsyncJsonWebSocketConsumer):
    """
    WebSocket consumer for a single auction room.
    Clients join a group based on auction_id and receive real-time updates.
    """

    async def connect(self):
        self.auction_id = self.scope["url_route"]["kwargs"]["auction_id"]
        self.room_group_name = f"auction_{self.auction_id}"
        self.user = self.scope.get("user")

        # Join the auction room group
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        # Send initial auction state
        auction_data = await self.get_auction_state()
        if auction_data:
            await self.send_json({
                "type": "auction_state",
                "data": auction_data,
            })
        else:
            await self.send_json({
                "type": "error",
                "message": "Auction not found.",
            })
            await self.close()

    async def disconnect(self, close_code):
        # Leave the auction room group
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        message_type = content.get("type")

        if message_type == "place_bid":
            await self.handle_place_bid(content)
        elif message_type == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
            })

    async def handle_place_bid(self, content):
        """Process a bid placed via WebSocket."""
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.send_json({
                "type": "error",
                "message": "Authentication required to place a bid.",
            })
            return

        try:
            amount = Decimal(str(content.get("amount", "0")))
        except (InvalidOperation, TypeError, ValueError):
            await self.send_json({
                "type": "error",
                "message": "Invalid bid amount.",
            })
            return

        # Process the bid
        result = await self.process_bid(user, amount)

        if result["success"]:
            # Broadcast the new bid to all clients in the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "new_bid",
                    "data": result["data"],
                },
            )
        else:
            # Send error only to the bidder
            await self.send_json({
                "type": "bid_error",
                "message": result["message"],
            })

    @database_sync_to_async
    def process_bid(self, user, amount):
        """Process a bid within the database transaction."""
        from apps.bids.services import BidService

        try:
            bid = BidService.place_bid(
                auction_id=self.auction_id,
                bidder=user,
                amount=amount,
            )
            return {
                "success": True,
                "data": {
                    "type": "new_bid",
                    "bid": {
                        "id": bid.id,
                        "bidder": bid.bidder.username,
                        "amount": str(bid.amount),
                        "timestamp": bid.created_at.isoformat(),
                    },
                    "auction": {
                        "current_price": str(bid.auction.current_price),
                        "total_bids": bid.auction.total_bids,
                        "minimum_bid": str(bid.auction.minimum_bid),
                        "time_remaining": bid.auction.time_remaining,
                    },
                },
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            logger.error(f"Error processing bid: {e}")
            return {"success": False, "message": "An error occurred processing your bid."}

    @database_sync_to_async
    def get_auction_state(self):
        """Get current auction state for initial connection."""
        from .models import Auction
        from apps.bids.models import Bid

        try:
            auction = Auction.objects.select_related("seller", "category").get(
                id=self.auction_id
            )
        except Auction.DoesNotExist:
            return None

        # Get recent bids
        recent_bids = (
            Bid.objects.filter(auction=auction, is_valid=True)
            .select_related("bidder")
            .order_by("-created_at")[:20]
        )

        bids_data = [
            {
                "id": bid.id,
                "bidder": bid.bidder.username,
                "amount": str(bid.amount),
                "timestamp": bid.created_at.isoformat(),
            }
            for bid in recent_bids
        ]

        return {
            "auction": {
                "id": auction.id,
                "title": auction.title,
                "status": auction.status,
                "current_price": str(auction.current_price),
                "starting_price": str(auction.starting_price),
                "minimum_bid": str(auction.minimum_bid),
                "total_bids": auction.total_bids,
                "time_remaining": auction.time_remaining,
                "end_time": auction.end_time.isoformat(),
                "is_active": auction.is_active,
                "seller": auction.seller.username,
            },
            "recent_bids": bids_data,
        }

    # Group message handlers

    async def new_bid(self, event):
        """Handle new_bid group message - send to WebSocket client."""
        await self.send_json(event["data"])

    async def auction_update(self, event):
        """Handle auction_update group message - send to WebSocket client."""
        await self.send_json(event["data"])

    async def bid_retracted(self, event):
        """Handle bid_retracted group message."""
        await self.send_json(event["data"])
