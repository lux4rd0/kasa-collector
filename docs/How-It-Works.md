# How It Works

Kasa Collector is designed to automate data collection from Kasa Smart Plugs. It offers two modes of device configuration:

## Automatic Device Discovery

Kasa Collector automatically discovers compatible Kasa devices on your network. By default, it sends discovery packets regularly and identifies devices that support energy monitoring.

Control automatic discovery using the `KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY` environment variable:
- **Enable Auto-Discovery:** Set to `true`
- **Disable Auto-Discovery:** Set to `false`

## Manual Device Configuration

For devices not automatically discovered, manually specify device IPs or hostnames using `KASA_COLLECTOR_DEVICE_HOSTS`. This variable accepts a comma-separated list of device IPs/hostnames.

**Example:** `KASA_COLLECTOR_DEVICE_HOSTS="10.50.0.101,10.50.0.102"`

## TP-Link Account Configuration

For Kasa devices requiring TP-Link account authentication, provide credentials using:
- `KASA_COLLECTOR_TPLINK_USERNAME`
- `KASA_COLLECTOR_TPLINK_PASSWORD`

These credentials enable control of TP-Link cloud-authenticated devices.

For a complete list of environment variables, refer to the [Environmental Flags](Environmental-Flags.md) page.