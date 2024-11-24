import requests
import random, logging
import re

from django.contrib.auth.base_user import AbstractBaseUser as AbstractBaseUser

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from langate.user.models import User
from langate.settings import netcontrol
from langate.settings import SETTINGS

from .utils import generate_dev_name, get_mark

logger = logging.getLogger(__name__)


def validate_mac(mac):
    """
    Validate a MAC address
    """
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac):
        raise ValidationError(_("Invalid MAC address"))


class Device(models.Model):
    """
    A device is a machine connected to the network
    """

    name = models.CharField(max_length=50)
    mac = models.CharField(
      max_length=17,
      unique=True,
      validators=[validate_mac]
    )
    whitelisted = models.BooleanField(default=False)
    bypass = models.BooleanField(default=False)
    mark = models.IntegerField(default=SETTINGS["marks"][0]["value"])

class UserDevice(Device):
    """
    A user device is a device that is connected to the network by a user
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(blank=False)

class DeviceManager(models.Manager):
    """
    Manager for the Device and UserDevice models
    """

    @staticmethod
    def create_device(mac, name, whitelisted=False, bypass=None, mark=None):
        """
        Create a device with the given mac address and name
        """
        if not name:
            name = generate_dev_name()
        if not mark:
            mark = SETTINGS["marks"][0]["value"]
        if bypass is None and whitelisted is not None:
            # Whitelisted devices have bypass by default
            bypass = whitelisted
        elif bypass is None:
            bypass = False
        
        # Validate the MAC address
        validate_mac(mac)

        try:
            netcontrol.connect_user(mac, mark, bypass, name)
            logger.info("Connected device %s (the mac %s has been connected)", name, mac)
        except requests.HTTPError as e:
            raise ValidationError(
              _("Could not connect user.")
            ) from e

        try:
            device = Device.objects.create(mac=mac, name=name, whitelisted=whitelisted, bypass=bypass, mark=mark)
            device.save()
            return device
        except Exception as e:
            try:
                netcontrol.disconnect_user(mac)
            except requests.HTTPError as e:
                raise ValidationError(
                  _("Could not disconnect user.")
                ) from e
            raise ValidationError(
              _("There was an error creating the device. Please try again.")
            ) from e

    @staticmethod
    def delete_device(mac):
        """
        Delete a device with the given mac address
        """
        try:
            netcontrol.disconnect_user(mac)
            logger.info("Disconnected device %s from the internet.", mac)
        except requests.HTTPError as e:
            raise ValidationError(
              _("Could not disconnect user.")
            ) from e

        device = Device.objects.get(mac=mac)
        device.delete()
        return device

    @staticmethod
    def create_user_device(user: User, ip, name=None):
        """
        Create a device with the given mac address
        """
        if not name:
            name = generate_dev_name()

        try:
            mac = netcontrol.get_mac(ip)
        except requests.HTTPError as e:
            raise ValidationError(
              _("Could not get MAC address.")
            ) from e

        # Validate the MAC address
        validate_mac(mac)

        mark = get_mark(user)
        bypass = user.bypass

        try:
            netcontrol.connect_user(mac, mark, False, user.username)
            logger.info(
                "Connected device %s (owned by %s) at %s to the internet.",
                mac,
                user.username,
                ip
            )
        except requests.HTTPError as e:
            raise ValidationError(
              _("Could not connect user.")
            ) from e

        try:
            device = UserDevice.objects.create(mac=mac, name=name, user=user, ip=ip, mark=mark, bypass=bypass)
            device.save()
            return device
        except Exception as e:
            try:
                netcontrol.disconnect_user(mac)
            except requests.HTTPError as e:
                raise ValidationError(
                  _("Could not disconnect user.")
                ) from e
            raise ValidationError(
              _("There was an error creating the device. Please try again.")
            ) from e

    @staticmethod
    def delete_user_device(Device):
        """
        Delete a device with the given mac address
        """
        return DeviceManager.delete_device(Device.mac)

    @staticmethod
    def edit_device(device: Device, mac=None, name=None, mark=None, bypass=None):
        """
        Edit the status of a device
        """
        # If name is provided, update it
        if name and name != device.name:
            device.name = name
        if mac and mac != device.mac:
            validate_mac(mac)
            # Disconnect the old MAC
            try:
                netcontrol.disconnect_user(device.mac)
                # Connect the new MAC
                netcontrol.connect_user(mac, device.mark, device.bypass, device.name)
                device.mac = mac
            except requests.HTTPError as e:
                raise ValidationError(
                    _("Could not connect user")
                ) from e
        if (mark and mark != device.mark) or (bypass is not None and bypass != device.bypass):
            if mark and mark != device.mark:
                # Check if the mark is valid
                if mark not in [m["value"] for m in SETTINGS["marks"]]:
                    raise ValidationError(_("Invalid mark"))
                device.mark = mark
            else:
                mark = device.mark
            if bypass is None:
                bypass = device.bypass
            try:
                netcontrol.set_mark(device.mac, mark, bypass)
            except requests.HTTPError as e:
                raise ValidationError(
                    _("Could not set mark")
                ) from e

        try:
            device.save()
        except Exception as e:
            raise ValidationError(_("The data provided is invalid")) from e
