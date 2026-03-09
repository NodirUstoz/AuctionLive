"""
Custom exception handler and exception classes for the API.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    Extends DRF's default handler with additional error types.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            "error": True,
            "status_code": response.status_code,
        }

        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_response["message"] = str(response.data["detail"])
                custom_response["errors"] = {}
            else:
                custom_response["message"] = "Validation error."
                custom_response["errors"] = response.data
        elif isinstance(response.data, list):
            custom_response["message"] = " ".join(str(e) for e in response.data)
            custom_response["errors"] = {}
        else:
            custom_response["message"] = str(response.data)
            custom_response["errors"] = {}

        response.data = custom_response
        return response

    # Handle Django's ValidationError
    if isinstance(exc, DjangoValidationError):
        data = {
            "error": True,
            "status_code": 400,
            "message": "Validation error.",
            "errors": exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages},
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    # Log unhandled exceptions
    if exc:
        logger.error(
            f"Unhandled exception in {context.get('view', 'unknown')}: {exc}",
            exc_info=True,
        )

    return response


class AuctionNotActiveError(APIException):
    """Raised when trying to interact with an inactive auction."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This auction is not currently active."
    default_code = "auction_not_active"


class InsufficientBidError(APIException):
    """Raised when a bid amount is too low."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Your bid does not meet the minimum requirement."
    default_code = "insufficient_bid"


class SelfBidError(APIException):
    """Raised when a seller tries to bid on their own auction."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "You cannot bid on your own auction."
    default_code = "self_bid"


class PaymentError(APIException):
    """Raised for payment processing errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Payment processing failed."
    default_code = "payment_error"
