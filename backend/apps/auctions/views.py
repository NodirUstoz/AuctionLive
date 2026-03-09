"""
Auction views for listing, detail, creation, and seller dashboard.
"""

from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import Payment

from .models import Auction, AuctionCategory, AuctionStatus
from .serializers import (
    AuctionCategorySerializer,
    AuctionCreateSerializer,
    AuctionDetailSerializer,
    AuctionListSerializer,
    SellerDashboardSerializer,
)


class IsSellerOrReadOnly(permissions.BasePermission):
    """Allow sellers to create/edit, others can only read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_seller

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.seller == request.user


class AuctionListView(generics.ListAPIView):
    """List active auctions with filtering, search, and ordering."""

    serializer_class = AuctionListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "status", "condition", "featured"]
    search_fields = ["title", "description"]
    ordering_fields = ["current_price", "end_time", "created_at", "total_bids"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Auction.objects.select_related("seller", "category").prefetch_related(
            "images"
        )

        # Default to showing active auctions
        status_filter = self.request.query_params.get("status")
        if not status_filter:
            queryset = queryset.filter(
                status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
            )

        # Price range filter
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        if min_price:
            queryset = queryset.filter(current_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(current_price__lte=max_price)

        return queryset


class AuctionCreateView(generics.CreateAPIView):
    """Create a new auction (sellers only)."""

    serializer_class = AuctionCreateSerializer
    permission_classes = (permissions.IsAuthenticated, IsSellerOrReadOnly)

    def perform_create(self, serializer):
        serializer.save()


class AuctionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an auction."""

    permission_classes = (IsSellerOrReadOnly,)
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AuctionCreateSerializer
        return AuctionDetailSerializer

    def get_queryset(self):
        return Auction.objects.select_related(
            "seller", "category", "winner"
        ).prefetch_related("images")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        if instance.status in (AuctionStatus.ACTIVE, AuctionStatus.EXTENDED):
            instance.status = AuctionStatus.CANCELLED
            instance.save(update_fields=["status"])
        else:
            instance.delete()


class AuctionByIdView(generics.RetrieveAPIView):
    """Retrieve auction by ID (used internally for WebSocket lookups)."""

    serializer_class = AuctionDetailSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Auction.objects.select_related(
        "seller", "category", "winner"
    ).prefetch_related("images")


class CategoryListView(generics.ListAPIView):
    """List all active auction categories."""

    serializer_class = AuctionCategorySerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        return AuctionCategory.objects.filter(is_active=True, parent__isnull=True)


class CategoryDetailView(generics.RetrieveAPIView):
    """Get category details and its auctions."""

    serializer_class = AuctionCategorySerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    queryset = AuctionCategory.objects.filter(is_active=True)


class CategoryAuctionsView(generics.ListAPIView):
    """List auctions in a specific category."""

    serializer_class = AuctionListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return (
            Auction.objects.filter(
                Q(category__slug=slug) | Q(category__parent__slug=slug),
                status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED],
            )
            .select_related("seller", "category")
            .prefetch_related("images")
        )


class FeaturedAuctionsView(generics.ListAPIView):
    """List featured auctions."""

    serializer_class = AuctionListSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        return (
            Auction.objects.filter(
                featured=True,
                status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED],
            )
            .select_related("seller", "category")
            .prefetch_related("images")[:12]
        )


class SellerDashboardView(APIView):
    """Dashboard analytics for sellers."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if not user.is_seller:
            return Response(
                {"detail": "You must be a seller to access the dashboard."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_auctions = Auction.objects.filter(seller=user)
        active_auctions = user_auctions.filter(
            status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
        )
        sold_auctions = user_auctions.filter(status=AuctionStatus.SOLD)

        total_revenue = (
            sold_auctions.aggregate(total=Sum("winning_bid"))["total"] or 0
        )
        total_bids_received = sum(a.total_bids for a in user_auctions)

        pending_payments = Payment.objects.filter(
            auction__seller=user, status="pending"
        ).count()

        data = {
            "active_auctions": active_auctions.count(),
            "total_auctions": user_auctions.count(),
            "total_revenue": total_revenue,
            "total_bids_received": total_bids_received,
            "active_listings": AuctionListSerializer(
                active_auctions[:10], many=True, context={"request": request}
            ).data,
            "recent_sales": AuctionListSerializer(
                sold_auctions.order_by("-updated_at")[:10],
                many=True,
                context={"request": request},
            ).data,
            "pending_payments": pending_payments,
        }

        serializer = SellerDashboardSerializer(data)
        return Response(serializer.data)


class MyAuctionsView(generics.ListAPIView):
    """List auctions created by the authenticated seller."""

    serializer_class = AuctionListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            Auction.objects.filter(seller=self.request.user)
            .select_related("seller", "category")
            .prefetch_related("images")
        )
