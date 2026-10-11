import os
import pandas as pd

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


# =========================================================
# 1. CAU HINH
# =========================================================

load_dotenv()

URL = os.getenv("INFLUX_URL", "http://localhost:8086")
ORG = os.getenv("INFLUX_ORG", "")
BUCKET = os.getenv("INFLUX_BUCKET", "")
TOKEN = os.getenv("INFLUX_TOKEN", "")

DEVICE_ID = "esp32-wokwi"
SOURCE_MEASUREMENT = "sensor_telemetry"
OUTPUT_MEASUREMENT = "sensor_preprocessed"
OUTPUT_CSV = "preprocessed_data.csv"

FIELDS = [
    "temperature",
    "humidity",
    "distance_cm",
    "rssi",
]

if not all([ORG, BUCKET, TOKEN]):
    raise ValueError(
        "Hay kiem tra INFLUX_ORG, INFLUX_BUCKET "
        "va INFLUX_TOKEN trong file .env"
    )


# =========================================================
# 2. TRUY VAN DU LIEU THO TU INFLUXDB
# =========================================================

query = f'''
from(bucket: "{BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) =>
      r["_measurement"] == "{SOURCE_MEASUREMENT}"
  )
  |> filter(fn: (r) =>
      r["device_id"] == "{DEVICE_ID}"
  )
  |> filter(fn: (r) =>
      contains(
          value: r["_field"],
          set: ["temperature", "humidity", "distance_cm", "rssi"]
      )
  )
  |> pivot(
      rowKey: ["_time", "device_id"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> sort(columns: ["_time"])
'''


