/*
 * Lumina Desk — E1002 display server.
 *
 * Receives an 800x480 image from the Pi over serial and shows it on the color
 * ePaper. Pixels are packed 2 bits each (4 px/byte, row-major, MSB first):
 *   0 = white, 1 = black, 2 = red.   -> 800*480/4 = 96000 bytes per frame.
 *
 * Protocol (Pi -> ESP32):
 *   send  "LUMIMG"  then exactly 96000 bytes.
 *   ESP32 replies   "OK\n"  after the refresh, or "ERR ...\n".
 * On boot the ESP32 prints "LUMINA_DISPLAY_READY".
 */
#include "TFT_eSPI.h"

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

static const uint16_t IMG_W = 800;
static const uint16_t IMG_H = 480;
static const uint32_t PACKED = (uint32_t)IMG_W * IMG_H / 4;  // 96000
static uint8_t *buf = nullptr;

static const char MAGIC[6] = {'L', 'U', 'M', 'I', 'M', 'G'};

void setup() {
  Serial.setRxBufferSize(16384);   // must be before begin()
  Serial.begin(921600);
  Serial.setTimeout(50);
  delay(200);

  buf = (uint8_t *)ps_malloc(PACKED);
  if (!buf) buf = (uint8_t *)malloc(PACKED);

#ifdef EPAPER_ENABLE
  epaper.begin();      // no boot-clear; the first pushed frame sets the screen
#endif
  Serial.println("LUMINA_DISPLAY_READY");
}

// Scan the stream until the 6-byte magic is seen. Returns true when matched.
bool waitMagic() {
  static uint8_t m = 0;
  while (Serial.available()) {
    int c = Serial.read();
    if (c == MAGIC[m]) {
      if (++m == 6) { m = 0; return true; }
    } else {
      m = (c == MAGIC[0]) ? 1 : 0;
    }
  }
  return false;
}

void renderBuf() {
#ifdef EPAPER_ENABLE
  uint32_t idx = 0;
  for (uint32_t i = 0; i < PACKED; i++) {
    uint8_t b = buf[i];
    for (int k = 0; k < 4; k++) {
      uint8_t v = (b >> (6 - 2 * k)) & 0x3;
      uint16_t color = (v == 0) ? TFT_WHITE : (v == 1) ? TFT_BLACK : TFT_RED;
      epaper.drawPixel(idx % IMG_W, idx / IMG_W, color);
      idx++;
    }
  }
  epaper.update();  // full refresh
#endif
}

void loop() {
  if (!waitMagic()) return;

  // Read exactly PACKED bytes.
  uint32_t got = 0;
  uint32_t t = millis();
  while (got < PACKED && (millis() - t) < 15000) {
    int n = Serial.readBytes(buf + got, PACKED - got);
    if (n > 0) { got += n; t = millis(); }
  }

  if (got != PACKED) {
    Serial.printf("ERR got %lu of %lu\n", (unsigned long)got, (unsigned long)PACKED);
    return;
  }

  renderBuf();
  Serial.println("OK");
}
