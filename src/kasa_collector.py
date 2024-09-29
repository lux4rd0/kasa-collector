import asyncio
import logging
from datetime import datetime, timedelta
import socket
from kasa_api import KasaAPI
from influxdb_storage import InfluxDBStorage
from config import Config
from kasa import SmartStrip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("KasaCollector")
logger.setLevel(Config.KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR)


class KasaCollector:
    def __init__(self):
        """
        Initialize the KasaCollector with a storage instance and an empty devices dictionary.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(Config.KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR)
        self.storage = InfluxDBStorage()
        self.devices = {}

        # Initialize manual devices if provided
        self.device_hosts = []
        if Config.KASA_COLLECTOR_DEVICE_HOSTS:
            self.device_hosts = [
                ip.strip() for ip in Config.KASA_COLLECTOR_DEVICE_HOSTS.split(",")
            ]

        # Initialize credentials if provided
        self.tplink_username = Config.KASA_COLLECTOR_TPLINK_USERNAME
        self.tplink_password = Config.KASA_COLLECTOR_TPLINK_PASSWORD

    async def initialize_manual_devices(self):
        """
        Initialize manual devices based on the IPs or hostnames specified in the configuration.
        """
        for ip in self.device_hosts:
            try:
                device = await KasaAPI.get_device(
                    ip, self.tplink_username, self.tplink_password
                )

                # Log detailed device information
                self.logger.debug(f"Device details for {ip}: {device.__dict__}")

                # Check and set alias, log for clarity
                device_alias = device.alias if device.alias else device.host
                self.devices[ip] = device
                self.logger.info(
                    f"Manually added device: {device_alias} (IP/Hostname: {ip}, Hostname: {socket.getfqdn(ip)})"
                )
            except Exception as e:
                self.logger.error(f"Failed to add manual device {ip}: {e}")

    async def discover_devices(self):
        """
        Discover Kasa devices on the network and merge with existing devices.
        """
        if not Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
            self.logger.info("Auto-discovery is disabled. Skipping device discovery.")
            return

        discovered_devices = await KasaAPI.discover_devices()
        self.logger.info(
            f"Discovered {len(discovered_devices)} devices: {discovered_devices}"
        )

        # Merge auto-discovered devices without overwriting manual devices
        for ip, device in discovered_devices.items():
            if ip not in self.devices:
                self.devices[ip] = device
                self.logger.info(
                    f"Auto-discovered new device: {device.alias} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                )
            else:
                self.logger.info(
                    f"Device {device.alias} (IP: {ip}) already initialized manually."
                )

    async def start(self):
        """
        Start the KasaCollector by initializing manual devices, discovering devices,
        and starting periodic tasks.
        """
        # Initialize manual devices first
        await self.initialize_manual_devices()

        # Perform device discovery if auto-discovery is enabled
        if Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
            await self.discover_devices()

        # Start periodic tasks
        asyncio.create_task(self.periodic_fetch())
        asyncio.create_task(self.periodic_discover())
        asyncio.create_task(self.periodic_sysinfo_fetch())

    async def periodic_discover(self):
        """
        Periodically discover devices on the network, respecting existing manual devices.
        """
        while True:
            await self.discover_devices()
            await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)

    async def fetch_and_store_data(self):
        """
        Fetch emeter and system info data from each device and store the data in InfluxDB.
        """
        for ip, device in self.devices.items():
            try:
                # Fetch device data and log the response
                data = await KasaAPI.fetch_device_data(device)
                self.logger.debug(f"Fetched data for device {ip}: {data}")

                # Log current aliases before using them
                self.logger.debug(f"Pre-fetch device alias: {device.alias}, IP: {ip}")

                # Re-fetch alias to ensure it's updated correctly
                updated_alias = device.alias if device.alias else device.host
                self.logger.debug(f"Post-fetch device alias: {updated_alias}, IP: {ip}")

                # Store emeter and sysinfo data
                self.logger.debug(
                    f"Storing emeter data for {updated_alias}: {data['emeter']}"
                )
                await self.storage.write_data(
                    "kasa_device",
                    data["emeter"],
                    {"ip": ip, "device_alias": updated_alias},
                )

                self.logger.debug(
                    f"Storing sysinfo data for {updated_alias}: {data['sys_info']}"
                )
                await self.storage.write_data(
                    "kasa_sysinfo",
                    data["sys_info"],
                    {"ip": ip, "device_alias": updated_alias},
                )

                if Config.KASA_COLLECTOR_WRITE_TO_FILE:
                    await self.storage.write_to_json(
                        data, Config.KASA_COLLECTOR_OUTPUT_DIR
                    )
            except Exception as e:
                self.logger.error(f"Failed to fetch data from device {ip}: {e}")

    async def periodic_fetch(self):
        """
        Periodically fetch and store data from all devices.
        """
        while True:
            await self.fetch_and_store_data()
            await asyncio.sleep(Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL)

    async def fetch_and_send_emeter_data(self, ip, device):
        """
        Fetch and send emeter data from a device. Retry if necessary.
        """
        retries = 0
        alias = device.alias if device.alias else device.host
        hostname = socket.getfqdn(ip)

        while retries < Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
            try:
                await device.update()
                if isinstance(device, SmartStrip):
                    await self.process_smart_strip_data(ip, device)
                elif device.has_emeter:
                    await self.process_device_data(ip, device)
                break  # Break the loop if successful
            except Exception as e:
                self.logger.error(
                    f"Error updating device {ip} (Alias: {alias}, Hostname: {hostname}): {e}"
                )
                retries += 1
                await asyncio.sleep(Config.KASA_COLLECTOR_FETCH_RETRY_DELAY)

            if retries == Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
                self.logger.warning(
                    f"Max retries reached for device {ip} (Alias: {alias}, Hostname: {hostname})"
                )

    async def process_smart_strip_data(self, ip, smart_strip):
        """
        Process emeter data for a smart strip and its child plugs.
        """
        smart_strip_emeter_data = {
            key: int(value) for key, value in smart_strip.emeter_realtime.items()
        }
        smart_strip_data = {
            "emeter": smart_strip_emeter_data,
            "alias": smart_strip.alias,
            "dns_name": socket.getfqdn(ip),
            "ip": ip,
            "equipment_type": "device",
        }
        await self.storage.process_emeter_data({ip: smart_strip_data})

        for child in smart_strip.children:
            await child.update()
            plug_alias = f"{child.alias}"
            child_emeter_data = {
                key: int(value) for key, value in child.emeter_realtime.items()
            }
            child_data = {
                "emeter": child_emeter_data,
                "alias": smart_strip.alias,
                "plug_alias": plug_alias,
                "dns_name": socket.getfqdn(ip),
                "ip": ip,
                "equipment_type": "plug",
            }
            await self.storage.process_emeter_data({ip: child_data})

    async def process_device_data(self, ip, device):
        """
        Process emeter data for a device.
        """
        emeter_data = {key: int(value) for key, value in device.emeter_realtime.items()}
        device_alias = device.alias if device.alias else device.host

        device_data = {
            "emeter": emeter_data,
            "alias": device_alias,
            "dns_name": socket.getfqdn(ip),
            "ip": ip,
            "equipment_type": "device",
        }
        await self.storage.process_emeter_data({ip: device_data})

    async def fetch_and_send_sysinfo(self, device):
        """
        Fetch and send system info data from a device. Retry if necessary.
        """
        ip = device.host
        alias = (
            device.alias if device.alias else device.host
        )  # Use alias or host as fallback
        hostname = None  # Initialize hostname to avoid uninitialized variable error
        retries = 0

        while retries < Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
            try:
                await device.update()
                hostname = socket.getfqdn(
                    ip
                )  # Get the hostname after successful update

                # Log the sysinfo and alias
                self.logger.debug(f"Fetched sysinfo for device {ip}: {device.sys_info}")
                self.logger.debug(f"Pre-fetch Alias: {alias}, Hostname: {hostname}")

                # Re-fetch alias to ensure it's updated correctly
                alias = device.alias if device.alias else device.host
                self.logger.debug(f"Post-fetch Alias: {alias}, Hostname: {hostname}")

                sysinfo_data = {
                    "sysinfo": device.sys_info,
                    "device_alias": alias,  # Use the updated alias
                    "dns_name": hostname,
                    "ip": ip,
                    "equipment_type": "device",
                }
                # Log the data being sent to InfluxDBStorage
                self.logger.debug(f"Storing sysinfo data for {ip}: {sysinfo_data}")
                await self.storage.process_sysinfo_data({ip: sysinfo_data})
                break  # Break the loop if successful
            except Exception as e:
                self.logger.error(
                    f"Error fetching sysinfo for device {ip} (Alias: {alias}, Hostname: {hostname}): {e}"
                )
                retries += 1
                await asyncio.sleep(Config.KASA_COLLECTOR_FETCH_RETRY_DELAY)

            if retries == Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
                self.logger.warning(
                    f"Max retries reached for device {ip} (Alias: {alias}, Hostname: {hostname})"
                )

    async def periodic_fetch(self):
        """
        Periodically fetch and process emeter data from all devices.
        """
        while True:
            start_time = datetime.now()
            device_count = len(self.devices)
            self.logger.info(f"Starting periodic_fetch for {device_count} devices")

            # Use asyncio.gather to concurrently fetch data from all devices
            await asyncio.gather(
                *[
                    self.fetch_and_send_emeter_data(ip, device)
                    for ip, device in self.devices.items()
                ]
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # Check if the fetch operation took longer than the defined interval
            if elapsed > Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL:
                self.logger.warning(
                    f"Fetch operation took {format_duration(elapsed)}, which is longer than the set interval of {Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL} seconds."
                )

            # Calculate next run time and log the details
            next_run = end_time + timedelta(
                seconds=max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
            )
            self.logger.info(
                f"Finished periodic_fetch for {device_count} devices. "
                f"Duration: {format_duration(elapsed)}. Next run in "
                f"{format_duration(Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)} "
                f"at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Sleep until the next scheduled fetch time
            await asyncio.sleep(
                max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
            )

    async def periodic_sysinfo_fetch(self):
        """
        Periodically fetch and process system info data from all devices.
        """
        while True:
            start_time = datetime.now()
            device_count = len(self.devices)
            self.logger.info(
                f"Starting periodic_sysinfo_fetch for {device_count} devices"
            )

            await asyncio.gather(
                *[
                    self.fetch_and_send_sysinfo(device)
                    for device in self.devices.values()
                ]
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            if elapsed > Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL:
                self.logger.warning(
                    f"Sysinfo fetch operation took {format_duration(elapsed)}, which is longer than the set interval of {Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL} seconds."
                )

            next_run = end_time + timedelta(
                seconds=max(0, Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed)
            )
            self.logger.info(
                f"Finished periodic_sysinfo_fetch for {device_count} devices. Duration: {format_duration(elapsed)}. Next run in {format_duration(Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed)} at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            await asyncio.sleep(
                max(0, Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed)
            )

    async def periodic_discover_devices(self, lock):
        """
        Periodically discover devices on the network.
        """
        first_interval = True
        while True:
            start_time = datetime.now()
            sleep_time = Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL

            if not first_interval:
                self.logger.info("Starting periodic_discover_devices")
                discovered_devices = await KasaAPI.discover_devices()
                new_devices_list = []
                missing_devices_list = []

                async with lock:
                    for ip, device in discovered_devices.items():
                        if ip not in self.devices:
                            self.devices[ip] = device
                            new_devices_list.append(f"\t{device.alias} (IP: {ip})")
                            self.logger.info(
                                f"New device discovered: {device.alias} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                            )

                    if not Config.KASA_COLLECTOR_KEEP_MISSING_DEVICES:
                        for ip in list(self.devices.keys()):
                            if ip not in discovered_devices:
                                missing_device = self.devices.pop(ip)
                                missing_devices_list.append(
                                    f"\t{missing_device.alias} (IP: {ip})"
                                )
                                self.logger.info(
                                    f"Device missing: {missing_device.alias} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                                )

                total_device_count = len(self.devices)
                new_devices_info = (
                    ", ".join(new_devices_list) if new_devices_list else "None"
                )
                missing_devices_info = (
                    ", ".join(missing_devices_list) if missing_devices_list else "None"
                )

                end_time = datetime.now()
                elapsed_time = (end_time - start_time).total_seconds()
                sleep_time = max(
                    0, Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL - elapsed_time
                )
                next_run_time = datetime.now() + timedelta(seconds=sleep_time)
                next_run_time_str = next_run_time.strftime("%Y-%m-%d %H:%M:%S")

                self.logger.info(
                    f"Periodic device discovery completed in {format_duration(elapsed_time)}. Total devices: {total_device_count}, New devices: {len(new_devices_list)} ({new_devices_info}), Missing devices: {len(missing_devices_list)} ({missing_devices_info}). Next discovery in {format_duration(sleep_time)}, at {next_run_time_str}."
                )
            else:
                current_time = datetime.now()
                next_run_time = current_time + timedelta(seconds=sleep_time)
                next_run_time_str = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self.logger.info(
                    f"Next discovery in {format_duration(sleep_time)}, at {next_run_time_str}."
                )

            first_interval = False
            await asyncio.sleep(sleep_time)


def format_duration(seconds):
    """
    Format a duration given in seconds into a string with minutes and seconds.
    """
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes} minutes, {seconds} seconds" if minutes else f"{seconds} seconds"


async def main():
    """
    Main function to start the KasaCollector and handle discovery, data fetch, and sysinfo fetch tasks.
    """
    lock = asyncio.Lock()
    logger.info("Starting Kasa Collector")

    # Initialize the KasaCollector instance
    collector = KasaCollector()

    try:
        # Initialize manual devices first
        await collector.initialize_manual_devices()

        # Perform initial device discovery if auto-discovery is enabled
        if Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
            logger.info("Starting initial Kasa device discovery...")
            start_time_discovery = datetime.now()
            try:
                await collector.discover_devices()
            except Exception as e:
                logger.error(f"Error during initial device discovery: {e}")

            end_time_discovery = datetime.now()
            elapsed_discovery = (
                end_time_discovery - start_time_discovery
            ).total_seconds()
            logger.info(
                f"Initial device discovery completed in {format_duration(elapsed_discovery)}"
            )
        else:
            logger.info(
                "Auto-discovery is disabled. Only using manually specified devices."
            )

        # Start periodic tasks
        discovery_task = asyncio.create_task(collector.periodic_discover())
        data_fetch_task = asyncio.create_task(collector.periodic_fetch())
        sysinfo_fetch_task = asyncio.create_task(collector.periodic_sysinfo_fetch())

        await asyncio.gather(discovery_task, data_fetch_task, sysinfo_fetch_task)
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
        tasks = [discovery_task, data_fetch_task, sysinfo_fetch_task]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Tasks successfully cancelled")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Kasa Device Collector stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Received KeyboardInterrupt. Exiting gracefully.")
