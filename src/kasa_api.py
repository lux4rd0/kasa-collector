import asyncio
from kasa import Discover, SmartDevice, DeviceConfig
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
        Log basic discovery information without checking emeter functionality yet.
        """
        discovery_timeout = Config.KASA_COLLECTOR_DISCOVERY_TIMEOUT
        discovery_packets = Config.KASA_COLLECTOR_DISCOVERY_PACKETS
        devices = await Discover.discover(
            discovery_timeout=discovery_timeout, discovery_packets=discovery_packets
        )
        logger.info(f"Discovered {len(devices)} devices")

        # Log each device discovered, but avoid mentioning emeter until authenticated
        for ip, device in devices.items():
            device_info = await KasaAPI.get_device_info(device)
            logger.info(
                f"Device discovered: Alias: {device_info['alias']}, IP: {device_info['ip']}, DNS: {device_info['dns_name']}"
            )

        return devices

    @staticmethod
    async def get_device(ip_or_hostname, username=None, password=None):
        """
        Get a Kasa device by IP address or hostname. Attempt to use credentials if provided.
        Log whether authentication was attempted and if it was successful.
        """
        try:
            # Resolve hostname to IP if necessary
            ip = socket.gethostbyname(ip_or_hostname)
        except socket.gaierror:
            logger.error(f"Failed to resolve hostname: {ip_or_hostname}")
            raise

        try:
            # Discover the device
            if username and password:
                # Discover with credentials for devices that require authentication
                device = await Discover.discover_single(
                    ip, username=username, password=password
                )
                logger.info(
                    f"Discovered and authenticated device: {device.alias if device.alias else device.model} (IP: {ip})"
                )
            else:
                # Discover without credentials for devices that do not require authentication
                device = await Discover.discover_single(ip)
                logger.info(
                    f"Discovered device: {device.alias if device.alias else device.model} (IP: {ip})"
                )

            # Ensure full initialization by calling update
            await device.update()

            # Check if the device has emeter capability
            if device.has_emeter:
                logger.info(f"Device {device.alias} supports emeter functionality.")
            else:
                logger.warning(
                    f"Device {device.alias} does not support emeter functionality."
                )

        except Exception as e:
            logger.error(f"Failed to discover or authenticate device {ip}: {e}")
            raise

        return device

    @staticmethod
    async def fetch_emeter_data(device):
        """
        Fetch emeter data from a device, with logging.
        """
        await device.update()
        if not device.has_emeter:
            logger.warning(
                f"Device {device.model} does not support emeter functionality."
            )
            return {}
        logger.info(f"Fetched emeter data for device {device.model}")
        return device.emeter_realtime

    @staticmethod
    async def fetch_sysinfo(device):
        """
        Fetch system information from a device, with logging.
        """
        await device.update()
        if not hasattr(device, "sys_info"):
            logger.warning(
                f"Device {device.model} does not support sysinfo functionality."
            )
            return {}
        logger.info(f"Fetched sysinfo for device {device.model}")
        return device.sys_info

    @staticmethod
    async def fetch_device_data(device):
        """
        Fetch both emeter and system information from a device, with logging.
        """
        await device.update()
        logger.info(f"Fetched device data for {device.model}")
        data = {}
        if device.has_emeter:
            data["emeter"] = device.emeter_realtime
        if hasattr(device, "sys_info"):
            data["sys_info"] = device.sys_info
        return data

    @staticmethod
    async def _async_dns_lookup(ip):
        """
        Perform an asynchronous DNS lookup to get the hostname for an IP address.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.getnameinfo((ip, 0), socket.NI_NAMEREQD)
        except Exception as e:
            logger.warning(f"DNS lookup failed for {ip}: {e}")
            return "unknown"

    @staticmethod
    async def get_device_info(device):
        """
        Get the IP address, alias, and DNS name of a device, with fallback options.

        Parameters:
        - device (SmartDevice): The device to fetch information from.

        Returns:
        - dict: Dictionary containing device information.
        """
        ip = device.host

        try:
            # Attempt DNS lookup
            dns_name = await KasaAPI._async_dns_lookup(ip)
        except Exception as e:
            logger.warning(f"DNS lookup failed for {ip}: {e}")
            dns_name = "unknown"

        try:
            # Use alias if available, otherwise fallback to model name or "unknown"
            alias = (
                device.alias
                if device.alias
                else (device.model if device.model else "Unknown")
            )
        except Exception as e:
            logger.warning(f"Failed to get alias for {ip}: {e}")
            alias = "unknown"

        return {"ip": ip, "alias": alias, "dns_name": dns_name}
