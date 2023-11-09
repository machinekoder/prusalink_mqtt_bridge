# PrusaLink MQTT Bridge

This utility facilitates the bridging of PrusaLink data to an MQTT broker, enabling remote monitoring and integration with home automation systems.

## Service

```bash
nano /etc/systemd/system/prusalink_mqtt_bridge.service
```

```ini
[Unit]
Description=PrusaLink MQTT Bridge
After=syslog.target network.target

[Service]
Type=simple
ExecStart=/bin/bash /home/pi/bin/co2watcher/start-prusalink_mqtt_bridge.sh
User=pi
LimitMEMLOCK=33554432
Restart=on-failure
RestartSec=5s # Waits 5 seconds before restarting the service

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start prusalink_mqtt_bridge.service
sudo systemctl enable prusalink_mqtt_bridge.service
```
