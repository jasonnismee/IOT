
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <math.h>

// ==================== WIFI ====================
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// ==================== MQTT BROKER ====================
const char* MQTT_SERVER = "broker.emqx.io";
const int MQTT_PORT = 1883;

// Đổi chuỗi này thành topic riêng của bạn.
// Dùng đúng topic này trong Python collector.
const char* MQTT_TOPIC =
    "iot-lab/sensors/telemetry/esp32-demo-7429";

// ==================== SENSOR PINS ====================
const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN = 2;

// Gửi dữ liệu mỗi 5 giây
const unsigned long SEND_INTERVAL_MS = 5000;

// ==================== MQTT CLIENT ====================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
DHTesp dht;

unsigned long lastSend = 0;
unsigned long sequenceNo = 0;

// ==================== WIFI CONNECTION ====================
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println(" connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// ==================== MQTT CONNECTION ====================
void connectMQTT() {
  while (!mqttClient.connected()) {
    String clientId =
        "ESP32-IOT-" +
        String((uint32_t)ESP.getEfuseMac(), HEX);

    Serial.print("Connecting to EMQX...");

    // Broker công cộng thử nghiệm không cần token ThingsBoard
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" connected");
      Serial.print("Publish topic: ");
      Serial.println(MQTT_TOPIC);
    } else {
      Serial.printf(
          " failed, rc=%d. Retry in 2 seconds\n",
          mqttClient.state()
      );

      delay(2000);
    }
  }
}

// ==================== READ DISTANCE ====================
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration =
      pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return NAN;
  }

  return duration * 0.0343f / 2.0f;
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(300);

  Serial.println();
  Serial.println("--- ESP32 MQTT IoT STARTING ---");

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  dht.setup(DHT_PIN, DHTesp::DHT22);

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setBufferSize(512);
  mqttClient.setKeepAlive(60);
  mqttClient.setSocketTimeout(10);

  connectWiFi();
}

// ==================== MAIN LOOP ====================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected()) {
    connectMQTT();
  }

  mqttClient.loop();

  unsigned long now = millis();

  if (now - lastSend < SEND_INTERVAL_MS) {
    return;
  }

  lastSend = now;

  // Đọc cảm biến
  TempAndHumidity data = dht.getTempAndHumidity();
  float distance = readDistanceCm();

  // Kiểm tra dữ liệu hợp lệ
  if (!isfinite(data.temperature) ||
      !isfinite(data.humidity) ||
      !isfinite(distance) ||
      data.humidity < 0 ||
      data.humidity > 100 ||
      distance < 0) {

    Serial.println(
        "Invalid sensor data - skip publish"
    );

    return;
  }

  sequenceNo++;

  // Tạo JSON telemetry
  char payload[256];

  snprintf(
      payload,
      sizeof(payload),
      "{\"temperature\":%.2f,"
      "\"humidity\":%.2f,"
      "\"distance_cm\":%.2f,"
      "\"rssi\":%d,"
      "\"sequence\":%lu,"
      "\"uptime_s\":%lu}",
      data.temperature,
      data.humidity,
      distance,
      WiFi.RSSI(),
      sequenceNo,
      millis() / 1000UL
  );

  // Publish dữ liệu lên MQTT broker
  bool ok = mqttClient.publish(
      MQTT_TOPIC,
      payload
  );

  Serial.printf(
      "%s | publish=%s\n",
      payload,
      ok ? "OK" : "FAILED"
  );

  // Nháy LED khi gửi thành công
  if (ok) {
    digitalWrite(LED_PIN, HIGH);
    delay(80);
    digitalWrite(LED_PIN, LOW);
  }
}
