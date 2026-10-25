"""
Progress 1 report (English, simple words) -> PDF.

Run: python3 build_report.py <out_pdf>
"""
import asyncio
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root
sys.path.insert(0, str(ROOT / "tools" / "wiring"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagrams as d  # noqa: E402
from flow import flowchart  # noqa: E402

SCENE = json.load(open(ROOT / "build" / "scene.json"))   # run tools/cad/house_geometry.py build first
B = SCENE["variants"]["B"]
FIG = str(ROOT / "docs" / "reports" / "fig")

TEAM = [("Mahmoud Hisham", "2400844"), ("Ziad Hany", "2301401"),
        ("Ahmed Hany", "2400311"), ("Moatasem Mohamed", "2400732")]

CODE = open(Path(__file__).resolve().parent / "progress1_code.ino").read()

PART_ROLE = {
    "FRONT": "Main door, keypad, LCD, PIR, exterior light, control buttons",
    "BACK": "USB and power access for the Arduino, air vents",
    "LEFT": "Exhaust fan opening (Ø62 mm)",
    "RIGHT": "Window opening (70 × 55 mm), light sensor, window sensor",
    "PARTITION": "Separates the living room from the electronics bay",
    "FANPLATE": "Holds the fan motor", "FANRIB": "Sides of the fan duct",
    "SHELF": "Holds the door servo above the door", "DOOR": "Main door (moved by the servo)",
    "SASH": "Window frame (opens outward on a hinge)", "BASE": "Floor; all walls lock into its slots",
    "LID": "Removable flat roof", "LOCATOR": "Keep the lid in place on the walls", "KNOB": "Handle to lift the lid",
}


def img(name, cap, width="100%"):
    """Figure with caption.

    @param name file name in the figure folder  @param cap caption  @param width css width
    @returns html
    """
    return (f'<figure><img src="file://{FIG}/{name}" style="width:{width}"/>'
            f'<figcaption>{cap}</figcaption></figure>')


def svgfig(svg, cap, width="100%"):
    """Inline SVG figure with caption.

    @param svg svg markup  @param cap caption  @param width css width
    @returns html
    """
    return f'<figure><div class="svgw" style="width:{width}">{svg}</div><figcaption>{cap}</figcaption></figure>'


def parts_table():
    """Laser-cut parts list for the chosen design.

    @returns html
    """
    rows = "".join(
        f"<tr><td>{p['name']}</td><td class='m'>{p['size'][0]} × {p['size'][1]}</td><td class='c'>{p['qty']}</td>"
        f"<td>{PART_ROLE.get(p['id'], '')}</td></tr>" for p in B["parts"])
    total = sum(p["qty"] for p in B["parts"])
    return (f"<table><thead><tr><th>Part</th><th>Flat size (mm)</th><th>Qty</th><th>What it does</th></tr></thead>"
            f"<tbody>{rows}<tr class='tot'><td>Total</td><td></td><td class='c'>{total}</td><td>All from 3 mm MDF</td></tr></tbody></table>")


CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family: 'Cairo', 'DejaVu Sans', sans-serif; font-size: 10.6pt; line-height: 1.5; color: #1d232a; margin: 0; }
h1 { font-size: 26pt; line-height: 1.15; margin: 0 0 3mm; }
h2 { font-size: 16pt; margin: 0 0 3mm; padding-bottom: 1.5mm; border-bottom: 2.5px solid #1c5d99; color: #12395e; break-after: avoid; }
h3 { font-size: 12.5pt; margin: 5mm 0 1.5mm; color: #12395e; break-after: avoid; }
p { margin: 1.2mm 0 2.2mm; }
section { break-before: page; }
section.nobreak { break-before: auto; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 3mm; font-size: 9.6pt; break-inside: avoid; }
th { background: #eef3f8; text-align: left; padding: 1.5mm 2mm; border-bottom: 1.5px solid #9fb3c8; }
td { padding: 1.2mm 2mm; border-bottom: 1px solid #e3e8ee; vertical-align: top; }
td.m, .m { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; white-space: nowrap; }
td.c { text-align: center; }
tr.tot td { font-weight: 700; border-top: 1.5px solid #9fb3c8; }
figure { margin: 3mm 0; text-align: center; break-inside: avoid; }
figure img { border: 1px solid #dfe5ec; border-radius: 2mm; }
.svgw { margin: 0 auto; } .svgw svg { width: 100%; height: auto; border: 1px solid #dfe5ec; border-radius: 2mm; }
figcaption { font-size: 9pt; color: #5a6676; margin-top: 1mm; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
.grid2 figure { margin: 1mm 0; }
.callout { border-left: 4px solid #1c5d99; background: #f2f6fa; padding: 2mm 3.5mm; margin: 3mm 0; break-inside: avoid; }
.warn { border-left-color: #d9480f; background: #fff5ec; }
.ok { border-left-color: #2b8a3e; background: #effaf1; }
.pass { color: #2b8a3e; font-weight: 700; } .prog { color: #d9480f; font-weight: 700; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.6pt; line-height: 1.38; background: #f6f8fa; border: 1px solid #dfe5ec; border-radius: 2mm; padding: 3mm; white-space: pre-wrap; margin: 2mm 0; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; background: #f1f3f5; padding: 0 1mm; border-radius: 1mm; }
ul, ol { margin: 1mm 0 2mm; padding-left: 6mm; } li { margin: 0.6mm 0; }
.cover { height: 255mm; display: flex; flex-direction: column; }
.cover .uni { font-size: 11pt; color: #44505c; line-height: 1.45; }
.cover .course { margin-top: 32mm; font-size: 13pt; color: #1c5d99; font-weight: 700; }
.cover .sub { font-size: 13pt; color: #44505c; }
.cover table { margin-top: 12mm; width: 120mm; font-size: 11pt; }
.cover .bottom { margin-top: auto; font-size: 10pt; color: #5a6676; }
.toc li { margin: 1mm 0; }
.status { font-size: 9.6pt; }
svg .cut { fill: #e6d3bd; stroke: #d23a2a; stroke-width: .7; }
svg .hole { fill: #ffffff; stroke: #d23a2a; stroke-width: .7; }
svg .eng { fill: none; stroke: #1c5d99; stroke-width: .6; stroke-dasharray: 3 2; }
svg .engt { fill: #1c5d99; font-family: 'DejaVu Sans', sans-serif; }
svg .sheetbg { fill: #fafafa; stroke: #888; stroke-width: 1; stroke-dasharray: 6 4; }
svg .lbl { fill: #333; font: 600 11px 'DejaVu Sans Mono', monospace; text-anchor: middle; }
"""


def build():
    """Assemble the report HTML.

    @returns html string
    """
    team_rows = "".join(f"<tr><td>{n}</td><td class='m'>{i}</td></tr>" for n, i in TEAM)
    sheet_figs = "".join(f'<div class="svgw">{s}</div>' for s in B["sheet_svgs"])
    full_svg = d.diagram_full()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Progress 1 Report</title>
<style>{CSS}</style></head><body>

<section class="nobreak cover">
  <div class="uni">Ain Shams University<br>Faculty of Engineering<br>Mechatronics Engineering Department</div>
  <div class="course">MCT331s · Mechatronic System Integration · Fall 2026</div>
  <h1>Smart Home Prototype<br>Progress Report 1</h1>
  <div class="sub">Home structure and window security system</div>
  <table><thead><tr><th>Team member</th><th>ID</th></tr></thead><tbody>{team_rows}</tbody></table>
  <div class="bottom">Progress session: 21–22 October 2026</div>
</section>

<section>
  <h2>Contents</h2>
  <ol class="toc">
    <li>Summary</li><li>The project in short</li><li>Home structure</li><li>Security system (window alarm)</li>
    <li>Problems we faced and how we solved them</li><li>Next steps</li>
    <li>Appendix A: full code · Appendix B: planned pin map · Appendix C: project files</li>
  </ol>

  <h2 style="margin-top:8mm">1. Summary</h2>
  <p>For this progress session we were asked to show two things: <b>(1)</b> the home structure, built as a real
  engineering prototype, and <b>(2)</b> a working window alarm that sends an alert when the window is opened.</p>
  <table class="status"><thead><tr><th>Progress 1 item</th><th>Status</th><th>What we did</th></tr></thead><tbody>
    <tr><td>Home structure (layout, material, build)</td><td class="pass">Done</td><td>Designed in CAD, laser-cut from 3 mm MDF and assembled with finger joints and glue. 300 × 220 × 150 mm house on a 320 × 240 mm base with a removable flat roof.</td></tr>
    <tr><td>Window intrusion detection</td><td class="pass">Done</td><td>An MC-38 magnetic sensor on the window. When the window opens while security is on, the buzzer sounds and the LCD shows <code>!! INTRUSION !!</code>. When the window closes, the buzzer stops.</td></tr>
    <tr><td>LCD feedback</td><td class="pass">Done</td><td>A 16×2 I2C LCD shows the security mode and the window state at all times.</td></tr>
    <tr><td>Alert to the designated recipient(s)</td><td class="prog">In progress</td><td>The Arduino already sends the message <code>ALERT:WINDOW_OPEN</code> over serial on every new intrusion. The next step is an ESP8266 Wi-Fi board that forwards it to a phone.</td></tr>
  </tbody></table>
</section>

<section class="nobreak">
  <h2 style="margin-top:7mm">2. The project in short</h2>
  <p>We are building a small smart home controlled by an <b>Arduino UNO</b>. The final house will have five systems. This report covers the parts asked for in Progress 1: the <b>house</b>, the <b>window alarm</b> and the <b>LCD</b>.</p>
  <table><thead><tr><th>System</th><th>What it does</th><th>Main parts</th><th>Status</th></tr></thead><tbody>
    <tr><td>Main door access</td><td>Opens the door when the right code is typed, then closes it after a few seconds</td><td>4×4 keypad, SG90 servo</td><td>Next</td></tr>
    <tr><td><b>Security system</b></td><td>Alarm if the window opens; outside light turns on if someone moves near the door</td><td>MC-38 sensor, buzzer, PIR, LED, toggle switch</td><td class="pass">Window part done</td></tr>
    <tr><td>Indoor lighting</td><td>Light turns on when it gets dark, or with a button</td><td>LDR, 3 LEDs, push button</td><td>Next</td></tr>
    <tr><td>Climate control</td><td>Fan turns on when the room is hotter than the value set by a knob</td><td>DHT11, DC motor + propeller, potentiometer</td><td>Next</td></tr>
    <tr><td><b>LCD display</b></td><td>Shows the state of every system</td><td>16×2 LCD with I2C module</td><td class="pass">Working</td></tr>
  </tbody></table>
</section>

<section>
  <h2>3. Home structure</h2>
  <h3>3.1 Material and why we chose it</h3>
  <p>The house is made of <b>3 mm MDF</b> (wood fibre board), cut with a <b>laser cutter</b> from drawings we made in CAD.</p>
  <ul>
    <li><b>Accurate:</b> the laser cuts every hole to within a fraction of a millimetre, so the sensors, LCD and buttons fit exactly.</li>
    <li><b>Strong enough and light:</b> 3 mm MDF is stiff for a house this size and easy to glue.</li>
    <li><b>Cheap and fast:</b> the whole house comes out of <b>two 600 × 400 mm sheets</b>.</li>
    <li><b>Easy to work with:</b> it can be drilled, sanded or painted later if needed.</li>
  </ul>

  <h3>3.2 Main dimensions</h3>
  <table><thead><tr><th>Item</th><th>Size (mm)</th></tr></thead><tbody>
    <tr><td>House footprint (outside)</td><td class="m">300 × 220</td></tr>
    <tr><td>Wall height</td><td class="m">150</td></tr>
    <tr><td>Total height with lid and knob</td><td class="m">159</td></tr>
    <tr><td>Base plate</td><td class="m">320 × 240</td></tr>
    <tr><td>Roof lid (removable)</td><td class="m">306 × 226</td></tr>
    <tr><td>Main door opening</td><td class="m">60 × 100</td></tr>
    <tr><td>Window opening</td><td class="m">70 × 55</td></tr>
    <tr><td>Fan opening</td><td class="m">Ø 62</td></tr>
    <tr><td>Electronics bay (behind the inner wall)</td><td class="m">294 × 75</td></tr>
  </tbody></table>

  <h3>3.3 How the parts hold together</h3>
  <ul>
    <li><b>Finger joints at every corner:</b> the walls have teeth (7 per corner, 21.4 mm each) that lock into each other like puzzle pieces. This keeps the box square.</li>
    <li><b>Tabs and slots in the base:</b> every wall has small tabs on its bottom edge that drop into slots in the base, so each wall can only go in one place.</li>
    <li><b>Wood glue (PVA)</b> on all joints. No screws are needed for the shell.</li>
    <li><b>Removable lid:</b> four small L-shaped pieces under the lid sit inside the walls and stop it from sliding. Lifting the lid gives full access to the wiring.</li>
  </ul>
</section>

<section>
  <h3 style="margin-top:0">3.4 Inside layout: where everything goes</h3>
  <p>An inner wall (partition) splits the house into two zones. The front zone is the <b>living room</b> with all the sensors and outputs.
  The back zone (75 mm deep) is the <b>electronics bay</b>, where the Arduino and the breadboard sit hidden. The Arduino USB port lines up with a hole in the back wall, so we can upload code without opening the house.</p>
  <table><thead><tr><th>Where</th><th>What is mounted there</th></tr></thead><tbody>
    <tr><td>Front wall</td><td>Main door (servo above it), keypad, LCD, PIR motion sensor, outside light, ARM switch, buttons, fan knob</td></tr>
    <tr><td>Right wall</td><td><b>Window with the MC-38 sensor</b>, light sensor (LDR)</td></tr>
    <tr><td>Left wall</td><td>Exhaust fan (motor + propeller in a small duct)</td></tr>
    <tr><td>Inner wall</td><td>Indoor lights (3 LEDs), temperature sensor (DHT11)</td></tr>
    <tr><td>Electronics bay</td><td>Arduino UNO on standoffs, breadboard, buzzer, wiring</td></tr>
    <tr><td>Back wall</td><td>USB and power holes for the Arduino, air vents</td></tr>
  </tbody></table>
  {img("c_xray.png", "Figure 1. CAD model with see-through walls showing where each component sits.", "88%")}
</section>

<section>
  <h3 style="margin-top:0">3.5 CAD views</h3>
  {img("c_iso.png", "Figure 2. Isometric view with the main dimensions (mm).", "80%")}
  <div class="grid2">
    {img("c_front.png", "Figure 3. Front view: door, keypad, LCD, PIR and controls.")}
    {img("c_right.png", "Figure 4. Right view: window with the MC-38 sensor.")}
  </div>
</section>

<section>
  <div class="grid2">
    {img("c_top.png", "Figure 5. Top view (with the lid on).")}
    {img("c_exploded.png", "Figure 6. Exploded view: how the panels fit together.")}
  </div>
  <h3>3.6 Laser-cut parts</h3>
  <p>The design has <b>{sum(p['qty'] for p in B['parts'])} parts</b> ({len(B['parts'])} different shapes), nested on <b>{B['sheets']} sheets of 600 × 400 mm</b>.
  Total cut length is <b>{B['cut_m']} m</b>. The team names are engraved under the base.</p>
  {parts_table()}
</section>

<section>
  <h3 style="margin-top:0">3.7 Cutting layout</h3>
  <p>These are the two sheets sent to the laser cutter. Red lines are cut through, and the blue lines are light engraving (labels).</p>
  <div class="grid2" style="grid-template-columns:1fr">{sheet_figs}</div>
  <div class="callout"><b>Saving material:</b> our first design needed 3 sheets. We lowered the walls from 160 to 150 mm and replaced a full frame under the lid with four small corner pieces.
  The same house now fits on 2 sheets (<b>33 % less MDF</b>), with 11 % less cutting.</div>
</section>

<section>
  <h2>4. Security system (window alarm)</h2>
  <h3>4.1 What it does</h3>
  <ul>
    <li>When <b>security mode is ON</b> and someone <b>opens the window</b>, the buzzer sounds <b>continuously</b> and the LCD shows <code>!! INTRUSION !!</code>.</li>
    <li>When the window is <b>closed again</b>, the buzzer <b>stops right away</b> and the LCD shows <code>Window: CLOSED</code>.</li>
    <li>At the moment the alarm starts, the Arduino sends the message <code>ALERT:WINDOW_OPEN</code> <b>once</b>. This message is what will be forwarded to the phone.</li>
    <li>Security mode is turned on and off with the <b>ARM toggle switch</b> (pin D7). In our bench tests the code setting <code>ALWAYS_ARMED = true</code> kept security on without the switch. With the switch connected, this setting becomes <code>false</code>.</li>
  </ul>

  <h3>4.2 Components used</h3>
  <table><thead><tr><th>Component</th><th>Class</th><th>Job in this system</th><th>Arduino pin</th></tr></thead><tbody>
    <tr><td>Arduino UNO R3</td><td>Information processing</td><td>Reads the sensor, decides, drives the outputs</td><td>-</td></tr>
    <tr><td>MC-38 magnetic window sensor</td><td>Sensor</td><td>Tells whether the window is open or closed</td><td class="m">D2</td></tr>
    <tr><td>Buzzer 5 V</td><td>Actuator</td><td>Alarm sound</td><td class="m">D8</td></tr>
    <tr><td>LCD 16×2 with I2C module</td><td>Information processing (display)</td><td>Shows the security mode and window state</td><td class="m">A4 (SDA), A5 (SCL)</td></tr>
    <tr><td>Toggle switch</td><td>Sensor (user input)</td><td>Turns security mode on and off</td><td class="m">D7</td></tr>
    <tr><td>Breadboard 830 + jumper wires</td><td>Mechanical / wiring</td><td>Shares 5 V and GND, joins the parts</td><td>5V, GND</td></tr>
  </tbody></table>

  <h3>4.3 How the window sensor works</h3>
  <p>The MC-38 has two pieces: a <b>switch</b> fixed on the wall (with two wires) and a <b>magnet</b> fixed on the window.
  Inside the switch is a tiny metal contact that closes when the magnet is near.</p>
  <p>We connect one wire to <b>D2</b> and the other to <b>GND</b>, and turn on the Arduino's built-in pull-up resistor (<code>INPUT_PULLUP</code>).
  The pull-up makes the pin read HIGH when nothing pulls it down, so no extra resistor is needed.</p>
  <table><thead><tr><th>Window</th><th>Magnet</th><th>Switch inside</th><th>D2 reads</th><th>Meaning in the code</th></tr></thead><tbody>
    <tr><td>Closed</td><td>Next to the switch</td><td>Closed (joins D2 to GND)</td><td class="m">LOW</td><td><code>windowOpen = false</code></td></tr>
    <tr><td>Open</td><td>Away from the switch</td><td>Open</td><td class="m">HIGH</td><td><code>windowOpen = true</code></td></tr>
  </tbody></table>
  <div class="callout">The magnet must be within about <b>10 mm</b> of the switch when the window is closed. We mounted them side by side on the window edge.</div>
</section>

<section>
  <h3 style="margin-top:0">4.4 Wiring</h3>
  <p>The Arduino's 5 V and GND go to the breadboard power rails first, and every part takes power from there. The numbers on the wires match the table below.</p>
  {svgfig(full_svg, "Figure 7. Wiring of the LCD, buzzer and window sensor (breadboard view).")}
  <table><thead><tr><th>#</th><th>From</th><th>To</th><th>Wire</th></tr></thead><tbody>
    <tr><td>1</td><td class="m">Arduino 5V</td><td class="m">Rail + (col 2)</td><td>Red</td></tr>
    <tr><td>2</td><td class="m">Arduino GND</td><td class="m">Rail − (col 1)</td><td>Black</td></tr>
    <tr><td>3</td><td class="m">Arduino D8</td><td class="m">j17 (buzzer + leg in f17)</td><td>Orange</td></tr>
    <tr><td>4</td><td class="m">j20 (buzzer − leg in f20)</td><td class="m">Rail − (col 20)</td><td>Black</td></tr>
    <tr><td>5</td><td class="m">MC-38 wire 1</td><td class="m">h24</td><td>Sensor wire</td></tr>
    <tr><td>6</td><td class="m">MC-38 wire 2</td><td class="m">Rail − (col 27)</td><td>Sensor wire</td></tr>
    <tr><td>7</td><td class="m">Arduino D2</td><td class="m">j24</td><td>Purple</td></tr>
    <tr><td>8 / 9</td><td class="m">LCD GND / VCC</td><td class="m">Rail − (col 30) / Rail + (col 29)</td><td>Black / Red</td></tr>
    <tr><td>10 / 11</td><td class="m">LCD SDA / SCL</td><td class="m">Arduino A4 / A5</td><td>Blue / Green</td></tr>
  </tbody></table>
</section>

<section>
  <h3 style="margin-top:0">4.5 Control logic (flowchart)</h3>
  <div class="grid2" style="grid-template-columns: 1.35fr 1fr; align-items:start">
    {svgfig(flowchart(), "Figure 8. Flowchart of the security program.")}
    <div>
      <p><b>In simple words:</b></p>
      <ol>
        <li>When the Arduino turns on, <code>setup()</code> runs <b>once</b>. It sets up the pins, starts the LCD and shows a welcome message.</li>
        <li>Then <code>loop()</code> runs <b>again and again</b>, thousands of times every second.</li>
        <li>Each time, it reads the window sensor and the ARM switch.</li>
        <li>If security is ON <b>and</b> the window is open, the buzzer turns on and the LCD shows the alarm. The first time this happens, it also sends <code>ALERT:WINDOW_OPEN</code>.</li>
        <li>Otherwise, the buzzer is off and the LCD shows the normal status.</li>
      </ol>
      <div class="callout ok">The program never uses <code>delay()</code> inside the loop, so it always reacts at once.
      Only the 1.5 s welcome message in <code>setup()</code> waits.</div>
    </div>
  </div>
</section>

<section>
  <h3 style="margin-top:0">4.6 The main ideas in the code</h3>
  <table><thead><tr><th>Part of the code</th><th>What it does, in simple words</th></tr></thead><tbody>
    <tr><td class="m">readDebounced()</td><td>A metal switch "shakes" for a few milliseconds when it opens or closes, and the Arduino can see many fake changes. This function only accepts a new reading after it stays the same for <b>30 ms</b>. That keeps the alarm from flickering.</td></tr>
    <tr><td class="m">buzzer(on)</td><td>Turns the buzzer on with <code>tone(D8, 2500 Hz)</code> or off with <code>noTone()</code>. It only acts when the state <b>changes</b>, so the sound stays smooth. <code>tone()</code> works for both buzzer types (active and passive).</td></tr>
    <tr><td class="m">lcdWrite()</td><td>Writes the two LCD lines, padded to 16 characters so old letters are erased. It only rewrites a line when its text changes, so the screen does not flicker.</td></tr>
    <tr><td class="m">updateSecurity()</td><td>Reads the sensor and the switch and sets <code>alarmOn = armed AND windowOpen</code>. Then it drives the buzzer and sends the alert message once when the alarm starts.</td></tr>
    <tr><td class="m">updateLCD()</td><td>Shows <code>!! INTRUSION !!</code> during an alarm. Otherwise it shows <code>Security:ARMED/OFF</code> and <code>Window: OPEN/CLOSED</code>.</td></tr>
    <tr><td class="m">Settings at the top</td><td>All pin numbers and options are at the top of the file (LCD address <code>0x27</code>, sensor <code>D2</code>, buzzer <code>D8</code>, switch <code>D7</code>), so they are easy to change.</td></tr>
  </tbody></table>
  <p>The full code is in Appendix A. Every function has a comment that explains its job, inputs and output.</p>

  <h3>4.7 Tests and results</h3>
  <table><thead><tr><th>#</th><th>Test</th><th>Expected</th><th>Result</th></tr></thead><tbody>
    <tr><td>1</td><td>Power on</td><td>LCD shows <code>SMART HOME / MCT331s Team</code>, then the status</td><td class="pass">Pass</td></tr>
    <tr><td>2</td><td>Window closed, security on</td><td>Buzzer silent, LCD <code>Window: CLOSED</code></td><td class="pass">Pass</td></tr>
    <tr><td>3</td><td>Open the window</td><td>Buzzer sounds continuously, LCD <code>!! INTRUSION !!</code></td><td class="pass">Pass</td></tr>
    <tr><td>4</td><td>Close the window again</td><td>Buzzer stops at once, LCD back to <code>Window: CLOSED</code></td><td class="pass">Pass</td></tr>
    <tr><td>5</td><td>Open and close the window several times quickly</td><td>No false beeps or flicker (debounce)</td><td class="pass">Pass</td></tr>
    <tr><td>6</td><td>Alarm starts</td><td><code>ALERT:WINDOW_OPEN</code> printed once on the Serial Monitor</td><td>Shown live</td></tr>
  </tbody></table>

  <h3>4.8 Sending the alert to the recipients (next step)</h3>
  <p>The Arduino UNO has no Wi-Fi, so it cannot send a message to a phone by itself. Our plan:</p>
  <ol>
    <li>Add an <b>ESP8266</b> Wi-Fi board (ESP-01 or NodeMCU).</li>
    <li>Arduino <b>TX (D1)</b> goes to ESP8266 <b>RX</b> through a 1 kΩ / 2 kΩ divider, because the ESP8266 works at 3.3 V.</li>
    <li>When the ESP8266 receives <code>ALERT:WINDOW_OPEN</code>, it sends a <b>Telegram</b> message to the team's phones.</li>
  </ol>
  <p>The Arduino side is already done: the message is sent once per intrusion.</p>
</section>

<section>
  <h2>5. Problems we faced and how we solved them</h2>
  <table><thead><tr><th>Problem</th><th>Cause</th><th>Solution</th></tr></thead><tbody>
    <tr><td>Compile error: <code>LiquidCrystal_I2C.h: No such file</code></td><td>The LCD library was not installed</td><td>Installed <i>LiquidCrystal I2C</i> (Frank de Brabander) from the Library Manager</td></tr>
    <tr><td>Upload error: <code>cannot open port COM7</code> / <code>semaphore timeout</code></td><td>Wrong COM port selected; the port was busy</td><td>Chose the right port in Tools → Port, closed the Serial Monitor and reconnected the USB</td></tr>
    <tr><td>LCD showed only black boxes</td><td>The Arduino was not talking to the LCD (address / contrast)</td><td>Ran an I2C scanner to find the address (<code>0x27</code>) and adjusted the contrast screw on the back</td></tr>
    <tr><td>LCD always said <i>Window: CLOSED</i></td><td>The first LCD program never read the window sensor</td><td>Wrote one program that runs the sensor and the LCD together</td></tr>
    <tr><td>Buzzer worked alone but not in the combined program</td><td>Our buzzer needs a tone signal; a plain HIGH only made it click</td><td>Used <code>tone()</code> / <code>noTone()</code>, which work for both buzzer types</td></tr>
    <tr><td>Buzzer kept sounding after the window closed</td><td>The first version latched the alarm until a mute button was pressed</td><td>Changed the logic so the alarm follows the window: open = sound, closed = silent</td></tr>
    <tr><td>Not enough Arduino pins for all five systems</td><td>The 4×4 keypad alone needs 8 pins</td><td>Planned a PCF8574 I2C module, so the keypad shares the LCD's two I2C wires</td></tr>
    <tr><td>First house design needed 3 MDF sheets</td><td>Tall walls and a big frame under the lid</td><td>Lowered the walls to 150 mm and used 4 small corner locators: now 2 sheets</td></tr>
  </tbody></table>

  <h2 style="margin-top:7mm">6. Next steps</h2>
  <table><thead><tr><th>Next</th><th>Work</th><th>Parts still to buy</th></tr></thead><tbody>
    <tr><td>1</td><td>Connect the ARM toggle switch (D7) and set <code>ALWAYS_ARMED = false</code></td><td>-</td></tr>
    <tr><td>2</td><td>Phone alert through ESP8266 + Telegram</td><td>ESP8266 (ESP-01 + adapter, or NodeMCU)</td></tr>
    <tr><td>3</td><td>Outside light with the PIR motion sensor</td><td>PIR HC-SR501</td></tr>
    <tr><td>4</td><td>Indoor lighting (LDR + button + LEDs)</td><td>10 kΩ resistor</td></tr>
    <tr><td>5</td><td>Climate control (DHT11 + fan + knob)</td><td>10 kΩ potentiometer, TIP120 + 1N4007 + 1 kΩ, 5 V 2 A adapter</td></tr>
    <tr><td>6</td><td>Main door (keypad + servo, auto close)</td><td>PCF8574 I2C module</td></tr>
    <tr><td>7</td><td>Move the wiring to a soldered veroboard, write the final report, record the video</td><td>Veroboard</td></tr>
  </tbody></table>
</section>

<section>
  <h2>Appendix A: Full code (security + LCD)</h2>
  <pre>{html.escape(CODE)}</pre>
</section>

<section>
  <h2>Appendix B: Planned pin map (whole house)</h2>
  <table><thead><tr><th>Pin</th><th>Connected to</th><th>System</th><th>Status</th></tr></thead><tbody>
    <tr><td class="m">D2</td><td>MC-38 window sensor</td><td>Security</td><td class="pass">Used</td></tr>
    <tr><td class="m">D3</td><td>PIR motion sensor</td><td>Security</td><td>Planned</td></tr>
    <tr><td class="m">D4</td><td>DHT11 temperature sensor</td><td>Climate</td><td>Planned</td></tr>
    <tr><td class="m">D5</td><td>Fan driver (TIP120)</td><td>Climate</td><td>Planned</td></tr>
    <tr><td class="m">D6</td><td>Light override button</td><td>Lighting</td><td>Planned</td></tr>
    <tr><td class="m">D7</td><td>ARM toggle switch</td><td>Security</td><td>Next</td></tr>
    <tr><td class="m">D8</td><td>Buzzer</td><td>Security</td><td class="pass">Used</td></tr>
    <tr><td class="m">D9</td><td>Door servo SG90</td><td>Door</td><td>Planned</td></tr>
    <tr><td class="m">D10</td><td>Exterior light LED</td><td>Security</td><td>Planned</td></tr>
    <tr><td class="m">D11</td><td>Indoor LEDs ×3</td><td>Lighting</td><td>Planned</td></tr>
    <tr><td class="m">D12</td><td>Alarm mute button</td><td>Security</td><td>Optional</td></tr>
    <tr><td class="m">A0</td><td>LDR light sensor</td><td>Lighting</td><td>Planned</td></tr>
    <tr><td class="m">A1</td><td>Potentiometer (fan set point)</td><td>Climate</td><td>Planned</td></tr>
    <tr><td class="m">A4 / A5</td><td>I2C bus: LCD (0x27) and keypad PCF8574 (0x20)</td><td>Display / Door</td><td class="pass">LCD used</td></tr>
    <tr><td class="m">D1 (TX)</td><td>ESP8266 (phone alerts)</td><td>Security</td><td>Next</td></tr>
  </tbody></table>

  <h2 style="margin-top:8mm">Appendix C: Project files</h2>
  <table><thead><tr><th>File / folder</th><th>Contents</th></tr></thead><tbody>
    <tr><td class="m">laser_dxf/variant_B_flat_roof_v2/</td><td>The 2 nested cutting sheets and one DXF per part</td></tr>
    <tr><td class="m">MCT331s_Smart_Home_Design.html</td><td>Interactive 3D model and simulation of the house</td></tr>
    <tr><td class="m">wiring/Wiring_Guide.pdf</td><td>Step-by-step wiring guide with breadboard diagrams</td></tr>
    <tr><td class="m">cad_tools/house_geometry.py</td><td>Script that generates all the panels and DXF files</td></tr>
  </tbody></table>
</section>
</body></html>"""


async def main(out_pdf):
    """Render the report to PDF.

    @param out_pdf output path
    @returns None
    """
    from playwright.async_api import async_playwright
    path = str(ROOT / "build" / "report.html")
    open(path, "w", encoding="utf-8").write(build())
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto("file://" + path)
        await pg.wait_for_timeout(800)
        await pg.pdf(path=out_pdf, format="A4", print_background=True, prefer_css_page_size=True,
                     display_header_footer=True, header_template="<span></span>",
                     footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#888;font-family:sans-serif">'
                                     'MCT331s Smart Home · Progress Report 1 · page <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        await b.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
