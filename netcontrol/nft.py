import nftables
import json
import logging
import subprocess
from .variables import Variables
from fastapi import HTTPException

variables = Variables()

class Nft:
    """
    Class which interacts with the nftables backend
    """
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.nft = nftables.Nftables()
        self.nft.set_json_output(True)

    def check_nftables(self):
        data = self._execute_nft_cmd("list ruleset")
        metainfo = data[0]["metainfo"]
        self.logger.info(f"Found running nftables version {metainfo['version']} with {len(data)} ruleset entries.")
    
    def _execute_nft_cmd(self, cmd: str) -> dict:
        """
        Executes an nft command, handles the exception properly and returns an object

        Args:
            cmd (str): string representation of the command

        Raises:
            NftablesException: if the command returned an exception

        Returns:
            dict: parsed JSON output
        """
        output: str
        rc, output, error = self.nft.cmd(cmd)
        if rc != 0 or (error is not None and error != ""):
            raise NftablesException(rc, error)
        if output == "":
            return {}
        else:
            return json.loads(output)["nftables"]

    def setup_portail(self):
        """
        Sets up the necessary nftables rules that block network access to unauthenticated devices, and marks packets based on the map
        """
        
        # Set up table, set and map
        self._execute_nft_cmd("add table ip insalan")
        self._execute_nft_cmd("add set insalan netcontrol-auth { type ether_addr; }")
        self._execute_nft_cmd("add map insalan netcontrol-mac2mark { type ether_addr : mark; }")
        
        # Marks packets from authenticated users using the map
        self._execute_nft_cmd("add chain insalan netcontrol-filter { type filter hook prerouting priority 2; }")
        self._execute_nft_cmd("add rule insalan netcontrol-filter ip daddr != 172.16.1.0/24 ether saddr @netcontrol-auth meta mark set ether saddr map @netcontrol-mac2mark")

        # Let traffic with "bypass" pass through if no external rules have been added
        self._execute_nft_cmd("add chain insalan netcontrol-debypass { type filter hook prerouting priority 0; }")
        self._execute_nft_cmd("add rule insalan netcontrol-debypass meta mark > 1024 meta mark set meta mark ^ 1024")
        
        # Block external requests to the netcontrol module
        ips = subprocess.run('ip addr | grep -o "[0-9]*\\.[0-9]*\\.[0-9]*\\.[0-9]*/[0-9]*" | grep -o "[0-9]*\\.[0-9]*\\.[0-9]*\\.[0-9]*"', shell=True, capture_output=True).stdout.decode("utf-8").split("\n")[:-1]
        docker0_ip = subprocess.run("ip addr show docker0 | awk '/inet / {print $2}' | cut -d'/' -f1", shell=True, capture_output=True).stdout.decode("utf-8").strip()
        self._execute_nft_cmd(f"add rule insalan netcontrol-filter ip daddr {{ {docker0_ip},172.16.1.1 }} tcp dport 6784 ip saddr != {{ {','.join(ips)} }} drop")
        
        # Allow traffic to port 80 from unauthenticated devices and redirect it to the network head, to allow access to the langate webpage
        self._execute_nft_cmd("add chain insalan netcontrol-nat { type nat hook prerouting priority 0; }")
        self._execute_nft_cmd("add rule insalan netcontrol-nat ip daddr != 172.16.1.0/24 ether saddr != @netcontrol-auth tcp dport 80 redirect to :80")
        
        # Block other traffic from users that are not authenticated
        self._execute_nft_cmd("add chain insalan netcontrol-forward { type filter hook forward priority 0; }")
        docker_subnet = ".".join(docker0_ip.split(".")[:2]) + ".0.0/16"
        self._execute_nft_cmd(f"add rule insalan netcontrol-forward ip daddr != {{ 172.16.1.1,{docker_subnet} }} ip saddr {variables.ip_range()} ip saddr != {{ 172.16.1.1,{docker_subnet} }} ether saddr != @netcontrol-auth reject")

        self.logger.info("Gate nftables set up")
        
    def remove_portail(self):
        """
        Removes netcontrol-related chains, sets and maps from insalan table
        """
        self._execute_nft_cmd("delete chain insalan netcontrol-filter")
        self._execute_nft_cmd("delete chain insalan netcontrol-nat")
        self._execute_nft_cmd("delete chain insalan netcontrol-forward")
        self._execute_nft_cmd("delete set insalan netcontrol-auth")
        self._execute_nft_cmd("delete map insalan netcontrol-mac2mark")
        
        self.logger.info("Gate nftables removed")

    def set_mark(self, mac: str, mark: int, bypass: bool):
        """
        Changes mark of the given MAC address
        
        Args:
            mac (str): MAC address
            mark (int): mark to set
        """
        
        self.delete_user(mac)
        self.connect_user(mac, mark, bypass, "previously_connected_device")

    def connect_user(self, mac: str, mark: int, bypass: bool, name: str):
        """
        Connects given device with given mark
        
        Args:
            mac (str): MAC address
        """
        
        if bypass and mark < 1024:
            mark += 1024
        
        mac = mac.lower()
        try:
            self._execute_nft_cmd(f"add element insalan netcontrol-mac2mark {{ {mac} : {str(mark)} }}")
            self._execute_nft_cmd(f"add element insalan netcontrol-auth {{ {mac} }}")
        except NftablesException:
            self.logger.error(f"Tried to add device {mac} (name: {name}), unexpected nftables error occurred")
            raise HTTPException(status_code=500, detail="Unexpected nftables error occurred")
        
        self.logger.info(f"Device {mac} (name: {name}) connected with mark {mark}")

    def delete_user(self, mac: str) -> None:
        """
        Disconnects given device
        
        Args:
            mac (str): MAC address
        """
        
        mac = mac.lower()
        try:
            self._execute_nft_cmd(f"delete element insalan netcontrol-mac2mark {{ {mac} }}")
            self._execute_nft_cmd(f"delete element insalan netcontrol-auth {{ {mac} }}")
        except NftablesException:
            self.logger.error(f"Tried to delete device {mac} which was not previously connected")
            raise HTTPException(status_code=404, detail="Device was not previously connected")
        
        self.logger.info(f"Device {mac} disconnected")

class NftablesException(Exception):
    pass
