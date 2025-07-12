import asyncio
from kasa import Discover, Device, DeviceConfig, Credentials
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
    _first_discovery_complete = False  # Class variable to track first discovery

    @staticmethod
    async def discover_devices():
        """
        Discover Kasa devices on the network using the Discover class.
        Log basic discovery information without checking emeter functionality yet.
        """
        discovery_timeout = Config.KASA_COLLECTOR_DISCOVERY_TIMEOUT
        discovery_packets = Config.KASA_COLLECTOR_DISCOVERY_PACKETS

        # Include credentials in discovery for devices that need them
        username = Config.KASA_COLLECTOR_TPLINK_USERNAME
        password = Config.KASA_COLLECTOR_TPLINK_PASSWORD

        devices = await Discover.discover(
            discovery_timeout=discovery_timeout,
            discovery_packets=discovery_packets,
            username=username,
            password=password,
        )
        logger.info(f"Discovered {len(devices)} devices")

        # Log each device discovered, but avoid mentioning emeter until authenticated
        for ip, device in devices.items():
            device_info = await KasaAPI.get_device_info(device)
            # Add debugging info about device type and protocol
            device_type = getattr(device, "device_type", "unknown")
            device_family = getattr(device, "family", "unknown")
            protocol = device.__class__.__name__

            # Show details at INFO level for first discovery
            if not KasaAPI._first_discovery_complete:
                logger.info(
                    f"Discovered: {device_info['alias']}, IP: {device_info['ip']}, "
                    f"DNS: {device_info['dns_name']}, Type: {device_type}, "
                    f"Family: {device_family}, Protocol: {protocol}"
                )
            else:
                logger.debug(
                    f"Discovered: {device_info['alias']}, IP: {device_info['ip']}, "
                    f"DNS: {device_info['dns_name']}, Type: {device_type}, "
                    f"Family: {device_family}, Protocol: {protocol}"
                )

        # Mark first discovery as complete
        KasaAPI._first_discovery_complete = True
        return devices

    @staticmethod
    async def authenticate_discovered_device(device, username=None, password=None):
        """
        Authenticate a discovered device.
        For IOT devices, they're already authenticated from discovery.
        For SMART devices, we need different handling.
        Returns True if device is ready to use, False otherwise.
        """
        try:
            # Log device details for debugging
            device_type = getattr(device, "device_type", "unknown")
            device_family = getattr(device, "family", "unknown")
            protocol = device.__class__.__name__
            logger.debug(
                f"Checking device {device.host} - Type: {device_type}, "
                f"Family: {device_family}, Protocol: {protocol}"
            )

            # IOT devices (IotPlug, IotStrip) are already discovered with credentials
            # They don't need additional authentication
            if protocol in ["IotPlug", "IotStrip", "IotBulb", "IotDimmer"]:
                # Just update to ensure it's working
                await device.update()
                logger.debug(f"IOT device ready: {device.alias} (IP: {device.host})")
                return True

            # SmartDevice needs special handling - it might need HTTP/HTTPS
            elif protocol == "SmartDevice":
                logger.warning(
                    f"SmartDevice {device.host} detected. This device type may use "
                    f"HTTP/HTTPS protocol and might not be fully supported yet."
                )
                # Try to update anyway
                try:
                    await device.update()
                    return True
                except Exception as smart_error:
                    logger.debug(f"SmartDevice update failed: {smart_error}")
                    return False

            # Unknown device type
            else:
                logger.warning(f"Unknown device protocol: {protocol}")
                await device.update()
                return True

        except Exception as e:
            error_type = type(e).__name__
            logger.debug(
                f"Failed to verify discovered device {device.host}: "
                f"{error_type}: {e}"
            )
            # Check if it's a connection error that we should handle differently
            if "Connect call failed" in str(e) or "Connection reset" in str(e):
                logger.warning(
                    f"Device {device.host} appears to be discovered but not "
                    f"connectable. "
                    f"It may be on a different VLAN or have firewall rules."
                )
            return False

    @staticmethod
    async def get_device(ip_or_hostname, username=None, password=None):
        """
        Get a Kasa device by IP address or hostname.
        Attempt to use credentials if provided.
        Uses Device.connect() for better performance as recommended by the API.
        """
        try:
            # Resolve hostname to IP if necessary using async DNS resolution
            loop = asyncio.get_running_loop()
            result = await loop.getaddrinfo(ip_or_hostname, None, family=socket.AF_INET)
            ip = result[0][4][0]  # Extract IP address from result
        except socket.gaierror:
            logger.error(f"Failed to resolve hostname: {ip_or_hostname}")
            raise

        device = None
        
        # First try discover_single for better cross-subnet compatibility
        # This properly detects device type and protocol
        try:
            logger.debug(f"Attempting discover_single for {ip}")
            device = await Discover.discover_single(
                ip,
                credentials=Credentials(username=username, password=password) if username and password else None
            )
            if device:
                await device.update()
                logger.debug(
                    f"Connected to device via discovery: "
                    f"{device.alias if device.alias else device.model} (IP: {ip})"
                )
                return device
        except Exception as discover_error:
            logger.debug(f"discover_single failed for {ip}: {discover_error}")
            # Fall through to try Device.connect
        
        try:
            # Fallback to direct connection if discovery fails
            if username and password:
                # Create config with credentials for authenticated devices
                credentials = Credentials(username=username, password=password)
                config = DeviceConfig(
                    host=ip,
                    credentials=credentials,
                    timeout=Config.KASA_COLLECTOR_AUTH_TIMEOUT,
                )
                try:
                    device = await Device.connect(config=config)
                    logger.debug(
                        f"Connected to authenticated device: "
                        f"{device.alias if device.alias else device.model} (IP: {ip})"
                    )
                except Exception as auth_error:
                    logger.warning(f"Failed to connect with credentials: {auth_error}")
                    # Try without credentials as fallback
                    try:
                        device = await Device.connect(host=ip)
                        logger.debug(
                            f"Connected to device without authentication: "
                            f"{device.alias if device.alias else device.model} (IP: {ip})"
                        )
                    except Exception as fallback_error:
                        logger.error(f"Failed to connect without credentials: {fallback_error}")
                        raise
            else:
                # Connect without credentials for devices without authentication
                device = await Device.connect(host=ip)
                logger.debug(
                    f"Connected to device: "
                    f"{device.alias if device.alias else device.model} (IP: {ip})"
                )

            # Ensure full initialization by calling update
            await device.update()

            # Check if the device has emeter capability
            if device.has_emeter:
                logger.debug(f"Device {device.alias} supports emeter functionality.")
            else:
                logger.debug(
                    f"Device {device.alias} does not support emeter functionality."
                )

        except Exception as e:
            logger.error(f"Failed to connect to device {ip}: {e}")
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
        logger.debug(f"Fetched emeter data for device {device.model}")
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
        logger.debug(f"Fetched sysinfo for device {device.model}")
        return device.sys_info

    @staticmethod
    async def fetch_device_data(device):
        """
        Fetch both emeter and system information from a device, with logging.
        """
        await device.update()
        logger.debug(f"Fetched device data for {device.model}")
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

    @staticmethod
    async def disconnect_device(device):
        """
        Properly disconnect from a device using the official API.
        """
        if not device:
            return

        try:
            # Use the official disconnect method
            await device.disconnect()
            logger.debug(
                f"Disconnected from device {getattr(device, 'host', 'unknown')}"
            )
        except Exception as e:
            # Log but don't re-raise to avoid masking original errors
            logger.debug(
                f"Error disconnecting from {getattr(device, 'host', 'unknown')}: {e}"
            )
