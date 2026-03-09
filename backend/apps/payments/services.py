"""
Payment services: Stripe integration, escrow management, fee calculations.
"""

import logging
import uuid
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Escrow, EscrowStatus, Payment, PaymentStatus

logger = logging.getLogger(__name__)

PLATFORM_FEE_PERCENT = Decimal("5.00")  # 5% platform fee


class PaymentService:
    """Service class for payment operations."""

    @staticmethod
    @transaction.atomic
    def create_payment(auction, payer, payment_method="stripe"):
        """
        Create a payment for a won auction.

        Args:
            auction: The won auction
            payer: The buyer (winner)
            payment_method: Payment method string

        Returns:
            Payment instance
        """
        from apps.auctions.models import AuctionStatus

        if auction.status != AuctionStatus.SOLD:
            raise ValueError("Payment can only be created for sold auctions.")

        if auction.winner != payer:
            raise ValueError("Only the auction winner can make the payment.")

        # Check for existing payment
        existing = Payment.objects.filter(
            auction=auction,
            payer=payer,
            status__in=[PaymentStatus.PENDING, PaymentStatus.PROCESSING],
        ).first()

        if existing:
            return existing

        amount = auction.winning_bid
        shipping = auction.shipping_cost
        platform_fee = (amount * PLATFORM_FEE_PERCENT / Decimal("100")).quantize(
            Decimal("0.01")
        )
        total = amount + shipping

        payment = Payment.objects.create(
            auction=auction,
            payer=payer,
            payee=auction.seller,
            amount=amount,
            shipping_cost=shipping,
            total_amount=total,
            platform_fee=platform_fee,
            payment_method=payment_method,
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
        )

        # Create or update Stripe PaymentIntent if using Stripe
        if payment_method == "stripe" and settings.STRIPE_SECRET_KEY:
            try:
                import stripe

                stripe.api_key = settings.STRIPE_SECRET_KEY

                intent = stripe.PaymentIntent.create(
                    amount=int(total * 100),  # Stripe uses cents
                    currency="usd",
                    metadata={
                        "auction_id": auction.id,
                        "payment_id": payment.id,
                    },
                )
                payment.stripe_payment_intent_id = intent.id
                payment.save(update_fields=["stripe_payment_intent_id"])
            except Exception as e:
                logger.error(f"Stripe PaymentIntent creation failed: {e}")
                # Payment still created, can retry later

        return payment

    @staticmethod
    @transaction.atomic
    def confirm_payment(payment_id, user):
        """
        Confirm a payment has been received.

        Args:
            payment_id: Payment ID
            user: The payer confirming

        Returns:
            Payment instance
        """
        from apps.notifications.services import NotificationService

        try:
            payment = Payment.objects.select_for_update().get(
                id=payment_id, payer=user
            )
        except Payment.DoesNotExist:
            raise ValueError("Payment not found.")

        if payment.status != PaymentStatus.PENDING:
            raise ValueError(
                f"Payment cannot be confirmed. Current status: {payment.get_status_display()}"
            )

        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at"])

        # Update escrow if exists
        try:
            escrow = payment.auction.escrow
            escrow.status = EscrowStatus.FUNDED
            escrow.funded_at = timezone.now()
            escrow.save(update_fields=["status", "funded_at"])
        except Escrow.DoesNotExist:
            pass

        # Notify seller
        NotificationService.create_notification(
            user=payment.payee,
            notification_type="payment_received",
            title=f"Payment received for {payment.auction.title}",
            message=(
                f"Payment of ${payment.total_amount} has been received for "
                f'"{payment.auction.title}".'
            ),
            auction=payment.auction,
        )

        return payment

    @staticmethod
    @transaction.atomic
    def release_escrow(escrow_id):
        """Release escrow funds to the seller."""
        from apps.notifications.services import NotificationService

        try:
            escrow = Escrow.objects.select_for_update().get(id=escrow_id)
        except Escrow.DoesNotExist:
            raise ValueError("Escrow not found.")

        if escrow.status != EscrowStatus.FUNDED:
            raise ValueError(
                f"Escrow cannot be released. Current status: {escrow.get_status_display()}"
            )

        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = timezone.now()
        escrow.save(update_fields=["status", "released_at"])

        # Update seller revenue
        if hasattr(escrow.seller, "seller_profile"):
            net_amount = escrow.amount - escrow.platform_fee
            escrow.seller.seller_profile.update_stats(net_amount)

        # Notify both parties
        NotificationService.create_notification(
            user=escrow.seller,
            notification_type="escrow_released",
            title=f"Funds released for {escrow.auction.title}",
            message=(
                f"Escrow funds of ${escrow.amount} for "
                f'"{escrow.auction.title}" have been released to your account.'
            ),
            auction=escrow.auction,
        )

        NotificationService.create_notification(
            user=escrow.buyer,
            notification_type="escrow_released",
            title=f"Payment completed for {escrow.auction.title}",
            message=(
                f"Your payment for \"{escrow.auction.title}\" has been "
                f"finalized and released to the seller."
            ),
            auction=escrow.auction,
        )

        return escrow


@shared_task
def cleanup_expired_escrows():
    """Mark unfunded escrows as expired if past their deadline."""
    expired = Escrow.objects.filter(
        status=EscrowStatus.PENDING,
        expires_at__lt=timezone.now(),
    )

    count = 0
    for escrow in expired:
        escrow.status = EscrowStatus.EXPIRED
        escrow.save(update_fields=["status"])
        count += 1

        from apps.notifications.services import NotificationService

        NotificationService.create_notification(
            user=escrow.buyer,
            notification_type="escrow_expired",
            title=f"Payment deadline expired: {escrow.auction.title}",
            message=(
                f"The payment deadline for \"{escrow.auction.title}\" "
                f"has expired. Please contact support."
            ),
            auction=escrow.auction,
        )

    logger.info(f"Cleaned up {count} expired escrows")
    return f"Cleaned up {count} expired escrows"
