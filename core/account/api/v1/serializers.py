from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from django.core import exceptions
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from ...models.users import User
from ...models.profiles import Profile


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Handles user registration logic.

    Responsibilities:
    - Validate password confirmation and password strength
    - Create a User instance
    - Populate the related Profile with first_name and last_name
    """

    # Password confirmation field (used only for validation)
    password2 = serializers.CharField(write_only=True)

    # These fields belong to Profile, not User
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'password',
            'password2',
        )
        extra_kwargs = {
            # Prevent password from ever being exposed in responses
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        """
        Cross-field validation.

        - Ensures password and password2 match
        - Runs Django's password validators (length, complexity, etc.)
        """
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(
                {"detail": "passwords doesn't match"}
            )

        try:
            validate_password(attrs.get("password"))
        except exceptions.ValidationError as e:
            # Normalize Django validation errors to DRF format
            raise serializers.ValidationError(
                {"password": list(e.messages)}
            )

        return super().validate(attrs)

    def create(self, validated_data):
        """
        Creates User and updates the related Profile.

        Workflow:
        1. Extract profile-related fields
        2. Remove password confirmation field
        3. Create user via custom manager (handles hashing)
        4. Update auto-created Profile instance
        """

        # Extract Profile-related fields
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')

        # password2 is not stored anywhere
        validated_data.pop('password2')

        # Create User using custom manager
        user = User.objects.create_user(**validated_data)

        # Profile is assumed to be created via post_save signal
        profile = user.profile
        profile.first_name = first_name
        profile.last_name = last_name
        profile.save()

        return user


class ActivationResendSerializer(serializers.Serializer):
    """
    Handles resending account activation for unverified users.
    """

    email = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        - Ensures user exists
        - Prevents resending activation for already verified users
        """
        email = attrs.get("email")

        # Fetch user or fail with 404-style error
        user = get_object_or_404(User, email=email)

        if user.is_verified:
            raise serializers.ValidationError(
                {"detail": "user is Verified"}
            )

        # Attach user instance for use in the view
        attrs["user"] = user
        return super().validate(attrs)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends JWT token response with basic user identifiers.
    """

    def validate(self, attrs):
        """
        Adds user_id and user_email to JWT response payload.
        """
        validated_data = super().validate(attrs)
        validated_data['user_email'] = self.user.email
        validated_data['user_id'] = self.user.id
        return validated_data


class ChangePasswordSerializer(serializers.Serializer):
    """
    Handles password change for authenticated users.
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        - Ensures new passwords match
        - Enforces Django password validation rules
        """
        if attrs.get("new_password") != attrs.get("new_password1"):
            raise serializers.ValidationError(
                {"detail": "passwords doesn't match"}
            )

        try:
            validate_password(attrs.get("new_password"))
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(
                {"new_password": list(e.messages)}
            )

        return super().validate(attrs)


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "email", "image", "description", "email")
