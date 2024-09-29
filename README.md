
  

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

This project currently supports collecting data from the Kasa [KP115](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-plug-slim-energy-monitoring-kp115) smart plug device, Kasa [HS300](https://www.kasasmart.com/us/products/smart-plugs/kasa-smart-wi-fi-power-strip-hs300) power strip, and the Kasa [KP125M](https://www.tp-link.com/us/home-networking/smart-plug/kp125m/). I have personally tested these three devices - others may be supported based on the "energy" tag found during device discovery.

## TPLink Smartplug Open Source Project

This project uses the python-kasa module to discover and connect to Kasa devices. More details on supported devices may be found on their [project site](https://github.com/python-kasa/python-kasa).

## Deploying Kasa Collector

Use the following [Docker container](https://hub.docker.com/r/lux4rd0/kasa-collector):

```plaintext
lux4rd0/kasa-collector:2.0.07
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
      KASA_COLLECTOR_TPLINK_USERNAME: user@example.com  # Optional
      KASA_COLLECTOR_TPLINK_PASSWORD: yourpassword       # Optional
      KASA_COLLECTOR_DEVICE_HOSTS: "10.50.0.101,10.50.0.102"  # Optional
      KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY: false        # Optional
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
      -e KASA_COLLECTOR_TPLINK_USERNAME=user@example.com \  # Optional
      -e KASA_COLLECTOR_TPLINK_PASSWORD=yourpassword \     # Optional
      -e KASA_COLLECTOR_DEVICE_HOSTS="10.50.0.101,10.50.0.102" \  # Optional
      -e KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY=false \      # Optional
      -e TZ=America/Chicago \
      --restart always \
      --network host \
      lux4rd0/kasa-collector:latest
```

Be sure to change your InfluxDB details and timezone in the environmental variables.

Running `docker-compose up -d` or the `docker run` command will download and start up the kasa-collector container. 

## How It Works

The Kasa Collector is designed to automate data collection from Kasa Smart Plugs, providing a streamlined approach to gathering, storing, and visualizing device information. It supports both automatic device discovery and manual device configuration, allowing for flexible integration in various environments. Below is a high-level overview of its capabilities:

### Automatic Device Discovery

The Kasa Collector can automatically discover compatible Kasa devices on your network without requiring manual configuration. By default, the collector sends discovery packets regularly (`KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL`) and identifies devices supporting energy monitoring features. The `KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY` environment variable controls this behavior:

- **To Enable Auto-Discovery:** Ensure that `KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY` is set to `true` (default behavior).
- **To Disable Auto-Discovery:** Set `KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY` to `false`. This prevents automatic discovery and only uses manually specified devices.

### Manual Device Configuration

In cases where devices are not automatically discovered or need specific attention, you can manually specify device IPs or hostnames using the `KASA_COLLECTOR_DEVICE_HOSTS` variable. This variable accepts a comma-separated list of device IPs/hostnames. Manually added devices take precedence over auto-discovered devices and are continuously monitored.

- **Example:** `KASA_COLLECTOR_DEVICE_HOSTS="10.50.0.101,10.50.0.102"`

### TP-Link Account Configuration

For newer Kasa devices that require TP-Link account authentication, you can provide your account credentials using the `KASA_COLLECTOR_TPLINK_USERNAME` and `KASA_COLLECTOR_TPLINK_PASSWORD` variables. These credentials enable the collector to authenticate with devices linked to your TP-Link account.

- **Example Configuration:**
  ```yaml
  KASA_COLLECTOR_TPLINK_USERNAME: user@example.com
  KASA_COLLECTOR_TPLINK_PASSWORD: yourpassword
  ```

When configured, the collector will attempt to authenticate and control these devices, providing extended functionality for devices that need TP-Link cloud authentication.

## Environmental Flags

Kasa Collector may be configured with additional environment flags to control its behaviors. They are described below:

### Required Variables

`KASA_COLLECTOR_INFLUXDB_URL`  
The URL of the InfluxDB instance.

- Example: `http://influxdb.lux4rd0.com:8086`

`KASA_COLLECTOR_INFLUXDB_TOKEN`  
The token for the InfluxDB instance.

- Example: `your-influxdb-token`

`KASA_COLLECTOR_INFLUXDB_ORG`  
The organization for the InfluxDB instance.

- Example: `Lux4rd0`

`KASA_COLLECTOR_INFLUXDB_BUCKET`  
The bucket for the InfluxDB instance.

- Example: `kasa`

### Optional Variables

`KASA_COLLECTOR_DATA_FETCH_INTERVAL`  
How frequently the Collector polls your devices to collect measurements in seconds. Defaults to `15` (seconds) if not set.

- Example: `15`
- Type: Integer (seconds)

`KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL`  
How frequently the Collector discovers devices in seconds. Defaults to `300` (seconds) if not set.

- Example: `300`
- Type: Integer (seconds)

`KASA_COLLECTOR_DISCOVERY_TIMEOUT`  
Timeout for discovering devices in seconds. Defaults to `5` (seconds) if not set.

- Example: `5`
- Type: Integer (seconds)

`KASA_COLLECTOR_DISCOVERY_PACKETS`  
Number of packets sent for device discovery. Defaults to `3` if not set.

- Example: `3`
- Type: Integer

`KASA_COLLECTOR_FETCH_MAX_RETRIES`  
Maximum number of retries for fetching data. Defaults to `3` if not set.

- Example: `3`
- Type: Integer

`KASA_COLLECTOR_FETCH_RETRY_DELAY`  
The delay between retries for fetching data in seconds. Defaults to `1` (second) if not set.

- Example: `1`
- Type: Integer (seconds)

`KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL`  
How frequently the Collector gathers system information in seconds. Defaults to `60` (seconds) if not set.

- Example: `60`
- Type: Integer (seconds)

`KASA_COLLECTOR_WRITE_TO_FILE`  
Indicates whether to write data to JSON files. Defaults to `false` if not set.

- Example: `true` or `false`
- Type: Boolean

`KASA_COLLECTOR_KEEP_MISSING_DEVICES`  
Indicates whether to keep missing devices in the collection. Defaults to `true` if not set.

- Example: `true` or `false`
- Type: Boolean

`KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY`  
Enables or disables automatic device discovery. Defaults to `true` if not set.

- Example: `true` or `false`
- Type: Boolean

`KASA_COLLECTOR_TPLINK_USERNAME`  
Your TP-Link Kasa account username (email) is used to authenticate with devices. If set, manual device control is enabled.

- Example: `user@example.com`
- Type: String

`KASA_COLLECTOR_TPLINK_PASSWORD`  
Your TP-Link Kasa account password for authenticating with devices. Required if `KASA_COLLECTOR_TPLINK_USERNAME` is set.

- Example: `yourpassword`
- Type: String

`KASA_COLLECTOR_DEVICE_HOSTS`  
Comma-separated list of IP addresses or hostnames of specific Kasa devices to monitor manually.

- Example: `"10.50.0.101,10.50.0.102"`
- Type: String

`KASA_COLLECTOR_LOG_LEVEL_KASA_API`  
Log level for Kasa API. Defaults to `INFO`.

- Example: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

`KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE`  
Log level for InfluxDB Storage. Defaults to `INFO`.

- Example: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

`KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR`  
Log level for Kasa Collector. Defaults to `INFO`.

- Example: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Collector Details

#### kasa-collector

Kasa Collector is the primary data collector and is responsible for gathering details per Kasa device for the following:

* Current (milliamps)
* Voltage (millivolts)
* Power (milliwatts)
* Total Watt Hours

Additional details, such as Wi-Fi RSSI signal strength, device and plug names, and device details, are also collected. Not all devices provide all the details.

## Grafana Dashboards

Collecting data is only half the fun. Now it's time to provision some Grafana Dashboards to visualize your essential Kasa data. You'll find a [folder of dashboards](https://github.com/lux4rd0/kasa-collector/dashboards) with collectors and backends split out. You can also use the links/numbers next to each dashboard title to load the dashboards [directly from Grafana](https://grafana.com/grafana/dashboards?search=kasa%20collector).

### In General:

Each dashboard has dropdowns at the top that allow you to filter measurements based on devices and plugs. The dropdowns default to "All," but you can select and save preferences.

**Interval**:  A dropdown that provides different smoothing levels helps manage how the graphs look based on the interval of data collected by the Kasa Collector. Think of this as a level of "smoothing" based on your chosen time frame and the polling time you're collecting data. Be sure to set these to a time frame higher than your poll rate.

**Time Range**: This defaults to "Today so far" but can be updated to any other Relative or Absolute time range. To smooth out any data, change the "Interval" dropdown for longer time ranges.

**Dashboard Refresh**: Each dashboard is set to refresh every sixty seconds, but this can be changed or disabled.

### Kasa Collector - Energy (By Measurement) - [14762](https://grafana.com/grafana/dashboards/14762)

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector-energy_by_measurement.jpg"></center>

### Kasa Collector - Energy (By Device) - [14772](https://grafana.com/grafana/dashboards/14772)

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector-energy_by_device.jpg"></center>

The Energy dashboard provides panels representing Power, Watt-Hours, Current, and Voltage. Measurements are at the top for total combined information (and voltage average) and rows for both devices and plugs (as part of power strips). You can use the device and plug dropdown menus at the top of the dashboard to filter on each. If you choose a single device that happens to be a power strip, only the plugs for that power strip will be shown in the Plugs dropdown.

## Grafana Datasource

This collector uses InfluxQL, and for the dashboards to function, you need to create a data source in Grafana using the credentials you set in InfluxDB V2. More details can be found on the InfluxDB V2 Web site:

https://docs.influxdata.com/influxdb/v2/tools/grafana/?t=InfluxQL#configure-your-influxdb-connection

The most significant change here is:

 - Configure InfluxDB authentication:
   
   **Token authentication**
   Under **Custom HTTP Headers**, select **Add Header**. Provide your InfluxDB API token:
   
   **Header**: Enter `Authorization`
   
   **Value**: Use the `Token` schema and provide your InfluxDB API token. For example:
   
       Token y0uR5uP3rSecr3tT0k3n

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

Dave Schmid: dave@pulpfree.org

Project Link: https://github.com/lux4rd0/kasa-collector

## Acknowledgements

- Grafana Labs - [https://grafana.com/](https://grafana.com/)
- Grafana - [https://grafana.com/oss/grafana/](https://grafana.com/oss/grafana/)
- Grafana Dashboard Community - [https://grafana.com/grafana/dashboards/](https://grafana.com/grafana/dashboards/)
