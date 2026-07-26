/*
 * E1002 panel hardware test — cycles clean full-screen patterns to reveal
 * any stuck/missing line (hardware) vs a rendering artifact (software).
 * White -> Black -> White with border + crosshair + text.
 */
#include "TFT_eSPI.h"

#ifdef EPAPER_ENABLE
EPaper epaper;
#endif

void setup() {
  Serial.begin(115200);
#ifdef EPAPER_ENABLE
  epaper.begin();

  // 1) Full white — a stray dark line here = hardware artifact
  epaper.fillScreen(TFT_WHITE);
  epaper.update();
  delay(3500);

  // 2) Full black — a stray white line here = dead/missing line
  epaper.fillScreen(TFT_BLACK);
  epaper.update();
  delay(3500);

  // 3) Clean reference: white with a crisp border + centre crosshair
  epaper.fillScreen(TFT_WHITE);
  epaper.drawRect(0, 0, epaper.width(), epaper.height(), TFT_BLACK);
  epaper.drawRect(2, 2, epaper.width() - 4, epaper.height() - 4, TFT_BLACK);
  epaper.drawFastHLine(0, epaper.height() / 2, epaper.width(), TFT_RED);
  epaper.drawFastVLine(epaper.width() / 2, 0, epaper.height(), TFT_RED);
  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.drawString("PANEL TEST", 320, 190, 4);
  epaper.drawString("border + crosshair should be the ONLY lines", 190, 250, 2);
  epaper.update();
#endif
}

void loop() {}
