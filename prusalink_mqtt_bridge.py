import requests
import json
import time
import logging
from paho.mqtt import client as mqtt_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PrusaLinkMQTTForwarder:
    def __init__(
        self,
        api_base_url,
        mqtt_broker,
        mqtt_port,
        mqtt_topic,
        http_username,
        http_password,
        mqtt_username,
        mqtt_password,
        update_interval_s,
        http_timeout=10,
    ):
        self.api_base_url = api_base_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
        self.lwt_topic = f"{mqtt_topic}/online"
        self.status_topic = f"{mqtt_topic}/server_online"
        self.http_auth = (http_username, http_password)
        self.update_interval = update_interval_s
        self.http_timeout = http_timeout
        self.mqtt_client = mqtt_client.Client("prusa_link_mqtt_bridge")

        # Set up MQTT authentication
        self.mqtt_client.username_pw_set(mqtt_username, mqtt_password)

        # Set up Last Will and Testament (LWT)
        self.mqtt_client.will_set(self.lwt_topic, payload="false", qos=1, retain=True)

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.connect(mqtt_broker, mqtt_port)
        self.mqtt_client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT Broker!")
            # Publish online status
            self.mqtt_client.publish(self.lwt_topic, "true", qos=1, retain=True)
        else:
            logging.error(f"Failed to connect, return code {rc}")

    def get_printer_data(self, endpoint):
        try:
            return self._extracted_from_get_printer_data_(endpoint)
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP Request failed: {e}")
            # Report HTTP server status as error
            self.mqtt_client.publish(self.status_topic, "false", qos=1)
            return None

    def _extracted_from_get_printer_data_(self, endpoint):
        url = f"{self.api_base_url}{endpoint}"
        response = requests.get(
            url, headers={"X-Api-Key": self.http_auth[1]}, timeout=self.http_timeout
        )  # password is api key
        if response.status_code == 200:
            return response.json()
        logging.error(
            f"Failed to get data from {url}, status code: {response.status_code}"
        )
        # Report HTTP server status as error
        self.mqtt_client.publish(self.status_topic, "false", qos=1)
        return None

    def publish_to_mqtt(self, topic, message):
        result = self.mqtt_client.publish(topic, message, qos=1)
        status = result[0]
        if status == 0:
            logging.info(f"Sent `{message}` to topic `{topic}`")
        else:
            logging.error(f"Failed to send message to topic {topic}")

    def run(self):
        try:
            next_run_time = time.time() + self.update_interval
            while True:
                printer_data = self.get_printer_data("/api/v1/status")
                if printer_data:
                    # Extract the 'printer' and 'job' data from the response
                    printer_info = printer_data.get("printer")
                    job_info = printer_data.get("job")

                    # Publish 'printer' data to its topic if it exists
                    if printer_info is not None:
                        self.publish_to_mqtt(
                            f"{self.mqtt_topic}/printer", json.dumps(printer_info)
                        )

                    # Publish 'job' data to its topic if it exists
                    if job_info is not None:
                        self.publish_to_mqtt(
                            f"{self.mqtt_topic}/job", json.dumps(job_info)
                        )

                    # Report HTTP server status as online
                    self.mqtt_client.publish(self.status_topic, "true", qos=1)

                # Calculate the time to sleep to maintain the update interval
                sleep_time = next_run_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                next_run_time += self.update_interval
        except KeyboardInterrupt:
            logging.info("Exiting...")
        finally:
            self.mqtt_client.loop_stop()


if __name__ == "__main__":
    from config import config

    forwarder = PrusaLinkMQTTForwarder(**config)
    forwarder.run()