with InfluxDBClient(
    url=URL,
    token=TOKEN,
    org=ORG
) as client:

    query_api = client.query_api()
    tables = query_api.query_data_frame(query, org=ORG)

    # Chuyen ket qua truy van thanh mot DataFrame
    if isinstance(tables, list):
        frames = [
            table for table in tables
            if table is not None and not table.empty
        ]

        df = (
            pd.concat(frames, ignore_index=True)
            if frames
            else pd.DataFrame()
        )
    else:
        df = tables

    if df.empty:
        raise SystemExit(
            "Khong tim thay du lieu sensor_telemetry trong 24 gio qua. "
            "Hay kiem tra bucket, thoi gian va device_id."
        )

    if "_time" not in df.columns:
        raise SystemExit("Ket qua InfluxDB khong co cot _time.")

    # Chuan hoa timestamp
    df["_time"] = pd.to_datetime(df["_time"], utc=True)

    # Dam bao chi xu ly dung thiet bi
    if "device_id" in df.columns:
        df = df[df["device_id"] == DEVICE_ID].copy()

    df = (
        df.sort_values("_time")
        .drop_duplicates(
            subset=["_time"],
            keep="last"
        )
        .copy()
    )

    # Dam bao cac cot cam bien ton tai va la kieu so
    for col in FIELDS:
        if col not in df.columns:
            df[col] = float("nan")

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    print("=" * 55)
    print("THONG TIN DU LIEU THO")
    print("=" * 55)
    print("So dong du lieu tho:", len(df))
    print("Thoi gian bat dau:", df["_time"].min())
    print("Thoi gian ket thuc:", df["_time"].max())
    print("So moc thoi gian khac nhau:", df["_time"].nunique())
    print(
        "So phut co du lieu:",
        df["_time"].dt.floor("min").nunique()
    )

    print("\nSo gia tri thieu truoc khi xu ly:")
    print(df[FIELDS].isna().sum().to_string())

    # =====================================================
    # 3. LAM SACH VA NOI SUY DU LIEU THO
    # =====================================================

    df = df.set_index("_time").sort_index()

    # Gioi han gia tri vat ly co the kiem tra chac chan
    # Khong tu dong loai RSSI chi dua tren IQR
    invalid_humidity = (
        (df["humidity"] < 0)
        | (df["humidity"] > 100)
    )
    invalid_distance = df["distance_cm"] < 0

    df.loc[invalid_humidity, "humidity"] = float("nan")
    df.loc[invalid_distance, "distance_cm"] = float("nan")

    # Phat hien outlier bang IQR, chi danh dau va in thong ke.
    # Khong tu dong xoa/thay the outlier de tranh mat du lieu that.
    print("\nKiem tra outlier bang IQR:")
    for col in FIELDS:
        values = df[col].dropna()

        if len(values) < 4:
            print(f"{col}: khong du mau de kiem tra")
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        mask = (df[col] < lower) | (df[col] > upper)

        print(f"{col}: so outlier IQR = {int(mask.sum())}")

    # Noi suy chi cac khoang thieu ngan:
    # toi da 2 mau lien tiep, khong noi suy dau/cuoi chuoi.
    df[FIELDS] = df[FIELDS].interpolate(
        method="time",
        limit=2,
        limit_area="inside"
    )

    # =====================================================
    # 4. RESAMPLING THEO PHUT
    # =====================================================

    # Moi phut tinh gia tri trung binh tu cac mau co san.
    # Khoang phut khong co mau van la NaN.
    resampled = df[FIELDS].resample("1min").mean()

    print("\nSo dong sau resampling:", len(resampled))
    print("So gia tri thieu sau resampling:")
    print(resampled.isna().sum().to_string())

    # Chi noi suy toi da 2 phut lien tiep.
    # Khong dien cac khoang trong dai bang gia tri tu tao.
    resampled[FIELDS] = resampled[FIELDS].interpolate(
        method="time",
        limit=2,
        limit_area="inside"
    )

    # =====================================================
    # 5. TAO DAC TRUNG
    # =====================================================

    result = resampled.copy()

    for col in FIELDS:
        result[f"{col}_rolling_mean"] = (
            result[col]
            .rolling(window=3, min_periods=1)
            .mean()
        )

        result[f"{col}_delta"] = result[col].diff()

    # =====================================================
    # 6. CHUAN HOA MIN-MAX
    # =====================================================

    for col in FIELDS:
        min_val = result[col].min()
        max_val = result[col].max()

        normalized_col = f"{col}_normalized"

        if pd.notna(min_val) and pd.notna(max_val):
            if max_val > min_val:
                result[normalized_col] = (
                    (result[col] - min_val)
                    / (max_val - min_val)
                )
            else:
                result[normalized_col] = result[col].where(
                    result[col].isna(),
                    0.0
                )
        else:
            result[normalized_col] = float("nan")

    # Dua _time thanh cot de ghi CSV va InfluxDB
    result = result.reset_index()

    # Luu CSV; ghi de file ket qua cu, khong sua du lieu tho
    result.to_csv(OUTPUT_CSV, index=False)

    print("\nSo dong ket qua:", len(result))
    print("So gia tri thieu trong ket qua:")
    print(result.isna().sum().to_string())

    # =====================================================
    # 7. GHI VAO MEASUREMENT RIENG
    # =====================================================

    # Chi ghi nhung field co gia tri hop le.
    # Dung cung device_id voi measurement du lieu tho.
    write_api = client.write_api(
        write_options=SYNCHRONOUS
    )

    points = []

    try:
        for _, row in result.iterrows():
            timestamp = row["_time"]

            if pd.isna(timestamp):
                continue

            point = (
                Point(OUTPUT_MEASUREMENT)
                .tag("device_id", DEVICE_ID)
                .time(
                    timestamp.to_pydatetime(),
                    WritePrecision.NS
                )
            )

            field_count = 0

            for col in result.columns:
                if col == "_time":
                    continue

                value = row[col]

                if pd.notna(value):
                    point = point.field(
                        col,
                        float(value)
                    )
                    field_count += 1

            # Khong ghi point neu tat ca field deu thieu
            if field_count > 0:
                points.append(point)

        if points:
            write_api.write(
                bucket=BUCKET,
                org=ORG,
                record=points
            )

    finally:
        write_api.close()

    print("\n" + "=" * 55)
    print("DA HOAN TAT TIEN XU LY")
    print("=" * 55)
    print("File CSV:", OUTPUT_CSV)
    print("Measurement:", OUTPUT_MEASUREMENT)
    print("Device ID:", DEVICE_ID)
    print("So dong CSV:", len(result))
    print("So point co du lieu da gui:", len(points))
