/*
 * Lumina Desk — XIAO 7.5" mono ePaper display server (UC8179, 800x480 B/W).
 * Same image protocol as the color panel; red pixels map to black here.
 * Config in driver.h (BOARD_SCREEN_COMBO 502 + USE_XIAO_EPAPER_DRIVER_BOARD).
 *
 * Protocol (Pi -> ESP32): "LUMIMG" then 96000 bytes (2 bits/pixel, 4 px/byte,
 * row-major, MSB first: 0=white, 1=black, 2=red->black). ESP32 replies "OK\n".
 */
#include "TFT_eSPI.h"

// Without EPAPER_ENABLE the driver compiles away to nothing: begin() and
// update() vanish, the sketch still boots, still accepts a whole frame, and
// still answers "OK" — while the panel stays blank. That reads exactly like a
// hardware fault and sends you looking at the ribbon cable. Refuse to build.
#ifndef EPAPER_ENABLE
#error "EPAPER_ENABLE not defined - Seeed_GFX did not pick up driver.h."
#endif
#ifndef BOARD_SCREEN_COMBO
#error "BOARD_SCREEN_COMBO not defined - driver.h was not applied."
#endif

EPaper epaper;

static const uint16_t IMG_W = 800;
static const uint16_t IMG_H = 480;
static const uint32_t PACKED = (uint32_t)IMG_W * IMG_H / 4;  // 96000
static uint8_t *buf = nullptr;

static const char MAGIC[6] = {'L', 'U', 'M', 'I', 'M', 'G'};

void setup() {
  Serial.setRxBufferSize(16384);
  Serial.begin(921600);
  Serial.setTimeout(50);
  delay(200);

  buf = (uint8_t *)malloc(PACKED);   // C3 has no PSRAM; 96 KB fits in SRAM

  // Resetting the MCU does not reset the panel. If it was mid-refresh when we
  // rebooted (or the last sketch died), the panel keeps BUSY asserted and
  // begin() waits for a line that is never released — the board hangs here
  // forever, printing nothing further, which reads exactly like a dead panel.
  // Pulsing RST first puts it back in a known state. Measured: BUSY 0 -> 1.
  pinMode(TFT_BUSY, INPUT_PULLUP);
  pinMode(TFT_RST, OUTPUT);
  digitalWrite(TFT_RST, LOW);
  delay(20);
  digitalWrite(TFT_RST, HIGH);
  delay(200);
  Serial.printf("BOOT: panel reset, BUSY=%d\n", digitalRead(TFT_BUSY));

  Serial.println("BOOT: before epaper.begin()");
  epaper.begin();
  Serial.println("BOOT: after epaper.begin()");
  Serial.println("LUMINA_DISPLAY_READY");
}

bool waitMagic() {
  static uint8_t m = 0;
  while (Serial.available()) {
    int c = Serial.read();
    if (c == MAGIC[m]) { if (++m == 6) { m = 0; return true; } }
    else               { m = (c == MAGIC[0]) ? 1 : 0; }
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
      uint16_t color = (v == 0) ? TFT_WHITE : TFT_BLACK;  // mono: black & red -> black
      epaper.drawPixel(idx % IMG_W, idx / IMG_W, color);
      idx++;
    }
  }
  epaper.update();
#endif
}

void loop() {
  if (!waitMagic()) return;

  uint32_t got = 0, t = millis();
  while (got < PACKED && (millis() - t) < 15000) {
    int n = Serial.readBytes(buf + got, PACKED - got);
    if (n > 0) { got += n; t = millis(); }
  }
  if (got != PACKED) { Serial.printf("ERR got %lu\n", (unsigned long)got); return; }

  renderBuf();
  Serial.println("OK");
}
