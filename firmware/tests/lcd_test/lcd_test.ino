/**
 * LCD test: prints two lines. Wiring: GND-GND, VCC-5V, SDA-A4, SCL-A5.
 */
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);   // 0x3F if the scanner found 0x3F

/**
 * Start the LCD and print two test lines.
 * @return void
 */
void setup() {
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0); lcd.print("  SMART HOME");
  lcd.setCursor(0, 1); lcd.print("  MCT331s Team");
}

/**
 * Nothing to do.
 * @return void
 */
void loop() {}
