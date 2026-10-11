# IoT Sensor Monitoring System

Hệ thống giám sát cảm biến IoT sử dụng ESP32, MQTT, Python, InfluxDB 2.x và Streamlit. Hệ thống thu thập dữ liệu cảm biến, lưu trữ dữ liệu chuỗi thời gian, tiền xử lý dữ liệu và trực quan hóa kết quả trên dashboard.

## 1. Mục tiêu dự án

- Thu thập dữ liệu cảm biến từ ESP32.
- Truyền dữ liệu qua giao thức MQTT.
- Sử dụng Python để nhận, kiểm tra và ghi dữ liệu vào InfluxDB.
- Tiền xử lý dữ liệu cảm biến để phục vụ phân tích.
- Theo dõi hiệu năng collector thông qua các chỉ số latency.
- Xây dựng dashboard trực quan bằng Streamlit.

## 2. Kiến trúc hệ thống

```text
DHT22 ─────┐
           ├──> ESP32 (Wokwi)
HC-SR04 ───┘          |
                      | MQTT
                      v
                MQTT Broker
                      |
                      v
              mqtt_collector.py
                 /          \
                v            v
           InfluxDB       Latency Log
                |
                v
           preprocess.py
                |
                v
      sensor_preprocessed
                |
                v
             app.py
                |
                v
        Streamlit Dashboard
```

ESP32 thu thập dữ liệu từ cảm biến và gửi bản tin MQTT. Python collector tiếp nhận dữ liệu và ghi vào InfluxDB. Script tiền xử lý tạo dữ liệu phục vụ phân tích, còn dashboard hiển thị dữ liệu gốc, dữ liệu sau tiền xử lý và các chỉ số latency.

## 3. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Thiết bị nhúng | ESP32 |
| Mô phỏng phần cứng | Wokwi |
| Cảm biến | DHT22, HC-SR04 |
| Giao thức truyền dữ liệu | MQTT |
| MQTT broker | EMQX Public Broker |
| Lưu trữ chuỗi thời gian | InfluxDB 2.x |
| Thu thập và tiền xử lý | Python, pandas |
| Giao diện giám sát | Streamlit |
| Cấu hình môi trường | python-dotenv |

## 4. Cấu trúc thư mục

```text
IOTB2/
├── .env                  # Cấu hình riêng, không đưa lên GitHub
├── .env.example          # Mẫu cấu hình
├── .gitignore            # Các file không theo dõi bằng Git
├── README.md             # Tài liệu dự án
├── app.py                # Dashboard Streamlit
├── mqtt_collector.py     # Thu thập MQTT và ghi InfluxDB
├── preprocess.py         # Tiền xử lý dữ liệu
├── write_influx.py       # Script ghi dữ liệu vào InfluxDB
├── test_mqtt.py          # Kiểm thử MQTT
├── test_thingsboard.py   # Kiểm thử ThingsBoard
├── collect_continuous.py # Script thu thập ThingsBoard nếu sử dụng
├── mqtt_latency_log.csv  # Log latency được tạo khi chạy collector
└── preprocessed_data.csv # Dữ liệu sau tiền xử lý
```

Cấu trúc trên mô tả các file chính của dự án. Chỉ giữ trong README những file thực sự có trong repository của bạn.

## 5. Yêu cầu môi trường

- Windows 10/11.
- Python 3.10 trở lên, tương thích với các thư viện của dự án.
- InfluxDB OSS 2.x.
- Kết nối Internet để sử dụng Wokwi và MQTT broker công khai.
- Trình duyệt web để xem dashboard.

## 6. Cài đặt

### Bước 1: Tạo môi trường Python

Mở Command Prompt (CMD), di chuyển đến thư mục dự án:

```cmd
cd /d "%USERPROFILE%\Downloads\IOTB2"
```

Tạo môi trường ảo:

```cmd
python -m venv .venv
```

Kích hoạt môi trường:

```cmd
.venv\Scripts\activate.bat
```

### Bước 2: Cài đặt thư viện

Nếu repository đã có file `requirements.txt`, chạy:

```cmd
python -m pip install -r requirements.txt
```

Nếu chưa có file này, cài các thư viện chính:

```cmd
python -m pip install pandas paho-mqtt influxdb-client python-dotenv streamlit
```

### Bước 3: Cài đặt và khởi động InfluxDB

Cài InfluxDB OSS 2.x và khởi động dịch vụ hoặc chạy `influxd.exe` theo cách cài đặt trên máy.

Mở giao diện:

http://localhost:8086

Thiết lập hoặc kiểm tra các thông tin:

- Organization: `iot-lab`
- Bucket: `sensor_data`
- API token có quyền đọc hoặc ghi phù hợp với các script.

Tên organization và bucket phải khớp với cấu hình thực tế.

## 7. Cấu hình môi trường

Sao chép `.env.example` thành `.env` trong thư mục dự án.

Có thể tạo bản sao bằng CMD:

```cmd
copy .env.example .env
```

Mở `.env` và điền các giá trị xác thực của bạn.

Các biến cấu hình:

