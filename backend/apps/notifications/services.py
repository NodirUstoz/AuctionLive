"""
Notification service: create and send notifications.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for creating and managing notifications."""

    @staticmethod
    def create_notification(
        user,
        notification_type,
        title,
        message,
        auction=None,
        send_email=True,
        metadata=None,
    ):
        """
        Create a notification for a user and optionally send an email.

        Args:
            user: Target user
            notification_type: Type of notification
            title: Notification title
            message: Notification message body
            auction: Related auction (optional)
            send_email: Whether to send email notification
            metadata: Additional JSON metadata

        Returns:
            Notification instance
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            auction=auction,
            metadata=metadata or {},
        )

        # Send email notification in background
        if send_email and user.email:
            from apps.notifications.tasks import send_email_notification

            send_email_notification.delay(notification.id)

        logger.info(
            f"Notification created: {notification_type} for user {user.username}"
        )

        return notification

    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications for a user."""
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_all_read(user):
        """Mark all notifications as read for a user."""
        from django.utils import timezone

        Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

    @staticmethod
    def send_email_for_notification(notification):
        """Send an email for a notification."""
        try:
            subject = notification.title
            text_message = notification.message

            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #1a1a2e; padding: 20px; text-align: center;">
                    <h1 style="color: #e94560; margin: 0;">AuctionLive</h1>
                </div>
                <div style="padding: 20px; background-color: #f5f5f5;">
                    <h2 style="color: #333;">{notification.title}</h2>
                    <p style="color: #555; line-height: 1.6;">{notification.message}</p>
                    {"<p><a href='http://localhost/auction/" +
                     str(notification.auction.slug) +
                     "' style='background-color: #e94560; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;'>View Auction</a></p>"
                     if notification.auction else ""}
                </div>
                <div style="padding: 10px; text-align: center; color: #999; font-size: 12px;">
                    <p>You received this email from AuctionLive.</p>
                </div>
            </body>
            </html>
            """

            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.user.email],
                html_message=html_message,
                fail_silently=True,
            )

            notification.email_sent = True
            notification.save(update_fields=["email_sent"])

        except Exception as e:
            logger.error(
                f"Failed to send email notification {notification.id}: {e}"
            )
