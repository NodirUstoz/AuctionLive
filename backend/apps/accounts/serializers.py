"""
Account serializers for registration, login, and profile management.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import BidderProfile, SellerProfile

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    is_seller = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
            "is_seller",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        is_seller = validated_data.pop("is_seller", False)
        user = User.objects.create_user(**validated_data, is_seller=is_seller)

        # Create profiles
        BidderProfile.objects.create(user=user)
        if is_seller:
            SellerProfile.objects.create(user=user)

        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "avatar",
            "date_of_birth",
            "is_seller",
            "is_verified",
            "created_at",
        )
        read_only_fields = ("id", "email", "is_verified", "created_at")


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "date_of_birth",
        )


class SellerProfileSerializer(serializers.ModelSerializer):
    """Serializer for seller profile."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SellerProfile
        fields = (
            "id",
            "username",
            "email",
            "business_name",
            "description",
            "website",
            "address",
            "rating",
            "total_sales",
            "total_revenue",
            "is_approved",
            "created_at",
        )
        read_only_fields = (
            "id",
            "rating",
            "total_sales",
            "total_revenue",
            "is_approved",
            "created_at",
        )


class BidderProfileSerializer(serializers.ModelSerializer):
    """Serializer for bidder profile."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = BidderProfile
        fields = (
            "id",
            "username",
            "total_bids",
            "auctions_won",
            "total_spent",
            "shipping_address",
            "created_at",
        )
        read_only_fields = (
            "id",
            "total_bids",
            "auctions_won",
            "total_spent",
            "created_at",
        )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
