"""
WebSocket URL routing for AuctionLive.
"""

from django.urls import re_path

from apps.auctions.consumers import AuctionConsumer

websocket_urlpatterns = [
    re_path(r"ws/auction/(?P<auction_id>\d+)/$", AuctionConsumer.as_asgi()),
]
