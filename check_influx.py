
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

url = os.getenv("INFLUX_URL")
token = os.getenv("INFLUX_TOKEN")
org = os.getenv("INFLUX_ORG")
bucket = os.getenv("INFLUX_BUCKET")

if not all([url, token, org, bucket]):
    raise RuntimeError("Thieu cau hinh InfluxDB trong file .env")

with InfluxDBClient(url=url, token=token, org=org) as client:
    health = client.health()
    print("InfluxDB status:", health.status)

    buckets = client.buckets_api().find_buckets().buckets
    names = [b.name for b in buckets]

    print("Buckets:", names)
    print("Bucket sensor_data:", "OK" if bucket in names else "NOT FOUND")
