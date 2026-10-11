import csv
import json
import os
import time
import math
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv()

MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "iot-lab/sensors/telemetry/esp32-demo-7429"

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_data")

CSV_FILE = "mqtt_latency_log.csv"

if not all([INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET]):
    raise RuntimeError(
        "Thieu INFLUX_TOKEN, INFLUX_ORG hoac INFLUX_BUCKET trong .env"
    )

# ==========================================
# 2. INITIALIZE CSV LOG
# ==========================================

if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp_utc",
            "sequence",
            "influx_write_ms",
            "processing_ms",
            "status",
        ])

# ==========================================
# 3. CONNECT TO INFLUXDB
# ==========================================

db = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
)

# Synchronous mode: write() waits for the server response
write_api = db.write_api(write_options=SYNCHRONOUS)


# ==========================================
# 4. MQTT CALLBACKS
# ==========================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("MQTT connected")

        result, _ = client.subscribe(MQTT_TOPIC)

        if result == mqtt.MQTT_ERR_SUCCESS:
            print("Subscribed:", MQTT_TOPIC)
        else:
            print("Subscribe failed:", result)
    else:
        print("MQTT connection failed:", reason_code)


def on_message(client, userdata, msg):
    callback_start = time.perf_counter()

    try:
        data = json.loads(msg.payload.decode("utf-8"))

        required = [
            "temperature",
            "humidity",
            "distance_cm",
            "rssi",
            "sequence",
            "uptime_s",
        ]

        for key in required:
            if key not in data:
                raise ValueError(f"Missing field: {key}")

        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        distance = float(data["distance_cm"])
        rssi = int(data["rssi"])
        sequence = int(data["sequence"])
        uptime = int(data["uptime_s"])

        numeric_values = [
            temperature,
            humidity,
            distance,
        ]

        if not all(math.isfinite(v) for v in numeric_values):
            raise ValueError("Non-finite sensor value")

        if not 0 <= humidity <= 100 or distance < 0:
            raise ValueError("Sensor value out of range")

        # Build InfluxDB point
        point = (
            Point("sensor_telemetry")
            .tag("device_id", "esp32-wokwi")
            .field("temperature", temperature)
            .field("humidity", humidity)
            .field("distance_cm", distance)
            .field("rssi", float(rssi))
            .field("sequence", float(sequence))
            .field("uptime_s", float(uptime))
            .time(time.time_ns(), WritePrecision.NS)
        )

        # Measure synchronous InfluxDB write duration
        write_start = time.perf_counter()

        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point,
        )

        influx_write_ms = (
            time.perf_counter() - write_start
        ) * 1000

        processing_ms = (
            time.perf_counter() - callback_start
        ) * 1000

        timestamp_utc = datetime.now(timezone.utc).isoformat()

        # Append successful write measurements to CSV
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp_utc,
                sequence,
                round(influx_write_ms, 3),
                round(processing_ms, 3),
                "OK",
            ])

        print(
            f"Saved | seq={sequence} | "
            f"temp={temperature:.2f} C | "
            f"humidity={humidity:.2f}% | "
            f"distance={distance:.2f} cm | "
            f"Influx write={influx_write_ms:.2f} ms | "
            f"Processing={processing_ms:.2f} ms"
        )

    except Exception as exc:
        print("Message rejected/error:", exc)


# ==========================================
# 5. START MQTT CLIENT
# ==========================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"iot-collector-{int(time.time())}",
    protocol=mqtt.MQTTv311,
)

client.on_connect = on_connect
client.on_message = on_message

try:
    print("Connecting to MQTT...")
    print("InfluxDB URL:", INFLUX_URL)
    print("InfluxDB bucket:", INFLUX_BUCKET)
    print("Latency log:", CSV_FILE)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

except KeyboardInterrupt:
    print("\nStopping collector...")

except Exception as exc:
    print("Collector error:", exc)

finally:
    client.disconnect()
    write_api.close()
    db.close()
    print("Collector stopped.")