import random
import jwt

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from jwt import ExpiredSignatureError, InvalidSignatureError

from ...models import User
from ...tasks import send_registration_email, send_change_email
from .serializers import *
from ...rate_limit import RegistrationRateThrottle, ActivationRateThrottle, LoginRateThrottle, ChangePasswordRateThrottle, ProfileRateThrottle
from ...models.users import EmailChangeRequestModel

class RegistrationAPIView(GenericAPIView):
    """
    Handles user registration.

    Responsibilities:
    - Validate registration data
    - Create user and related profile
    - Generate activation token
    - Dispatch activation email asynchronously
    """

    serializer_class = RegistrationSerializer
    throttle_classes = [RegistrationRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user_obj = serializer.save()
            email = serializer.validated_data["email"]

            try:
                # Retrieve user's full name from Profile
                full_name = user_obj.profile.get_full_name()

                # Prepare safe response payload (never return password data)
                data = {
                    "detail": "the registration was successful check your email and verify your account",
                    "email": email,
                    "full_name": full_name,
                }

                # Generate short-lived JWT activation token
                token = self.get_token_for_user(user_obj)

                # Send activation email asynchronously
                send_registration_email.apply_async(kwargs={
                    "token": token,
                    "full_name": full_name,
                    "email": email,
                })

                return Response(data=data, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Roll back user creation on any downstream failure
                User.objects.get(email=email).delete()

                # Log error (print is not acceptable for production)
                print(f"error: {str(e)}")

                return Response(
                    {"detail": "An error occurred, please try again later and call to admins"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_token_for_user(self, user):
        """
        Generates an access token for account activation.
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class ActivationAPIView(APIView):
    """
    Handles account activation via JWT token.
    """

    throttle_classes = [ActivationRateThrottle]
    permission_classes = [AllowAny]
    def get(self, request, token, *args, **kwargs):
        try:
            # Decode activation token using project SECRET_KEY
            payload = jwt.decode(
                jwt=token,
                key=settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            user_id = payload["user_id"]

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

        # Retrieve user or fail
        user = get_object_or_404(User, pk=user_id)

        # Prevent re-activation
        if user.is_verified:
            return Response(
                {"detail": "User already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Activate user account
        user.is_verified = True
        user.save()

        return Response(
            {"detail": "Activation Successful."},
            status=status.HTTP_200_OK,
        )


class ActivationResendAPIView(GenericAPIView):
    """
    Resends activation email for unverified users.
    """

    serializer_class = ActivationResendSerializer
    throttle_classes = [RegistrationRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data["user"]
            email = serializer.validated_data["email"]
            full_name = serializer.validated_data["full_name"]
            # Generate new activation token
            token = self.get_token_for_user(user)

            # Send activation email asynchronously
            send_registration_email.apply_async(kwargs={
                "token": token,
                "full_name": full_name,
                "email": email,
            })
            return Response(
                {"detail": "email sent successfully."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "request failed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_token_for_user(self, user):
        """
        Generates a fresh activation token.
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    JWT login endpoint with customized response payload.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class CustomDiscardAuthToken(APIView):
    """
    Logs out user by deleting DRF auth token.
    WARNING: This is incompatible with pure JWT-based auth.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [LoginRateThrottle]


    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordAPIView(generics.GenericAPIView):
    """
    Allows authenticated users to change their password.
    """

    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChangePasswordRateThrottle]

    def get_object(self):
        """
        Returns the currently authenticated user.
        """
        return self.request.user

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Validate old password
            if not self.object.check_password(serializer.data["old_password"]):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Set and hash new password
            self.object.set_password(serializer.data["new_password"])
            self.object.save()

            return Response(
                {"detail": "Password Changed Successfully"},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangeEmailAPIView(generics.GenericAPIView):
    """
    API endpoint to request an email change.

    - Requires authentication.
    - Validates the old and new email addresses.
    - Generates a 6-digit verification code.
    - Stores the request in the database.
    - Sends the verification code to the new email asynchronously via Celery.
    """
    serializer_class = ChangeEmailSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        """
        Handle PUT request to initiate email change.
        """
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            new_email = serializer.validated_data["new_email"]
            code = str(random.randint(100000, 999999))

            EmailChangeRequestModel.objects.create(user=request.user, new_email=new_email, code=code)

            send_change_email.apply_async(kwargs={
                "code": code,
                "new_email": new_email,
            })

            return Response({"detail": "Email sent successfully."}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmEmailChangeAPIView(generics.GenericAPIView):
    """
    API endpoint to confirm an email change.

    - Requires authentication.
    - Validates the verification code.
    - Marks the request as verified if valid and not expired.
    - Updates the user's email address.
    """
    serializer_class = ConfirmEmailChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handle POST request to confirm email change.
        """
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            req = serializer.validated_data["email_request"]

            req.is_verified = True
            req.save()

            user = request.user
            user.email = req.new_email
            user.save()

            return Response({"detail": "Email successfully changed."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to retrieve and update the authenticated user's profile.

    - Requires authentication.
    - Supports multipart/form-data for profile picture uploads.
    - Applies custom rate limiting via ProfileRateThrottle.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ProfileRateThrottle]

    def get_object(self):
        """
        Return the profile object of the currently authenticated user.
        """
        return self.request.user.profile
