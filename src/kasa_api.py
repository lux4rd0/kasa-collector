import asyncio
import re
from kasa import Discover, SmartStrip
import socket
import logging
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("KasaAPI")
logger.setLevel(Config.KASA_COLLECTOR_LOG_LEVEL_KASA_API)


class KasaAPI:
    @staticmethod
    async def discover_devices():
        """
        Discover Kasa devices on the network using the Discover class.
        Filters out devices that do not have emeter functionality.
        """
        discovery_timeout = Config.KASA_COLLECTOR_DISCOVERY_TIMEOUT
        discovery_packets = Config.KASA_COLLECTOR_DISCOVERY_PACKETS
        username = Config.KASA_COLLECTOR_TPLINK_USERNAME
        password = Config.KASA_COLLECTOR_TPLINK_PASSWORD
        use_credentials = Config.KASA_COLLECTOR_USE_CREDENTIALS
        hosts = re.split(r',\s*', Config.KASA_COLLECTOR_DEVICE_HOSTS.strip())

        if Config.KASA_COLLECTOR_DEVICE_DISCOVERY:
            devices = await Discover.discover(
                discovery_timeout=discovery_timeout,
                discovery_packets=discovery_packets,
                username=username if use_credentials else None,
                password=password if use_credentials else None
            )
            logger.info(f"Discovered {len(devices)} devices")
            return {ip: device for ip, device in devices.items() if device.has_emeter}
        else:
            devices = {}
            for host in hosts:
                device = await Discover.discover_single(host, username=username if use_credentials else None, password=password if use_credentials else None)
                devices[host] = device
            logger.info(f"Found {len(devices)} devices from Host List")
            return {ip: device for ip, device in devices.items()}

    @staticmethod
    async def fetch_emeter_data(device):
        """
        Fetch emeter data from a device.
        """
        await device.update()
        logger.info(f"Fetched emeter data for device {device.alias}")
        return device.emeter_realtime

    @staticmethod
    async def fetch_sysinfo(device):
        """
        Fetch system information from a device.
        """
        await device.update()
        logger.info(f"Fetched sysinfo for device {device.alias}")
        return device.sys_info

    @staticmethod
    async def fetch_device_data(device):
        """
        Fetch both emeter and system information from a device.
        """
        await device.update()
        logger.info(f"Fetched device data for {device.alias}")
        return {"emeter": device.emeter_realtime, "sys_info": device.sys_info}

    @staticmethod
    async def _async_dns_lookup(ip):
        """
        Perform an asynchronous DNS lookup to get the hostname for an IP address.
        """
        loop = asyncio.get_event_loop()
        return await loop.getnameinfo((ip, 0), socket.NI_NAMEREQD)

    @staticmethod
    async def get_device_info(device):
        """
        Get the IP address, alias, and DNS name of a device.
        """
        ip = device.host
        try:
            dns_name = await KasaAPI._async_dns_lookup(ip)
        except Exception as e:
            logger.warning(f"DNS lookup failed for {ip}: {e}")
            dns_name = "unknown"

        try:
            alias = device.alias
        except Exception as e:
            logger.warning(f"Failed to get alias for {ip}: {e}")
            alias = "unknown"

        return {"ip": ip, "alias": alias, "dns_name": dns_name}
