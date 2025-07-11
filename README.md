# Kasa Collector

![Kasa Collector](https://labs.lux4rd0.com/wp-content/uploads/2021/07/kasa_collector_header.png)

**Kasa Collector** is a Python-based application deployed with Docker that discovers and monitors TP-Link Kasa smart plugs and power strips on your network. It continuously collects energy consumption data and stores it in InfluxDB for visualization with Grafana dashboards.

A live set of dashboards using this Collector [are available here](https://labs.lux4rd0.com/kasa-collector/) for you to explore.

## Quick Start

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
```

## Documentation

Full documentation is available in the [docs/wiki](docs/wiki) directory:

- **[Getting Started](docs/wiki/Getting-Started.md)** - Initial setup guide
- **[Configuration](docs/wiki/Environmental-Flags.md)** - All environment variables
- **[Supported Devices](docs/wiki/Supported-Devices.md)** - Compatible Kasa devices
- **[Grafana Dashboards](docs/wiki/Grafana-Dashboards.md)** - Visualization setup
- **[Troubleshooting](docs/wiki/Troubleshooting.md)** - Common issues and solutions
- **[FAQ](docs/wiki/FAQ.md)** - Frequently asked questions
- **[How It Works](docs/wiki/How-It-Works.md)** - Technical details

## Features

- Automatic device discovery
- Energy monitoring (power, current, voltage, consumption)
- Smart power strip support with individual outlet monitoring
- Docker health checks
- Grafana dashboards included
- Production-ready with graceful shutdown

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/lux4rd0/kasa-collector/issues)
- **Author**: Dave Schmid ([dave@pulpfree.org](mailto:dave@pulpfree.org))
- **Live Demo**: [https://labs.lux4rd0.com/kasa-collector/](https://labs.lux4rd0.com/kasa-collector/)

---

**Note**: This project is not affiliated with TP-Link or Kasa. It's an independent tool for monitoring energy consumption of Kasa smart devices.