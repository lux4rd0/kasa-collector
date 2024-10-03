import socket
import asyncio
from kasa_api import KasaAPI
from config import Config
from datetime import datetime, timedelta


class DeviceManager:
    def __init__(self, logger):
        """
        Initialize the DeviceManager with an empty devices dictionary and device hosts.
        """
        self.logger = logger
        self.devices = {}  # All devices (manual and discovered)
        self.emeter_devices = {}  # Only devices with emeter functionality
        self.polling_devices = {}  # Devices that need polling (can be expanded)

        # Initialize manual devices if provided
        self.device_hosts = []
        if Config.KASA_COLLECTOR_DEVICE_HOSTS:
            self.device_hosts = [
                ip.strip() for ip in Config.KASA_COLLECTOR_DEVICE_HOSTS.split(",")
            ]

        # Initialize credentials if provided
        self.tplink_username = Config.KASA_COLLECTOR_TPLINK_USERNAME
        self.tplink_password = Config.KASA_COLLECTOR_TPLINK_PASSWORD

        # Configurable retry and timeout settings for device authentication
        self.max_retries = Config.KASA_COLLECTOR_AUTH_MAX_RETRIES
        self.timeout_seconds = Config.KASA_COLLECTOR_AUTH_TIMEOUT

    async def initialize_manual_devices(self):
        """
        Initialize manual devices based on IPs or hostnames specified in the configuration.
        Fetch and authenticate devices manually specified in the configuration file.
        """
        for ip in self.device_hosts:
            try:
                device = await KasaAPI.get_device(
                    ip, self.tplink_username, self.tplink_password
                )
                self.devices[ip] = device
                # Check and store devices based on emeter capabilities
                self._check_and_add_emeter_device(ip, device)
                device_name = self.get_device_name(device)
                self.logger.info(
                    f"Manually added device: {device_name} (IP/Hostname: {ip}, Hostname: {socket.getfqdn(ip)})"
                )
            except Exception as e:
                self.logger.error(f"Failed to add manual device {ip}: {e}")

    async def discover_devices(self):
        """
        Discover Kasa devices on the network and authenticate them.
        Adds discovered devices to the list of managed devices.
        """
        if not Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
            self.logger.info("Auto-discovery is disabled. Skipping device discovery.")
            return

        self.logger.info("Starting device discovery...")

        # Track the start time for measuring how long the discovery takes
        start_time = datetime.now()

        # Discover devices
        discovered_devices = await KasaAPI.discover_devices()
        num_discovered = len(discovered_devices)
        self.logger.info(f"Discovered {num_discovered} devices.")

        # List to hold async tasks for parallel execution
        auth_tasks = []

        for ip, device in discovered_devices.items():
            if ip not in self.devices:  # Only authenticate new devices
                auth_tasks.append(self._authenticate_device_with_retry(ip, device))
                device_name = self.get_device_name(device)
                dns_name = socket.getfqdn(ip)
                self.logger.debug(
                    f"Device discovered: Alias: {device_name}, IP: {ip}, DNS: {dns_name}"
                )

        # Run all authentication tasks concurrently
        await asyncio.gather(*auth_tasks)

        # Track the time taken for discovery and authentication
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()
        self.logger.info(
            f"Device discovery and authentication completed in {elapsed_time:.2f} seconds."
        )

        # Calculate the time of the next discovery based on the interval and log it
        next_discovery_interval = Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL
        next_discovery_time = (
            datetime.now() + timedelta(seconds=next_discovery_interval)
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"Next device discovery will run at {next_discovery_time}.")

    async def _authenticate_device_with_retry(self, ip, device):
        """
        Authenticate the device with retries and timeout. If authentication succeeds,
        add the device to the managed devices list.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # Add timeout for authentication process
                authenticated_device = await asyncio.wait_for(
                    KasaAPI.get_device(ip, self.tplink_username, self.tplink_password),
                    timeout=self.timeout_seconds,
                )

                # If authentication is successful, store the device
                self.devices[ip] = authenticated_device
                self._check_and_add_emeter_device(ip, authenticated_device)
                device_name = self.get_device_name(authenticated_device)
                self.logger.info(
                    f"Authenticated device: {device_name} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                )
                return  # Exit if authentication succeeds

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Timeout while authenticating device {ip}. Retrying... {attempt}/{self.max_retries}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to authenticate device {ip}: {e}. Retrying... {attempt}/{self.max_retries}"
                )

        # After max retries, log failure
        self.logger.error(
            f"Failed to authenticate device {ip} after {self.max_retries} attempts."
        )
        self.devices[ip] = device  # Store the unauthenticated device
        self._check_and_add_emeter_device(ip, device)
        device_name = self.get_device_name(device)
        self.logger.info(
            f"Storing unauthenticated device: {device_name} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
        )

    async def remove_missing_devices(self, discovered_devices):
        """
        Remove devices that are missing from the discovered list if Config.KASA_COLLECTOR_KEEP_MISSING_DEVICES is False.
        """
        if not Config.KASA_COLLECTOR_KEEP_MISSING_DEVICES:
            for ip in list(self.devices.keys()):
                if ip not in discovered_devices:
                    missing_device = self.devices.pop(ip)
                    device_name = self.get_device_name(missing_device)
                    self.emeter_devices.pop(
                        ip, None
                    )  # Remove from emeter devices if applicable
                    self.polling_devices.pop(
                        ip, None
                    )  # Remove from polling devices if applicable
                    self.logger.info(
                        f"Device missing: {device_name} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                    )

    def _check_and_add_emeter_device(self, ip, device):
        """
        Check if the device has emeter capabilities and add it to the emeter_devices list if it does.
        Also adds the device to polling_devices if it qualifies.
        """
        if hasattr(device, "has_emeter") and device.has_emeter:
            self.emeter_devices[ip] = device
            self.polling_devices[
                ip
            ] = device  # Initially, only emeter devices get polled

            # Log device emeter functionality as DEBUG
            device_name = self.get_device_name(device)
            self.logger.debug(
                f"Device {device_name} (IP: {ip}) supports emeter functionality."
            )
        else:
            device_name = self.get_device_name(device)
            self.logger.debug(
                f"Device {device_name} (IP: {ip}) does not support emeter functionality."
            )

    async def get_device_list(self):
        """
        Return the complete list of discovered and manually added devices.
        """
        return self.devices

    async def get_emeter_device_list(self):
        """
        Return the list of devices that have emeter capabilities.
        """
        return self.emeter_devices

    async def get_polling_device_list(self):
        """
        Return the list of devices that should be polled.
        """
        return self.polling_devices

    @staticmethod
    def get_device_name(device):
        """
        Helper function to fetch the correct alias from the device object.
        """
        if hasattr(device, "alias") and device.alias:
            return device.alias
        return device.host if hasattr(device, "host") else "Unknown"
