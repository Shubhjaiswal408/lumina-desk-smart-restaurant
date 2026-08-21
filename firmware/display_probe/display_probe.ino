/*
 * Lumina Desk — ePaper panel probe.
 *
 * Answers, in order, the three questions you actually have when a panel stays
 * blank:
 *   1. Did the driver config reach the compiler at all?
 *   2. Is the panel electrically there — does BUSY move when we talk to it?
 *   3. Can the library itself draw, ignoring our own packing code?
 *
 * If 3 draws and the real firmware doesn't, the fault is in our frame format.
 * If 3 is blank too, it's wiring, pins, or the wrong BOARD_SCREEN_COMBO.
 */
#include "TFT_eSPI.h"

#ifndef EPAPER_ENABLE
#error "EPAPER_ENABLE not defined - driver.h was not picked up."
#endif

EPaper epaper;

static void busyReport(const char *when) {
  Serial.printf("  BUSY(pin %d) = %d   %s\n", TFT_BUSY, digitalRead(TFT_BUSY), when);
}

void setup() {
  Serial.begin(115200);
  delay(2500);                       // native USB needs a moment to enumerate
  Serial.println("\n=== Lumina ePaper probe ===");
  Serial.printf("BOARD_SCREEN_COMBO %d\n", BOARD_SCREEN_COMBO);
  Serial.printf("pins  SCLK %d  MOSI %d  CS %d  DC %d  RST %d  BUSY %d\n",
                TFT_SCLK, TFT_MOSI, TFT_CS, TFT_DC, TFT_RST, TFT_BUSY);
  Serial.printf("panel %d x %d\n", TFT_WIDTH, TFT_HEIGHT);

  pinMode(TFT_BUSY, INPUT_PULLUP);
  busyReport("before reset");

  // An MCU reset does not reset the panel. If it was mid-refresh it keeps BUSY
  // asserted, and begin() waits for a line that will never be released — the
  // sketch hangs before printing anything and it looks like a dead panel.
  // Pulse RST first so the panel starts from a known state.
  pinMode(TFT_RST, OUTPUT);
  digitalWrite(TFT_RST, LOW);
  delay(20);
  digitalWrite(TFT_RST, HIGH);
  delay(200);
  busyReport("after reset pulse");

  uint32_t t = millis();
  epaper.begin();
  Serial.printf("begin() took %lu ms\n", (unsigned long)(millis() - t));
  busyReport("after begin()");

  // A full black screen is the least ambiguous thing a panel can show.
  Serial.println("filling BLACK...");
  epaper.fillScreen(TFT_BLACK);
  t = millis();
  epaper.update();
  Serial.printf("update() took %lu ms\n", (unsigned long)(millis() - t));
  busyReport("after black update()");

  delay(2000);

  Serial.println("drawing text on WHITE...");
  epaper.fillScreen(TFT_WHITE);
  epaper.setTextColor(TFT_BLACK, TFT_WHITE);
  epaper.drawString("LUMINA PROBE", 60, 150, 4);
  epaper.drawString("If you can read this,", 60, 220, 4);
  epaper.drawString("the panel and pins are fine.", 60, 270, 4);
  epaper.fillRect(60, 340, 300, 60, TFT_BLACK);
  t = millis();
  epaper.update();
  Serial.printf("update() took %lu ms\n", (unsigned long)(millis() - t));
  busyReport("after text update()");

  Serial.println("=== probe done ===");
}

void loop() { delay(5000); Serial.println("alive"); }
