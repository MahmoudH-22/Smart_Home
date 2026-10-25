# Arduino UNO pin map

Pins marked **Used** are wired and running in `firmware/smart_home`. The rest are planned.
Every pin is defined in [`firmware/smart_home/config.h`](../firmware/smart_home/config.h).

| Pin | Connected to | Mode | System | Status |
|---|---|---|---|---|
| D0 (RX) | USB serial | - | - | Reserved |
| D1 (TX) | ESP8266 RX through a 1 kΩ / 2 kΩ divider | Serial 9600 | Security (phone alert) | Next |
| **D2** | **MC-38 window sensor** (other wire to GND) | INPUT_PULLUP, HIGH = open | Security | **Used** |
| D3 | PIR HC-SR501 OUT | INPUT | Security | Planned |
| D4 | DHT11 data | INPUT | Climate | Planned |
| D5 | Fan driver base (1 kΩ → TIP120) | OUTPUT / PWM | Climate | Planned |
| D6 | Light override button (to GND) | INPUT_PULLUP | Lighting | Planned |
| D7 | ARM toggle switch (middle leg; side leg to GND) | INPUT_PULLUP, LOW = armed | Security | Next |
| **D8** | **Buzzer +** (− to GND) | OUTPUT, `tone()` | Security | **Used** |
| D9 | Servo SG90 signal | Servo library | Door | Planned |
| D10 | Exterior LED + 220 Ω | OUTPUT | Security | Planned |
| D11 | Indoor LEDs ×3 (220 Ω each) | OUTPUT | Lighting | Planned |
| D12 | Alarm mute button (to GND) | INPUT_PULLUP | Security | Optional |
| D13 | On-board LED | - | - | Spare |
| A0 | LDR + 10 kΩ divider | analogRead | Lighting | Planned |
| A1 | Potentiometer 10 kΩ wiper | analogRead → 20–40 °C | Climate | Planned |
| A2, A3 | - | - | - | Spare |
| **A4 (SDA)** | **I2C bus**: LCD backpack `0x27` (+ PCF8574 keypad `0x20` later) | Wire | Display / Door | **Used** |
| **A5 (SCL)** | **I2C bus** | Wire | Display / Door | **Used** |
| 5V / GND | Breadboard power rails | - | All | **Used** |

## Notes

- The 4×4 keypad needs 8 pins on its own, which would not fit. A **PCF8574** I2C module puts it on A4/A5 next to the LCD.
- **Never drive the fan motor straight from a pin.** It goes through a transistor (TIP120), with a 1N4007 diode across the motor.
- The servo and the fan get their power from a separate **5 V 2 A** supply. Its GND must connect to the Arduino GND.
- The breadboard rails are **split in the middle**. If you use columns past 31, add a short jumper between the two halves.
