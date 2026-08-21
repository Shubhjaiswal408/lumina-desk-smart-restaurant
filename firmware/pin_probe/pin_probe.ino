/*
 * Is the panel electrically there?
 *
 * Reads BUSY with an internal pull-up and then a pull-down. A pin that simply
 * follows whichever pull we apply is connected to nothing — the panel is not
 * driving it, so the ribbon is unseated or the board isn't mated. A pin held by
 * the panel will refuse to follow at least one of them.
 *
 * Touches no display driver, so it cannot hang.
 */
#include "TFT_eSPI.h"

void setup() {
  Serial.begin(115200);
  delay(2500);
  Serial.println("\n=== pin probe ===");
  Serial.printf("BUSY=%d RST=%d CS=%d DC=%d SCLK=%d MOSI=%d\n",
                TFT_BUSY, TFT_RST, TFT_CS, TFT_DC, TFT_SCLK, TFT_MOSI);

  pinMode(TFT_BUSY, INPUT_PULLUP);
  delay(50);
  int up = digitalRead(TFT_BUSY);
  pinMode(TFT_BUSY, INPUT_PULLDOWN);
  delay(50);
  int down = digitalRead(TFT_BUSY);
  pinMode(TFT_BUSY, INPUT);
  delay(50);
  int floatv = digitalRead(TFT_BUSY);

  Serial.printf("BUSY with pull-up=%d  pull-down=%d  no-pull=%d\n", up, down, floatv);
  if (up == 1 && down == 0) {
    Serial.println("VERDICT: BUSY is FLOATING - nothing is driving it.");
    Serial.println("         The panel is not connected (check the FPC ribbon).");
  } else {
    Serial.println("VERDICT: BUSY is DRIVEN by the panel - wiring is good.");
  }

  // Toggle RST and watch whether BUSY reacts; a live panel pulses BUSY on reset.
  pinMode(TFT_RST, OUTPUT);
  pinMode(TFT_BUSY, INPUT_PULLUP);
  digitalWrite(TFT_RST, LOW);  delay(20);
  digitalWrite(TFT_RST, HIGH);
  int moved = 0;
  uint32_t t = millis();
  while (millis() - t < 3000) {
    if (digitalRead(TFT_BUSY) == 0) { moved = 1; break; }
  }
  Serial.printf("after a reset pulse, BUSY went low: %s\n", moved ? "YES (panel alive)" : "NO");
  Serial.println("=== done ===");
}

void loop() { delay(5000); Serial.println("alive"); }
