"""
Network module. This module is responsible for the device and user connexion management.
"""

import requests
import sys, logging
import os

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from langate.settings import netcontrol
from langate.settings import SETTINGS

logger = logging.getLogger(__name__)

class NetworkConfig(AppConfig):
    """Configuration of the Network Django App"""

    name = "langate.network"
    verbose_name = _("Network module")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
            Reconnecting devices registered in the Device set but not in netcontrol.
            This is important when for example netcontrol is reset, you want the users that are already
            registered on the gate to be automatically reconnected when the gate restarts.
            This is important to maintain the consistency between the device state from django's point of view
            and the device state from netcontrol's point of view.
        """
        from langate.network.models import Device, UserDevice, DeviceManager

        if not any(
            x in sys.argv
            for x in
            [
                'pylint_django',
                'makemigrations',
                'migrate',
                'shell',
                'createsuperuser',
                'flush',
                'collectstatic',
                'test',
            ]
        ):

            logger.info(_("[PortalConfig] Adding previously connected devices to netcontrol"))

            for dev in Device.objects.all():
                userdevice = UserDevice.objects.filter(mac=dev.mac).first()
                try:
                    if userdevice is not None:
                        connect_res = netcontrol.connect_user(userdevice.mac, userdevice.mark, userdevice.bypass, userdevice.user.username)
                    else:
                        connect_res = netcontrol.connect_user(dev.mac, dev.mark, dev.bypass, dev.name)
                except requests.HTTPError as e:
                    logger.info("[PortalConfig] {e}")

                try:
                    mark_res = netcontrol.set_mark(dev.mac, dev.mark, dev.bypass)
                except requests.HTTPError as e:
                    logger.info("[PortalConfig] {e}")

            logger.info(_("[PortalConfig] Add default whitelist devices to netcontrol"))
            if os.path.exists("assets/misc/whitelist.txt"):
                with open("assets/misc/whitelist.txt", "r") as f:
                    for line in f:
                        line = line.strip().split("|")
                        if len(line) == 2 or len(line) == 3:
                            name = line[0]
                            mac = line[1]
                            mark = line[2] if len(line) == 3 else SETTINGS["marks"][0]["value"]
                            dev = Device.objects.filter(mac=mac).first()
                            if dev is None:
                                dev = DeviceManager.create_device(mac, name, True, True, mark)
                            else:
                                dev.whitelisted = True
                                dev.bypass = True
                                dev.save()
                                try:
                                    connect_res = netcontrol.connect_user(dev.mac, dev.mark, dev.bypass, dev.name)
                                except requests.HTTPError as e:
                                    logger.info("[PortalConfig] {e}")

                                try:
                                    mark_res = netcontrol.set_mark(dev.mac, mark, dev.bypass)
                                except requests.HTTPError as e:
                                    logger.info("[PortalConfig] {e}")
                        else:
                            logger.error("[PortalConfig] Invalid line in whitelist.txt: %s", line)
