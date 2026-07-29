/*
 * Lumina Desk — E1002 WiFi display panel (battery, untethered).
 *
 * Receives 800x480 frames over MQTT (packed 2 bits/pixel: 0=white,1=black,2=red).
 *
 * Frame protocol on  lumina/table/<id>/frame :
 *   chunk   = [4-byte LE offset][data...]      -> memcpy into the frame buffer
 *   commit  = [0xFFFFFFFF][4-byte LE total]    -> render + refresh, then ACK
 *
 * ---------------------------------------------------------------------------
 * This panel is expected to survive anything the room does to it: the router
 * rebooting, the Pi getting a new DHCP lease, the Pi being switched off for a
 * day, the panel itself being switched off mid-refresh. So:
 *
 *   - The broker address is resolved on EVERY connect attempt, not once at
 *     boot. mDNS first; a previously-working IP from flash second; the
 *     compile-time fallback last. A working address is written back to flash,
 *     so even a panel that boots before the Pi (or with mDNS broken) reconnects
 *     to wherever it last found it.
 *   - Nothing blocks. Reconnects back off up to 30 s, and the buttons keep
 *     working the whole time.
 *   - A WiFi drop is retried, then escalated to a full radio restart, then to a
 *     reboot. A hardware watchdog catches anything that wedges below that.
 *   - A half-received frame is discarded rather than rendered, and the panel
 *     re-announces itself periodically so the Pi can push the current screen.
 * ---------------------------------------------------------------------------
 */
#include "TFT_eSPI.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <esp_task_wdt.h>
#include "wifi_secrets.h"

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

static const uint16_t IMG_W = 800, IMG_H = 480;
static const uint32_t PACKED = (uint32_t)IMG_W * IMG_H / 4;  // 96000
static uint8_t *fb = nullptr;
static uint32_t received = 0;
static uint32_t lastChunkAt = 0;

// How long to wait before giving up on things, in ms.
static const uint32_t FRAME_GAP_TIMEOUT = 30000;   // silence mid-frame -> discard
static const uint32_t WIFI_RETRY_EVERY  = 20000;   // re-issue WiFi.begin
static const uint32_t WIFI_REBOOT_AFTER = 300000;  // 5 min offline -> reboot
static const uint32_t HEARTBEAT_EVERY   = 60000;   // re-announce to the Pi
static const uint32_t MQTT_BACKOFF_MAX  = 30000;
static const uint32_t WDT_SECONDS       = 90;

WiFiClient net;
PubSubClient mqtt(net);
Preferences prefs;

String T_FRAME = String("lumina/table/") + TABLE_ID + "/frame";
String T_ACK   = String("lumina/table/") + TABLE_ID + "/frame/ack";
String T_PANEL = String("lumina/table/") + TABLE_ID + "/panel";
String T_BTN   = String("lumina/table/") + TABLE_ID + "/button";

// The three front buttons (active-low) and the buzzer, per Seeed's pinout.
static const uint8_t KEYS[3] = {2, 3, 5};
static const uint8_t BUZZER  = 45;
static uint32_t lastPress[3] = {0, 0, 0};

static uint32_t wifiDownSince   = 0;
static uint32_t lastWifiAttempt = 0;
static uint32_t nextMqttAttempt = 0;
static uint32_t mqttBackoff     = 1000;
static uint32_t lastHeartbeat   = 0;
static bool     everConnected   = false;

void beep(uint16_t ms = 60) {
  tone(BUZZER, 2000, ms);
}

void pollButtons() {
  for (int i = 0; i < 3; i++) {
    if (digitalRead(KEYS[i]) == LOW && millis() - lastPress[i] > 400) {  // debounce
      lastPress[i] = millis();
      beep();
      // Feedback is local, so a button still feels alive even with no broker.
      if (mqtt.connected()) {
        char msg[2] = {char('0' + i), 0};
        mqtt.publish(T_BTN.c_str(), msg);
      }
      Serial.printf("[btn] key %d pressed%s\n", i,
                    mqtt.connected() ? "" : " (offline, not sent)");
    }
  }
}

void renderBuf() {
#ifdef EPAPER_ENABLE
  if (!fb) return;
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
  // A colour refresh takes ~15-20 s, far longer than the watchdog's patience.
  esp_task_wdt_reset();
  epaper.update();
  esp_task_wdt_reset();
#endif
}

/* A first-boot message, so a panel that can't reach the Pi says why instead of
   sitting blank and looking broken. Drawn once — refreshes are far too slow to
   use this as a live status line. */
void showBootMessage(const char *line1, const char *line2) {
#ifdef EPAPER_ENABLE
  epaper.fillScreen(TFT_WHITE);
  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.setTextSize(3);
  epaper.drawString(line1, 60, 190);
  epaper.setTextSize(2);
  epaper.drawString(line2, 60, 250);
  esp_task_wdt_reset();
  epaper.update();
  esp_task_wdt_reset();
#endif
}

void onMsg(char *topic, byte *payload, unsigned int len) {
  if (len < 4 || !fb) return;
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
    lastChunkAt = millis();
  }
}

/* Where is the Pi right now?
   mDNS is the answer that survives a DHCP change, so it's tried first. If the
   network's multicast is unreliable (some cheap routers), fall back to the last
   address that actually worked, then to the one compiled in. */
