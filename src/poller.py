import asyncio
import socket
from datetime import datetime, timedelta
from kasa import SmartStrip
from influxdb_storage import InfluxDBStorage
from config import Config


class Poller:
    def __init__(self, logger):
        self.logger = logger
        self.storage = InfluxDBStorage()

    async def periodic_emeter_fetch(self, devices):
        """
        Periodically fetch and store emeter data from all devices.
        Runs at the interval defined by the configuration.
        """
        while True:
            start_time = datetime.now()
            device_count = len(devices)
            self.logger.info(f"Starting emeter data fetch for {device_count} devices.")

            try:
                await asyncio.gather(
                    *[
                        self.fetch_and_store_emeter_data(ip, device)
                        for ip, device in devices.items()
                    ]
                )
            except Exception as e:
                self.logger.error(f"Error during emeter fetch: {e}")

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # Log a summary of the fetch cycle
            self.logger.info(
                f"Emeter data fetch completed for {device_count} devices in {elapsed:.2f} seconds."
            )

            if elapsed > Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL:
                self.logger.warning(
                    f"Emeter fetch took longer ({elapsed:.2f} seconds) than the configured interval of "
                    f"{Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL} seconds."
                )

            # Calculate the next fetch time and log it
            next_fetch_time = (
                datetime.now()
                + timedelta(
                    seconds=max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
                )
            ).strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"Next emeter data fetch will run at {next_fetch_time}.")

            # Sleep for the remaining time (if any) before the next cycle
            await asyncio.sleep(
                max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
            )

    async def periodic_sysinfo_fetch(self, devices):
        """
        Periodically fetch and store system info data from all devices.
        Runs at the interval defined by the configuration.
        """
        while True:
            start_time = datetime.now()
            device_count = len(devices)
            self.logger.info(f"Starting system info fetch for {device_count} devices.")

            try:
                await asyncio.gather(
                    *[
                        self.fetch_and_store_sysinfo(ip, device)
                        for ip, device in devices.items()
                    ]
                )
            except Exception as e:
                self.logger.error(f"Error during sysinfo fetch: {e}")

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # Log a summary of the fetch cycle
            self.logger.info(
                f"System info fetch completed for {device_count} devices in {elapsed:.2f} seconds."
            )

            if elapsed > Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL:
                self.logger.warning(
                    f"System info fetch took longer ({elapsed:.2f} seconds) than the configured interval of "
                    f"{Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL} seconds."
                )

            # Calculate the next fetch time and log it
            next_fetch_time = (
                datetime.now()
                + timedelta(
                    seconds=max(
                        0, Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed
                    )
                )
            ).strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"Next system info fetch will run at {next_fetch_time}.")

            # Sleep for the remaining time (if any) before the next cycle
            await asyncio.sleep(
                max(0, Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed)
            )

    async def fetch_and_store_emeter_data(self, ip, device):
        """
        Fetch and store emeter data for a specific device with retries and exponential backoff.
        """
        retries = 0
        device_name = self.get_device_name(device)
        hostname = socket.getfqdn(ip)

        while retries < Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
            try:
                await device.update()
                if isinstance(device, SmartStrip):
                    await self.process_smart_strip_data(ip, device)
                elif device.has_emeter:
                    await self.process_device_data(ip, device)
                self.logger.debug(
                    f"Successfully fetched emeter data for {device_name} (IP: {ip})"
                )
                break
            except Exception as e:
                self.logger.error(
                    f"Error fetching emeter data from {ip} (Device: {device_name}, Hostname: {hostname}): {e}. Retrying..."
                )
                retries += 1
                # Exponential backoff before retrying
                await asyncio.sleep(
                    Config.KASA_COLLECTOR_FETCH_RETRY_DELAY * (2**retries)
                )

            if retries == Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
                self.logger.warning(
                    f"Max retries reached for device {ip} (Device: {device_name}, Hostname: {hostname})"
                )

    async def process_smart_strip_data(self, ip, smart_strip):
        """
        Process emeter data for a smart strip and its child plugs.
        Stores the data in InfluxDB for the strip and each child plug.
        """
        try:
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
            self.logger.debug(
                f"Storing smart strip data for {smart_strip.alias} (IP: {ip})."
            )
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
                self.logger.debug(
                    f"Storing child plug data for {plug_alias} (IP: {ip})."
                )
                await self.storage.process_emeter_data({ip: child_data})
        except Exception as e:
            self.logger.error(f"Error processing smart strip data for {ip}: {e}")

    async def process_device_data(self, ip, device):
        """
        Process emeter data for a device and store it in InfluxDB.
        """
        try:
            emeter_data = {
                key: int(value) for key, value in device.emeter_realtime.items()
            }
            device_alias = device.alias if device.alias else device.host
            device_data = {
                "emeter": emeter_data,
                "alias": device_alias,
                "dns_name": socket.getfqdn(ip),
                "ip": ip,
                "equipment_type": "device",
            }
            self.logger.debug(f"Storing emeter data for {device_alias} (IP: {ip}).")
            await self.storage.process_emeter_data({ip: device_data})
        except Exception as e:
            self.logger.error(f"Error processing emeter data for {ip}: {e}")

    async def fetch_and_store_sysinfo(self, ip, device):
        """
        Fetch and store system info data for a device.
        """
        retries = 0
        device_name = self.get_device_name(device)
        hostname = socket.getfqdn(ip)

        while retries < Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
            try:
                await device.update()
                self.logger.debug(f"Fetched sysinfo for device {ip}: {device.sys_info}")
                sysinfo_data = {
                    "sysinfo": device.sys_info,
                    "device_alias": device_name,
                    "dns_name": hostname,
                    "ip": ip,
                    "equipment_type": "device",
                }
                self.logger.debug(f"Storing sysinfo data for {device_name} (IP: {ip})")
                await self.storage.process_sysinfo_data({ip: sysinfo_data})
                break
            except Exception as e:
                self.logger.error(
                    f"Error fetching sysinfo for {ip} (Device: {device_name}, Hostname: {hostname}): {e}"
                )
                retries += 1
                # Exponential backoff before retrying
                await asyncio.sleep(
                    Config.KASA_COLLECTOR_FETCH_RETRY_DELAY * (2**retries)
                )

            if retries == Config.KASA_COLLECTOR_FETCH_MAX_RETRIES:
                self.logger.warning(
                    f"Max retries reached for device {ip} (Device: {device_name}, Hostname: {hostname})"
                )

    @staticmethod
    def format_duration(seconds):
        """
        Format a duration given in seconds into a string with minutes and seconds.
        """
        minutes, seconds = divmod(int(seconds), 60)
        return (
            f"{minutes} minutes, {seconds} seconds" if minutes else f"{seconds} seconds"
        )

    @staticmethod
    def get_device_name(device):
        """
        Helper function to fetch the correct alias from the device.
        """
        if hasattr(device, "alias") and device.alias:
            return device.alias
        return device.host if hasattr(device, "host") else "Unknown"
