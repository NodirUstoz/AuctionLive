"""
Bid views for placing bids, managing auto-bids, and viewing bid history.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AutoBid, Bid, BidHistory
from .serializers import (
    AutoBidSerializer,
    BidHistorySerializer,
    BidSerializer,
    CreateAutoBidSerializer,
    PlaceBidSerializer,
)
from .services import BidService


class PlaceBidView(APIView):
    """Place a bid on an auction."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = PlaceBidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            bid = BidService.place_bid(
                auction_id=serializer.validated_data["auction_id"],
                bidder=request.user,
                amount=serializer.validated_data["amount"],
            )
            return Response(
                BidSerializer(bid).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AuctionBidsView(generics.ListAPIView):
    """List all bids for a specific auction."""

    serializer_class = BidSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        auction_id = self.kwargs["auction_id"]
        return (
            Bid.objects.filter(auction_id=auction_id, is_valid=True)
            .select_related("bidder", "auction")
            .order_by("-created_at")
        )


class UserBidsView(generics.ListAPIView):
    """List all bids by the authenticated user."""

    serializer_class = BidSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            Bid.objects.filter(bidder=self.request.user, is_valid=True)
            .select_related("bidder", "auction")
            .order_by("-created_at")
        )


class AutoBidCreateView(APIView):
    """Create or update an auto-bid."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = CreateAutoBidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            auto_bid = BidService.setup_auto_bid(
                auction_id=serializer.validated_data["auction_id"],
                bidder=request.user,
                max_amount=serializer.validated_data["max_amount"],
                increment=serializer.validated_data["increment"],
            )
            return Response(
                AutoBidSerializer(auto_bid).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AutoBidListView(generics.ListAPIView):
    """List auto-bids for the authenticated user."""

    serializer_class = AutoBidSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            AutoBid.objects.filter(bidder=self.request.user)
            .select_related("bidder", "auction")
            .order_by("-created_at")
        )


class AutoBidDeactivateView(APIView):
    """Deactivate an auto-bid."""

    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, pk):
        try:
            auto_bid = AutoBid.objects.get(pk=pk, bidder=request.user)
            auto_bid.deactivate()

            BidHistory.objects.create(
                auction=auto_bid.auction,
                user=request.user,
                event="auto_bid_deactivated",
                amount=auto_bid.max_amount,
                metadata={"auto_bid_id": auto_bid.id},
            )

            return Response(
                {"detail": "Auto-bid deactivated."},
                status=status.HTTP_200_OK,
            )
        except AutoBid.DoesNotExist:
            return Response(
                {"detail": "Auto-bid not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class BidHistoryView(generics.ListAPIView):
    """View bid history for an auction."""

    serializer_class = BidHistorySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        auction_id = self.kwargs["auction_id"]
        return (
            BidHistory.objects.filter(auction_id=auction_id)
            .select_related("user", "auction")
            .order_by("-created_at")
        )
