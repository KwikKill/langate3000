import copy
from functools import reduce
from operator import or_

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from langate.settings import SETTINGS
from langate.user.models import Role
from langate.network.models import Device, UserDevice, DeviceManager
from langate.network.utils import validate_marks, validate_games, save_settings, get_mark

from langate.network.serializers import DeviceSerializer, UserDeviceSerializer, FullDeviceSerializer

class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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

class DeviceList(generics.ListCreateAPIView):
    """
    API endpoint that allows devices to be viewed or created.
    """
    serializer_class = FullDeviceSerializer
    permission_classes = [StaffPermission]
    pagination_class = Pagination

    def get_queryset(self):
        """
        Return a list of all UserDevice and Device objects.
        """
        user_devices = UserDevice.objects.all()
        # devices that are not in user_devices
        devices = Device.objects.exclude(id__in=user_devices.values_list('id', flat=True))

        queryset = list(user_devices) + list(devices)

        # order by id
        queryset = sorted(queryset, key=lambda x: x.id)

        return queryset

    def get(self, request):
        """
        Return a list of all UserDevice and Device objects.
        """
        queryset = self.get_queryset()
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = FullDeviceSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
      responses={
        201: FullDeviceSerializer,
        400: "Bad request",
      },
    )
    def post(self, request):
        """
        Create a new User device
        """
        # If it's a list of devices, create them all
        if isinstance(request.data, list):
            serializer = FullDeviceSerializer(data=request.data, many=True)
        else:
            serializer = FullDeviceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDeviceList(generics.ListAPIView):
    """
    API endpoint that allows user devices to be viewed.
    """
    serializer_class = UserDeviceSerializer
    permission_classes = [StaffPermission]
    pagination_class = Pagination

    def get_queryset(self):
        """
        Return a list of all UserDevice objects.
        """
        query = UserDevice.objects.all().order_by("id")

        orders = [
          "id", "-id", "ip", "-ip", "mac", "-mac", "name", "-name", "user", "-user", "mark", "-mark"
        ]
        filters = [
          "ip", "mac", "name", "user__username", "mark"
        ]
        # Fuzzy search
        if 'filter' in self.request.query_params:
            filter = self.request.query_params['filter']
            q_objects = [Q(**{f'{f}__icontains': filter}) for f in filters]
            query = query.filter(reduce(or_, q_objects))
        # Search specific mark
        if 'mark' in self.request.query_params:
            query = query.filter(mark=self.request.query_params['mark'])
        # Manage ordering
        if 'order' in self.request.query_params:
            order = self.request.query_params['order']
            if order in orders:
                query = query.order_by(order)
        return query

    @swagger_auto_schema(
        operation_description="List all UserDevices",
        responses={200: UserDeviceSerializer(many=True)},
        # Add query parameters
        manual_parameters=[
            openapi.Parameter(
                name="filter",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter the devices by IP, MAC, Name or User",
            ),
            openapi.Parameter(
                name="order",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Order the devices by id, ip, mac, name or user",
            ),
        ]
    )
    def get(self, request):
        """
        Return a list of all UserDevice objects.
        """
        try:
          queryset = self.get_queryset()
        except Exception as e:
          return Response({"error": "Bad query"}, status=status.HTTP_400_BAD_REQUEST)
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = UserDeviceSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

