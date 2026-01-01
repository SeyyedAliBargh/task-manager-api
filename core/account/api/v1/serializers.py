from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from django.core import exceptions
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from ...models.users import User, EmailChangeRequestModel, PasswordResetRequest
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
        full_name = user.profile.get_full_name()
        if user.is_verified:
            raise serializers.ValidationError(
                {"detail": "user is Verified"}
            )

        # Attach user instance for use in the view
        attrs["user"] = user
        attrs["full_name"] = full_name
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


class ChangeEmailSerializer(serializers.Serializer):
    """
    Serializer for requesting an email change.

    Purpose:
        - Validates the old and new email addresses.
        - Ensures the old email matches the user's current email.
        - Ensures the new email is different from the old one.
        - Ensures the new email is unique (not already used by another user).
    """
    new_email = serializers.EmailField(required=True)
    old_email = serializers.EmailField(required=True)

    def validate(self, attrs):
        """
        Validate the provided old and new email addresses.
        """
        request = self.context.get("request")
        user = request.user

        # Normalize emails to lowercase for comparison
        old_email = attrs.get("old_email").lower()
        new_email = attrs.get("new_email").lower()

        # Check if old email matches the user's current email
        if user.email.lower() != old_email:
            raise serializers.ValidationError("The old email is invalid!")

        # Check if new email is different from the current email
        if user.email.lower() == new_email:
            raise serializers.ValidationError("New email cannot be the same as the current email!")

        # Check if new email is already in use by another user
        if User.objects.filter(email=new_email).exists():
            raise serializers.ValidationError("This email is already in use!")

        # Save normalized new email back into attrs
        attrs["new_email"] = new_email
        return attrs


class ConfirmEmailChangeSerializer(serializers.Serializer):
    """
    Serializer for confirming an email change request.

    Purpose:
        - Validates the verification code provided by the user.
        - Ensures the code exists, belongs to the user, and is not already verified.
        - Ensures the code has not expired (older than 1 day).
    """
    code = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate the provided verification code.
        """
        request = self.context.get("request")
        user = request.user
        code = attrs.get("code")

        try:
            # Find the latest unverified email change request for this user and code
            req = EmailChangeRequestModel.objects.filter(
                user=user, code=code, is_verified=False
            ).latest("created_at")
        except EmailChangeRequestModel.DoesNotExist:
            raise serializers.ValidationError("Invalid code!")

        # Check if the code has expired (older than 1 day)
        if timezone.now() - req.created_at > timedelta(days=1):
            raise serializers.ValidationError("This code has expired!")

        # Attach the request object to attrs for use in the view
        attrs["email_request"] = req
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating the user's profile.

    Purpose:
        - Provides access to profile fields such as first name, last name, image, and description.
        - Includes the user's email (read-only, sourced from the User model).
    """
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "email", "image", "description", "email")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get("email").lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email!")
        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user
        code = attrs.get("code")

        try:
            req = PasswordResetRequest.objects.filter(
                user=user, code=code, is_verified=False
            ).latest("created_at")
        except PasswordResetRequest.DoesNotExist:
            raise serializers.ValidationError("Invalid code!")

        # check expiration (1 day)
        if timezone.now() - req.created_at > timedelta(days=1):
            raise serializers.ValidationError("This code has expired!")

        attrs["reset_request"] = req
        return attrs


class PasswordResetCompleteSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        password = attrs.get("new_password")
        try:
            validate_password(password)
            return attrs
        except exceptions.ValidationError as e:
            # Normalize Django validation errors to DRF format
            raise serializers.ValidationError(
                {"password": list(e.messages)}
            )

