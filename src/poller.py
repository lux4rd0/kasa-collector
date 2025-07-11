import asyncio
from datetime import datetime, timedelta
from kasa import SmartStrip
from influxdb_storage import InfluxDBStorage
from config import Config
from dns_cache import get_hostname_cached
from utils import async_retry, DeviceContext


class Poller:
    def __init__(self, logger):
        self.logger = logger
        try:
            self.storage = InfluxDBStorage()
        except SystemExit:
            # InfluxDBStorage already logged detailed error messages
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize storage backend: {e}")
            raise SystemExit(1)

    async def periodic_emeter_fetch(self, devices):
        """
        Periodically fetch and store emeter data from all devices.
        Runs at the interval defined by the configuration.
        """
        while True:
            start_time = datetime.now()
            device_count = len(devices)
            self.logger.debug(f"Starting emeter data fetch for {device_count} devices.")

            try:
                async with asyncio.TaskGroup() as tg:
                    for ip, device in devices.items():
                        tg.create_task(self.fetch_and_store_emeter_data(ip, device))
            except* (ConnectionError, TimeoutError, OSError) as eg:
                for exc in eg.exceptions:
                    self.logger.error(f"Network error during emeter fetch: {exc}")
            except* Exception as eg:
                for exc in eg.exceptions:
                    if isinstance(exc, asyncio.CancelledError):
                        self.logger.info("Emeter fetch task was cancelled")
                        raise exc
                    else:
                        self.logger.error(
                            f"Unexpected error during emeter fetch: {exc}"
                        )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # Log a summary of the fetch cycle
            if (
                elapsed > Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL * 0.8
            ):  # Log if taking >80% of interval
                self.logger.warning(
                    f"Emeter data fetch completed for {device_count} devices "
                    f"in {elapsed:.2f} seconds (approaching interval limit)."
                )
            else:
                self.logger.debug(
                    f"Emeter data fetch completed for {device_count} devices "
                    f"in {elapsed:.2f} seconds."
                )

            if elapsed > Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL:
                self.logger.warning(
                    f"Emeter fetch took longer ({elapsed:.2f} seconds) than "
                    f"the configured interval of "
                    f"{Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL} seconds."
                )

            # Calculate the next fetch time and log it
            next_fetch_time = (
                datetime.now()
                + timedelta(
                    seconds=max(0, Config.KASA_COLLECTOR_DATA_FETCH_INTERVAL - elapsed)
                )
            ).strftime("%Y-%m-%d %H:%M:%S")
            self.logger.debug(f"Next emeter data fetch will run at {next_fetch_time}.")

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
            self.logger.debug(f"Starting system info fetch for {device_count} devices.")

            try:
                async with asyncio.TaskGroup() as tg:
                    for ip, device in devices.items():
                        tg.create_task(self.fetch_and_store_sysinfo(ip, device))
            except* (ConnectionError, TimeoutError, OSError) as eg:
                for exc in eg.exceptions:
                    self.logger.error(f"Network error during sysinfo fetch: {exc}")
            except* Exception as eg:
                for exc in eg.exceptions:
                    if isinstance(exc, asyncio.CancelledError):
                        self.logger.info("Sysinfo fetch task was cancelled")
                        raise exc
                    else:
                        self.logger.error(
                            f"Unexpected error during sysinfo fetch: {exc}"
                        )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # Log a summary of the fetch cycle
            if (
                elapsed > Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL * 0.8
            ):  # Log if taking >80% of interval
                self.logger.warning(
                    f"System info fetch completed for {device_count} devices "
                    f"in {elapsed:.2f} seconds (approaching interval limit)."
                )
            else:
                self.logger.debug(
                    f"System info fetch completed for {device_count} devices "
                    f"in {elapsed:.2f} seconds."
                )

            if elapsed > Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL:
                self.logger.warning(
                    f"System info fetch took longer ({elapsed:.2f} seconds) than "
                    f"the configured interval of "
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
            self.logger.debug(f"Next system info fetch will run at {next_fetch_time}.")

            # Sleep for the remaining time (if any) before the next cycle
            await asyncio.sleep(
                max(0, Config.KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL - elapsed)
            )

    @async_retry(operation_name="emeter data fetch")
    async def fetch_and_store_emeter_data(self, ip, device):
        """
        Fetch and store emeter data for a specific device with automatic retry handling.
        """
        async with DeviceContext(device, ip, "emeter fetch"):
            await device.update()
            if isinstance(device, SmartStrip):
                await self.process_smart_strip_data(ip, device)
            elif device.has_emeter:
                await self.process_device_data(ip, device)

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
                "dns_name": await get_hostname_cached(ip),
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
                    "dns_name": await get_hostname_cached(ip),
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
                "dns_name": await get_hostname_cached(ip),
                "ip": ip,
                "equipment_type": "device",
            }
            self.logger.debug(f"Storing emeter data for {device_alias} (IP: {ip}).")
            await self.storage.process_emeter_data({ip: device_data})
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Data processing error for emeter data at {ip}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error processing emeter data for {ip}: {e}")

    @async_retry(operation_name="sysinfo fetch")
    async def fetch_and_store_sysinfo(self, ip, device):
        """
        Fetch and store system info data for a device with automatic retry handling.
        """
        async with DeviceContext(device, ip, "sysinfo fetch") as ctx:
            await device.update()
            self.logger.debug(f"Fetched sysinfo for device {ip}: {device.sys_info}")
            sysinfo_data = {
                "sysinfo": device.sys_info,
                "device_alias": ctx.device_name,
                "dns_name": ctx.hostname,
                "ip": ip,
                "equipment_type": "device",
            }
            self.logger.debug(f"Storing sysinfo data for {ctx.device_name} (IP: {ip})")
            await self.storage.process_sysinfo_data({ip: sysinfo_data})
