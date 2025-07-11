import os
import logging
import json
import aiofiles

from datetime import datetime, timezone
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import WriteOptions
from influxdb_client.rest import ApiException
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("InfluxDBStorage")
logger.setLevel(Config.KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE)


class InfluxDBStorage:
    def __init__(self):
        """
        Initialize the InfluxDBStorage with InfluxDB client and write API.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(Config.KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE)

        # Validate required config values
        if not Config.KASA_COLLECTOR_INFLUXDB_URL:
            raise ValueError("KASA_COLLECTOR_INFLUXDB_URL is required")
        if not Config.KASA_COLLECTOR_INFLUXDB_TOKEN:
            raise ValueError("KASA_COLLECTOR_INFLUXDB_TOKEN is required")
        if not Config.KASA_COLLECTOR_INFLUXDB_ORG:
            raise ValueError("KASA_COLLECTOR_INFLUXDB_ORG is required")
        if not Config.KASA_COLLECTOR_INFLUXDB_BUCKET:
            raise ValueError("KASA_COLLECTOR_INFLUXDB_BUCKET is required")

        try:
            self.client = InfluxDBClient(
                url=Config.KASA_COLLECTOR_INFLUXDB_URL,
                token=Config.KASA_COLLECTOR_INFLUXDB_TOKEN,
                org=Config.KASA_COLLECTOR_INFLUXDB_ORG,
            )

            # Validate connection by checking health
            self._validate_connection()

            self.write_api = self.client.write_api(
                write_options=WriteOptions(
                    batch_size=Config.KASA_COLLECTOR_INFLUXDB_BATCH_SIZE,
                    flush_interval=Config.KASA_COLLECTOR_INFLUXDB_FLUSH_INTERVAL,
                )
            )
            self.bucket = Config.KASA_COLLECTOR_INFLUXDB_BUCKET
            self.sysinfo_data = (
                {}
            )  # Store sysinfo for device mapping during emeter processing

            self.logger.info("InfluxDB connection established successfully")

        except ApiException as e:
            # Handle InfluxDB API errors gracefully
            if e.status == 401:
                self.logger.error("\n" + "=" * 60)
                self.logger.error("InfluxDB Authentication Failed")
                self.logger.error("=" * 60)
                self.logger.error("The provided InfluxDB credentials are invalid.")
                self.logger.error(
                    "\nPlease verify the following environment variables:"
                )
                self.logger.error("  - KASA_COLLECTOR_INFLUXDB_TOKEN")
                self.logger.error("  - KASA_COLLECTOR_INFLUXDB_ORG")
                self.logger.error("  - KASA_COLLECTOR_INFLUXDB_URL")
                self.logger.error(
                    "\nMake sure your token has write access to the bucket."
                )
                self.logger.error("=" * 60 + "\n")
            elif e.status == 404:
                self.logger.error("\n" + "=" * 60)
                self.logger.error("InfluxDB Resource Not Found")
                self.logger.error("=" * 60)
                self.logger.error(
                    f"Could not access InfluxDB at: "
                    f"{Config.KASA_COLLECTOR_INFLUXDB_URL}"
                )
                self.logger.error("\nPlease verify:")
                self.logger.error("  - The InfluxDB URL is correct")
                self.logger.error("  - InfluxDB is running and accessible")
                self.logger.error("  - The specified organization exists")
                self.logger.error("=" * 60 + "\n")
            else:
                self.logger.error("\n" + "=" * 60)
                self.logger.error("InfluxDB Connection Error")
                self.logger.error("=" * 60)
                self.logger.error(f"Failed to connect to InfluxDB: {e}")
                self.logger.error(f"Status Code: {e.status}")
                self.logger.error(f"Reason: {e.reason}")
                self.logger.error("=" * 60 + "\n")
            raise SystemExit(1)
        except ValueError as e:
            # Handle bucket not found errors
            self.logger.error("\n" + "=" * 60)
            self.logger.error("InfluxDB Configuration Error")
            self.logger.error("=" * 60)
            self.logger.error(str(e))
            self.logger.error("\nPlease verify:")
            self.logger.error(
                f"  - The bucket '{Config.KASA_COLLECTOR_INFLUXDB_BUCKET}' exists"
            )
            self.logger.error("  - Your token has access to this bucket")
            self.logger.error("  - The bucket name is spelled correctly")
            self.logger.error("=" * 60 + "\n")
            raise SystemExit(1)
        except ConnectionError as e:
            # Handle connection errors
            self.logger.error("\n" + "=" * 60)
            self.logger.error("InfluxDB Connection Failed")
            self.logger.error("=" * 60)
            self.logger.error(str(e))
            self.logger.error(
                f"\nCould not connect to InfluxDB at: "
                f"{Config.KASA_COLLECTOR_INFLUXDB_URL}"
            )
            self.logger.error("\nPlease verify:")
            self.logger.error("  - InfluxDB is running")
            self.logger.error("  - The URL and port are correct")
            self.logger.error("  - No firewall is blocking the connection")
            self.logger.error("=" * 60 + "\n")
            raise SystemExit(1)
        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error("\n" + "=" * 60)
            self.logger.error("Unexpected Error During InfluxDB Initialization")
            self.logger.error("=" * 60)
            self.logger.error(f"Error: {type(e).__name__}: {e}")
            self.logger.error("\nPlease check your configuration and try again.")
            self.logger.error("=" * 60 + "\n")
            raise SystemExit(1)

    def _validate_connection(self):
        """
        Validate InfluxDB connection by checking health endpoint.
        """
        try:
            # Check if InfluxDB is healthy and accessible
            health = self.client.health()
            if health.status != "pass":
                raise ConnectionError(f"InfluxDB health check failed: {health.message}")

            # Verify bucket exists and is accessible
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(
                Config.KASA_COLLECTOR_INFLUXDB_BUCKET
            )
            if not bucket:
                raise ValueError(
                    f"Bucket '{Config.KASA_COLLECTOR_INFLUXDB_BUCKET}' not found"
                )

            self.logger.debug(
                f"InfluxDB validated - Health: {health.status}, "
                f"Bucket: {bucket.name}"
            )

        except ApiException:
            # Re-raise API exceptions to be handled by the caller
            raise
        except Exception as e:
            # Log validation errors but re-raise for proper handling
            self.logger.debug(f"InfluxDB connection validation failed: {e}")
            raise

    async def write_data(self, measurement, data, tags=None):
        """
        Write data to InfluxDB.
        """
        point = Point(measurement).time(datetime.utcnow())
        for k, v in data.items():
            point = point.field(k, v)
        if tags:
            for k, v in tags.items():
                point = point.tag(k, v)

        self.write_api.write(bucket=self.bucket, org=self.client.org, record=point)
        self.logger.debug(
            f"Wrote data to InfluxDB: {measurement}, Tags: {tags}, Data: {data}"
        )

    async def process_emeter_data(self, device_data):
        """
        Process emeter data and send it to InfluxDB.
        """
        try:
            points = []
            for ip, data in device_data.items():
                emeter_data = data.get("emeter", {})
                alias = data.get("alias", "unknown")
                dns_name = data.get("dns_name", "unknown")
                equipment_type = data.get("equipment_type", "device")

                # Fetch the sysinfo for this device
                sysinfo = self.sysinfo_data.get(ip, {}).get("sysinfo", {})
                device_id = sysinfo.get("deviceId", None)  # Get device_id from sysinfo
                children = sysinfo.get("children", [])

                # Log for sysinfo lookup
                self.logger.debug(f"Lookup sysinfo for {ip}: {sysinfo}")

                # Determine if it's a plug on a power strip
                plug_alias = data.get(
                    "plug_alias", alias
                )  # Default plug alias to device alias
                plug_id = None

                if children:
                    # This is a power strip with child plugs
                    plug_info = self._get_plug_info_from_sysinfo_by_alias(
                        sysinfo, plug_alias
                    )
                    if plug_info:
                        plug_id = plug_info.get(
                            "plug_id", f"{len(children)}"
                        )  # Use numeric plug_id (1, 2, 3, ...)
                        plug_alias = plug_info.get("alias", plug_alias)
                    self.logger.debug(
                        f"Found plug_alias={plug_alias}, plug_id={plug_id} for ip={ip}"
                    )

                # Log Device Alias and IDs for debugging
                self.logger.debug(f"Device Alias: {alias}, Device ID: {device_id}")

                for metric, value in emeter_data.items():
                    point = (
                        Point("emeter")
                        .tag("ip", ip)
                        .tag("dns_name", dns_name)
                        .tag("device_alias", alias)
                        .tag("equipment_type", equipment_type)
                    )

                    # Add device_id for all devices if available
                    if device_id:
                        point = point.tag("device_id", device_id)

                    # Add plug-specific tags if this is a plug
                    if plug_id:
                        point = point.tag("plug_alias", plug_alias).tag(
                            "plug_id", plug_id
                        )

                    point = point.field(metric, value)
                    point = point.time(datetime.now(timezone.utc))
                    points.append(point)

            await self.send_to_influxdb(points)
            await self._append_to_file(device_data)

        except Exception as e:
            self.logger.error(f"Error processing emeter data for InfluxDB: {e}")

    def _get_plug_info_from_sysinfo_by_alias(self, sysinfo, plug_alias):
        """
        Retrieve plug info from sysinfo data and assign a numeric plug ID.
        """
        children = sysinfo.get("children", [])
        for index, child in enumerate(children):
            if child.get("alias") == plug_alias:
                # Assign plug_id as the index + 1 (1-based index)
                child["plug_id"] = f"{index + 1}"
                return child
        return None

    async def process_sysinfo_data(self, device_data):
        """
        Process sysinfo data and store it for later use in emeter processing.
        """
        try:
            # Store the sysinfo data for later use in emeter processing
            self.sysinfo_data.update(device_data)

            # Log for adding sysinfo data
            self.logger.debug(
                f"Updated sysinfo data: {json.dumps(self.sysinfo_data, indent=4)}"
            )

            points = []
            for ip, data in device_data.items():
                normalized_sysinfo = self.normalize_sysinfo(data.get("sysinfo", {}))
                device_id = normalized_sysinfo.get("device_id", "unknown")
                alias = data.get("device_alias") or data.get("alias") or ip
                self.logger.debug(
                    f"Processing sysinfo for IP: {ip}, Alias: {alias}, "
                    f"Hostname: {data.get('dns_name')}"
                )

                # Create a sysinfo point for the parent device
                point = (
                    Point("sysinfo")
                    .tag("ip", ip)
                    .tag("dns_name", data.get("dns_name"))
                    .tag("device_alias", alias)
                    .tag("device_id", device_id)
                )

                for key, value in normalized_sysinfo.items():
                    point = point.field(key, self._format_value(value))

                point = point.time(datetime.now(timezone.utc))
                points.append(point)

                # Process child devices (plugs) and assign sequential plug_id values
                children = normalized_sysinfo.get("children", [])
                for index, child in enumerate(children, start=1):
                    plug_alias = child.get("alias", f"Plug {index}")

                    # Generate sequential plug_id based on the index (1, 2, 3, etc.)
                    plug_id = str(index)

                    child_point = (
                        Point("sysinfo_child")
                        .tag("ip", ip)
                        .tag("dns_name", data.get("dns_name"))
                        .tag("device_alias", alias)
                        .tag("device_id", device_id)
                        .tag("plug_id", plug_id)  # Sequential plug_id (1, 2, 3, etc.)
                        .tag("plug_alias", plug_alias)
                    )

                    for key, value in child.items():
                        if key != "id":  # Exclude the original 'id' field
                            child_point = child_point.field(
                                key, self._format_value(value)
                            )

                    child_point = child_point.time(datetime.now(timezone.utc))
                    points.append(child_point)

                self.logger.debug(f"Full sysinfo data: {normalized_sysinfo}")

            self.logger.debug(f"Collected points for InfluxDB: {points}")
            await self.send_to_influxdb(points)
            await self._append_to_file(device_data)

        except Exception as e:
            self.logger.error(f"Error processing sysinfo data for InfluxDB: {e}")

    def normalize_sysinfo(self, sysinfo):
        """
        Normalize sysinfo data to standardize fields and handle variations,
        with specific updates for KP125M devices.
        """
        normalized = {}
        device_model = sysinfo.get("model", "")

        # Only apply specific transformations for KP125M devices
        if device_model == "KP125M":
            for key, value in sysinfo.items():
                if key == "fw_ver":
                    normalized["sw_ver"] = value
                    self.logger.debug(
                        f"Normalized 'fw_ver' to 'sw_ver' with value: {value}"
                    )
                elif key == "device_on":
                    # Normalize 'device_on' to 'relay_state' for KP125M
                    normalized["relay_state"] = 1 if value else 0
                    self.logger.debug(
                        f"Normalized 'device_on' to 'relay_state' for KP125M: {value}"
                    )
                else:
                    normalized[key] = value
        else:
            # If not KP125M, retain the sysinfo as-is
            normalized = sysinfo

        return normalized

    async def send_to_influxdb(self, points):
        """
        Send data points to InfluxDB.
        """
        try:
            for point in points:
                self.logger.debug(f"Sending to InfluxDB: {point.to_line_protocol()}")
                self.write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            self.logger.error(f"Error sending data to InfluxDB: {e}")

    async def _append_to_file(self, data):
        """
        Append device data to individual files based on type (sysinfo or emeter).
        """
        try:
            output_dir = Config.KASA_COLLECTOR_OUTPUT_DIR
            os.makedirs(output_dir, exist_ok=True)

            for ip, device_data in data.items():
                alias = (
                    device_data.get("alias") or device_data.get("device_alias") or ip
                )
                dns_name = device_data.get("dns_name", "")
                identifier = alias or dns_name or ip
                sanitized_identifier = "".join(
                    c if c.isalnum() or c in "-_." else "_" for c in identifier
                )
                file_type = "emeter" if "emeter" in device_data else "sysinfo"
                filename = os.path.join(
                    output_dir, f"{file_type}_{sanitized_identifier}.json"
                )

                # Append data to the file instead of overwriting it
                async with aiofiles.open(filename, "a") as f:
                    await f.write(json.dumps({ip: device_data}, indent=4) + "\n")
                    self.logger.debug(
                        f"Appended {file_type} data to JSON file: {filename}"
                    )

        except Exception as e:
            self.logger.error(f"Error writing data to file: {e}")

    def _format_value(self, value):
        """
        Format values for InfluxDB points.
        """
        if isinstance(value, (int, float, str, bool)):
            return value
        elif isinstance(value, list):
            return ",".join(map(str, value))
        return str(value)

    def close(self):
        """
        Close the InfluxDB client.
        """
        self.client.close()
