import jwt
from django.shortcuts import get_object_or_404
from djoser.conf import settings
from jwt import ExpiredSignatureError, InvalidSignatureError
from rest_framework import status
from rest_framework import generics
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegistrationSerializer, ActivationResendSerializer
from ...models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


class RegistrationAPIView(generics.GenericAPIView):
    serializer_class = RegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            email = serializer.validated_data["email"]
            full_name = serializer.validated_data["first_name"] + " " + serializer.validated_data["last_name"]
            # we change data because data itself returns hashed password too
            data = {
                "email": email,
                "full_name": full_name,
            }
            user_obj = get_object_or_404(User, email=email)
            token = self.get_token_for_user(user_obj)
            # send email for user with token

            html_content = render_to_string(
                "account/registration_email.html",
                {
                    "token": token,
                    "full_name": full_name,
                }
            )
            text_content = "This is a Registration Email"

            email_obj = EmailMultiAlternatives(
                "Activation Email",
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            email_obj.attach_alternative(html_content, "text/html")
            email_obj.send()

            return Response(data=data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_token_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class ActivationAPIView(APIView):
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
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


