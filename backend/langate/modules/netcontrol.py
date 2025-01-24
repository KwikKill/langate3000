import requests
import subprocess
import logging

GET_REQUESTS = ["get_mac", "get_ip", '']
POST_REQUESTS = ["connect_user"]
DELETE_REQUESTS = ["disconnect_user"]
PUT_REQUESTS = ["set_mark"]

class Netcontrol:
    """
    Class which interacts with the netcontrol API.
    """
    def request(self, endpoint='', args={}):
        """
        Make a given request to the netcontrol API.
        """
        response = None

        # Make the request
        try:
            # Check the type of request
            if endpoint in GET_REQUESTS:
                response = requests.get(self.REQUEST_URL + endpoint, params=args)
            elif endpoint in POST_REQUESTS:
                response = requests.post(self.REQUEST_URL + endpoint, params=args)
            elif endpoint in DELETE_REQUESTS:
                response = requests.delete(self.REQUEST_URL + endpoint, params=args)
            elif endpoint in PUT_REQUESTS:
                response = requests.put(self.REQUEST_URL + endpoint, params=args)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            raise requests.HTTPError("Could not connect to the netcontrol API.")
        except requests.exceptions.Timeout:
            raise requests.HTTPError("The request to the netcontrol API timed out.")

    def check_api(self):
        """
        Check if the netcontrol API is running.
        """
        self.logger.info("Checking connection with the netcontrol API...")
        return self.request()

    def get_mac(self, ip: str):
        """
        Get the MAC address of the device with the given IP address.
        """
        self.logger.info(f"Getting MAC address of {ip}...")
        return self.request("get_mac", {"ip": ip})["mac"]

    def get_ip(self, mac: str):
        """
        Get the IP address of the device with the given MAC address.
        """
        self.logger.info(f"Getting IP address of {mac}...")
        return self.request("get_ip", {"mac": mac})["ip"]

    def connect_user(self, mac: str, mark: int, name: str) -> None:
        """
        Connect the user with the given MAC address.
        """
        self.logger.info(f"Connecting user with MAC address {mac} ({name})...")
        self.request("connect_user", {"mac": mac, "mark": mark, "name": name})

    def disconnect_user(self, mac: str) -> None:
        """
        Disconnect the user with the given MAC address.
        """
        self.logger.info(f"Disconnecting user with MAC address {mac}...")
        self.request("disconnect_user", {"mac": mac})

    def set_mark(self, mac: str, mark: int) -> None:
        """
        Set the mark of the user with the given MAC address.
        """
        self.logger.info(f"Setting mark of user with MAC address {mac} to {mark}...")
        self.request("set_mark", {"mac": mac, "mark": mark})

    def __init__(self):
        """
        Initialize HOST_IP to the docker's default route, set up REQUEST_URL and check the connection with the netcontrol API.
        """
        self.HOST_IP = subprocess.run(["/sbin/ip", "route"], capture_output=True).stdout.decode("utf-8").split()[2]
        self.REQUEST_URL = f"http://{self.HOST_IP}:6784/"

        self.logger = logging.getLogger(__name__)

        #self.check_api()
