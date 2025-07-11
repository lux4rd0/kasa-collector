import asyncio
import logging
import os
from config import Config
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
        self.tasks = set()  # Store task references
        self.influxdb_storage = None  # Will be initialized when needed
        self.check_required_configs()

        # Initialize poller after config check
        try:
            self.poller = Poller(self.logger)
        except SystemExit:
            # Poller/InfluxDBStorage already logged detailed error messages
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise SystemExit(1)

    def check_required_configs(self):
        """
        Ensure that all required configuration details are present.
        If any required config is missing, raise an error and exit.
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
                f"Cannot start. Missing configs: {', '.join(missing_configs)}"
            )

        # Obfuscate the token for logging (show only the first and last 4 characters)
        obfuscated_token = Config.KASA_COLLECTOR_INFLUXDB_TOKEN
        if obfuscated_token:
            obfuscated_token = obfuscated_token[:4] + "****" + obfuscated_token[-4:]

        # Get version information
        version = os.getenv("KASA_COLLECTOR_VERSION", "unknown")
        build_timestamp = os.getenv("KASA_COLLECTOR_BUILD_TIMESTAMP", "unknown")

        # Log startup information
        self.logger.info("=" * 60)
        self.logger.info("Kasa Collector")
        self.logger.info(f"Version: {version}")
        self.logger.info(f"Build Date: {build_timestamp}")
        self.logger.info("=" * 60)

        # Log the confirmation of key configurations
        self.logger.info("Configuration:")
        self.logger.info(f"  InfluxDB URL: {Config.KASA_COLLECTOR_INFLUXDB_URL}")
        self.logger.info(f"  InfluxDB Token: {obfuscated_token}")  # Obfuscated token
        self.logger.info(f"  InfluxDB Bucket: {Config.KASA_COLLECTOR_INFLUXDB_BUCKET}")
        self.logger.info(
            f"  InfluxDB Organization: {Config.KASA_COLLECTOR_INFLUXDB_ORG}"
        )
        self.logger.info("=" * 60)

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
                self.logger.debug("Starting initial device discovery...")
                await self.device_manager.discover_devices()

            # Start the poller tasks for fetching emeter and sysinfo data
            emeter_task = asyncio.create_task(
                self.poller.periodic_emeter_fetch(self.device_manager.emeter_devices)
            )
            sysinfo_task = asyncio.create_task(
                self.poller.periodic_sysinfo_fetch(self.device_manager.emeter_devices)
            )
            discovery_task = asyncio.create_task(self.periodic_discover())

            # Store task references for proper cleanup
            self.tasks.add(emeter_task)
            self.tasks.add(sysinfo_task)
            self.tasks.add(discovery_task)

        except Exception as e:
            self.logger.error(f"Failed to start KasaCollector: {e}")
            raise

    async def periodic_discover(self):
        """
        Periodically discover devices on the network.
        Respects existing manual devices.
        This runs at an interval defined by the configuration.
        """
        self.logger.debug(
            f"Waiting {Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL}s "
            f"before first periodic discovery."
        )

        # Wait for the discovery interval to pass before starting periodic discovery
        await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)

        while True:
            try:
                self.logger.debug("Running periodic device discovery.")
                await self.device_manager.discover_devices()
            except Exception as e:
                self.logger.error(f"Error during periodic device discovery: {e}")
            finally:
                await asyncio.sleep(Config.KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL)

    async def shutdown(self):
        """
        Gracefully shutdown by canceling all tasks and closing connections.
        """
        self.logger.info("Starting graceful shutdown...")

        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete cancellation with timeout
        if self.tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.tasks, return_exceptions=True),
                    timeout=Config.KASA_COLLECTOR_SHUTDOWN_TIMEOUT,
                )
                self.logger.debug(f"Cancelled {len(self.tasks)} tasks")
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Task cancellation timed out after "
                    f"{Config.KASA_COLLECTOR_SHUTDOWN_TIMEOUT}s"
                )

        # Close InfluxDB connection if it exists
        if self.influxdb_storage:
            self.influxdb_storage.close()
            self.logger.debug("Closed InfluxDB connection")

        # Close any connections in poller and device_manager
        if hasattr(self.poller, "storage") and self.poller.storage:
            self.poller.storage.close()
            self.logger.debug("Closed poller InfluxDB connection")

        # Disconnect from all Kasa devices
        await self.device_manager.disconnect_all_devices()

        self.logger.info("Graceful shutdown completed")


async def main():
    """
    Main function to start the KasaCollector.
    Initializes the collector and starts the periodic tasks.
    """
    try:
        collector = KasaCollector()
    except SystemExit:
        # Configuration or initialization errors already logged
        raise  # Re-raise to preserve exit code
    except Exception as e:
        logger.error(f"Failed to initialize Kasa Collector: {e}")
        raise SystemExit(1)

    try:
        await collector.start()

        # Keep the event loop alive to ensure periodic tasks keep running.
        # The Event().wait() will block indefinitely until an external event occurs.
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Received shutdown signal. Shutting down gracefully...")
        await collector.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Received KeyboardInterrupt. Exiting gracefully.")
    except SystemExit as e:
        # Exit with the specified code without printing traceback
        exit(e.code if e.code is not None else 1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)
