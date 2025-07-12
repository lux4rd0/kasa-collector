# Deploying Kasa Collector

You can deploy Kasa Collector using Docker by following these steps:

## Docker Compose

Create a `compose.yaml` file:

```yaml
services:
  kasa-collector:
    image: lux4rd0/kasa-collector:latest
    container_name: kasa-collector
    network_mode: host
    restart: unless-stopped
    environment:
      # Required - InfluxDB Configuration
      KASA_COLLECTOR_INFLUXDB_URL: http://influxdb:8086
      KASA_COLLECTOR_INFLUXDB_TOKEN: your-token-here
      KASA_COLLECTOR_INFLUXDB_ORG: your-org
      KASA_COLLECTOR_INFLUXDB_BUCKET: kasa
      
      # Optional - For newer devices requiring authentication
      # KASA_COLLECTOR_TPLINK_USERNAME: your-email@example.com
      # KASA_COLLECTOR_TPLINK_PASSWORD: your-password
      
      # Optional - Manual device configuration (disables auto-discovery)
      # KASA_COLLECTOR_DEVICE_HOSTS: "192.168.1.100,192.168.1.101"
      # KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY: "false"
      
      # Optional - Timezone
      TZ: America/Chicago
```

Then deploy with:
```bash
docker compose up -d
```

## Docker Run

Alternatively, you can use this `docker run` command:

```bash
docker run -d \
  --name kasa-collector \
  --network host \
  --restart unless-stopped \
  -e KASA_COLLECTOR_INFLUXDB_URL=http://influxdb:8086 \
  -e KASA_COLLECTOR_INFLUXDB_TOKEN=your-token-here \
  -e KASA_COLLECTOR_INFLUXDB_ORG=your-org \
  -e KASA_COLLECTOR_INFLUXDB_BUCKET=kasa \
  -e TZ=America/Chicago \
  lux4rd0/kasa-collector:latest
```