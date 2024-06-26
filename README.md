
## About The Project

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector_header.png"></center>

**Kasa Collector** is a set of scripts deployed with Docker that collects data from [Kasa](https://www.kasasmart.com/us/products/smart-plugs) Smart Plugs. Once deployed, you can visualize that data using Grafana dashboards.

A live set of dashboards using this Collector [are available](https://labs.lux4rd0.com/kasa-collector/) for you to try out.

## Getting Started

The project uses a Docker container that may be configured to accept different settings for how often you wish to poll your Kasa devices.

## Prerequisites

- [Docker](https://docs.docker.com/install)
- [Docker Compose](https://docs.docker.com/compose/install)
- [InfluxDB V2](https://docs.influxdata.com/influxdb/v2/)
- [Grafana 11.0.0](https://grafana.com/oss/grafana/)

## Supported Kasa Smart Plugs

This project currently supports collecting data from the Kasa [KP115](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-plug-slim-energy-monitoring-kp115) smart plug device and Kasa [HS300](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-wi-fi-power-strip-hs300) power strip. These are the two devices that I have - others may be supported based on the "energy" tag found during device disovery.

## TPLink Smartplug Open Source Project

This project uses the python-kasa module to discover and connect to Kasa devices. More details on supported devices may be found on their [project site](https://github.com/python-kasa/python-kasa).

## Deploying Kasa Collector

Use the following [Docker container](https://hub.docker.com/r/lux4rd0/kasa-collector):

```plaintext
lux4rd0/kasa-collector:2.0.06
lux4rd0/kasa-collector:latest
```

Kasa Collector requires some environmental variables for the container to function. It mainly needs details on your InfluxDB instance (Bucket, Org, Token, and URL).

You can start the container with something similar to the example `docker-compose.yaml` file:

```yaml
name: kasa-collector

services:
  kasa-collector:
    container_name: kasa-collector
    environment:
      KASA_COLLECTOR_INFLUXDB_BUCKET: kasa
      KASA_COLLECTOR_INFLUXDB_ORG: Lux4rd0
      KASA_COLLECTOR_INFLUXDB_TOKEN: TOKEN
      KASA_COLLECTOR_INFLUXDB_URL: http://influxdb.lux4rd0.com:8086
      TZ: America/Chicago
    image: lux4rd0/kasa-collector:latest
    network_mode: host
    restart: always
```

Or use this example docker run command:

```bash
docker run -d \
      --name=kasa-collector \
      -e KASA_COLLECTOR_INFLUXDB_BUCKET=kasa \
      -e KASA_COLLECTOR_INFLUXDB_ORG=Lux4rd0 \
      -e KASA_COLLECTOR_INFLUXDB_TOKEN=TOKEN \
      -e KASA_COLLECTOR_INFLUXDB_URL=http://influxdb.lux4rd0.com:8086 \
      -e TZ=America/Chicago \
      --restart always \
      --network host \
      lux4rd0/kasa-collector:latest
```

Be sure to change your InfluxDB details and timezone in the environmental variables.

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

Each dashboard has dropdowns at the top that allow you to filter measurements based on devices and plugs. The dropdowns default to "All," but you can select and save preferences.

**Interval**:  A dropdown that provides different smoothing levels helps manage how the graphs look based on the interval of data collected by the Kasa Collector. Think of this as a level of "smoothing" based on your chosen time frame and the polling time you're collecting data. Be sure to set these to a time frame higher than your poll rate.

**Time Range**: This defaults to "Today so far" but can be updated to any other Relative or Absolute time range. Change the "Interval" dropdown for longer time ranges to smooth out any data.

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

