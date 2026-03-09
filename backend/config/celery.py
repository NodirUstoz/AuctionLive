"""
Celery configuration for AuctionLive project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("auctionlive")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "check-ending-auctions": {
        "task": "apps.auctions.tasks.check_ending_auctions",
        "schedule": 10.0,  # Every 10 seconds
    },
    "process-ended-auctions": {
        "task": "apps.auctions.tasks.process_ended_auctions",
        "schedule": 30.0,  # Every 30 seconds
    },
    "send-ending-soon-notifications": {
        "task": "apps.notifications.tasks.send_ending_soon_notifications",
        "schedule": 60.0,  # Every minute
    },
    "cleanup-expired-escrows": {
        "task": "apps.payments.services.cleanup_expired_escrows",
        "schedule": crontab(hour="*/6"),  # Every 6 hours
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
