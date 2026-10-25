# MCT331s Smart Home

An Arduino-controlled smart home prototype built for **MCT331s Mechatronic System Integration** (Ain Shams University, Faculty of Engineering, Fall 2026). The house is laser-cut from 3 mm MDF.

| Team member | ID |
|---|---|
| Mahmoud Hisham | 2400844 |
| Ziad Hany | 2301401 |
| Ahmed Hany | 2400311 |
| Moatasem Mohamed | 2400732 |

## Systems and status

| System | What it does | Status |
|---|---|---|
| Main door access | Keypad code opens the door (servo) and closes it after a delay | ⏳ Next |
| Security | Alarm when the window opens; outside light on motion | ✅ Window alarm done · ⏳ PIR, phone alert |
| Indoor lighting | LEDs turn on in the dark (LDR) or with a button | ⏳ Next |
| Climate control | Fan turns on above a temperature set by a knob | ⏳ Next |
| LCD feedback | 16×2 I2C LCD shows every system's state | ✅ Working |

Progress session: 21–22 Oct 2026 · Final submission: week 9 (14–20 Nov 2026)

## Repository structure

```
mct331s-smart-home/
├── firmware/                     Arduino code
│   ├── smart_home/               ← THE main sketch (open smart_home.ino in the Arduino IDE)
│   │   ├── smart_home.ino        setup() + loop() only: calls each module
│   │   ├── config.h              every pin number and setting
│   │   ├── state.h               shared system state (all modules write, LCD reads)
│   │   ├── debounce.h/.cpp       clean switch reading
│   │   ├── security.h/.cpp       window alarm (MC-38 + ARM toggle + buzzer)
│   │   └── display.h/.cpp        16×2 I2C LCD
│   └── tests/                    small one-job sketches to test a single part
│       ├── i2c_scanner/          find the LCD address
│       ├── lcd_test/
│       └── buzzer_test/
├── hardware/
│   ├── laser_dxf/                laser-cut files: 2 sheets 600×400 (3 mm MDF) + one DXF per part
│   ├── wiring/                   wiring guide (PDF) + breadboard diagrams (PNG)
│   └── cad/                      SolidWorks files go here
├── docs/
│   ├── reports/                  progress / final reports (PDF) + figures
│   ├── design/smart_home_3d.html interactive 3D model + simulation (open in a browser, works offline)
│   ├── course/                   project brief + assessment sheet
│   ├── BOM.md                    bill of materials with prices
│   ├── pin_map.md                Arduino pin plan for the whole house
│   └── history/                  daily log of what was built / decided
└── tools/                        Python scripts that GENERATE the files above
    ├── cad/                      house geometry → DXF + 3D page
    ├── wiring/                   wiring diagrams + guide
    └── report/                   progress report PDF
```

## Upload the firmware

1. Install the **Arduino IDE** and the **LiquidCrystal I2C** library by Frank de Brabander (Library Manager).
2. Open `firmware/smart_home/smart_home.ino`. All the `.h` / `.cpp` files open as tabs automatically.
3. Check the pins in `config.h` (sensor `D2`, buzzer `D8`, ARM toggle `D7`, LCD `0x27`).
4. **Tools → Board → Arduino Uno**, pick the right **Port**, then click **Upload**.
5. Open the Serial Monitor at **9600** baud. It prints `ALERT:WINDOW_OPEN` each time the alarm starts.

Wiring: see [`hardware/wiring/Wiring_Guide.pdf`](hardware/wiring/Wiring_Guide.pdf) and [`docs/pin_map.md`](docs/pin_map.md).

## How the firmware is organised

- **One module per system.** Each module has a `xxxBegin()` that runs once in `setup()`, and a `xxxUpdate()` that runs every `loop()` and **never blocks** (no `delay()`).
- **Modules don't call each other.** They write their results into the shared `sys` state (`state.h`), and `display` reads everything from there.
- **All pins live in `config.h`.** Never write a pin number anywhere else.
- **To add a system (e.g. the door):**
  1. Create `door.h` / `door.cpp` with `doorBegin()` and `doorUpdate()`.
  2. Add its fields (e.g. `bool doorOpen`) to `state.h`.
  3. Add its pins to `config.h`.
  4. Call `doorBegin()` in `setup()` and `doorUpdate()` in `loop()`.
  5. Show it in `display.cpp`.
- Test new hardware with a small sketch in `firmware/tests/` before adding it to the main sketch.

## Laser cutting

Send `hardware/laser_dxf/sheet_1_of_2_600x400.dxf` and `sheet_2_of_2_600x400.dxf`. Layer **CUT** (red) is cut through, **ENGRAVE** (blue) is a light engrave, and **NOTE** is the sheet border, which is not cut. The base is drawn upside-down on purpose, so the team name plate ends up engraved on its underside. Measure the MDF first: the slots are made for exactly 3.0 mm.

## Regenerating the generated files

```bash
pip install -r tools/requirements.txt
python -m playwright install chromium        # only needed for the PDFs

python tools/cad/house_geometry.py build              # DXF + build/scene.json  (edit T = sheet thickness at the top)
python tools/cad/build.py build/scene.json build/smart_home_3d.html
python tools/wiring/build_guide.py build/wiring       # wiring guide PDF + PNGs
python tools/report/build_report.py build/Progress1_Report.pdf
```

Everything in `build/` is temporary (git-ignored). Copy a result into `hardware/` or `docs/` when you want to keep it.