class DeviceDetail(generics.RetrieveDestroyAPIView):
    """
    API endpoint that allows a device to be viewed, updated, or deleted.
    """
    serializer_class = FullDeviceSerializer
    permission_classes = [StaffPermission]

    def get_queryset(self):
        """
        Return a list of all UserDevice and Device objects.
        """
        user_devices = UserDevice.objects.all()
        # devices that are not in user_devices
        devices = Device.objects.exclude(id__in=user_devices.values_list('id', flat=True))

        queryset = list(user_devices) + list(devices)

        # order by id
        queryset = sorted(queryset, key=lambda x: x.id)

        return queryset

    @swagger_auto_schema(
        responses={
            200: FullDeviceSerializer,
            404: "Device not found",
        }
    )
    def get(self, request, pk):
        """
        Get a device by its primary key
        """
        try:
            device = UserDevice.objects.get(pk=pk)
            serializer = FullDeviceSerializer(device)
            return Response(serializer.data)
        except UserDevice.DoesNotExist:
            try:
                device = Device.objects.get(pk=pk)
                serializer = FullDeviceSerializer(device)
                return Response(serializer.data)
            except Device.DoesNotExist:
                return Response({"error": _("Device not found")}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        responses={
            204: "Device deleted",
            404: "Device not found",
        }
    )
    def delete(self, request, pk):
        """
        Delete a device by its primary key
        """
        try:
            device = Device.objects.get(pk=pk)
            DeviceManager.delete_device(device.mac)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Device.DoesNotExist:
            return Response({"error": _("Device not found")}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        responses={
            200: "Device updated",
            400: "Bad request",
            404: "Device not found",
        }
    )
    def patch(self, request, pk):
        """
        Update a device by its primary key
        """
        try:
            device = Device.objects.get(pk=pk)
            DeviceManager.edit_device(
              device,
              request.data.get("mac", device.mac),
              request.data.get("name", device.name),
              request.data.get("mark", device.mark),
            )

            return Response(status=status.HTTP_200_OK)

        except Device.DoesNotExist:
            return Response({"error": _("Device not found")}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)

