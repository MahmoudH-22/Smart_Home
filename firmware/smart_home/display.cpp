#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "display.h"
#include "config.h"
#include "state.h"

static LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

/**
 * Write two lines, padded/cut to 16 chars, redrawing only the lines that changed
 * (no lcd.clear() -> no flicker).
 * @param l1 row 0 text
 * @param l2 row 1 text
 * @return void
 */
static void lcdWrite(const char *l1, const char *l2) {
  static char shown[2][17] = { "", "" };
  const char *src[2] = { l1, l2 };
  for (uint8_t r = 0; r < 2; r++) {
    char buf[17];
    snprintf(buf, sizeof(buf), "%-16.16s", src[r]);
    if (strcmp(buf, shown[r]) != 0) {
      lcd.setCursor(0, r);
      lcd.print(buf);
      strcpy(shown[r], buf);
    }
  }
}

/**
 * Start the LCD, turn on the backlight and show the welcome screen.
 * @return void
 */
void displayBegin() {
  lcd.init();
  lcd.backlight();
  lcdWrite("  SMART HOME", "  MCT331s Team");
}

/**
 * Redraw the screen from the shared state.
 * @return void
 */
void displayUpdate() {
  if (sys.alarmOn) {
    lcdWrite("!! INTRUSION !!", "Window OPEN");
    return;
  }
  char l1[17], l2[17];
  snprintf(l1, sizeof(l1), "Security:%s", sys.armed ? "ARMED" : "OFF");
  snprintf(l2, sizeof(l2), "Window:  %s", sys.windowOpen ? "OPEN" : "CLOSED");
  lcdWrite(l1, l2);
}
