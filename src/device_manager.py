import asyncio
from kasa_api import KasaAPI
from config import Config
from datetime import datetime, timedelta
from dns_cache import get_hostname_cached
from utils import get_device_name


class DeviceManager:
    def __init__(self, logger):
        """
        Initialize the DeviceManager with an empty devices dictionary and device hosts.
        """
        self.logger = logger
        self.devices = {}  # All devices (manual and discovered)
        self.emeter_devices = {}  # Only devices with emeter functionality
        self.polling_devices = {}  # Devices that need polling (can be expanded)
        self.first_discovery_complete = False  # Track if we've done initial discovery

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
        Initialize manual devices based on IPs or hostnames in the config.
        Fetch and authenticate devices manually specified in the config.
        """
        if not self.device_hosts:
            return
            
        async def add_manual_device(ip):
            """Add a single manual device."""
            try:
                device = await KasaAPI.get_device(
                    ip, self.tplink_username, self.tplink_password
                )
                self.devices[ip] = device
                # Check and store devices based on emeter capabilities
                self._check_and_add_emeter_device(ip, device)
                device_name = get_device_name(device)
                hostname = await get_hostname_cached(ip)
                # Always show manually added devices at INFO level
                self.logger.info(
                    f"Manually added device: {device_name} (IP: {ip}, Host: {hostname})"
                )
            except Exception as e:
                self.logger.error(f"Failed to add manual device {ip}: {e}")
        
        # Process all manual devices in parallel
        async with asyncio.TaskGroup() as tg:
            for ip in self.device_hosts:
                tg.create_task(add_manual_device(ip))

    async def discover_devices(self):
        """
        Discover Kasa devices on the network and authenticate them.
        Adds discovered devices to the list of managed devices.
        """
        if not Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
            self.logger.debug("Auto-discovery is disabled. Skipping device discovery.")
            return

        # Log at INFO level for first discovery, DEBUG for subsequent
        if not self.first_discovery_complete:
            self.logger.info("Starting initial device discovery...")
        else:
            self.logger.debug("Starting device discovery...")

        # Track the start time for measuring how long the discovery takes
        start_time = datetime.now()

        # Discover devices
        discovered_devices = await KasaAPI.discover_devices()
        num_discovered = len(discovered_devices)
        if num_discovered > 0:
            self.logger.info(f"Discovered {num_discovered} devices.")
        else:
            self.logger.warning("No devices discovered on the network.")

        # List to hold async tasks for parallel execution
        auth_tasks = []

        for ip, device in discovered_devices.items():
            if ip not in self.devices:  # Only authenticate new devices
                auth_tasks.append(self._authenticate_device_with_retry(ip, device))
                device_name = get_device_name(device)
                dns_name = await get_hostname_cached(ip)
                self.logger.debug(
                    f"Device discovered: {device_name}, IP: {ip}, DNS: {dns_name}"
                )

        # Run all authentication tasks concurrently
        if auth_tasks:
            try:
                async with asyncio.TaskGroup() as tg:
                    for task_coro in auth_tasks:
                        tg.create_task(task_coro)
            except* Exception as eg:
                for exc in eg.exceptions:
                    self.logger.error(f"Error during device authentication: {exc}")

        # Track the time taken for discovery and authentication
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        # Show completion at INFO level for first discovery
        if not self.first_discovery_complete:
            self.logger.info(
                f"Initial device discovery completed in {elapsed_time:.2f} seconds."
            )
            self.logger.info(
                f"Found {len(self.emeter_devices)} devices with "
                f"energy monitoring capabilities."
            )
        else:
            self.logger.debug(
                f"Device discovery completed in {elapsed_time:.2f} seconds."
            )

        # Calculate the time of the next discovery based on the interval and log it
        next_discovery_interval = Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL
        next_discovery_time = (
            datetime.now() + timedelta(seconds=next_discovery_interval)
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.logger.debug(f"Next device discovery will run at {next_discovery_time}.")

        # Mark first discovery as complete
        self.first_discovery_complete = True

    async def _authenticate_device_with_retry(self, ip, discovered_device):
        """
        Authenticate the device with retries and timeout. If authentication succeeds,
        add the device to the managed devices list.
        """
        # First try to use the discovered device directly
        if discovered_device:
            success = await KasaAPI.authenticate_discovered_device(
                discovered_device, self.tplink_username, self.tplink_password
            )
            if success:
                self.devices[ip] = discovered_device
                self._check_and_add_emeter_device(ip, discovered_device)
                device_name = get_device_name(discovered_device)
                hostname = await get_hostname_cached(ip)
                # Show details on first run at INFO level
                if not self.first_discovery_complete:
                    self.logger.info(
                        f"Authenticated device: {device_name} "
                        f"(IP: {ip}, Host: {hostname})"
                    )
                else:
                    self.logger.debug(
                        f"Authenticated device: {device_name} "
                        f"(IP: {ip}, Host: {hostname})"
                    )
                return
            else:
                # If it's a SmartDevice that failed, don't try legacy connection
                if discovered_device.__class__.__name__ == "SmartDevice":
                    self.logger.warning(
                        f"SmartDevice at {ip} couldn't be connected. "
                        f"This device may require newer protocol support."
                    )
                    return

        # Fallback to creating new connection if discovered device fails
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
                device_name = get_device_name(authenticated_device)
                hostname = await get_hostname_cached(ip)
                # Show details on first run at INFO level
                if not self.first_discovery_complete:
                    self.logger.info(
                        f"Authenticated device: {device_name} "
                        f"(IP: {ip}, Host: {hostname})"
                    )
                else:
                    self.logger.debug(
                        f"Authenticated device: {device_name} "
                        f"(IP: {ip}, Host: {hostname})"
                    )
                return  # Exit if authentication succeeds

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Timeout authenticating {ip}. Retry {attempt}/{self.max_retries}"
                )
            except Exception as e:
                # Check if it's a credentials error specifically
                error_msg = str(e)
                if (
                    "credentials" in error_msg.lower()
                    or "authentication" in error_msg.lower()
                    or "challenge" in error_msg.lower()
                ):
                    self.logger.warning(
                        f"Device {ip} requires authentication. "
                        f"Attempting without credentials..."
                    )
                    # Don't retry for credential errors
                    break
                elif "connection reset" in error_msg.lower():
                    self.logger.warning(
                        f"Device {ip} reset connection. "
                        f"It may be offline or unreachable. "
                        f"Retry {attempt}/{self.max_retries}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to auth {ip}: {e}. Retry {attempt}/{self.max_retries}"
                    )

        # After max retries or credential failure, try without authentication
        try:
            # Try to connect without credentials as some devices may not require them
            unauthenticated_device = await KasaAPI.get_device(ip)
            self.devices[ip] = unauthenticated_device
            self._check_and_add_emeter_device(ip, unauthenticated_device)
            device_name = get_device_name(unauthenticated_device)
            hostname = await get_hostname_cached(ip)
            # Show details on first run at INFO level
            if not self.first_discovery_complete:
                self.logger.info(
                    f"Connected without auth: {device_name} "
                    f"(IP: {ip}, Host: {hostname})"
                )
            else:
                self.logger.debug(
                    f"Connected without auth: {device_name} "
                    f"(IP: {ip}, Host: {hostname})"
                )
        except Exception as e:
            error_msg = str(e)
            if "connection reset" in error_msg.lower():
                self.logger.error(
                    f"Device {ip} is unreachable (connection reset). "
                    "It may be offline, blocked by firewall, or have networking issues."
                )
            elif "challenge" in error_msg.lower():
                self.logger.error(
                    f"Device {ip} requires TP-Link cloud credentials. "
                    "Please set KASA_COLLECTOR_TPLINK_USERNAME and "
                    "KASA_COLLECTOR_TPLINK_PASSWORD."
                )
            else:
                self.logger.error(f"Failed to connect to device {ip}: {e}")

    async def remove_missing_devices(self, discovered_devices):
        """
        Remove missing devices if KEEP_MISSING_DEVICES is False.
        """
        if not Config.KASA_COLLECTOR_KEEP_MISSING_DEVICES:
            for ip in list(self.devices.keys()):
                if ip not in discovered_devices:
                    missing_device = self.devices.pop(ip)
                    device_name = get_device_name(missing_device)
                    self.emeter_devices.pop(
                        ip, None
                    )  # Remove from emeter devices if applicable
                    self.polling_devices.pop(
                        ip, None
                    )  # Remove from polling devices if applicable
                    hostname = await get_hostname_cached(ip)
                    self.logger.warning(
                        f"Device missing: {device_name} (IP: {ip}, Host: {hostname})"
                    )

    def _check_and_add_emeter_device(self, ip, device):
        """
        Check if device has emeter capabilities and add to emeter_devices.
        Also adds the device to polling_devices if it qualifies.
        """
        if hasattr(device, "has_emeter") and device.has_emeter:
            self.emeter_devices[ip] = device
            self.polling_devices[ip] = (
                device  # Initially, only emeter devices get polled
            )

            # Log device emeter functionality as DEBUG
            device_name = get_device_name(device)
            self.logger.debug(
                f"Device {device_name} (IP: {ip}) supports emeter functionality."
            )
        else:
            device_name = get_device_name(device)
            self.logger.debug(f"Device {device_name} (IP: {ip}) no emeter support.")

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

    async def disconnect_all_devices(self):
        """
        Disconnect from all managed devices during shutdown.
        """
        self.logger.info(f"Disconnecting from {len(self.devices)} devices...")
        disconnect_tasks = []

        for ip, device in self.devices.items():
            try:
                disconnect_tasks.append(KasaAPI.disconnect_device(device))
            except Exception as e:
                self.logger.debug(f"Error preparing disconnect for {ip}: {e}")

        if disconnect_tasks:
            # Disconnect all devices concurrently
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self.devices.clear()
        self.emeter_devices.clear()
        self.polling_devices.clear()
        self.logger.info("All devices disconnected")
