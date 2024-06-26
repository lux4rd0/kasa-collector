## About The Project

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector_header.png"></center>

**Kasa Collector** is a set of scripts deployed with Docker that collects data from [Kasa](https://www.kasasmart.com/us/products/smart-plugs) Smart Plugs. Once deployed, you can use Grafana dashboards to visualize that data.

A live set of dashboards using this Collector [are available](https://labs.lux4rd0.com/kasa-collector/) for you to try out.

## Getting Started

The project builds a pre-configured Docker container that takes different configurations based on how often you wish to poll your Kasa devices.

## Prerequisites

- [Docker](https://docs.docker.com/install)
- [Docker Compose](https://docs.docker.com/compose/install)
- [InfluxDB V2](https://docs.influxdata.com/influxdb/v2/)
- [Grafana 11.0.0](https://grafana.com/oss/grafana/)

## Supported Kasa Smart Plugs

This project currently supports collecting data from the Kasa [KP115](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-plug-slim-energy-monitoring-kp115) smart plug device and Kasa [HS300](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-wi-fi-power-strip-hs300) power strip.

## TPLink Smartplug Open Source Project

The underlying Python script used to communicate with the Kasa devices by the Kasa Collector comes from the softScheck [tplink-smartplug](https://github.com/softScheck/tplink-smartplug) project. An [overview](https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/) on how they reversed-engineered getting access to the local devices is available.

## Deploying Kasa Collector

Use the following [Docker container](https://hub.docker.com/r/lux4rd0/kasa-collector):

```plaintext
lux4rd0/kasa-collector:2.0.06
lux4rd0/kasa-collector:latest
```

Kasa Collector requires environmental variables for the container to function. It mainly needs details on your InfluxDB instance (URL, username, and password) and the list of Kasa devices you'd like it to poll.

You can start the container with something similar to the example `docker-compose.yaml` file:

```yaml
version: '3.8'

name: kasa-collector

services:
  kasa-collector:
    container_name: kasa-collector
    environment:
      KASA_COLLECTOR_DATA_FETCH_INTERVAL: "15"
      KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL: "300"
      KASA_COLLECTOR_DISCOVERY_PACKETS: "3"
      KASA_COLLECTOR_DISCOVERY_TIMEOUT: "5"
      KASA_COLLECTOR_FETCH_MAX_RETRIES: "3"
      KASA_COLLECTOR_FETCH_RETRY_DELAY: "1"
      KASA_COLLECTOR_INFLUXDB_BUCKET: kasa
      KASA_COLLECTOR_INFLUXDB_ORG: Tylephony
      KASA_COLLECTOR_INFLUXDB_TOKEN: qB7XT9fVnqNly9AZiUffFYZDGFiwLyPL6IHqhSphAPBE24PpDBPCMw71u8NpeCf3If1ktn4RzFFlgVoFNOfpgw==
      KASA_COLLECTOR_INFLUXDB_URL: http://influxdb02.tylephony.com:8086
      KASA_COLLECTOR_KEEP_MISSING_DEVICES: "False"
      KASA_COLLECTOR_OUTPUT_DIR: output
      KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL: "60"
      KASA_COLLECTOR_WRITE_TO_FILE: "True"
      TZ: America/Chicago
      KASA_COLLECTOR_LOG_LEVEL_KASA_API: "DEBUG"
      KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE: "DEBUG"
      KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR: "DEBUG"
    image: docker.tylephony.com:5000/lux4rd0/kasa-collector:2.0.5
    network_mode: host
    restart: always
    volumes:
      - type: bind
        source: /mnt/docker/kasa-collector/output
        target: /app/kasa_collector/output
        bind:
          create_host_path: true
```

Or use this example docker run command:

```bash
docker run -d \
      --name=kasa-collector \
      -e KASA_COLLECTOR_DATA_FETCH_INTERVAL=15 \
      -e KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL=300 \
      -e KASA_COLLECTOR_DISCOVERY_PACKETS=3 \
      -e KASA_COLLECTOR_DISCOVERY_TIMEOUT=5 \
      -e KASA_COLLECTOR_FETCH_MAX_RETRIES=3 \
      -e KASA_COLLECTOR_FETCH_RETRY_DELAY=1 \
      -e KASA_COLLECTOR_INFLUXDB_BUCKET=kasa \
      -e KASA_COLLECTOR_INFLUXDB_ORG=Tylephony \
      -e KASA_COLLECTOR_INFLUXDB_TOKEN=qB7XT9fVnqNly9AZiUffFYZDGFiwLyPL6IHqhSphAPBE24PpDBPCMw71u8NpeCf3If1ktn4RzFFlgVoFNOfpgw== \
      -e KASA_COLLECTOR_INFLUXDB_URL=http://influxdb02.tylephony.com:8086 \
      -e KASA_COLLECTOR_KEEP_MISSING_DEVICES=False \
      -e KASA_COLLECTOR_OUTPUT_DIR=output \
      -e KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL=60 \
      -e KASA_COLLECTOR_WRITE_TO_FILE=True \
      -e TZ=America/Chicago \
      -e KASA_COLLECTOR_LOG_LEVEL_KASA_API=DEBUG \
      -e KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE=DEBUG \
      -e KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR=DEBUG \
      --restart always \
      --network host \
      -v /mnt/docker/kasa-collector/output:/app/kasa_collector/output \
      docker.tylephony.com:5000/lux4rd0/kasa-collector:2.0.5
```

Be sure to change your InfluxDB details, timezone, and list of Kasa devices in the environmental variables.

Running `docker-compose up -d` or the `docker run` command will download and start up the kasa-collector container. 

## Environmental Flags

Kasa Collector may be configured with additional environment flags to control its behaviors. They are described below:

`KASA_COLLECTOR_DATA_FETCH_INTERVAL` - OPTIONAL

How frequently does the Collector poll your devices to collect measurements in seconds? Defaults to 15 (seconds) if it's not set.

- integer (in seconds)

`KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL` - OPTIONAL

How frequently the Collector discovers devices in seconds. Defaults to 300 (seconds) if it's not set.

- integer (in seconds)

`KASA_COLLECTOR_DISCOVERY_TIMEOUT` - OPTIONAL

Timeout for discovering devices in seconds. Defaults to 5 (seconds) if it's not set.

- integer (in seconds)

`KASA_COLLECTOR_DISCOVERY_PACKETS` - OPTIONAL

Number of packets sent for device discovery. Defaults to 3 if it's not set.

- integer

`KASA_COLLECTOR_FETCH_MAX_RETRIES` - OPTIONAL

Maximum number of retries for fetching data. Defaults to 3 if it's not set.

- integer

`KASA_COLLECTOR_FETCH_RETRY_DELAY` - OPTIONAL

The delay between retries for fetching data in seconds. If it's not set, it defaults to 1 (second).

- integer (in seconds)

`KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL` - OPTIONAL

How frequently the Collector gathers system information in seconds. Defaults to 60 (seconds) if it's not set.

- integer (in seconds)

`KASA_COLLECTOR_WRITE_TO_FILE` - OPTIONAL

Indicates whether to write data to JSON files. Defaults to False.

- true
- false

`KASA_COLLECTOR_KEEP_MISSING_DEVICES` - OPTIONAL

Indicates whether to keep missing devices in the collection. Defaults to True.

- true
- false

`KASA_COLLECTOR_INFLUXDB_URL` - REQUIRED

The URL of the InfluxDB instance.

`KASA_COLLECTOR_INFLUXDB_TOKEN` - REQUIRED

The token for the InfluxDB instance.

`KASA_COLLECTOR_INFLUXDB_ORG` - REQUIRED

The organization for the InfluxDB instance.

`KASA_COLLECTOR_INFLUXDB_BUCKET` - REQUIRED

The bucket for the InfluxDB instance.

`KASA_COLLECTOR_LOG_LEVEL_KASA_API` - OPTIONAL

Log level for Kasa API. Defaults to "INFO".

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

`KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE` - OPTIONAL

Log level for InfluxDB Storage. Defaults to "INFO".

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

`KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECT

OR` - OPTIONAL

Log level for Kasa Collector. Defaults to "INFO".

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## Collector Details

#### kasa-collector

Kasa Collector is the primary data collector and is responsible for gathering details per Kasa device for the following:

* Current (milliamps)
* Voltage (millivolts)
* Power (milliwatts)
* Total Watt Hours

Additional details like Wifi RSSI signal strength, device and plug names, and device details are also collected.

## Grafana Dashboards

Collecting data is only half the fun. Now it's time to provision some Grafana Dashboards to visualize your essential Kasa data. You'll find a [folder of dashboards](https://github.com/lux4rd0/kasa-collector/dashboards) with collectors and backends split out. You can also use the links/numbers next to each dashboard title to load the dashboards [directly from Grafana](https://grafana.com/grafana/dashboards?search=kasa%20collector).

### In General:

Each dashboard has dropdowns at the top that allow you to filter measurements based on devices and plugs. The dropdowns default to "All," but you can certainly select and save preferences.

**Interval**:  A dropdown that provides different smoothing levels helps manage how the graphs look based on the interval of data being collected by the Kasa Collector. Think of this as a level of "smoothing" based on your chosen time frame and the polling time you're collecting data. Be sure to set these to a time frame higher than your poll rate.

**Time Range**: This defaults to "Today so far" but can be updated to any other Relative or Absolute time range. Change the "Interval" dropdown for longer time ranges if you want to smooth out any of the data.

**Dashboard Refresh**: Each dashboard is set to refresh every sixty seconds, but this can be changed or disabled.

### Kasa Collector - Energy (By Measurement) - [14762](https://grafana.com/grafana/dashboards/14762)

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector-energy_by_measurement.jpg"></center>

### Kasa Collector - Energy (By Device) - [14772](https://grafana.com/grafana/dashboards/14772)

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector-energy_by_device.jpg"></center>

The Energy dashboard provides panels representing Power, Watt-Hours, Current, and Voltage. Measurements are at the top for total combined information (and voltage average) and rows for both devices and plugs (as part of power strips). You can use the device and plug dropdown menus at the top of the dashboard to filter on each. If you choose a single device that happens to be a power strip, only the plugs for that power strip will be shown in the Plugs dropdown.

## Troubleshooting

**Error Messages**

Sometimes, you'll see the following error message from the Kasa Collector:

```plaintext
kasa_request_info: malformed JSON, retrying
```

This is because some devices that respond to the collector might be malformed data. The collector will try again until a good response is received.

## Roadmap

See the open issues for a list of proposed features (and known issues).

## Contact

Dave Schmid: [@lux4rd0](https://twitter.com/lux4rd0) - dave@pulpfree.org

Project Link: https://github.com/lux4rd0/kasa-collector

## Acknowledgements

- Grafana Labs - [https://grafana.com/](https://grafana.com/)
- Grafana - [https://grafana.com/oss/grafana/](https://grafana.com/oss/grafana/)
- Grafana Dashboard Community - [https://grafana.com/grafana/dashboards/](https://grafana.com/grafana/dashboards/)

