
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# Doc cau hinh tu file .env
load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = os.getenv("INFLUX_ORG", "iot-lab")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_data")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")

RAW_MEASUREMENT = "sensor_telemetry"
PROCESSED_MEASUREMENT = "sensor_preprocessed"

st.set_page_config(
    page_title="IoT Sensor Monitoring",
    page_icon="📡",
    layout="wide",
)

st.title("📡 IoT Sensor Monitoring")
st.write(
    "Ứng dụng giám sát dữ liệu cảm biến IoT "
    "và dữ liệu sau tiền xử lý."
)

if not INFLUX_TOKEN:
    st.error(
        "Chưa tìm thấy INFLUX_TOKEN trong file .env. "
        "Hãy kiểm tra cấu hình InfluxDB của bạn."
    )
    st.stop()

# Thanh ben
with st.sidebar:
    st.header("Cấu hình")
    time_option = st.selectbox(
        "Khoảng thời gian",
        ["1 giờ qua", "6 giờ qua", "24 giờ qua", "7 ngày qua"],
        index=2,
    )

    time_ranges = {
        "1 giờ qua": "-1h",
        "6 giờ qua": "-6h",
        "24 giờ qua": "-24h",
        "7 ngày qua": "-7d",
    }

    if st.button("🔄 Tải lại dữ liệu"):
        st.cache_data.clear()

    st.caption(f"InfluxDB: {INFLUX_URL}")
    st.caption(f"Bucket: {INFLUX_BUCKET}")
    st.caption(f"Organization: {INFLUX_ORG}")


@st.cache_data(ttl=15)
def read_influx(measurement, time_range):
    """Doc du lieu InfluxDB va chuyen thanh bang."""
    query = f'''
from(bucket: "{INFLUX_BUCKET}")
    |> range(start: {time_range})
    |> filter(fn: (r) =>
        r["_measurement"] == "{measurement}"
    )
    |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
    )
    |> sort(columns: ["_time"])
'''

    with InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
        timeout=20000,
    ) as client:
        result = client.query_api().query_data_frame(
            query=query,
            org=INFLUX_ORG,
        )

    if isinstance(result, pd.DataFrame):
        df = result.copy()
    elif result:
        frames = [frame for frame in result if not frame.empty]
        df = (
            pd.concat(frames, ignore_index=True)
            if frames else pd.DataFrame()
        )
    else:
        df = pd.DataFrame()

    if not df.empty and "_time" in df.columns:
        df["_time"] = pd.to_datetime(
            df["_time"], utc=True, errors="coerce"
        )
        df = df.dropna(subset=["_time"])
        df = df.sort_values("_time")

    return df


def show_chart(df, fields, title):
    available = [
        field for field in fields
        if field in df.columns
        and pd.api.types.is_numeric_dtype(df[field])
    ]

    if not available:
        st.info(f"Chưa có trường dữ liệu phù hợp cho {title}.")
        return

    selected = st.multiselect(
        f"Chọn dữ liệu — {title}",
        options=available,
        default=available[:2],
        key=title,
    )

    if selected:
        chart_data = df.set_index("_time")[selected]
        st.line_chart(chart_data, height=300)


# Doc du lieu
try:
    with st.spinner("Đang tải dữ liệu từ InfluxDB..."):
        raw_df = read_influx(
            RAW_MEASUREMENT, time_ranges[time_option]
        )
        processed_df = read_influx(
            PROCESSED_MEASUREMENT, time_ranges[time_option]
        )

except Exception as error:
    st.error(
        "Không thể đọc dữ liệu từ InfluxDB. "
        "Hãy kiểm tra InfluxDB đang chạy và cấu hình trong .env."
    )
    st.code(str(error))
    st.stop()


# PHAN 1: DU LIEU CAM BIEN GOC
st.header("1. Dữ liệu cảm biến gốc")

if raw_df.empty:
    st.warning(
        "Không tìm thấy dữ liệu sensor_telemetry "
        "trong khoảng thời gian đã chọn. "
        "Hãy chạy chương trình thu thập hoặc chọn khoảng dài hơn."
    )
else:
    latest = raw_df.iloc[-1]

    sensor_info = [
        ("temperature", "Nhiệt độ", " °C"),
        ("humidity", "Độ ẩm", " %"),
        ("distance_cm", "Khoảng cách", " cm"),
        ("rssi", "Wi-Fi RSSI", " dBm"),
    ]

    columns = st.columns(4)

    for index, (field, label, unit) in enumerate(sensor_info):
        if field in raw_df.columns:
            value = latest[field]
            display_value = (
                f"{value:.2f}{unit}"
                if pd.notna(value) else "N/A"
            )
            columns[index].metric(label, display_value)
        else:
            columns[index].metric(label, "N/A")

    st.caption(
        f"Số dòng dữ liệu: {len(raw_df)} | "
        f"Thời điểm mới nhất: {latest['_time']}"
    )

    show_chart(
        raw_df,
        ["temperature", "humidity", "distance_cm"],
        "Dữ liệu cảm biến gốc",
    )

    with st.expander("Xem bảng dữ liệu gốc"):
        st.dataframe(
            raw_df,
            use_container_width=True,
            hide_index=True,
        )


# PHAN 2: DU LIEU SAU TIEN XU LY
st.divider()
st.header("2. Dữ liệu sau tiền xử lý")

if processed_df.empty:
    st.warning(
        "Không tìm thấy dữ liệu sensor_preprocessed. "
        "Hãy chạy preprocess.py trước, sau đó tải lại ứng dụng."
    )
