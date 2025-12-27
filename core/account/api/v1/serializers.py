from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.core import exceptions
from ...models.users import User
from ...models.profiles import Profile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    This serializer handles the creation of both the User and the associated Profile.
    It ensures that first and last names are stored in the Profile, while the User
    model stores email and password. It also validates password confirmation.

    Attributes
    ----------
    password2 : CharField
        Write-only field for password confirmation.
    first_name : CharField
        Write-only field for the Profile's first name.
    last_name : CharField
        Write-only field for the Profile's last name.

    Methods
    -------
    validate(attrs):
        Ensures that password and password2 match and validates password strength.
    create(validated_data):
        Creates a new User and updates the associated Profile with first and last name.
    """
    # Additional fields for registration (not stored directly on User model)
    password2 = serializers.CharField(write_only=True)  # For password confirmation
    first_name = serializers.CharField(write_only=True)  # Profile's first name
    last_name = serializers.CharField(write_only=True)  # Profile's last name

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password", "password2")
        extra_kwargs = {
            "password": {
                "write_only": True
            }  # Ensure password is never returned in API responses
        }

    def validate(self, attrs):
        """
        Validate registration data.

        Ensures that the provided password and password2 match.
        Also validates password strength using Django's built-in validators.

        Parameters
        ----------
        attrs : dict
            The input data containing email, password, password2, first_name, last_name.

        Returns
        -------
        dict
            The validated data if successful.

        Raises
        ------
        serializers.ValidationError
            If passwords do not match or fail validation rules.
        """
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"detail": "passwords doesn't match"})

        try:
            validate_password(attrs.get("password"))
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return super().validate(attrs)

    def create(self, validated_data):
        """
        Create a new User instance and update the associated Profile.

        Steps:
        1. Pop first_name, last_name, and password2 from validated_data
           (password2 is only for validation, not stored).
        2. Create the User with create_user().
        3. Retrieve the automatically created Profile (via post_save signal).
        4. Update Profile's first_name and last_name and save.
        5. Return the created User instance.

        Parameters
        ----------
        validated_data : dict
            The validated data containing user and profile information.

        Returns
        -------
        User
            The created User instance.
        """
        # Extract profile fields and remove password2
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        validated_data.pop("password2")

        # Create the User instance using custom manager
        user = User.objects.create_user(**validated_data)

        # Retrieve the auto-created Profile and update with names
        profile = user.profile  # Profile is guaranteed by post_save signal
        profile.first_name = first_name
        profile.last_name = last_name
        profile.save()

        return user


class ActivationResendSerializer(serializers.Serializer):
    """
    Serializer for resending activation emails.

    This serializer validates the provided email, ensures the user exists,
    and checks that the user is not already verified. If valid, it attaches
    the user object to the validated data for further processing.

    Attributes
    ----------
    email : CharField
        Required field for the user's email.

    Methods
    -------
    validate(attrs):
        Validates that the user exists and is not already verified.
    """
    email = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate the provided email.

        Ensures that the user exists and is not already verified.

        Parameters
        ----------
        attrs : dict
            The input data containing the email.

        Returns
        -------
        dict
            The validated data with the user object attached.

        Raises
        ------
        serializers.ValidationError
            If the user does not exist or is already verified.
        """
        email = attrs.get("email")
        try:
            user = get_object_or_404(User, email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "user doesn't exist"})

        if user.is_verified:
            raise serializers.ValidationError({"detail": "user is Verified"})
        attrs["user"] = user
        return super().validate(attrs)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for obtaining JWT token pairs.

    Extends the default TokenObtainPairSerializer to include additional
    user information (email and ID) in the response payload.

    Methods
    -------
    validate(attrs):
        Validates credentials and adds user_email and user_id to the response.
    """

    def validate(self, attrs):
        """
        Validate user credentials and extend token response.

        Parameters
        ----------
        attrs : dict
            The input data containing user credentials.

        Returns
        -------
        dict
            The validated data including JWT tokens and user info.
        """
        validated_data = super().validate(attrs)
        validated_data["user_email"] = self.user.email
        validated_data["user_id"] = self.user.id
        return validated_data