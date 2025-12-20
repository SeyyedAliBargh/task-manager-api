from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from .serializers import RegisterUserSerializer



class RegisterUserAPIView(GenericAPIView):
    serializer_class = RegisterUserSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)