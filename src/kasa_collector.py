import asyncio
import logging
from datetime import datetime, timedelta
from kasa_api import KasaAPI
from influxdb_storage import InfluxDBStorage
from config import Config
from kasa import SmartStrip
from device_manager import DeviceManager
from poller import Poller

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
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device_manager = DeviceManager(self.logger)
        self.poller = Poller(self.logger)
        self.check_required_configs()

    def check_required_configs(self):
        """
        Ensure that all required configuration details are present. If any required config
        is missing, raise an error and exit. Provide user-friendly logging.
        """
        required_configs = {
            "InfluxDB URL": Config.KASA_COLLECTOR_INFLUXDB_URL,
            "InfluxDB Token": Config.KASA_COLLECTOR_INFLUXDB_TOKEN,
            "InfluxDB Organization": Config.KASA_COLLECTOR_INFLUXDB_ORG,
            "InfluxDB Bucket": Config.KASA_COLLECTOR_INFLUXDB_BUCKET,
        }

        missing_configs = [
            name for name, value in required_configs.items() if not value
        ]

        if missing_configs:
            self.logger.error(
                f"Missing required configurations: {', '.join(missing_configs)}"
            )
            raise SystemExit(
                f"Cannot start KasaCollector. Missing configurations: {', '.join(missing_configs)}"
            )

        # Obfuscate the token for logging (show only the first and last 4 characters)
        obfuscated_token = Config.KASA_COLLECTOR_INFLUXDB_TOKEN
        if obfuscated_token:
            obfuscated_token = obfuscated_token[:4] + "****" + obfuscated_token[-4:]

        # Log the confirmation of key configurations
        self.logger.info("Starting KasaCollector with the following configurations:")
        self.logger.info(f"InfluxDB URL: {Config.KASA_COLLECTOR_INFLUXDB_URL}")
        self.logger.info(f"InfluxDB Token: {obfuscated_token}")  # Obfuscated token
        self.logger.info(f"InfluxDB Bucket: {Config.KASA_COLLECTOR_INFLUXDB_BUCKET}")
        self.logger.info(f"InfluxDB Organization: {Config.KASA_COLLECTOR_INFLUXDB_ORG}")

    async def start(self):
        """
        Start the KasaCollector by initializing manual devices, discovering devices,
        and starting periodic tasks.
        """
        try:
            # Initialize manual devices first
            await self.device_manager.initialize_manual_devices()

            # Perform initial device discovery if auto-discovery is enabled
            if Config.KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY:
                self.logger.info("Starting initial device discovery...")
                await self.device_manager.discover_devices()

            # Start the poller tasks for fetching emeter and sysinfo data
            asyncio.create_task(
                self.poller.periodic_emeter_fetch(self.device_manager.emeter_devices)
            )
            asyncio.create_task(
                self.poller.periodic_sysinfo_fetch(self.device_manager.emeter_devices)
            )

            # Start periodic device discovery after the initial discovery
            asyncio.create_task(self.periodic_discover())

        except Exception as e:
            self.logger.error(f"Failed to start KasaCollector: {e}")
            raise

    async def periodic_discover(self):
        """
        Periodically discover devices on the network, respecting existing manual devices.
        This runs at an interval defined by the configuration.
        """
        self.logger.info(
            f"Waiting for {Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL} seconds before the first periodic discovery."
        )

        # Wait for the discovery interval to pass before starting periodic discovery
        await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)

        while True:
            try:
                self.logger.info("Running periodic device discovery.")
                await self.device_manager.discover_devices()
            except Exception as e:
                self.logger.error(f"Error during periodic device discovery: {e}")
            finally:
                await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)


async def main():
    """
    Main function to start the KasaCollector and handle discovery, data fetch, and sysinfo fetch tasks.
    Initializes the collector and starts the periodic tasks for device management.
    """
    collector = KasaCollector()
    await collector.start()

    # Keep the event loop alive to ensure periodic tasks keep running.
    # The Event().wait() will block indefinitely until an external event occurs.
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Received KeyboardInterrupt. Exiting gracefully.")
