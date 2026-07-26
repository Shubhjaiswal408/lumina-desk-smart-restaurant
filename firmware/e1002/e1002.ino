/*
 * Lumina Desk — reTerminal E1002 "Hello" test
 * ESP32-S3, 7.5" color (B/W/Red) ePaper, 800x480, ED2208, Seeed_GFX.
 * Config in driver.h (BOARD_SCREEN_COMBO 521).
 */
#include "TFT_eSPI.h"

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("=== BOOT OK (E1002) ===");

#ifdef EPAPER_ENABLE
  Serial.println("EPAPER_ENABLE defined -> drawing");
  epaper.begin();
  epaper.setRotation(0);
  epaper.fillScreen(TFT_WHITE);

  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.drawString("Hello, Lumina Desk!", 60, 160, 4);

  epaper.setTextColor(TFT_RED, TFT_WHITE);
  epaper.drawString("reTerminal E1002 - 800 x 480 color", 60, 230, 4);

  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.drawString("ePaper is alive", 60, 300, 4);

  epaper.update();
  Serial.println("drew HELLO + update done");
#else
  Serial.println("EPAPER_ENABLE NOT defined");
#endif
}

void loop() {
  Serial.println("alive");
  delay(3000);
}
