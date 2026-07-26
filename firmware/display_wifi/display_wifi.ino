/*
 * Lumina Desk — E1002 WiFi display panel (battery, untethered).
 *
 * Joins WiFi, connects to the Pi's MQTT broker, and receives 800x480 frames
 * over MQTT (packed 2 bits/pixel: 0=white,1=black,2=red). No USB needed.
 *
 * Frame protocol on  lumina/table/<id>/frame :
 *   chunk   = [4-byte LE offset][data...]      -> memcpy into the frame buffer
 *   commit  = [0xFFFFFFFF][4-byte LE total]    -> render + refresh, then ACK
 * Publishes "online" to lumina/table/<id>/panel so the Pi (re)sends the frame.
 */
#include "TFT_eSPI.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <PubSubClient.h>
#include "wifi_secrets.h"

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

static const uint16_t IMG_W = 800, IMG_H = 480;
static const uint32_t PACKED = (uint32_t)IMG_W * IMG_H / 4;  // 96000
static uint8_t *fb = nullptr;
static uint32_t received = 0;

WiFiClient net;
PubSubClient mqtt(net);

String T_FRAME = String("lumina/table/") + TABLE_ID + "/frame";
String T_ACK   = String("lumina/table/") + TABLE_ID + "/frame/ack";
String T_PANEL = String("lumina/table/") + TABLE_ID + "/panel";
String T_BTN   = String("lumina/table/") + TABLE_ID + "/button";

// The three front buttons (active-low) and the buzzer, per Seeed's pinout.
static const uint8_t KEYS[3] = {2, 3, 5};
static const uint8_t BUZZER  = 45;
static uint32_t lastPress[3] = {0, 0, 0};

void beep(uint16_t ms = 60) {
  tone(BUZZER, 2000, ms);
}

void pollButtons() {
  for (int i = 0; i < 3; i++) {
    if (digitalRead(KEYS[i]) == LOW && millis() - lastPress[i] > 400) {  // debounce
      lastPress[i] = millis();
      beep();
      char msg[2] = {char('0' + i), 0};
      mqtt.publish(T_BTN.c_str(), msg);
      Serial.printf("[btn] key %d pressed\n", i);
    }
  }
}

void renderBuf() {
#ifdef EPAPER_ENABLE
  uint32_t idx = 0;
  for (uint32_t i = 0; i < PACKED; i++) {
    uint8_t b = fb[i];
    for (int k = 0; k < 4; k++) {
      uint8_t v = (b >> (6 - 2 * k)) & 0x3;
      uint16_t c = (v == 0) ? TFT_WHITE : (v == 1) ? TFT_BLACK : TFT_RED;
      epaper.drawPixel(idx % IMG_W, idx / IMG_W, c);
      idx++;
    }
  }
  epaper.update();
#endif
}

void onMsg(char *topic, byte *payload, unsigned int len) {
  if (len < 4) return;
  uint32_t off = payload[0] | (payload[1] << 8) | (payload[2] << 16) | ((uint32_t)payload[3] << 24);

  if (off == 0xFFFFFFFF) {                 // commit -> render
    renderBuf();
    mqtt.publish(T_ACK.c_str(), "ok");
    received = 0;
    return;
  }
  uint32_t dlen = len - 4;
  if (off + dlen <= PACKED) {
    memcpy(fb + off, payload + 4, dlen);
    received += dlen;
  }
}

void connectMqtt() {
  int tries = 0;
  while (!mqtt.connected() && tries < 10) {
    String cid = String("panel-table-") + TABLE_ID;
    if (mqtt.connect(cid.c_str())) {
      mqtt.subscribe(T_FRAME.c_str(), 1);
      mqtt.publish(T_PANEL.c_str(), "online", true);   // ask Pi to (re)send frame
      return;
    }
    Serial.print("[mqtt] connect failed rc=");
    Serial.print(mqtt.state());
    Serial.println(" retrying...");
    tries++;
    delay(1500);
  }
}

void setup() {
  Serial.begin(115200);
  fb = (uint8_t *)ps_malloc(PACKED);
  if (!fb) fb = (uint8_t *)malloc(PACKED);

#ifdef EPAPER_ENABLE
  epaper.begin();
#endif

  for (int i = 0; i < 3; i++) pinMode(KEYS[i], INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT);

  Serial.print("\n[wifi] connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 20000) {
    delay(250);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\n[wifi] connected, IP ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[wifi] FAILED to connect (check SSID/password)");
  }

  // Resolve the Pi by mDNS so a DHCP IP change never breaks the panel.
  IPAddress broker;
  broker.fromString(MQTT_BROKER);          // fallback
  if (MDNS.begin("lumina-panel")) {
    IPAddress r = MDNS.queryHost(MQTT_HOSTNAME, 4000);
    if (r != IPAddress((uint32_t)0)) {
      broker = r;
      Serial.print("[mdns] "); Serial.print(MQTT_HOSTNAME);
      Serial.print(".local -> "); Serial.println(broker);
    } else {
      Serial.println("[mdns] not found, using fallback IP");
    }
  }
  mqtt.setServer(broker, MQTT_PORT);
  mqtt.setBufferSize(2048);          // holds one ~1 KB chunk + overhead
  mqtt.setKeepAlive(60);
  mqtt.setCallback(onMsg);
  Serial.print("[mqtt] connecting to ");
  Serial.println(broker);
  connectMqtt();
  Serial.println("[mqtt] connected + subscribed");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    delay(500);
    return;
  }
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  pollButtons();
}
