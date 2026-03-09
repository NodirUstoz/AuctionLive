"""
Payment models: Payment processing and Escrow management.
"""

from django.conf import settings
from django.db import models


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    STRIPE = "stripe", "Stripe"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    ESCROW = "escrow", "Escrow"


class Payment(models.Model):
    """Payment record for an auction transaction."""

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments_made",
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments_received",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Platform commission fee.",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.STRIPE,
    )
    stripe_payment_intent_id = models.CharField(
        max_length=200, blank=True, null=True
    )
    stripe_charge_id = models.CharField(max_length=200, blank=True, null=True)
    transaction_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True
    )
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["payer", "status"]),
        ]

    def __str__(self):
        return f"Payment ${self.total_amount} for {self.auction.title}"

    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.amount + self.shipping_cost
        super().save(*args, **kwargs)


class EscrowStatus(models.TextChoices):
    PENDING = "pending", "Pending Payment"
    FUNDED = "funded", "Funded"
    RELEASED = "released", "Released to Seller"
    DISPUTED = "disputed", "Disputed"
    REFUNDED = "refunded", "Refunded to Buyer"
    EXPIRED = "expired", "Expired"


class Escrow(models.Model):
    """Escrow account for holding funds between buyer and seller."""

    auction = models.OneToOneField(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="escrow",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="escrow_as_buyer",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="escrow_as_seller",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20,
        choices=EscrowStatus.choices,
        default=EscrowStatus.PENDING,
    )
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for the buyer to fund the escrow.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Escrows"

    def __str__(self):
        return f"Escrow ${self.amount} for {self.auction.title}"