IPAddress resolveBroker() {
  if (WiFi.status() == WL_CONNECTED) {
    IPAddress r = MDNS.queryHost(MQTT_HOSTNAME, 3000);
    esp_task_wdt_reset();
    if (r != IPAddress((uint32_t)0)) {
      Serial.printf("[mdns] %s.local -> %s\n", MQTT_HOSTNAME, r.toString().c_str());
      return r;
    }
    Serial.println("[mdns] no answer");
  }
  String saved = prefs.getString("broker", "");
  IPAddress ip;
  if (saved.length() && ip.fromString(saved)) {
    Serial.printf("[mqtt] using last known good %s\n", saved.c_str());
    return ip;
  }
  ip.fromString(MQTT_BROKER);
  Serial.printf("[mqtt] using compiled fallback %s\n", MQTT_BROKER);
  return ip;
}

void tryMqtt() {
  IPAddress broker = resolveBroker();
  mqtt.setServer(broker, MQTT_PORT);

  String cid = String("panel-table-") + TABLE_ID;
  if (mqtt.connect(cid.c_str())) {
    mqtt.subscribe(T_FRAME.c_str(), 1);
    mqtt.publish(T_PANEL.c_str(), "online", true);   // ask the Pi to (re)send
    lastHeartbeat = millis();
    mqttBackoff = 1000;
    received = 0;                                    // any partial frame is stale
    // Remember what worked, so the next boot doesn't depend on mDNS.
    String s = broker.toString();
    if (prefs.getString("broker", "") != s) prefs.putString("broker", s);
    Serial.printf("[mqtt] connected to %s\n", s.c_str());
    if (!everConnected) everConnected = true;
    return;
  }

  Serial.printf("[mqtt] connect failed rc=%d, retry in %lus\n",
                mqtt.state(), (unsigned long)(mqttBackoff / 1000));
  nextMqttAttempt = millis() + mqttBackoff;
  mqttBackoff = mqttBackoff * 2 > MQTT_BACKOFF_MAX ? MQTT_BACKOFF_MAX : mqttBackoff * 2;
}

void startWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);            // sleep adds seconds of latency to a refresh
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  lastWifiAttempt = millis();
}

void onWifiUp() {
  Serial.printf("\n[wifi] connected, IP %s\n", WiFi.localIP().toString().c_str());
  // mDNS is bound to the interface, so it has to come back up with it.
  MDNS.end();
  MDNS.begin("lumina-panel");
  nextMqttAttempt = 0;
  mqttBackoff = 1000;
}

void superviseWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (wifiDownSince) {                 // just came back
      wifiDownSince = 0;
      onWifiUp();
    }
    return;
  }

  uint32_t now = millis();
  if (!wifiDownSince) {
    wifiDownSince = now;
    Serial.println("[wifi] lost");
  }
  // Nothing has worked for minutes — the radio or the stack is wedged. A reboot
  // is a legitimate repair for a device stuck to a table with no keyboard.
  if (now - wifiDownSince > WIFI_REBOOT_AFTER) {
    Serial.println("[wifi] offline too long, restarting");
    delay(100);
    ESP.restart();
  }
  if (now - lastWifiAttempt > WIFI_RETRY_EVERY) {
    Serial.println("[wifi] retrying");
    WiFi.disconnect(true);
    delay(100);
    startWifi();
  }
}

void setup() {
  Serial.begin(115200);
  fb = (uint8_t *)ps_malloc(PACKED);
  if (!fb) fb = (uint8_t *)malloc(PACKED);
  if (!fb) Serial.println("[fb] ALLOCATION FAILED — frames will be dropped");

  prefs.begin("lumina", false);

  // The Arduino core may already have started the task watchdog, in which case
  // init() refuses and we just widen the timeout instead (a colour refresh
  // blocks for ~20 s, which the default would call a hang).
  esp_task_wdt_config_t wdt = {
      .timeout_ms = WDT_SECONDS * 1000,
      .idle_core_mask = 0,
      .trigger_panic = true,
  };
  if (esp_task_wdt_init(&wdt) == ESP_ERR_INVALID_STATE) esp_task_wdt_reconfigure(&wdt);
  esp_task_wdt_add(NULL);

#ifdef EPAPER_ENABLE
  epaper.begin();
#endif

  for (int i = 0; i < 3; i++) pinMode(KEYS[i], INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT);

  mqtt.setBufferSize(2048);          // holds one ~1 KB chunk + overhead
  mqtt.setKeepAlive(60);
  mqtt.setSocketTimeout(5);          // don't stall the loop on a dead broker
  mqtt.setCallback(onMsg);

  Serial.printf("\n[wifi] connecting to %s\n", WIFI_SSID);
  startWifi();
  uint32_t t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 20000) {
    delay(250);
    esp_task_wdt_reset();
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    onWifiUp();
  } else {
    Serial.println("\n[wifi] not up yet — will keep trying in the background");
    wifiDownSince = millis();
    showBootMessage("Can't reach the Wi-Fi",
                    "Check the network, then power-cycle this panel.");
  }
}

void loop() {
  esp_task_wdt_reset();
  superviseWifi();

  if (WiFi.status() == WL_CONNECTED) {
    if (!mqtt.connected()) {
      if (millis() >= nextMqttAttempt) tryMqtt();
    } else {
      mqtt.loop();
      // Re-announce now and then. If the Pi restarted, or a frame went missing,
      // this is what gets the current screen pushed again.
      if (millis() - lastHeartbeat > HEARTBEAT_EVERY) {
        mqtt.publish(T_PANEL.c_str(), "online", true);
        lastHeartbeat = millis();
      }
    }
  }

  // Chunks stopped arriving and no commit came. Whatever is in the buffer is a
  // torn frame; drop it so it can never be rendered on top of a later one.
  if (received && millis() - lastChunkAt > FRAME_GAP_TIMEOUT) {
    Serial.printf("[frame] incomplete (%lu bytes), discarded\n", (unsigned long)received);
    received = 0;
  }

  pollButtons();
  delay(10);
}
