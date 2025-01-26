"""User module API Endpoints"""
import requests

from functools import reduce
from operator import or_

from django.db.models import Q
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError

from rest_framework import generics, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from langate.user.serializers import (
    UserLoginSerializer,
    UserSerializer,
    UserRegisterSerializer,
)

from .models import User, Role
from langate.settings import netcontrol

from langate.network.models import UserDevice, Device, DeviceManager
from langate.network.serializers import UserDeviceSerializer

class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@require_GET
@ensure_csrf_cookie
def get_csrf(request):
    """
    Returns a response setting CSRF cookie in headers
    """
    return JsonResponse({"csrf": _("CSRF cookie set")})

# Filter, can only acces this view when user.role == 'admin' or 'staff'
class StaffPermission(permissions.BasePermission):
    """
    Custom permission to only allow staff or admin to access the view
    """

    def has_permission(self, request, view):
        """
        Check if the user has the permission to access the view
        """
        if request.user.is_authenticated:
            return request.user.role in [Role.ADMIN, Role.STAFF]
        return False

class UserView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [StaffPermission]
    authentication_classes = [SessionAuthentication]
    serializer_class = UserSerializer

    def patch(self, request, *args, **kwargs):
        """
        Update a user
        """
        if "password" in request.data:
            del request.data["password"]
            return Response(
                {"error": [_("Password cannot be changed")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "bypass" in request.data:
            user = UserSerializer(request.user, context={"request": request}).data
            user_devices = UserDevice.objects.filter(user=request.user)
            for d in user_devices:
                DeviceManager.edit_device(d, bypass=request.data["bypass"])
        return self.partial_update(request, *args, **kwargs)


class UserMe(generics.RetrieveAPIView):
    """
    API endpoint that allows a logged in user to get and set some of their own
    account fields.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        """
        Returns an user's own informations
        """
        user = UserSerializer(request.user, context={"request": request}).data

        user_devices = UserDevice.objects.filter(user=request.user)
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')

        if not user_devices.filter(ip=client_ip).exists():
            # If the user is still logged in but the device is not registered on the network,
            # we register it.
            try:
                client_mac = netcontrol.get_mac(client_ip)
            except requests.HTTPError as e:
                raise ValidationError(
                    _("Could not get MAC address")
                ) from e
            try:
                # The following should never raise a MultipleObjectsReturned exception
                # because it would mean that there are more than one devices
                # already registered with the same MAC.

                device = UserDevice.objects.get(mac=client_mac)
                # If the device MAC is already registered on the network but with a different IP,
                # This could happen if the DHCP has changed the IP of the client.

                # * If the registered device is owned by another user, we delete the old device and we register the new one.
                if device.user != request.user:
                    if user_devices.count() >= request.user.max_device_nb:
                        user["too_many_devices"] = True
                        
                        user_devices = UserDevice.objects.filter(user=request.user)

                        # Add UserDevices that belong to the user
                        user["devices"] = UserDeviceSerializer(
                            user_devices, many=True
                        ).data
                        
                        return Response(user, status=status.HTTP_200_OK)
                    DeviceManager.delete_user_device(device)

                    DeviceManager.create_user_device(request.user, client_ip)
                # * If the registered device is owned by the requesting user, we change the IP of the registered device.
                else:
                    device.ip = client_ip
                    device.save()

            except UserDevice.DoesNotExist:
                # If the device is not registered on the network, we register it.
                if user_devices.count() >= request.user.max_device_nb:
                    user["too_many_devices"] = True
                    
                    user_devices = UserDevice.objects.filter(user=request.user)

                    # Add UserDevices that belong to the user
                    user["devices"] = UserDeviceSerializer(
                        user_devices, many=True
                    ).data
                    
                    return Response(user, status=status.HTTP_200_OK)
                DeviceManager.create_user_device(request.user, client_ip)

        user_devices = UserDevice.objects.filter(user=request.user)

        # Add UserDevices that belong to the user
        user["devices"] = UserDeviceSerializer(
            user_devices, many=True
        ).data

        return Response(user)

class UserLogin(APIView):
    """
    API endpoint that allows user login.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = [SessionAuthentication]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description=_("Username")
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description=_("Password")
                ),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "user": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description=_("User logged in")
                    )
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description=_("Invalid data format")
                        )
                    )
                }
            ),
            404: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description=_("Bad Username or password")
                        )
                    )
                }
            )
        }
    )
    def post(self, request):
        """
        Submit a login form
        """
        data = request.data
        serializer = UserLoginSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            user = serializer.check_validity(data)
            if user is None:
                return Response(
                    {"error": [_("Bad Username or password")]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            login(request, user)

            user = UserSerializer(user, context={"request": request}).data

            # handle user device
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
            user_devices = UserDevice.objects.filter(user=request.user)

            user["current_ip"] = client_ip
            user["too_many_devices"] = False

            # If this device is not registered on the network, we register it.
            if not user_devices.filter(ip=client_ip).exists():
                try:
                    client_mac = netcontrol.get_mac(client_ip)
                except requests.HTTPError as e:
                    raise ValidationError(
                        _("Could not get MAC address")
                    ) from e
                try:
                    # The following should never raise a MultipleObjectsReturned exception
                    # because it would mean that there are more than one devices
                    # already registered with the same MAC.

                    device = UserDevice.objects.get(mac=client_mac)
                    # If the device MAC is already registered on the network but with a different IP,
                    # This could happen if the DHCP has changed the IP of the client.

                    # * If the registered device is owned by another user, we delete the old device and we register the new one.
                    if device.user != request.user:
                        if user_devices.count() >= request.user.max_device_nb:
                            user["too_many_devices"] = True
                            
                            user_devices = UserDevice.objects.filter(user=request.user)

                            # Add UserDevices that belong to the user
                            user["devices"] = UserDeviceSerializer(
                                user_devices, many=True
                            ).data
                            
                            return Response(user, status=status.HTTP_200_OK)
                        DeviceManager.delete_user_device(device)

                        DeviceManager.create_user_device(request.user, client_ip)
                    # * If the registered device is owned by the requesting user, we change the IP of the registered device.
                    else:
                        device.ip = client_ip
                        device.save()

                except UserDevice.DoesNotExist:
                    # If the device is not registered on the network, we register it.
                    if user_devices.count() >= request.user.max_device_nb:
                        user["too_many_devices"] = True
                        
                        user_devices = UserDevice.objects.filter(user=request.user)

                        # Add UserDevices that belong to the user
                        user["devices"] = UserDeviceSerializer(
                            user_devices, many=True
                        ).data
                        
                        return Response(user, status=status.HTTP_200_OK)
                    DeviceManager.create_user_device(request.user, client_ip)

            user_devices = UserDevice.objects.filter(user=request.user)

            user["devices"] = UserDeviceSerializer(
                user_devices, many=True
            ).data

            return Response(status=status.HTTP_200_OK, data=user)
        return Response(
            {"error": [_("Invalid data format")]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserLogout(APIView):
    """
    API endpoint that allows a user to logout.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = [SessionAuthentication]

    def post(self, request):
        """
        Will logout an user.
        """
        # if the user is not authenticated, we return a 200 OK
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_200_OK)

        user_devices = UserDevice.objects.filter(user=request.user)
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')

        if user_devices.filter(ip=client_ip).exists():
            # When the user decides to disconnect from the portal from a device,
            # we delete the device from the database.
            device = user_devices.get(ip=client_ip)
            DeviceManager.delete_user_device(device)

        logout(request)
        return Response(status=status.HTTP_200_OK)

class UserList(generics.ListCreateAPIView):
    """
    API endpoint that allows users to be viewed or created.
    """

    permission_classes = [StaffPermission]
    authentication_classes = [SessionAuthentication]
    serializer_class = UserSerializer
    pagination_class = Pagination

    def get_queryset(self):
        """
        Return a list of all users
        """
        query = User.objects.all().order_by("-date_joined")
        orders = [
          "id", "-id", "last_login", "-last_login", "username", "-username",
          "role", "-role", "is_active", "-is_active", "date_joined", "-date_joined",
          "max_device_nb", "-max_device_nb", "tournament", "-tournament", "team", "-team",
        ]
        filters = [
          "username", "role", "tournament", "team"
        ]
        # Fuzzy search
        if 'filter' in self.request.query_params:
            filter = self.request.query_params['filter']
            q_objects = [Q(**{f'{f}__icontains': filter}) for f in filters]
            query = query.filter(reduce(or_, q_objects))
        # Manage ordering
        if 'order' in self.request.query_params:
            order = self.request.query_params['order']
            if order in orders:
                query = query.order_by(order)
        return query

    @swagger_auto_schema(
      # Add query parameters
      manual_parameters=[
        openapi.Parameter(
          name="filter",
          in_=openapi.IN_QUERY,
          type=openapi.TYPE_STRING,
          description=_("Filter the users"),
        ),
        openapi.Parameter(
          name="order",
          in_=openapi.IN_QUERY,
          type=openapi.TYPE_STRING,
          description=_("Order the users"),
        ),
      ],
      responses={200: UserSerializer(many=True)},
    )
    def get(self, request):
        """
        Return a list of all users
        """
        queryset = self.get_queryset()
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(queryset, self.request)
        serializer = UserSerializer(result_page, many=True)

        # add devices to the response
        for user in serializer.data:
            user_devices = UserDevice.objects.filter(user=user['id'])
            user["devices"] = UserDeviceSerializer(
                user_devices, many=True
            ).data

        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=UserRegisterSerializer,
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "user": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description=_("User created")
                    )
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description=_("Invalid data format")
                        )
                    )
                }
            )
        }
    )
    def post(self, request):
        """
        Create a new User
        """
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
            except ValidationError as e:
                return Response({
                  "error": e.messages
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
          {"error": serializer.errors},
          status=status.HTTP_400_BAD_REQUEST
        )

class ChangePassword(APIView):
    """
    API endpoint that allows staff to change a user's password.
    This endpoint takes the user id as url parameter and the new password as request body.
    """

    permission_classes = [StaffPermission]
    authentication_classes = [SessionAuthentication]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description=_("New password")
                )
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "user": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description=_("Password changed")
                    )
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description=_("Invalid data format")
                        )
                    )
                }
            ),
            404: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description=_("User not found")
                        )
                    )
                }
            )
        }
    )
    def post(self, request, pk):
        """
        Change a user's password
        """
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": [_("User not found")]},
                status=status.HTTP_404_NOT_FOUND,
            )
        if "password" in request.data:
            user.set_password(request.data["password"])
            user.save()
            return Response(status=status.HTTP_200_OK)
        return Response(
            {"error": [_("Invalid data format")]},
            status=status.HTTP_400_BAD_REQUEST,
        )
