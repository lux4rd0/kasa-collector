# Grafana Dashboards

After collecting data with Kasa Collector, you can visualize it using prebuilt Grafana dashboards. The links take you to the Grafana-hosted Dashboards. The number next to the link is the ID you can use in Grafana when importing. You can also find the latest JSON file under [grafana/shared](https://github.com/lux4rd0/kasa-collector/tree/main/grafana/shared).

## Available Dashboards

### [Kasa Collector - Device Details](https://grafana.com/grafana/dashboards/22015) - 22015

The Device Details dashboard provides an overview of connected smart devices and plugs, focusing on:
- Device state
- Software version
- Network connectivity
- Device names and models
- Firmware versions
- On/off status
- Individual plug states
- Real-time signal strength tracking

### [Kasa Collector - Energy (By Device)](https://grafana.com/grafana/dashboards/14772) - 14772

This dashboard offers panels representing:
- Power
- Watt-Hours
- Current
- Voltage

Measurements include:
- Total combined information
- Voltage average
- Device and plug-level details
- Filtering options for devices and plugs

### [Kasa Collector - Energy (By Measurement)](https://grafana.com/grafana/dashboards/14762) - 14762

Provides detailed insights into:
- Power
- Watt-hours
- Current
- Voltage for devices and plugs
- Combined metrics
- Comparative charts
- RSSI signal strength tracking

### [Kasa Collector - Energy (By Time)](https://grafana.com/grafana/dashboards/22014) - 22014

Summarizes energy consumption and costs:
- Watt Hours per device/day
- Plug-level energy usage
- Estimated daily device and plug costs
- Trend monitoring across multiple days

### [Kasa Collector - Status](https://grafana.com/grafana/dashboards/22015) - 22015

Real-time power consumption monitoring:
- Combined metrics for power, watt-hours, current, voltage