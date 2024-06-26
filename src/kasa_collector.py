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

    async def discover_devices(self):
        """
        Discover Kasa devices on the network and store them in the devices attribute.
        """
        self.devices = await KasaAPI.discover_devices()
        self.logger.info(f"Discovered {len(self.devices)} devices")

    async def fetch_and_store_data(self):
        """
        Fetch emeter and system info data from each device and store the data in InfluxDB.
        """
        for ip, device in self.devices.items():
            try:
                data = await KasaAPI.fetch_device_data(device)
                await self.storage.write_data("kasa_device", data["emeter"], {"ip": ip})
                await self.storage.write_data(
                    "kasa_sysinfo", data["sys_info"], {"ip": ip}
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

    async def periodic_discover(self):
        """
        Periodically discover devices on the network.
        """
        while True:
            await self.discover_devices()
            await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)

    async def start(self):
        """
        Start the KasaCollector by discovering devices and starting periodic tasks.
        """
        await self.discover_devices()
        asyncio.create_task(self.periodic_fetch())
        asyncio.create_task(self.periodic_discover())

    async def fetch_and_send_emeter_data(self, ip, device):
        """
        Fetch and send emeter data from a device. Retry if necessary.
        """
        retries = 0
        alias = "Unknown"
        hostname = "Unknown"

        try:
            alias = device.alias
            hostname = socket.getfqdn(ip)
        except Exception as e:
            self.logger.error(
                f"Error retrieving alias or hostname for device {ip}: {e}"
            )

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
        device_data = {
            "emeter": emeter_data,
            "alias": device.alias,
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
        alias = "Unknown"
        hostname = "Unknown"
        retries = 0

        try:
            alias = device.alias
            hostname = socket.getfqdn(ip)
        except Exception as e:
            self.logger.error(
                f"Error retrieving alias or hostname for device {ip}: {e}"
            )

        while retries < Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
            try:
                await device.update()
                sysinfo = {"sysinfo": device.sys_info}
                await self.storage.process_sysinfo_data({ip: sysinfo})
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

            await asyncio.gather(
                *[
                    self.fetch_and_send_emeter_data(ip, device)
                    for ip, device in self.devices.items()
                ]
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            if elapsed > Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL:
                self.logger.warning(
                    f"Fetch operation took {format_duration(elapsed)}, which is longer than the set interval of {Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL} seconds."
                )

            next_run = end_time + timedelta(
                seconds=max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
            )
            self.logger.info(
                f"Finished periodic_fetch for {device_count} devices. Duration: {format_duration(elapsed)}. Next run in {format_duration(Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)} at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )

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

    try:
        logger.info("Starting Kasa device discovery...")
        start_time_discovery = datetime.now()
        try:
            devices = await KasaAPI.discover_devices()
        except Exception as e:
            logger.error(f"Error during device discovery: {e}")
            devices = {}

        if devices:
            device_details = [
                f"\t{device.alias} (IP: {ip}, Hostname: {socket.getfqdn(ip)})"
                for ip, device in devices.items()
            ]
            device_details_str = "\n".join(device_details)
            logger.info(
                f"Initial device discovery found {len(devices)} devices:\n{device_details_str}"
            )
        else:
            logger.info("No devices found in initial discovery")

        end_time_discovery = datetime.now()
        elapsed_discovery = (end_time_discovery - start_time_discovery).total_seconds()
        logger.info(
            f"Device discovery at startup took {format_duration(elapsed_discovery)}"
        )

        collector = KasaCollector()
        collector.devices = devices

        discovery_task = asyncio.create_task(collector.periodic_discover_devices(lock))
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