class DeviceWhitelist(generics.ListAPIView):
    """
    API endpoint that allows devices to be viewed.
    Creation of Whitelist devices need to be done with the DeviceList view.
    """
    queryset = Device.objects.filter(whitelisted=True)
    serializer_class = DeviceSerializer
    permission_classes = [StaffPermission]
    pagination_class = Pagination

    def get_queryset(self):
        """
        Return a list of all UserDevice objects.
        """
        query = self.queryset

        orders = [
          "id", "-id", "mac", "-mac", "name", "-name", "mark", "-mark"
        ]
        filters = [
          "mac", "name", "mark"
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

class MarkList(APIView):
    """
    API endpoint that allows marks to be viewed.
    """
    permission_classes = [StaffPermission]

    def get(self, request):
        """
        Return a list of all marks
        """
        # Make a copy
        marks = copy.deepcopy(SETTINGS["marks"])

        # for each mark, add the number of devices with that mark
        for mark in marks:
            mark["devices"] = Device.objects.filter(mark=mark["value"], whitelisted=False).count()
            mark["whitelisted"] = Device.objects.filter(mark=mark["value"], whitelisted=True).count()

        return Response(marks)

    def patch(self, request):
        """
        Modify the list of marks
        """
        if request.data is None or len(request.data) == 0:
            return Response({"error": _("No data provided")}, status=status.HTTP_400_BAD_REQUEST)

        if not validate_marks(request.data):
            return Response({"error": _("Invalid mark")}, status=status.HTTP_400_BAD_REQUEST)

        # Only keep the valid fields from the request
        marks = []
        for mark in request.data:
            marks.append({
              "name": mark["name"],
              "value": mark["value"],
              "priority": mark["priority"]
            })

        # If some marks are removed, add the new marks first, spread the devices and then remove the old marks
        old_marks = [m["value"] for m in SETTINGS["marks"]]
        new_marks = [m["value"] for m in marks]
        removed_marks = [m for m in old_marks if m not in new_marks]

        SETTINGS["marks"] = marks
        save_settings(SETTINGS)

        if removed_marks:
            for mark in removed_marks:
                devices = Device.objects.filter(mark=mark)
                for device in devices:
                    new = get_mark(excluded_marks=[mark])
                    DeviceManager.edit_device(device, device.mac, device.name, new)

        return Response(SETTINGS["marks"], status=status.HTTP_200_OK)

class MarkMove(APIView):
    """
    API endpoint that allows all devices on a mark to be moved to another mark.
    """

    permission_classes = [StaffPermission]

    def post(self, request, old, new):
        """
        Move all devices on a mark to another mark
        """
        # Check that the old and new marks are valid
        marks = [m["value"] for m in SETTINGS["marks"]]

        if old not in marks:
            return Response({"error": _("Invalid origin mark")}, status=status.HTTP_400_BAD_REQUEST)

        if new not in marks:
            return Response({"error": _("Invalid destination mark")}, status=status.HTTP_400_BAD_REQUEST)

        devices = Device.objects.filter(mark=old, whitelisted=False)
        for device in devices:
            DeviceManager.edit_device(device, device.mac, device.name, new)

        return Response(status=status.HTTP_200_OK)

class MarkSpread(APIView):
    """
    API endpoint that allows all devices on a mark to be moved to another mark.
    """

    permission_classes = [StaffPermission]

    def post(self, request, old):
        """
        Move all devices on a mark to another mark
        """
        # Check that the old and new marks are valid
        marks = [m["value"] for m in SETTINGS["marks"]]

        if old not in marks:
            return Response({"error": _("Invalid origin mark")}, status=status.HTTP_400_BAD_REQUEST)

        if sum([mark["priority"] for mark in SETTINGS["marks"] if mark["value"] != old]) == 0:
            return Response({"error": _("No mark to spread to")}, status=status.HTTP_400_BAD_REQUEST)

        devices = Device.objects.filter(mark=old, whitelisted=False)
        for device in devices:
            new = get_mark(excluded_marks=[old])
            DeviceManager.edit_device(device, device.mac, device.name, new)

        return Response(status=status.HTTP_200_OK)

class GameList(APIView):
    """
    API endpoint that allows games to be viewed.
    """
    permission_classes = [StaffPermission]

    def get(self, request):
        """
        Return a list of all games
        """
        return Response(SETTINGS["games"])

    def patch(self, request):
        """
        Create a new game
        """
        if not validate_games(request.data):
            return Response({"error": _("Invalid game")}, status=status.HTTP_400_BAD_REQUEST)

        SETTINGS["games"] = request.data

        save_settings(SETTINGS)

        return Response(SETTINGS["games"], status=status.HTTP_201_CREATED)

class UserDeviceDetail(APIView):
    """
    API endpoint that allows a user to edit or delete their devices
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={
            204: "Device deleted",
            403: {"error": _("You are not allowed to delete this device")},
            404: {"error": _("Device not found")},
        }
    )
    def delete(self, request, pk):
        """
        Delete a device by its primary key
        """
        try:
            device = UserDevice.objects.get(pk=pk)

            # Check if the user is the owner of the device
            if device.user != request.user:
                return Response({"error": _("You are not allowed to delete this device")}, status=status.HTTP_403_FORBIDDEN)

            DeviceManager.delete_device(device.mac)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserDevice.DoesNotExist:
            return Response({"error": _("Device not found")}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        responses={
            200: "Device updated",
            400: {"error": _("Bad request")},
            403: {"error": _("You are not allowed to edit this device")},
            404: {"error": _("Device not found")},
        }
    )
    def patch(self, request, pk):
        """
        Update a device by its primary key
        """
        try:
            device = UserDevice.objects.get(pk=pk)

            # Check if the user is the owner of the device
            if device.user != request.user:
                return Response({"error": _("You are not allowed to edit this device")}, status=status.HTTP_403_FORBIDDEN)

            DeviceManager.edit_device(
              device,
              request.data.get("mac", device.mac),
              request.data.get("name", device.name),
              request.data.get("mark", device.mark),
              request.data.get("bypass", device.bypass),
            )

            return Response(status=status.HTTP_200_OK)

        except UserDevice.DoesNotExist:
            return Response({"error": _("Device not found")}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
