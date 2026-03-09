"""
Watchlist views for managing watched auctions.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.models import Auction

from .models import WatchlistItem
from .serializers import WatchlistItemSerializer, WatchlistToggleSerializer


class WatchlistListView(generics.ListAPIView):
    """List all watchlist items for the authenticated user."""

    serializer_class = WatchlistItemSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            WatchlistItem.objects.filter(user=self.request.user)
            .select_related("auction__seller", "auction__category")
            .prefetch_related("auction__images")
        )


class WatchlistAddView(generics.CreateAPIView):
    """Add an auction to the user's watchlist."""

    serializer_class = WatchlistItemSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistRemoveView(generics.DestroyAPIView):
    """Remove an auction from the user's watchlist."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user)


class WatchlistToggleView(APIView):
    """Toggle an auction in/out of the user's watchlist."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = WatchlistToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auction_id = serializer.validated_data["auction_id"]

        try:
            auction = Auction.objects.get(id=auction_id)
        except Auction.DoesNotExist:
            return Response(
                {"detail": "Auction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item, created = WatchlistItem.objects.get_or_create(
            user=request.user,
            auction=auction,
        )

        if not created:
            item.delete()
            return Response(
                {"detail": "Removed from watchlist.", "is_watched": False},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Added to watchlist.", "is_watched": True},
            status=status.HTTP_201_CREATED,
        )
