import jwt
from ...models import User
from django.shortcuts import get_object_or_404
from jwt import ExpiredSignatureError, InvalidSignatureError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegistrationSerializer,
    ActivationResendSerializer,
)
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from ...tasks import send_registration_email



class RegistrationAPIView(GenericAPIView):
    """
    API view for user registration.

    This view handles user registration by validating the provided data,
    creating a new user, sending an activation email with a token, and
    returning the created user's basic information.

    Methods
    -------
    post(request, *args, **kwargs):
        Handles POST requests for user registration. Validates serializer data,
        creates a user, sends activation email, and returns user info.
    get_token_for_user(user):
        Generates a JWT access token for the given user.
    """
    serializer_class = RegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user_obj = serializer.save()
            email = serializer.validated_data["email"]
            try:
                full_name = user_obj.profile.get_full_name()
                # we change data because data itself returns hashed password too
                data = {
                    "detail": "the registration was successful check your email and verify your account",
                    "email": email,
                    "full_name": full_name,
                }
                user_obj = get_object_or_404(User, email=email)
                token = self.get_token_for_user(user_obj)
                # send email for user with token
                send_registration_email.apply_async(kwargs={
                    "token": token,
                    "full_name": full_name,
                    "email": email,
                })

                return Response(data=data, status=status.HTTP_201_CREATED)
            except Exception as e:
                User.objects.get(email=email).delete()
                data = {
                    "detail": "An error occurred, please try again later and call to admins",
                }
                print(f"error: {str(e)}")
                return Response(data=data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_token_for_user(self, user):
        """
        Generate a JWT access token for the given user.

        Parameters
        ----------
        user : User
            The user instance for which to generate the token.

        Returns
        -------
        str
            The generated JWT access token as a string.
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class ActivationAPIView(APIView):
    """
    API view for activating a user account.

    This view verifies the provided JWT token, checks if the user is already
    verified, and activates the user account if valid.

    Methods
    -------
    get(request, token, *args, **kwargs):
        Handles GET requests for user activation. Decodes the token, verifies
        the user, and updates the user's verification status.
    """

    def get(self, request, token, *args, **kwargs):
        try:
            token = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=["HS256"])
            user_id = token["user_id"]
        except ExpiredSignatureError:
            return Response(
                {"detail": "Token Expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidSignatureError:
            return Response(
                {"detail": "Invalid Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = get_object_or_404(User, pk=user_id)
        if user.is_verified:
            return Response(
                {"detail": "User already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_verified = True
        user.save()
        return Response({"detail": "Activation Successful."}, status=status.HTTP_200_OK)


class ActivationResendAPIView(GenericAPIView):
    """
    API view for resending activation emails.

    This view allows resending the activation email with a new token
    for users who are not yet verified.

    Methods
    -------
    post(request, *args, **kwargs):
        Handles POST requests to resend activation email. Validates serializer,
        generates token, and sends email.
    get_token_for_user(user):
        Generates a JWT access token for the given user.
    """
    serializer_class = ActivationResendSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data["user"]
            token = self.get_token_for_user(user)
            # send email for user with token

            return Response(
                {"detail": "email sent successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "request failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_token_for_user(self, user):
        """
        Generate a JWT access token for the given user.

        Parameters
        ----------
        user : User
            The user instance for which to generate the token.

        Returns
        -------
        str
            The generated JWT access token as a string.
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom API view for obtaining JWT token pairs.

    This view uses a custom serializer to generate access and refresh tokens
    for authenticated users.

    Attributes
    ----------
    serializer_class : CustomTokenObtainPairSerializer
        The serializer used for token generation.
    """
    serializer_class = CustomTokenObtainPairSerializer


