import os
import logging
import json
import socket
import aiofiles

from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import ASYNCHRONOUS
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
        self.client = InfluxDBClient(
            url=Config.KASA_COLLECTOR_INFLUXDB_URL,
            token=Config.KASA_COLLECTOR_INFLUXDB_TOKEN,
            org=Config.KASA_COLLECTOR_INFLUXDB_ORG,
        )
        self.write_api = self.client.write_api(
            write_options=WriteOptions(
                batch_size=1, flush_interval=10, write_type=ASYNCHRONOUS
            )
        )
        self.bucket = Config.KASA_COLLECTOR_INFLUXDB_BUCKET
        self.sysinfo_data = (
            {}
        )  # Store sysinfo for device mapping during emeter processing

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
        Retrieve plug info from sysinfo data and assign a simple numeric plug ID (e.g., 1, 2, 3).
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
                    f"Processing sysinfo for IP: {ip}, Alias: {alias}, Hostname: {data.get('dns_name')}"
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
                    # Normalize 'device_on' to 'relay_state' and convert boolean to integer for KP125M
                    normalized["relay_state"] = 1 if value else 0
                    self.logger.debug(
                        f"Normalized 'device_on' to 'relay_state' for KP125M with value: {value}"
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
