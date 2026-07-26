/*
 * Lumina Desk — ePaper config verification + visible test
 */
#include "TFT_eSPI.h"

// Compile-time proof of what config actually got applied:
#ifdef BOARD_SCREEN_COMBO
#pragma message "CHECK: BOARD_SCREEN_COMBO IS defined"
#else
#pragma message "CHECK: BOARD_SCREEN_COMBO NOT defined  <-- driver.h ignored"
#endif
#ifdef EPAPER_ENABLE
#pragma message "CHECK: EPAPER_ENABLE ON (ePaper selected)"
#else
#pragma message "CHECK: EPAPER_ENABLE OFF  <-- panel NOT selected, binary is a no-op"
#endif

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

void setup() {
  Serial.begin(115200);
  delay(3000);
  Serial.println("=== BOOT OK ===");
#ifdef EPAPER_ENABLE
  epaper.begin();
  epaper.fillScreen(TFT_BLACK);
  epaper.update();
  delay(1500);
  epaper.fillScreen(TFT_WHITE);
  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.drawString("Hello, Lumina Desk!", 60, 190, 4);
  epaper.drawString("ePaper is alive - 800 x 480", 60, 260, 4);
  epaper.update();
  Serial.println("drew HELLO");
#endif
}

void loop() { Serial.println("alive"); delay(2000); }
