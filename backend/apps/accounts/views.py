"""
Account views for authentication, registration, and profile management.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import BidderProfile, SellerProfile
from .serializers import (
    BidderProfileSerializer,
    ChangePasswordSerializer,
    SellerProfileSerializer,
    UserProfileUpdateSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """JWT token login. Returns access and refresh tokens."""

    permission_classes = (permissions.AllowAny,)


class TokenRefreshAPIView(TokenRefreshView):
    """Refresh JWT access token."""

    permission_classes = (permissions.AllowAny,)


class LogoutView(APIView):
    """Blacklist the refresh token to log out."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get and update the authenticated user's profile."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        data = UserSerializer(user).data

        # Include bidder profile
        try:
            bidder_profile = user.bidder_profile
            data["bidder_profile"] = BidderProfileSerializer(bidder_profile).data
        except BidderProfile.DoesNotExist:
            data["bidder_profile"] = None

        # Include seller profile if applicable
        if user.is_seller:
            try:
                seller_profile = user.seller_profile
                data["seller_profile"] = SellerProfileSerializer(seller_profile).data
            except SellerProfile.DoesNotExist:
                data["seller_profile"] = None

        return Response(data)


class SellerProfileView(generics.RetrieveUpdateAPIView):
    """Get and update seller profile."""

    serializer_class = SellerProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        profile, _ = SellerProfile.objects.get_or_create(user=self.request.user)
        if not self.request.user.is_seller:
            self.request.user.is_seller = True
            self.request.user.save(update_fields=["is_seller"])
        return profile


class BidderProfileView(generics.RetrieveUpdateAPIView):
    """Get and update bidder profile."""

    serializer_class = BidderProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        profile, _ = BidderProfile.objects.get_or_create(user=self.request.user)
        return profile


class ChangePasswordView(generics.UpdateAPIView):
    """Change user password."""

    serializer_class = ChangePasswordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )
