"""
Build the wiring guide (Egyptian Arabic, RTL) as HTML -> PDF, plus one PNG per diagram.

Run: python3 build_guide.py <out_dir>
"""
import asyncio
import html
import os
import sys

import diagrams as d

TEAM = "Mahmoud Hisham 2400844 · Ziad Hany 2301401 · Ahmed Hany 2400311 · Moatasem Mohamed 2400732"

BUZZER_TEST = r'''const uint8_t PIN_BUZZER = 8;   // buzzer + leg is on D8

/**
 * Set the buzzer pin as an output.
 * @return void
 */
void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
}

/**
 * Beep: 0.5 s on, 0.5 s off. tone() works for active and passive buzzers.
 * @return void
 */
void loop() {
  tone(PIN_BUZZER, 2500);
  delay(500);
  noTone(PIN_BUZZER);
  delay(500);
}'''

SCANNER = r'''#include <Wire.h>

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
}'''

LCD_TEST = r'''#include <Wire.h>
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
void loop() {}'''

FULL = r'''#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================= settings =================
const uint8_t LCD_ADDR        = 0x27;   // the address the scanner found
const uint8_t PIN_REED        = 2;      // MC-38 -> D2 + GND
const uint8_t PIN_BUZZER      = 8;      // buzzer + -> D8
const uint8_t PIN_ARM         = 7;      // toggle middle -> D7, side -> GND (later)
const bool    ALWAYS_ARMED    = true;   // true = no toggle needed; false when the toggle is wired
const uint8_t REED_OPEN_LEVEL = HIGH;   // if the window shows reversed, change to LOW
const unsigned int BUZZ_HZ    = 2500;   // buzzer tone frequency

LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);

bool armed = false, windowOpen = false, alarmOn = false;

/**
 * Read a pin and return its value only after it stays stable for 30 ms.
 * @param pin Arduino pin number
 * @param stable last stable value (updated in place)
 * @param lastRaw last raw reading (updated in place)
 * @param changedAt time of the last raw change (updated in place)
 * @return the stable logic level (HIGH / LOW)
 */
bool readDebounced(uint8_t pin, bool &stable, bool &lastRaw, unsigned long &changedAt) {
  bool raw = digitalRead(pin);
  if (raw != lastRaw) { lastRaw = raw; changedAt = millis(); }
  if (millis() - changedAt > 30) stable = raw;
  return stable;
}

/**
 * Turn the buzzer on (continuous tone) or off. Works for active and passive buzzers.
 * @param on true = sound, false = silent
 * @return void
 */
void buzzer(bool on) {
  static bool isOn = false;
  if (on == isOn) return;
  isOn = on;
  if (on) tone(PIN_BUZZER, BUZZ_HZ); else noTone(PIN_BUZZER);
}

/**
 * Write two lines (padded to 16 chars), redrawing only the lines that changed.
 * @param l1 row 0 text
 * @param l2 row 1 text
 * @return void
 */
void lcdWrite(const char *l1, const char *l2) {
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
 * Read the reed + toggle. Window open while armed = buzzer ON; window closed = buzzer OFF.
 * @return void
 */
void updateSecurity() {
  static bool rS = HIGH, rL = HIGH, aS = HIGH, aL = HIGH;
  static unsigned long rT = 0, aT = 0;
  static bool lastAlarm = false;

  windowOpen = (readDebounced(PIN_REED, rS, rL, rT) == REED_OPEN_LEVEL);
  armed = ALWAYS_ARMED || (readDebounced(PIN_ARM, aS, aL, aT) == LOW);
  alarmOn = armed && windowOpen;

  buzzer(alarmOn);

  if (alarmOn && !lastAlarm) Serial.println("ALERT:WINDOW_OPEN");   // for the ESP8266 later
  lastAlarm = alarmOn;
}

/**
 * Show the alarm or the normal status on the LCD.
 * @return void
 */
void updateLCD() {
  if (alarmOn) { lcdWrite("!! INTRUSION !!", "Window OPEN"); return; }
  char l1[17], l2[17];
  snprintf(l1, 17, "Security:%s", armed ? "ARMED" : "OFF");
  snprintf(l2, 17, "Window:  %s", windowOpen ? "OPEN" : "CLOSED");
  lcdWrite(l1, l2);
}

/**
 * Configure pins and start the LCD and serial port.
 * @return void
 */
void setup() {
  pinMode(PIN_REED, INPUT_PULLUP);
  pinMode(PIN_ARM, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();
  lcdWrite("  SMART HOME", "  MCT331s Team");
  delay(1500);
}

/**
 * Main loop: read the sensors, drive the buzzer, update the screen.
 * @return void
 */
void loop() {
  updateSecurity();
  updateLCD();
}'''


def code(src, small=False):
    """Render a code block (LTR).

    @param src source text  @param small use the compact size
    @returns html
    """
    cls = ' class="sm"' if small else ""
    return f'<pre dir="ltr"{cls}><code>{html.escape(src)}</code></pre>'


def table(rows, head=("#", "من (From)", "إلى (To)", "لون السلك", "ملاحظة")):
    """Render a wiring table.

    @param rows list of tuples (num, from, to, colour-hex, colour-name, note)
    @param head header labels
    @returns html
    """
    out = ['<table class="wt"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"]
    for (n, a, b, hexc, cname, note) in rows:
        out.append(f'<tr><td class="n"><span class="badge" style="border-color:{hexc}">{n}</span></td>'
                   f'<td class="pin" dir="ltr">{a}</td><td class="pin" dir="ltr">{b}</td>'
                   f'<td><span class="sw" style="background:{hexc}"></span>{cname}</td><td>{note}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


CSS = """
@page { size: A4 landscape; margin: 11mm 12mm; }
* { box-sizing: border-box; }
body { font-family: 'Cairo', 'DejaVu Sans', sans-serif; color: #1b1f24; font-size: 12.5pt; line-height: 1.6; margin: 0; }
h1 { font-size: 30pt; margin: 0 0 4mm; line-height: 1.2; }
h2 { font-size: 19pt; margin: 0 0 3mm; padding-bottom: 1.5mm; border-bottom: 3px solid #1971c2; }
h3 { font-size: 14pt; margin: 4mm 0 2mm; }
section { break-before: page; }
section.first { break-before: auto; }
.cover { display: flex; flex-direction: column; justify-content: center; min-height: 175mm; }
.cover .sub { font-size: 15pt; color: #495057; }
.cover .team { margin-top: 8mm; font-size: 13pt; direction: ltr; text-align: right; }
.cover .team div { padding: 1mm 0; border-bottom: 1px solid #dee2e6; max-width: 120mm; margin-right: 0; margin-left: auto; display: flex; justify-content: space-between; font-family: 'DejaVu Sans Mono', monospace; font-size: 12pt; }
.diagram-wrap { text-align: center; margin: 2mm 0; break-inside: avoid; }
.diagram-wrap svg { direction: ltr; unicode-bidi: isolate; width: 100%; height: auto; max-height: 168mm; border: 1px solid #dee2e6; border-radius: 3mm; }
table.wt { width: 100%; border-collapse: collapse; margin: 2mm 0 3mm; font-size: 10.5pt; break-inside: avoid; }
table.wt th { background: #f1f3f5; text-align: right; padding: 1.6mm 2mm; border-bottom: 2px solid #adb5bd; font-weight: 700; }
table.wt td { padding: 0.9mm 2mm; border-bottom: 1px solid #e9ecef; vertical-align: middle; }
table.wt td.pin { font-family: 'DejaVu Sans Mono', monospace; font-weight: 700; font-size: 11pt; text-align: right; }
.badge { display: inline-block; width: 7.5mm; height: 7.5mm; line-height: 6.4mm; text-align: center; border: 2.5px solid; border-radius: 50%; font-weight: 700; font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; }
.sw { display: inline-block; width: 9mm; height: 3.2mm; border-radius: 2mm; margin-left: 2mm; vertical-align: middle; border: 1px solid #0003; }
ol.steps { padding-right: 6mm; margin: 1mm 0; }
ol.steps li { margin: 1mm 0; }
.box { border: 1.5px solid #1971c2; background: #e7f1fb; border-radius: 3mm; padding: 2.5mm 4mm; margin: 3mm 0; break-inside: avoid; }
.warn { border-color: #e8590c; background: #fff4e6; }
.ok { border-color: #2b8a3e; background: #ebfbee; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
pre { direction: ltr; text-align: left; background: #1f2329; color: #e9ecef; padding: 3mm 4mm; border-radius: 2.5mm; font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; line-height: 1.45; white-space: pre-wrap; margin: 2mm 0; }
.code2 { columns: 3; column-gap: 4mm; }
.three { display: grid; grid-template-columns: 1.7fr 1fr 1fr; gap: 4mm; }
.three pre.sm { font-size: 6.6pt; padding: 2mm 2.5mm; }
.code2 pre { margin: 0; font-size: 6.9pt; line-height: 1.3; padding: 2.5mm 3mm; }
pre.sm { font-size: 7.4pt; line-height: 1.35; }
.mono { font-family: 'DejaVu Sans Mono', monospace; direction: ltr; unicode-bidi: embed; font-weight: 700; }
table.pins { width: 100%; border-collapse: collapse; font-size: 11.5pt; }
table.pins th, table.pins td { padding: 1.6mm 2.5mm; border-bottom: 1px solid #dee2e6; text-align: right; }
table.pins th { background: #f1f3f5; }
.used { color: #2b8a3e; font-weight: 700; } .later { color: #868e96; }
.foot { color: #868e96; font-size: 10pt; }
"""


def build_html(svgs):
    """Assemble the full guide HTML.

    @param svgs dict of diagram svgs
    @returns html string
    """
    C = d.COL
    buzzer_rows = [
        (1, "Arduino D8", "Breadboard j17", C["orange"], "برتقالي", "نفس العمود اللي فيه رجل الـ <b>+</b> (الطويلة) بتاعة الـ buzzer في <span class='mono'>f17</span>"),
        (2, "Breadboard j20", "Arduino GND", C["black"], "أسود", "نفس العمود اللي فيه رجل الـ <b>−</b> (القصيرة) في <span class='mono'>f20</span>. الـ GND اللي جنب AREF في الصف الفوقاني"),
    ]
    lcd_rows = [
        (1, "LCD GND", "Arduino GND", C["black"], "أسود", "أي GND في الأردوينو"),
        (2, "LCD VCC", "Arduino 5V", C["red"], "أحمر", "<b>5V</b> مش 3.3V"),
        (3, "LCD SDA", "Arduino A4", C["blue"], "أزرق", "A4 = SDA في الـ UNO"),
        (4, "LCD SCL", "Arduino A5", C["green"], "أخضر", "A5 = SCL في الـ UNO"),
    ]
    full_rows = [
        (1, "Arduino 5V", "Rail + (col 2)", C["red"], "أحمر", "الصف الأحمر <b>+</b> اللي تحت. أي خرم فيه ينفع"),
        (2, "Arduino GND", "Rail − (col 1)", C["black"], "أسود", "الصف الأزرق <b>−</b> اللي تحت. أي خرم فيه ينفع"),
        (3, "Arduino D8", "j17", C["orange"], "برتقالي", "رجل الـ buzzer الـ <b>+</b> (الطويلة) في <span class='mono'>f17</span>"),
        (4, "j20", "Rail − (col 20)", C["black"], "أسود", "رجل الـ buzzer الـ <b>−</b> (القصيرة) في <span class='mono'>f20</span>"),
        (5, "MC-38 wire 1", "h24", "#ced4da", "سلك الحساس", "سلك من سلكين الـ MC-38 (مش مهم أنهي واحد)"),
        (6, "MC-38 wire 2", "Rail − (col 27)", "#adb5bd", "سلك الحساس", "السلك التاني على طول على الـ GND"),
        (7, "Arduino D2", "j24", C["purple"], "بنفسجي", "نفس عمود سلك الحساس الأول (24)"),
        (8, "LCD GND", "Rail − (col 30)", C["black"], "أسود", "سلك male-female"),
        (9, "LCD VCC", "Rail + (col 29)", C["red"], "أحمر", "سلك male-female"),
        (10, "LCD SDA", "Arduino A4", C["blue"], "أزرق", "على الأردوينو على طول"),
        (11, "LCD SCL", "Arduino A5", C["green"], "أخضر", "على الأردوينو على طول"),
    ]
    team_rows = "".join(f"<div><span>{n}</span><span>{i}</span></div>" for n, i in
                        (("Mahmoud Hisham", "2400844"), ("Ziad Hany", "2301401"),
                         ("Ahmed Hany", "2400311"), ("Moatasem Mohamed", "2400732")))
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>Smart Home Wiring Guide</title><style>{CSS}</style></head><body>

<section class="first cover">
  <div class="sub">MCT331s · Mechatronic System Integration · Project 1</div>
  <h1>دليل التوصيل — Smart Home</h1>
  <div class="sub">كل التوصيلات اللي عملناها لحد دلوقتي، خطوة بخطوة، بالصور ورقم كل pin.<br>
  اللي في الدليل: الـ Buzzer لوحده ← الشاشة LCD لوحدها ← التوصيل الكامل (LCD + Buzzer + حساس الشباك MC-38).</div>
  <div class="team">{team_rows}</div>
  <div class="foot" style="margin-top:6mm">Ain Shams University · Faculty of Engineering · 21 Oct 2026</div>
</section>

<section>
  <h2>0) قبل ما تبدأ</h2>
  <div class="two">
    <div>
      <h3>الحاجات المطلوبة</h3>
      <ul>
        <li>Arduino UNO + كابل USB</li>
        <li>Breadboard 830</li>
        <li>شاشة LCD 16×2 عليها I2C backpack</li>
        <li>Buzzer 5V</li>
        <li>حساس شباك مغناطيسي MC-38 (قطعتين: حساس بسلكين + مغناطيس)</li>
        <li>سلوك jumper: <span class="mono">M-M</span> (ذكر-ذكر) و <span class="mono">F-F</span> (أنثى-أنثى)</li>
      </ul>
      <div class="box warn"><b>قواعد مهمة:</b>
        <ol class="steps">
          <li><b>افصل الـ USB</b> قبل ما توصّل أو تشيل أي سلك.</li>
          <li><b>متوصّلش 5V في GND</b> على طول أبدًا، دي قفلة (short) وممكن تحرق البورت.</li>
          <li>استخدم نفس الألوان: <b style="color:#d62828">أحمر = 5V</b>، <b>أسود = GND</b>، وباقي الألوان للإشارات.</li>
          <li>كل سلك لازم يكون <b>داخل جامد</b>. اسحبه بالراحة، لو طلع يبقى مش داخل كويس.</li>
        </ol>
      </div>
    </div>
    <div>
      <h3>إزاي تعمل سلك Male-Female</h3>
      <p>رجول الشاشة <b>ذكر</b> والأردوينو <b>أنثى</b>، فمحتاج سلك ذكر من ناحية وأنثى من الناحية التانية.
      لو معندكش، <b>دخّل سلك M-M جوه طرف سلك F-F</b>، فيبقى عندك سلك ذكر-أنثى. لفّ على الوصلة شوية شريط عشان متفكّش.</p>
      <div class="box"><b>اقرا مكان الخرم كده:</b> الحرف هو <b>الصف</b> (a–j) والرقم هو <b>العمود</b> (1–30).
      يعني <span class="mono">j17</span> = صف j، عمود 17. و <span class="mono">Rail −</span> = الصف الأزرق اللي تحت.</div>
      <div class="box warn">الـ breadboard بتاعتك <b>Split rails</b>، يعني الصف الأحمر والأزرق <b>مقسومين في النص</b>.
      طول ما إنت شغال في الأعمدة من 1 لـ 30 (زي الصور) مفيش مشكلة. لو نقلت لأعمدة بعد 31، وصّل سلك صغير بين نصين الـ rail.</div>
    </div>
  </div>
</section>
<section>
  <h2>0) الـ breadboard متوصلة من جوه إزاي</h2>
  <p>أهم حاجة تفهمها قبل أي توصيل: الخرمين اللي في <b>نفس العمود</b> (في نفس النص) متوصلين ببعض، فلو حطيت رجل قطعة وسلك في نفس العمود يبقوا متوصلين.</p>
  <div class="diagram-wrap" style="max-width:250mm;margin:0 auto">{svgs['bb']}</div>
</section>

<section>
  <h2>1) الـ Buzzer لوحده</h2>
  <div class="diagram-wrap">{svgs['buzzer']}</div>
</section>
<section>
  <h2>1) الـ Buzzer لوحده — الخطوات</h2>
  <div class="two">
    <div>
      <h3>حط الـ buzzer على الـ breadboard</h3>
      <ol class="steps">
        <li>بص على رجلين الـ buzzer: <b>الطويلة = +</b> والقصيرة = −. وغالبًا علامة <b>+</b> مكتوبة عليه من فوق.</li>
        <li>دخّل الرجل الطويلة (+) في <span class="mono">f17</span>، والقصيرة (−) في <span class="mono">f20</span>.</li>
      </ol>
      <h3>السلوك</h3>
      {table(buzzer_rows)}
      <div class="box ok"><b>النتيجة المتوقعة:</b> بعد ما ترفع الكود، الـ buzzer يزمّر نص ثانية ويسكت نص ثانية على طول.</div>
      <div class="box warn">لو مش بيزمّر: اقلب رجلين الـ buzzer، واتأكد إن السلك البرتقالي في <b>D8</b> مش في D7 أو D9.</div>
    </div>
    <div>
      <h3>كود التجربة</h3>
      {code(BUZZER_TEST)}
    </div>
  </div>
</section>

<section>
  <h2>2) الشاشة LCD لوحدها</h2>
  <div class="diagram-wrap">{svgs['lcd']}</div>
</section>
<section>
  <h2>2) الشاشة LCD لوحدها — الخطوات</h2>
  <div class="three">
    <div>
      <p>الشاشة متوصلة بـ <b>4 سلوك بس</b> عن طريق الـ I2C backpack (البوردة الصغيرة اللي ورا الشاشة). الـ 4 رجول مكتوب جنبهم أساميهم.</p>
      {table(lcd_rows)}
      <h3>الخطوات</h3>
      <ol class="steps">
        <li>نزّل الـ library: في الـ Arduino IDE افتح <b>Library Manager</b> وابحث عن <span class="mono">LiquidCrystal I2C</span> بتاعة <b>Frank de Brabander</b> ودوس Install.</li>
        <li>ارفع <b>الـ I2C Scanner</b> وافتح الـ Serial Monitor على <span class="mono">9600</span>. هيكتب <span class="mono">Found device at 0x27</span> أو <span class="mono">0x3F</span>.</li>
        <li>ارفع كود تجربة الشاشة، وحط فيه نفس الرقم اللي طلعلك.</li>
        <li>لو الشاشة منوّرة بس فيها <b>مربعات سودا</b>، أو مفيش كتابة: لفّ الـ <b>pot الأزرق</b> اللي ورا الشاشة بمفك لحد ما الكتابة تبان.</li>
      </ol>
      <div class="box ok"><b>النتيجة المتوقعة:</b> الشاشة تكتب <span class="mono">SMART HOME</span> في السطر الأول و <span class="mono">MCT331s Team</span> في التاني.</div>
    </div>
    <div>
      <h3>الـ I2C Scanner</h3>
      {code(SCANNER, True)}
    </div>
    <div>
      <h3>كود تجربة الشاشة</h3>
      {code(LCD_TEST, True)}
    </div>
  </div>
</section>

<section>
  <h2>3) التوصيل الكامل — LCD + Buzzer + حساس الشباك</h2>
  <div class="diagram-wrap">{svgs['full']}</div>
</section>
<section>
  <h2>3) التوصيل الكامل — جدول السلوك</h2>
  <p>هنا الكهربا (5V و GND) بتطلع من الأردوينو للـ breadboard الأول، وكل حاجة بتاخد منها. الأرقام نفس الأرقام اللي على السلوك في الصورة.</p>
  {table(full_rows)}
  <div class="two">
    <div class="box"><b>وصّل بالترتيب ده:</b>
      <ol class="steps">
        <li>السلكين <b>1 و 2</b> (الكهربا للـ breadboard).</li>
        <li>الـ buzzer في <span class="mono">f17</span> و <span class="mono">f20</span>، وبعدين السلكين <b>3 و 4</b>.</li>
        <li>حساس الشباك: السلكين <b>5 و 6</b>، وبعدين السلك <b>7</b>.</li>
        <li>الشاشة: <b>8 و 9</b> للـ breadboard، و <b>10 و 11</b> للأردوينو.</li>
        <li>راجع كل سلك مع الجدول، وبعدين وصّل الـ USB.</li>
      </ol>
    </div>
    <div class="box warn"><b>حساس الشباك MC-38:</b>
      <ul>
        <li>القطعة اللي فيها <b>سلكين</b> هي الحساس، والقطعة التانية <b>مغناطيس</b> ملهوش سلوك.</li>
        <li>لو سلوكه رفيعة ومش بتدخل في الـ breadboard، اقشر 1 سم ولفّ السلك، أو الحمه في رجل header.</li>
        <li>المغناطيس لازم يكون <b>أقل من 1 سم</b> من الحساس، والعلامات اللي على جنبهم قصاد بعض.</li>
        <li>المغناطيس قريب = الشباك <b>مقفول</b>. المغناطيس بعيد = الشباك <b>مفتوح</b>.</li>
      </ul>
    </div>
  </div>
</section>
<section>
  <h2>3) التوصيل الكامل — الكود</h2>
  <div class="code2">{code(FULL)}</div>
</section>
<section>
  <h2>3) التوصيل الكامل — التجربة وحل المشاكل</h2>
  <div class="two">
    <div>
      <h3>جرّب بالترتيب ده</h3>
      <ol class="steps">
        <li>ارفع الكود. الشاشة تكتب <span class="mono">SMART HOME</span> ثانية ونص، وبعدين <span class="mono">Security:ARMED</span> و <span class="mono">Window: CLOSED</span>.</li>
        <li><b>ابعد المغناطيس</b> عن الحساس: الـ buzzer <b>يزمّر على طول</b>، والشاشة تكتب <span class="mono">!! INTRUSION !!</span>.</li>
        <li><b>قرّب المغناطيس</b>: الـ buzzer <b>يسكت فورًا</b>، والشاشة ترجع <span class="mono">Window: CLOSED</span>.</li>
        <li>افتح الـ Serial Monitor على 9600: كل مرة تفتح الشباك هيكتب <span class="mono">ALERT:WINDOW_OPEN</span>. ده اللي الـ ESP8266 هيبعته على الموبايل بعدين.</li>
      </ol>
    </div>
    <div>
      <h3>لو حاجة مش شغالة</h3>
      <table class="pins">
        <tr><th>المشكلة</th><th>الحل</th></tr>
        <tr><td>الشاشة مربعات سودا</td><td>لفّ الـ pot الأزرق، واتأكد إن <span class="mono">LCD_ADDR</span> نفس رقم الـ scanner</td></tr>
        <tr><td>الشاشة مطفية</td><td>السلكين <b>8 و 9</b> أو <b>1 و 2</b> مش واصلين</td></tr>
        <tr><td>الشباك مقلوب (مفتوح يكتب CLOSED)</td><td>غيّر <span class="mono">REED_OPEN_LEVEL</span> لـ <span class="mono">LOW</span></td></tr>
        <tr><td>الشباك ثابت مش بيتغيّر</td><td>السلك <b>7</b> مش في D2، أو سلك الحساس <b>5</b> مش في نفس عمود 24</td></tr>
        <tr><td>الـ buzzer مش بيزمّر</td><td>السلك <b>3</b> مش في D8، أو رجلين الـ buzzer مقلوبين</td></tr>
        <tr><td>Upload error / COM</td><td>اختار البورت الصح من <b>Tools → Port</b>، واقفل الـ Serial Monitor قبل الرفع</td></tr>
      </table>
    </div>
  </div>
</section>

<section>
  <h2>4) ملخص الـ pins</h2>
  <table class="pins">
    <tr><th>Pin</th><th>متوصل بإيه</th><th>الحالة</th></tr>
    <tr><td class="mono">5V</td><td>الـ Rail + (الشاشة VCC)</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">GND</td><td>الـ Rail − (الشاشة + الـ buzzer + الحساس)</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">A4 (SDA)</td><td>LCD SDA (وبعدين الـ keypad عن طريق PCF8574)</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">A5 (SCL)</td><td>LCD SCL</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">D2</td><td>حساس الشباك MC-38</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">D8</td><td>Buzzer (+)</td><td class="used">مستخدم</td></tr>
    <tr><td class="mono">D3</td><td>PIR (حساس الحركة)</td><td class="later">جاي بعدين</td></tr>
    <tr><td class="mono">D7</td><td>Toggle الـ ARM (خلي <span class="mono">ALWAYS_ARMED = false</span> لما توصّله)</td><td class="later">جاي بعدين</td></tr>
    <tr><td class="mono">D6 / D11</td><td>زرار النور / LEDs النور الداخلي</td><td class="later">جاي بعدين</td></tr>
    <tr><td class="mono">A0</td><td>LDR</td><td class="later">جاي بعدين</td></tr>
    <tr><td class="mono">D1 (TX)</td><td>ESP8266 (التنبيه على الموبايل)</td><td class="later">جاي بعدين</td></tr>
  </table>
  <p class="foot" style="margin-top:6mm">{TEAM}</p>
</section>
</body></html>"""


async def render(out_dir):
    """Write the HTML, print it to PDF and export each diagram as PNG.

    @param out_dir output folder
    @returns None
    """
    from playwright.async_api import async_playwright
    os.makedirs(out_dir, exist_ok=True)
    svgs = {"bb": d.diagram_bb_explain(), "buzzer": d.diagram_buzzer(), "lcd": d.diagram_lcd(), "full": d.diagram_full()}
    page_html = build_html(svgs)
    html_path = os.path.join(out_dir, "Wiring_Guide.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(page_html)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto("file://" + html_path)
        await pg.wait_for_timeout(500)
        await pg.pdf(path=os.path.join(out_dir, "Wiring_Guide.pdf"), format="A4", landscape=True, print_background=True,
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}, prefer_css_page_size=True)
        img = await b.new_page(device_scale_factor=2)
        for name, key in (("00_breadboard_explained", "bb"), ("01_buzzer_alone", "buzzer"),
                          ("02_lcd_alone", "lcd"), ("03_full_system", "full")):
            await img.set_content(f"<html><body style='margin:0;background:#fff'>{svgs[key]}</body></html>")
            await img.locator("svg").screenshot(path=os.path.join(out_dir, name + ".png"))
        await b.close()


if __name__ == "__main__":
    asyncio.run(render(sys.argv[1] if len(sys.argv) > 1 else "out"))
