/**
 * I2C scanner: prints the address of every I2C device (LCD = 0x27 or 0x3F). Serial Monitor at 9600.
 */
#include <Wire.h>

/**
 * Start the I2C bus and the serial port.
 * @return void
 */
void setup() {
  Wire.begin();
  Serial.begin(9600);
}

/**
 * Knock on every I2C address every 2 s and print the ones that answer.
 * @return void
 */
void loop() {
  Serial.println("Scanning...");
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) Serial.println("No I2C devices found");
  Serial.println("----");
  delay(2000);
}
