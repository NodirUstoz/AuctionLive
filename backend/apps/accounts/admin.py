"""Admin configuration for accounts app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import BidderProfile, SellerProfile, User


class SellerProfileInline(admin.StackedInline):
    model = SellerProfile
    can_delete = False
    verbose_name_plural = "Seller Profile"


class BidderProfileInline(admin.StackedInline):
    model = BidderProfile
    can_delete = False
    verbose_name_plural = "Bidder Profile"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_seller",
        "is_verified",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_seller", "is_verified", "is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-created_at",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": (
                    "phone_number",
                    "avatar",
                    "date_of_birth",
                    "is_seller",
                    "is_verified",
                )
            },
        ),
    )

    inlines = [SellerProfileInline, BidderProfileInline]


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "rating",
        "total_sales",
        "total_revenue",
        "is_approved",
    )
    list_filter = ("is_approved",)
    search_fields = ("user__email", "user__username", "business_name")


@admin.register(BidderProfile)
class BidderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_bids", "auctions_won", "total_spent")
    search_fields = ("user__email", "user__username")