| Biến | Ý nghĩa |
|---|---|
| `TB_URL` | Địa chỉ ThingsBoard |
| `TB_JWT` | Token xác thực ThingsBoard nếu script cần |
| `TB_DEVICE_ID` | ID thiết bị ThingsBoard nếu script cần |
| `INFLUX_URL` | Địa chỉ InfluxDB |
| `INFLUX_ORG` | Organization của InfluxDB |
| `INFLUX_BUCKET` | Bucket lưu dữ liệu |
| `INFLUX_TOKEN` | Token truy cập InfluxDB |

Không chia sẻ file `.env` và không commit file này lên GitHub. Chỉ đưa `.env.example` với các giá trị mẫu lên repository.

## 8. Chạy hệ thống

### Bước 1: Chạy mô phỏng ESP32

Mở dự án Wokwi:

https://wokwi.com/projects/476915759318808577n

Khởi chạy mô phỏng và kiểm tra firmware có gửi bản tin MQTT hay không.

Broker và topic đang dùng trong cấu hình dự án:

- Broker: `broker.emqx.io`
- Port: `1883`
- Topic: `iot-lab/sensors/telemetry/esp32-demo-7429`

Payload dự kiến chứa các trường:

- `temperature`
- `humidity`
- `distance_cm`
- `rssi`
- `sequence`
- `uptime_s`

Broker và topic phải khớp với firmware và collector thực tế.

### Bước 2: Chạy MQTT Collector

Mở một cửa sổ CMD riêng:

```cmd
cd /d "%USERPROFILE%\Downloads\IOTB2"
.venv\Scripts\activate.bat
python mqtt_collector.py
```

Collector nhận bản tin MQTT, kiểm tra dữ liệu và ghi vào InfluxDB. Khi được cấu hình bật ghi log latency, chương trình cũng tạo hoặc cập nhật file `mqtt_latency_log.csv`.

Giữ cửa sổ CMD này mở để tiếp tục thu thập dữ liệu.

### Bước 3: Tiền xử lý dữ liệu

Mở cửa sổ CMD khác:

```cmd
cd /d "%USERPROFILE%\Downloads\IOTB2"
.venv\Scripts\activate.bat
python preprocess.py
```

Script truy vấn dữ liệu cảm biến gốc, xử lý một số khoảng trống dữ liệu, thống kê ngoại lệ và tạo các đặc trưng phục vụ phân tích.

Kết quả có thể bao gồm:

- File `preprocessed_data.csv`.
- Measurement `sensor_preprocessed` trong InfluxDB.
- Các đặc trưng như rolling mean, delta và normalized, tùy theo mã nguồn hiện tại.

### Bước 4: Khởi chạy dashboard

Mở một cửa sổ CMD khác:

```cmd
cd /d "%USERPROFILE%\Downloads\IOTB2"
.venv\Scripts\activate.bat
python -m streamlit run app.py
```

Mở địa chỉ local được Streamlit hiển thị trong CMD, thường là:

http://localhost:8501

Dashboard hỗ trợ:

- Theo dõi dữ liệu cảm biến gốc.
- Xem dữ liệu sau tiền xử lý.
- Trực quan hóa rolling mean, delta và normalized.
- Xem thống kê số dòng và khoảng thời gian dữ liệu.
- Theo dõi latency collector nếu file log hợp lệ tồn tại.

## 9. Schema dữ liệu

### 9.1. Measurement `sensor_telemetry`

Lưu dữ liệu cảm biến gốc.

| Trường | Ý nghĩa | Đơn vị |
|---|---|---|
| `device_id` | Tag nhận diện thiết bị | — |
| `temperature` | Nhiệt độ | °C |
| `humidity` | Độ ẩm | % |
| `distance_cm` | Khoảng cách | cm |
| `rssi` | Cường độ tín hiệu Wi-Fi | dBm |
| `sequence` | Số thứ tự bản tin | — |
| `uptime_s` | Thời gian hoạt động thiết bị | giây |
| `_time` | Thời điểm ghi dữ liệu | Timestamp |

Tên field và tag thực tế phụ thuộc vào cách ánh xạ trong `mqtt_collector.py`.

### 9.2. Measurement `sensor_preprocessed`

Lưu dữ liệu sau tiền xử lý và các đặc trưng được tạo bởi `preprocess.py`.

Các nhóm dữ liệu có thể gồm:

- Các giá trị cảm biến sau xử lý.
- Giá trị trung bình trượt (rolling mean).
- Độ biến thiên giữa các mẫu (delta).
- Giá trị chuẩn hóa (normalized).

Tên field cụ thể cần đối chiếu với mã nguồn `preprocess.py`.

## 10. Theo dõi latency

Collector ghi các chỉ số hiệu năng vào `mqtt_latency_log.csv`, bao gồm các trường như:

- `timestamp_utc`: thời điểm đo.
- `sequence`: số thứ tự bản tin.
- `influx_write_ms`: thời gian của lời gọi ghi đồng bộ InfluxDB.
- `processing_ms`: thời gian xử lý callback theo cách đo trong chương trình.
- `status`: trạng thái ghi dữ liệu.

Các chỉ số này phản ánh thời gian xử lý phía collector và lời gọi ghi InfluxDB. Chúng không đại diện cho toàn bộ độ trễ đầu-cuối từ ESP32 đến dashboard.

Khi đánh giá kết quả, nên xem xét số mẫu, giá trị trung bình, trung vị, P95, giá trị lớn nhất và các đỉnh latency bất thường.




