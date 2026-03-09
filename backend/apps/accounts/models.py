"""
Account models: Custom User, SellerProfile, BidderProfile.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role support."""

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_seller = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class SellerProfile(models.Model):
    """Profile for users who sell items through auctions."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="seller_profile"
    )
    business_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_sales = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seller Profile"
        verbose_name_plural = "Seller Profiles"

    def __str__(self):
        return f"Seller: {self.user.username}"

    def update_stats(self, sale_amount):
        """Update seller stats after a completed sale."""
        self.total_sales += 1
        self.total_revenue += sale_amount
        self.save(update_fields=["total_sales", "total_revenue"])


class BidderProfile(models.Model):
    """Profile for users who bid on auctions."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="bidder_profile"
    )
    total_bids = models.PositiveIntegerField(default=0)
    auctions_won = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bidder Profile"
        verbose_name_plural = "Bidder Profiles"

    def __str__(self):
        return f"Bidder: {self.user.username}"

    def record_win(self, amount):
        """Record an auction win."""
        self.auctions_won += 1
        self.total_spent += amount
        self.save(update_fields=["auctions_won", "total_spent"])

    def increment_bids(self):
        """Increment total bids count."""
        self.total_bids += 1
        self.save(update_fields=["total_bids"])
