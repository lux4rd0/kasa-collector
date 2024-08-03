import os


class Config:
    # Whether to write data to file. Expected values are "true" or "false".
    # Default is "False".
    KASA_COLLECTOR_WRITE_TO_FILE = (
        os.getenv("KASA_COLLECTOR_WRITE_TO_FILE", "False").lower() == "true"
    )

    # Directory where output files will be saved. Default is "output".
    KASA_COLLECTOR_OUTPUT_DIR = os.getenv("KASA_COLLECTOR_OUTPUT_DIR", "output")

    # Enable device discovery or fall-back to host list.
    KASA_COLLECTOR_DEVICE_DISCOVERY = (
        os.getenv("KASA_COLLECTOR_DEVICE_DISCOVERY", "True").lower() == "true"
    )

    # Enable use of credentials when querying hosts (certain Kasa products require this).
    KASA_COLLECTOR_USE_CREDENTIALS = (
        os.getenv("KASA_COLLECTOR_USE_CREDENTIALS", "False").lower() == "true"
    )

    # The TP-LINK (Kasa) Cloud Account username.
    KASA_COLLECTOR_TPLINK_USERNAME = os.getenv("KASA_COLLECTOR_TPLINK_USERNAME", "")

    # The TP-LINK (Kasa) Cloud Account password.
    KASA_COLLECTOR_TPLINK_PASSWORD = os.getenv("KASA_COLLECTOR_TPLINK_PASSWORD", "")

    # An array of device IPs to connect to.
    KASA_COLLECTOR_DEVICE_HOSTS = os.getenv("KASA_COLLECTOR_DEVICE_HOST", "")

    # Maximum number of retries for fetching data from devices. Default is 5.
    KASA_COLLECTOR_FETCH_MAX_RETRIES = int(
        os.getenv("KASA_COLLECTOR_FETCH_MAX_RETRIES", "5")
    )

    # Delay in seconds between fetch retries. Default is 1 second.
    KASA_COLLECTOR_FETCH_RETRY_DELAY = int(
        os.getenv("KASA_COLLECTOR_FETCH_RETRY_DELAY", "1")
    )

    # Interval in seconds between device discovery runs. Default is 300 seconds (5 minutes).
    KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL = int(
        os.getenv("KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL", "300")
    )

    # Timeout in seconds for device discovery. Default is 5 seconds.
    KASA_COLLECTOR_DISCOVERY_TIMEOUT = int(
        os.getenv("KASA_COLLECTOR_DISCOVERY_TIMEOUT", "5")
    )

    # Number of discovery packets to send. Default is 3.
    KASA_COLLECTOR_DISCOVERY_PACKETS = int(
        os.getenv("KASA_COLLECTOR_DISCOVERY_PACKETS", "3")
    )

    # Interval in seconds between data fetch runs. Default is 15 seconds.
    KASA_COLLECTOR_DATA_FETCH_INTERVAL = int(
        os.getenv("KASA_COLLECTOR_DATA_FETCH_INTERVAL", "15")
    )

    # Interval in seconds between system information fetch runs. Default is 60 seconds.
    KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL = int(
        os.getenv("KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL", "60")
    )

    # Whether to keep missing devices in the list. Expected values are "true" or "false".
    # Default is "True".
    KASA_COLLECTOR_KEEP_MISSING_DEVICES = (
        os.getenv("KASA_COLLECTOR_KEEP_MISSING_DEVICES", "True").lower() == "true"
    )

    # Path to the output file for system information data.
    KASA_COLLECTOR_SYSINFO_OUTPUT_FILE = os.path.join(
        os.getenv("KASA_COLLECTOR_OUTPUT_DIR", "output"), "sysinfo_output.json"
    )

    # Path to the output file for emeter data.
    KASA_COLLECTOR_EMETER_OUTPUT_FILE = os.path.join(
        os.getenv("KASA_COLLECTOR_OUTPUT_DIR", "output"), "emeter_output.json"
    )

    # URL for the InfluxDB instance.
    KASA_COLLECTOR_INFLUXDB_URL = os.getenv("KASA_COLLECTOR_INFLUXDB_URL")

    # Token for authenticating with InfluxDB.
    KASA_COLLECTOR_INFLUXDB_TOKEN = os.getenv("KASA_COLLECTOR_INFLUXDB_TOKEN")

    # Organization name for InfluxDB.
    KASA_COLLECTOR_INFLUXDB_ORG = os.getenv("KASA_COLLECTOR_INFLUXDB_ORG")

    # Bucket name for storing data in InfluxDB.
    KASA_COLLECTOR_INFLUXDB_BUCKET = os.getenv("KASA_COLLECTOR_INFLUXDB_BUCKET")

    # Log level for the KasaAPI module. Default is "INFO".
    KASA_COLLECTOR_LOG_LEVEL_KASA_API = os.getenv(
        "KASA_COLLECTOR_LOG_LEVEL_KASA_API", "INFO"
    ).upper()

    # Log level for the InfluxDBStorage module. Default is "INFO".
    KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE = os.getenv(
        "KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE", "INFO"
    ).upper()

    # Log level for the KasaCollector module. Default is "INFO".
    KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR = os.getenv(
        "KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR", "INFO"
    ).upper()
