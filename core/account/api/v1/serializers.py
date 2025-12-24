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
    Handles creation of both User and associated Profile with first and last name.
    """

    # Additional fields for registration (not stored directly on User model)
    password2 = serializers.CharField(write_only=True)  # For password confirmation
    first_name = serializers.CharField(write_only=True)  # Profile's first name
    last_name = serializers.CharField(write_only=True)  # Profile's last name

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}  # Ensure password is never returned in API responses
        }

    def validate(self, attrs):
        """
        Ensure that password and password2 match.
        Raise a validation error if they do not.
        """
        if attrs.get("password") != attrs.get("password1"):
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
           (password2 is only for validation, not stored)
        2. Create the User with create_user()
        3. Retrieve the automatically created Profile (via post_save signal)
        4. Update Profile's first_name and last_name and save
        5. Return the created User instance
        """
        # Extract profile fields and remove password2
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        validated_data.pop('password2')

        # Create the User instance using custom manager
        user = User.objects.create_user(**validated_data)

        # Retrieve the auto-created Profile and update with names
        profile = user.profile  # Profile is guaranteed by post_save signal
        profile.first_name = first_name
        profile.last_name = last_name
        profile.save()

        return user

class ActivationResendSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)

    def validate(self, attrs):
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
    def validate(self, attrs):
        validated_data = super().validate(attrs)
        validated_data['user_email'] = self.user.email
        validated_data['user_id'] = self.user.id
        return validated_data
