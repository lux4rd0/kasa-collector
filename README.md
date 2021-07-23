## About The Project

<center><img src="https://labs.lux4rd0.com/wp-content/uploads/2021/07/sense_collector_header.png"></center>

**Sense Collector** is a set of scripts deployed with Docker that provide a way of collecting data from the [Sense](https://sense.com/) energy monitoring system. Once deployed, this collection of Grafana dashboards will help you start visualizing that data. If you're just getting started with Grafana, InfluxDB, and Sense - you may want to check out my [Sense Dashboards AIO](https://github.com/lux4rd0/sense-dashboards-aio) (All In One) project.

A live set of dashboards using this Collector [are available](https://labs.lux4rd0.com/sense-collector/) for you to try out.

## Getting Started

The project builds a pre-configured Docker container that takes different configurations based on how often you wish to poll your Sense device and where you want to store your data.

## Prerequisites

- [Docker](https://docs.docker.com/install)
- [Docker Compose](https://docs.docker.com/compose/install)
- [InfluxDB 1.8](https://docs.influxdata.com/influxdb/v1.8/) or [Grafana Loki 2.2](https://grafana.com/oss/loki/)
- [Grafana 8.0.6](https://grafana.com/oss/grafana/)

## Deploying the Sense Collector

Use the following [Docker container](https://hub.docker.com/r/lux4rd0/sense-collector):

    lux4rd0/sense-collector:1.0.1
    lux4rd0/sense-collector:latest
    
Sense Collector requires environmental variables for the container to function. It mainly includes a **Monitor ID** and a corresponding **authentication token**. If you don't have those, the following script may be used:

    generate_docker-compose.sh

The script takes the following details about your InfluxDB and your Sense credentials as environmental variables:

    SENSE_COLLECTOR_INFLUXDB_PASSWORD
    SENSE_COLLECTOR_INFLUXDB_URL
    SENSE_COLLECTOR_INFLUXDB_USERNAME
    SENSE_COLLECTOR_PASSWORD
    SENSE_COLLECTOR_USERNAME

The username and password are the same that you use in your Sense mobile app or the Sense Web app.

An example command line would be (be sure to use your own personal access token):

    SENSE_COLLECTOR_INFLUXDB_PASSWORD="5Q7c7hwQtsZtCrXW" \
    SENSE_COLLECTOR_INFLUXDB_URL="http://influxdb01.com:8086/write?db=sense" \
    SENSE_COLLECTOR_INFLUXDB_USERNAME="senseuser" \
    SENSE_COLLECTOR_PASSWORD="twFQ8P3XBj55DvMw" \
    SENSE_COLLECTOR_USERNAME="lux4rd0@domain.com" \
    bash ./generate_docker-compose.sh

The following file will be generated for you:

#### `docker-compose.yml`

An example of this docker-compose.yml file is included in this repository.

    services:
      sense-collector:
        container_name: sense-collector-72535
        environment:
          SENSE_COLLECTOR_HOST_HOSTNAME: sense-collector.lux4rd0.com
          SENSE_COLLECTOR_INFLUXDB_PASSWORD: none
          SENSE_COLLECTOR_INFLUXDB_URL: http://influxdb01.lux4rd0.com:8086/write?db=sense
          SENSE_COLLECTOR_INFLUXDB_USERNAME: none
          SENSE_COLLECTOR_MONITOR_ID: 72535
          SENSE_COLLECTOR_TOKEN: t1.1476.1474.8e6dc77daf22e1fb471d7b942w97e477d1es53bcf2d72
          TZ: America/Chicago
        image: lux4rd0/sense-collector:latest
        restart: always
    version: '3.3'

An example docker run command will be displayed on the screen.

    docker run --rm \
      --name=sense-collector-72535 \
      -e SENSE_COLLECTOR_HOST_HOSTNAME=app02.tylephony.com \
      -e SENSE_COLLECTOR_INFLUXDB_PASSWORD=5Q7c7hwQtsZtCrXW \
      -e SENSE_COLLECTOR_INFLUXDB_URL=http://influxdb01.lux4rd0.com:8086/write?db=sense \
      -e SENSE_COLLECTOR_INFLUXDB_USERNAME=senseuser \
      -e SENSE_COLLECTOR_MONITOR_ID=72535 \
      -e SENSE_COLLECTOR_TOKEN=t1.1476.1474.8e6dc77daf22e1fb471d7b942w97e477d1es53bcf2d72 \
      -e TZ=America/Chicago \
      --restart always \
      lux4rd0/sense-collector:latest

Running `docker-compose up -d' or the `docker-run` command will download and start up the sense-collector container. 

## Environmental Flags:

The Docker contain can be configured with additional environment flags to control collector behaviors. They are descript below:

`SENSE_COLLECTOR_DEBUG` - OPTIONAL

Outputs additional logging. Defaults to false.

- false
- true

`SENSE_COLLECTOR_DEBUG_CURL` - OPTIONAL

Outputs additional logging specific to the curl commands to collect data from Sense and persist data to InfluxDB. Defaults to false.

- true
- false

`SENSE_COLLECTOR_DEBUG_IF` - OPTIONAL

Outputs additional logging specific to script validation. Defaults to false.

- true
- false

`SENSE_COLLECTOR_DEBUG_SLEEPING` - OPTIONAL

Outputs additional logging specific to when the Collector is sleeping between polling. Sometimes you want to see if it's doing anything. Defaults to false.

- true
- false

`SENSE_COLLECTOR_DISABLE_DEVICE_DETAILS` - OPTIONAL

Disables or enables the Device Details process. Defaults to false if not set.

- true
- false

`SENSE_COLLECTOR_DISABLE_HEALTH_CHECK` - OPTIONAL

Disables or enables the Health Check process. Defaults to false if not set.

- true
- false

`SENSE_COLLECTOR_DISABLE_HOST_PERFORMANCE` - OPTIONAL

Disables or enables the Host Performance process. Defaults to false if not set.

- true
- false

`SENSE_COLLECTOR_DISABLE_MONITOR_STATUS` - OPTIONAL

Disables or enables the Monitor Status process. Defaults to false if not set.

- true
- false

`SENSE_COLLECTOR_DISABLE_SENSE_COLLECTOR` - OPTIONAL

Disables or enables the Sense Collector process. Defaults to false if not set.

- true
- false

`SENSE_COLLECTOR_HOST_HOSTNAME` - OPTIONAL

This value represents the hostname that is running the Docker container. Docker creates a unique hostname each time a docker container is recycled. This entry is used in the Collector Info dashboard to know where the Collector is running. This value is populated when the `generate_docker-compose.sh` script generates the `docker-compose.yml` file.

`SENSE_COLLECTOR_HOST_PERFORMANCE_POLL_INTERVAL` - OPTIONAL

Time in seconds that the Host Performance process polls the host for performance details. Defaults to 60 (seconds).

`SENSE_COLLECTOR_INFLUXDB_PASSWORD` - REQUIRED

The password to your InfluxDB database instance. If you use the `generate_docker-compose.sh` script, it defaults to "password". It is a **required** environment variable.

`SENSE_COLLECTOR_INFLUXDB_URL` - REQUIRED

The URL required to persist data to InfluxDB. If you use the `generate_docker-compose.sh` script, it defaults to "http://influxdb:8086/write?db=sense". It is a **required** environment variable.

`SENSE_COLLECTOR_INFLUXDB_USERNAME` - REQUIRED

The username to your InfluxDB database instance. If you use the `generate_docker-compose.sh` script, it defaults to "influxdb". It is a **required** environment variable.

`SENSE_COLLECTOR_MONITOR_ID` - REQUIRED

The ID of your Sense monitor. If you use the generate_docker-compose.sh script, it will be automatically added to your docker-compose.yml or docker-compose run command for you based on your Sense username and password. There's no way to know this ID from the Sense mobile or Web app. It is a **required** environment variable.

`SENSE_COLLECTOR_MONITOR_STATUS_POLL_INTERVAL` - OPTIONAL

Time in seconds that the Monitor Status process polls the Sense monitor for details. Defaults to 60 (seconds).

`SENSE_COLLECTOR_SENSE_COLLECTOR_POLL_INTERVAL` - OPTIONAL

Determines how often the core Sense Collector polls mains and device information. There are two types of collections possible:

 - stream

Allows for ingesting all of the stream data from the Sense socket API. The data is generally updated about two times a second and provides a very high granularity of metric data on all of your mains and devices. However, depending on the performance of the running Sense Collector host, it may fall behind on processing data as well as possibly higher CPU utilization. Take a look at the Collector Info dashboard for more understanding of the Sense Collector utilization.

or

 - 5, 10, 15, 30, or 60

Use one of these settings (measured in seconds) if streaming data is not an option or a desire to reduce the host CPU consumed. When providing these settings, the data stream is still passed through the Sense Collector to listen for timeline events, but it will only process mains and device details on the polling interval provided.

`SENSE_COLLECTOR_THREADS` - OPTIONAL

The number of threads used for processing device details. Defaults to 4. Set threads something close to the number of CPUs on your host. For slower processing hosts, lowering this and using a polling interval may be helpful.

`SENSE_COLLECTOR_TOKEN` - REQUIRED

The authentication token for your Sense monitor. If you use the generate_docker-compose.sh script, it will be automatically added to your docker-compose.yml or docker-compose run command for you based on your Sense username and password. There's no way to obtain this token from the Sense mobile or Web app. It is a **required** environment variable.

## Collector Details

#### sense-collector

Sense Collector is the primary data collector and is responsible for gathering details on the following:

Voltage, Watts, Hz on the mains, and device-specific wattage details. If you happen to have any [Sense compatible](https://help.sense.com/hc/en-us/articles/360012089393-What-smart-plugs-are-compatible-with-Sense-) smart plugs, their additional metric details of voltage and amps are collected.

Timeline events for devices change of states (on, off, idle)

#### device-details

Device Details polls the Sense API to gather details on each of your devices. This includes:

avg_duration, avg_monthly_KWH, avg_monthly_cost, avg_monthly_cost, avg_monthly_pct, avg_monthly_runs, avg_watts, current_ao_wattage, current_month_KWH, current_month_cost, current_month_runs, icon, last_state, last_state_time, name, yearly_KWH, yearly_cost, yearly_text

#### host-performance

Host Performance is a process that gathers CPU, process details, netstat, process counts, and memory utilization. These details are viewable in the Collector Info Grafana dashboard.

#### monitor-status

Monitor Status gathers details about the Sense monitor and detection status for both in progress and found devices. Monitor details include: emac, ethernet, ip_address, mac, ndt_enabled, online, progress, serial, signal, ssid, status, test_result, version, wifi_strength

#### health-check

Health Check is a function that runs every 60 seconds to validate the health of the running processes. If no data has been collected or persisted to InfluxDB and this parameter is set to true, the docker container will be marked as Unhealthy and terminate. Setting this to false will always return a healthy response to the Docker health check. The health check is included as there may be times when the socket connection goes silent, and recycling the container is the only way to get it listening again.

## Grafana Dashboards

Collecting data is only half the fun. Now it's time to provision some Grafana Dashboards to visualize all of your essential Sense data. You'll find a [folder of dashboards](https://github.com/lux4rd0/sense-collector/dashboards) with collectors and backends split out. You can also use the links/numbers next to each dashboard title to load the dashboards in [directly from Grafana](https://grafana.com/grafana/dashboards?search=sense%20collector).

### In General:

Each dashboard has dropdowns at the top that provide for filtering of measurements based on devices and plugs. They default to "All," but you can certainly select and save preferences.

**Interval**:  A dropdown that provides some different levels of smoothing helps manage how the graphs look based on the interval of data being collected by the Sense Collector. Think of this as a level of "smoothing" based on the time frame you've chosen and the quantity of data collected (streaming versus polled data.)

**Device Status On/Off/Idle**: These three toggles provide for the overlay of event annotations in the Wattage By Devices panels as well as the Wattage, Volts, and Hz panels in the Mains Overview dashboard.

**Sense Collector Dashboard Links**: This dropdown in the top right-hand corner provides easy access to the other dashboards in this collection. The links maintain the current time range and any variables that have been changed between dashboards. Meaning - if you change the time range from "Today so far" to "Last 7 days" it'll stay the same between dashboards. Same for any selected devices and Interval smoothing.

**Time Range**: This defaults to "Today so far" but can be updated to any other Relative or Absolute time range. For longer time ranges, be sure to make changes to the "Interval" dropdown if you want to smooth out any of the data.

**Dashboard Refresh**: Each of the dashboards are set to refresh every sixty seconds. The refresh can be changed or disabled altogether.

### Collector Info - [14734](https://grafana.com/grafana/dashboards/14734)

<center><img src="./images/sense_collector-screen_shot-collector_info.jpg"></center>

**Collector Info**:  Provides observability into how the Sense Collector functions alongside metrics related to the host's performance. This dashboard helps understand the performance of the main collector functions to assist with troubleshooting.

**Epoch Time Difference**: Helps determine if your hosts can keep up with processing messages from the Sense monitor. It provides the difference between the host time and the epoch time received in the Sense monitor data. Negative numbers mean the Sense monitor is ahead of the hosts. Positive numbers mean the host is behind the Sense monitor. If the drift trends to the positive, it may also mean that there's just time clock drift. Ensure you keep an eye on the NTP time sync on both your host and Sense if there's a large discrepancy.

**CPU, Load Average, Memory Utilization**:  These panels show host-level details and are not specific to the performance of the docker container. Per Process CPU Usage, Netstat, and Processes are particular to the container.

**Collector Starts**: Provide the last time the container and process were started.  The connection is reset every ten minutes due to the way Sense times out the connection.

### Device Overview - [14735](https://grafana.com/grafana/dashboards/14735)

<center><img src="./images/sense_collector-screen_shot-device_overview.jpg"></center>

**Device Overview** is the main dashboard for Sense Collector. Here you'll see several different sections about both overall and detailed device details.

**Current Wattage**: A Bubble Chart showing current wattage usage by device. Larger circles represent higher wattage consumption.

**Wattage By Device (Stacked)**: Wattage overtime per device. The graph is stacked to represent total household wattage.

**Device Status**: This is a State Timeline representing event data from the Sensor Monitor over time. It currently represents three states, On, Off, and Idle.

**Device Details - Average**: A table view of current data representing the current state, state time, watts in use, average, and always on makeup. Average duration, monthly kWh, percent, and the number of runs are also listed. This table defaults to be sorted by "Watts (In Use)."

**Device Details - Current Month**: Shows the number of runs per device since the start of the current month.

**Device Details - Yearly**: Shows calculated kWh and costs for each device. The text next to each device provides details on how the costs are calculated. For example, "Based on the last 30 days," "Based on the last 7 days," or "Based on last season."

**Plug Details**: If you have any of the [Sense compatible](https://help.sense.com/hc/en-us/articles/360012089393-What-smart-plugs-are-compatible-with-Sense-) smart plugs, they will be listed here as well. Open up this row to display Volts and Amps measured by each plug. There's another measurement (Who Knows By Plugs), but I don't know what it does yet.

**Always On Devices**: Shows which devices that the Sense monitor has detected to have an Always On wattage component. This may be different than actual wattage and tends to update less frequently.

> **Notice**: This Grafana dashboard uses the community visualization [Bubble Chart](https://grafana.com/grafana/plugins/digrich-bubblechart-panel/) panel plugin. It hasn't been updated for quite some time and won't work out of the box with current versions of Grafana due to plugin signing requirements. [Configuration changes](https://grafana.com/docs/grafana/latest/administration/configuration/#allow_loading_unsigned_plugins) on your Grafana instance will be needed to load this plugin.

### Mains Overview - [14736](https://grafana.com/grafana/dashboards/14736)

<center><img src="./images/sense_collector-screen_shot-mains_overview.jpg"></center>

**Mains Overview** provides three panels showing Wattage (Stacked), Voltages, and Frequency. There are dropdowns at the top of the dashboard to show Leg 1, Leg 2, or both together. Device Status On, Off, and Idle event annotations may be toggled on or off.

### Monitor & Detection - [14737](https://grafana.com/grafana/dashboards/14737)

<center><img src="./images/sense_collector-screen_shot-monitor_and_detection.jpg"></center>

The **Monitor & Detection** dashboard provides observability of the monitor itself.

**Device Detection Status**:  Represents Device Detection Status for both "Found" and "In Progress" devices.

**Wifi Signal Strength - RSSI**: Represents the Wifi signal strength of your Sense monitor.

**Monitor Details**: This panel shows current information about Online status, General Status, Learning Progress, IP Address, MAC Address, Wifi SSID, Wifi Strength, Ethernet, NDT Enabled, and software version. 

## Multiple Devices

The Sense Collector and dashboards currently only support a single Sense instance. If you have more than one Sense device and are interested in having multiple devices supported, please let me know.

### Time Zone Variable

A TZ variable is used when running the Docker container based on what value is returned during the initial docker-compose configuration scripts. It's not currently in use in any of the current dashboards.

## Roadmap

See the open issues for a list of proposed features (and known issues).

## Contact

Dave Schmid: [@lux4rd0](https://twitter.com/lux4rd0) - dave@pulpfree.org

Project Link: https://github.com/lux4rd0/sense-collector

## Acknowledgements

- Grafana Labs - [https://grafana.com/](https://grafana.com/)
- Grafana - [https://grafana.com/oss/grafana/](https://grafana.com/oss/grafana/)
- Grafana Dashboard Community - [https://grafana.com/grafana/dashboards/](https://grafana.com/grafana/dashboards/)