else:
    st.caption(
        f"Số dòng dữ liệu sau tiền xử lý: {len(processed_df)}"
    )

    excluded = {
        "_time", "_start", "_stop", "_measurement",
        "_field", "_value", "result", "table", "device_id",
    }

    numeric_fields = [
        col for col in processed_df.columns
        if col not in excluded
        and pd.api.types.is_numeric_dtype(processed_df[col])
    ]

    rolling_fields = [
        col for col in numeric_fields
        if col.endswith("_rolling_mean")
    ]
    delta_fields = [
        col for col in numeric_fields
        if col.endswith("_delta")
    ]
    normalized_fields = [
        col for col in numeric_fields
        if col.endswith("_normalized")
    ]

    tab1, tab2, tab3 = st.tabs([
        "Rolling Mean", "Delta", "Normalized"
    ])

    with tab1:
        show_chart(
            processed_df,
            rolling_fields,
            "Rolling Mean",
        )

    with tab2:
        show_chart(
            processed_df,
            delta_fields,
            "Delta",
        )

    with tab3:
        show_chart(
            processed_df,
            normalized_fields,
            "Normalized",
        )

    with st.expander("Xem bảng dữ liệu đã tiền xử lý"):
        st.dataframe(
            processed_df,
            use_container_width=True,
            hide_index=True,
        )


# PHAN 3: THONG KE
st.divider()
st.header("3. Thống kê dữ liệu")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Dữ liệu gốc")
    st.metric("Số dòng", len(raw_df))
    st.metric("Số cột", len(raw_df.columns))

    if not raw_df.empty:
        st.write("Bắt đầu:", str(raw_df["_time"].min()))
        st.write("Kết thúc:", str(raw_df["_time"].max()))

with col2:
    st.subheader("Dữ liệu tiền xử lý")
    st.metric("Số dòng", len(processed_df))
    st.metric("Số cột", len(processed_df.columns))

    if not processed_df.empty:
        st.write("Bắt đầu:", str(processed_df["_time"].min()))
        st.write("Kết thúc:", str(processed_df["_time"].max()))

st.divider()
st.caption(
    "IoT Sensor Monitoring | Streamlit + InfluxDB 2.x"
)
# =========================================================
# PHAN 4: MQTT LATENCY
# =========================================================

st.divider()
st.header("4. Hiệu năng MQTT Collector")

LATENCY_FILE = "mqtt_latency_log.csv"

if not os.path.exists(LATENCY_FILE):
    st.warning(
        "Chưa tìm thấy mqtt_latency_log.csv. "
        "Hãy chạy mqtt_collector.py để bắt đầu ghi latency."
    )
else:
    try:
        latency_df = pd.read_csv(LATENCY_FILE)

        if latency_df.empty:
            st.info("File latency chưa có dữ liệu.")
        else:
            required_cols = [
                "timestamp_utc",
                "influx_write_ms",
                "processing_ms",
                "status",
            ]

            missing_cols = [
                col for col in required_cols
                if col not in latency_df.columns
            ]

            if missing_cols:
                st.error(
                    "File latency thiếu cột: "
                    + ", ".join(missing_cols)
                )
            else:
                latency_df["timestamp_utc"] = pd.to_datetime(
                    latency_df["timestamp_utc"],
                    utc=True,
                    errors="coerce",
                )

                for col in [
                    "influx_write_ms",
                    "processing_ms",
                ]:
                    latency_df[col] = pd.to_numeric(
                        latency_df[col],
                        errors="coerce",
                    )

                latency_df = latency_df.dropna(
                    subset=[
                        "timestamp_utc",
                        "influx_write_ms",
                        "processing_ms",
                    ]
                ).sort_values("timestamp_utc")

                if latency_df.empty:
                    st.warning(
                        "Chưa có mẫu latency hợp lệ để hiển thị."
                    )
                else:
                    write_avg = latency_df[
                        "influx_write_ms"
                    ].mean()

                    processing_avg = latency_df[
                        "processing_ms"
                    ].mean()

                    p95_write = latency_df[
                        "influx_write_ms"
                    ].quantile(0.95)

                    p95_processing = latency_df[
                        "processing_ms"
                    ].quantile(0.95)

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "Số mẫu latency",
                        len(latency_df),
                    )
                    c2.metric(
                        "Ghi InfluxDB TB",
                        f"{write_avg:.2f} ms",
                    )
                    c3.metric(
                        "Processing TB",
                        f"{processing_avg:.2f} ms",
                    )
                    c4.metric(
                        "P95 Processing",
                        f"{p95_processing:.2f} ms",
                    )

                    st.subheader("Latency theo thời gian")

                    chart_df = latency_df.set_index(
                        "timestamp_utc"
                    )[
                        [
                            "influx_write_ms",
                            "processing_ms",
                        ]
                    ]

                    st.line_chart(
                        chart_df,
                        height=320,
                    )

                    st.subheader("Thống kê latency")

                    stats = latency_df[
                        [
                            "influx_write_ms",
                            "processing_ms",
                        ]
                    ].describe(
                        percentiles=[0.5, 0.95]
                    ).round(2)

                    st.dataframe(
                        stats,
                        use_container_width=True,
                    )

                    st.caption(
                        "P95 ghi InfluxDB: "
                        f"{p95_write:.2f} ms. "
                        "Đây là thời gian ghi đồng bộ đo từ "
                        "phía collector, không phải latency "
                        "đầu-cuối từ ESP32 đến dashboard."
                    )

                    with st.expander(
                        "Xem dữ liệu latency chi tiết"
                    ):
                        st.dataframe(
                            latency_df,
                            use_container_width=True,
                            hide_index=True,
                        )

    except Exception as error:
        st.error(
            "Không thể đọc file mqtt_latency_log.csv."
        )
        st.code(str(error))
