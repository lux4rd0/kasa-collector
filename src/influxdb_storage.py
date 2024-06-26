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

    async def write_data(self, measurement, data, tags=None):
        """
        Write data to InfluxDB.

        Parameters:
        - measurement (str): The measurement name.
        - data (dict): The data to write.
        - tags (dict): Optional tags to add to the data.
        """
        point = Point(measurement).time(datetime.utcnow())
        for k, v in data.items():
            point = point.field(k, v)
        if tags:
            for k, v in tags.items():
                point = point.tag(k, v)

        self.write_api.write(bucket=self.bucket, org=self.client.org, record=point)
        self.logger.info(
            f"Wrote data to InfluxDB: {measurement}, Tags: {tags}, Data: {data}"
        )

    async def write_to_json(self, data, output_dir):
        """
        Write data to a JSON file.

        Parameters:
        - data (dict): The data to write.
        - output_dir (str): The directory to write the JSON file to.
        """
        filename = f"{output_dir}/{datetime.utcnow().isoformat()}.json"
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(data, indent=4))
        self.logger.info(f"Wrote data to JSON file: {filename}")

    def _dns_lookup(self, ip):
        """
        Perform a DNS lookup for the given IP address.

        Parameters:
        - ip (str): The IP address to look up.

        Returns:
        - str: The DNS name associated with the IP address.
        """
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.herror:
            return "unknown"

    def convert_to_points(self, data):
        """
        Convert device data to InfluxDB points.

        Parameters:
        - data (dict): The device data.

        Returns:
        - list: A list of InfluxDB points.
        """
        points = []
        for ip, device_data in data.items():
            alias = device_data["system"]["get_sysinfo"].get("alias", "unknown")
            dns_name = self._dns_lookup(ip)
            for category, data in device_data.items():
                self._parse_category(ip, alias, dns_name, category, data, points)
        return points

    def _parse_category(
        self, ip, alias, dns_name, category, data, points, parent_key=""
    ):
        """
        Recursively parse categories and add data to InfluxDB points.

        Parameters:
        - ip (str): The IP address of the device.
        - alias (str): The alias of the device.
        - dns_name (str): The DNS name of the device.
        - category (str): The category of the data.
        - data (dict or list or other): The data to parse.
        - points (list): The list of InfluxDB points to add to.
        - parent_key (str): The parent key for nested data.
        """
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                self._parse_category(
                    ip, alias, dns_name, category, value, points, new_key
                )
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._parse_list_item(
                        ip, alias, dns_name, category, item, points, parent_key
                    )
        else:
            point = (
                Point(category)
                .tag("ip", ip)
                .tag("alias", alias)
                .tag("dns_name", dns_name)
            )
            point = point.field(parent_key, self._format_value(data))
            point = point.time(datetime.now(timezone.utc))
            points.append(point)

    def _parse_list_item(self, ip, alias, dns_name, category, item, points, parent_key):
        """
        Parse list items and add them to InfluxDB points.

        Parameters:
        - ip (str): The IP address of the device.
        - alias (str): The alias of the device.
        - dns_name (str): The DNS name of the device.
        - category (str): The category of the data.
        - item (dict): The list item to parse.
        - points (list): The list of InfluxDB points to add to.
        - parent_key (str): The parent key for nested data.
        """
        for k, v in item.items():
            if isinstance(v, dict):
                for sub_key, sub_value in v.items():
                    new_key = (
                        f"{parent_key}.{k}.{sub_key}"
                        if parent_key
                        else f"{k}.{sub_key}"
                    )
                    self._parse_category(
                        ip, alias, dns_name, category, sub_value, points, new_key
                    )
            else:
                point = (
                    Point(category)
                    .tag("ip", ip)
                    .tag("alias", alias)
                    .tag("dns_name", dns_name)
                )
                point = point.field(f"{parent_key}.{k}", self._format_value(v))
                point = point.time(datetime.now(timezone.utc))
                points.append(point)

    def _format_value(self, value):
        """
        Format values for InfluxDB points.

        Parameters:
        - value: The value to format.

        Returns:
        - formatted value
        """
        if isinstance(value, (int, float, str, bool)):
            return value
        elif isinstance(value, list):
            return ",".join(map(str, value))
        return str(value)

    async def process_emeter_data(self, device_data):
        """
        Process emeter data and send it to InfluxDB.

        Parameters:
        - device_data (dict): The emeter data of devices.
        """
        points = []
        for ip, data in device_data.items():
            emeter_data = data.get("emeter", {})
            alias = data.get("alias", "unknown")
            dns_name = data.get("dns_name", "unknown")
            equipment_type = data.get("equipment_type", "device")
            plug_alias = data.get("plug_alias", "unknown")

            for metric, value in emeter_data.items():
                point = Point("emeter").tag("ip", ip).tag("dns_name", dns_name)
                point = point.field(metric, value)
                point = point.tag("device_alias", alias)
                point = point.tag("equipment_type", equipment_type)
                if equipment_type == "plug":
                    point = point.tag("plug_alias", plug_alias)
                point = point.time(datetime.now(timezone.utc))
                points.append(point)

        await self.send_to_influxdb(points)
        await self._write_to_file(Config.KASA_COLLECTOR_EMETER_OUTPUT_FILE, device_data)

    async def process_sysinfo_data(self, device_data):
        """
        Process sysinfo data and send it to InfluxDB.

        Parameters:
        - device_data (dict): The sysinfo data of devices.
        """
        try:
            points = []
            for ip, data in device_data.items():
                sysinfo = data.get("sysinfo", {})
                alias = sysinfo.get("alias", "unknown")
                dns_name = self._dns_lookup(ip)

                for key, value in sysinfo.items():
                    point = Point("sysinfo").tag("ip", ip).tag("dns_name", dns_name)
                    point = point.field(key, self._format_value(value))
                    point = point.tag("device_alias", alias)
                    point = point.time(datetime.now(timezone.utc))
                    points.append(point)

            self.logger.debug(f"Processing sysinfo data for InfluxDB: {points}")
            await self.send_to_influxdb(points)
            await self._write_to_file(
                Config.KASA_COLLECTOR_SYSINFO_OUTPUT_FILE, device_data
            )

        except Exception as e:
            self.logger.error(f"Error processing sysinfo data for InfluxDB: {e}")

    async def send_to_influxdb(self, points):
        """
        Send data points to InfluxDB.

        Parameters:
        - points (list): A list of InfluxDB points to send.
        """
        try:
            for point in points:
                self.logger.debug(f"Sending to InfluxDB: {point.to_line_protocol()}")
                self.write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            self.logger.error(f"Error sending data to InfluxDB: {e}")

    async def _write_to_file(self, file_path, data):
        """
        Write data to a file.

        Parameters:
        - file_path (str): The file path to write to.
        - data (dict): The data to write.
        """
        try:
            if Config.KASA_COLLECTOR_WRITE_TO_FILE:
                async with aiofiles.open(file_path, "a") as file:
                    await file.write(json.dumps(data, indent=4) + "\n")
        except Exception as e:
            self.logger.error(f"Error writing data to file {file_path}: {e}")

    def close(self):
        """
        Close the InfluxDB client.
        """
        self.client.close()
