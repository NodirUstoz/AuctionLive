"""Admin configuration for auctions app."""

from django.contrib import admin

from .models import Auction, AuctionCategory, AuctionImage


class AuctionImageInline(admin.TabularInline):
    model = AuctionImage
    extra = 1


@admin.register(AuctionCategory)
class AuctionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "seller",
        "category",
        "status",
        "current_price",
        "total_bids",
        "start_time",
        "end_time",
        "featured",
    )
    list_filter = ("status", "category", "condition", "featured")
    search_fields = ("title", "description", "seller__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "current_price",
        "total_bids",
        "view_count",
        "watchers_count",
        "winner",
        "winning_bid",
    )
    inlines = [AuctionImageInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "seller",
                    "category",
                    "title",
                    "slug",
                    "description",
                    "condition",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "starting_price",
                    "reserve_price",
                    "current_price",
                    "buy_now_price",
                    "min_bid_increment",
                )
            },
        ),
        (
            "Timing",
            {"fields": ("start_time", "end_time", "original_end_time")},
        ),
        (
            "Status & Results",
            {
                "fields": (
                    "status",
                    "winner",
                    "winning_bid",
                    "featured",
                )
            },
        ),
        (
            "Stats",
            {
                "fields": ("total_bids", "view_count", "watchers_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Shipping",
            {
                "fields": ("shipping_cost", "shipping_details"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(AuctionImage)
class AuctionImageAdmin(admin.ModelAdmin):
    list_display = ("auction", "is_primary", "order", "created_at")
    list_filter = ("is_primary",)
