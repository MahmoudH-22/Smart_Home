"""
Wiring diagrams (breadboard view) for the MCT331s smart home - Fritzing-style SVG.

Generates three diagrams that match the code the team is running:
  1. buzzer alone      (D8 -> buzzer +, buzzer - -> GND)
  2. LCD alone         (GND, 5V, A4=SDA, A5=SCL)
  3. full system       (LCD + buzzer + MC-38 reed on D2, power through the breadboard rails)
"""
from __future__ import annotations

P = 14  # hole pitch (2.54 mm) in drawing units

# ---------------------------------------------------------------- colours
COL = {
    "red": "#d62828", "black": "#1d1d1f", "orange": "#f08c00", "purple": "#7b2cbf",
    "blue": "#1971c2", "green": "#2b8a3e", "white": "#f1f3f5",
}


def esc(s: str) -> str:
    """Escape text for SVG.

    @param s raw text
    @returns escaped text
    """
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- Arduino UNO
class Uno:
    """Arduino UNO drawn with USB on the left, digital header on top, power/analog at the bottom."""

    TOP = ["SCL", "SDA", "AREF", "GND", "13", "12", "~11", "~10", "~9", "8",
           "7", "~6", "~5", "4", "~3", "2", "TX 1", "RX 0"]
    BOT = ["NC", "IOREF", "RESET", "3.3V", "5V", "GND", "GND", "VIN", "A0", "A1", "A2", "A3", "A4", "A5"]

    def __init__(self, x, y):
        """Place the board.

        @param x left edge  @param y top edge
        """
        self.x, self.y, self.w, self.h = x, y, 390, 300

    def _top_x(self, i):
        """X of the i-th top-header pin."""
        return self.x + 120 + i * P + (8 if i >= 10 else 0)

    def _bot_x(self, i):
        """X of the i-th bottom-header pin."""
        return self.x + 150 + i * P + (8 if i >= 8 else 0)

    def pin(self, name):
        """Centre of a header pin by label (e.g. 'D6', '5V', 'GND_TOP', 'A4').

        @param name pin label
        @returns (x, y)
        """
        alias = {"D%d" % n: str(n) for n in range(14)}
        alias.update({"D3": "~3", "D5": "~5", "D6": "~6", "D9": "~9", "D10": "~10", "D11": "~11",
                      "D1": "TX 1", "D0": "RX 0"})
        if name == "GND_TOP":
            return self._top_x(3), self.y + 14
        if name == "GND_BOT":
            return self._bot_x(5), self.y + self.h - 14
        n = alias.get(name, name)
        if n in self.TOP:
            return self._top_x(self.TOP.index(n)), self.y + 14
        return self._bot_x(self.BOT.index(n)), self.y + self.h - 14

    def svg(self, highlight=()):
        """Draw the board.

        @param highlight pin names to ring in yellow
        @returns svg fragment
        """
        x, y, w, h = self.x, self.y, self.w, self.h
        s = [f'<g class="uno">',
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#0e7c86" stroke="#075259" stroke-width="2"/>',
             # USB-B and DC jack
             f'<rect x="{x - 18}" y="{y + 50}" width="62" height="58" rx="3" fill="#c7cdd4" stroke="#7b848d"/>',
             f'<text x="{x + 13}" y="{y + 84}" class="chip">USB</text>',
             f'<rect x="{x - 10}" y="{y + 200}" width="56" height="44" rx="4" fill="#202226"/>',
             f'<text x="{x + 18}" y="{y + 227}" class="chipw">DC</text>',
             # MCU
             f'<rect x="{x + 170}" y="{y + 150}" width="170" height="44" rx="3" fill="#1b1d21"/>',
             f'<text x="{x + 255}" y="{y + 177}" class="chipw">ATmega328P</text>',
             f'<text x="{x + 120}" y="{y + 128}" class="unologo">ARDUINO UNO</text>',
             # reset button
             f'<rect x="{x + 28}" y="{y + 12}" width="26" height="26" rx="4" fill="#c9ccd1"/>',
             f'<circle cx="{x + 41}" cy="{y + 25}" r="8" fill="#d62828"/>',
             f'<text x="{x + 41}" y="{y + 52}" class="pinl">RESET</text>']
        # headers
        s.append(f'<rect x="{self._top_x(0) - 8}" y="{y + 6}" width="{10 * P + 2}" height="16" fill="#111" rx="2"/>')
        s.append(f'<rect x="{self._top_x(10) - 8}" y="{y + 6}" width="{8 * P + 2}" height="16" fill="#111" rx="2"/>')
        s.append(f'<rect x="{self._bot_x(0) - 8}" y="{y + h - 22}" width="{8 * P + 2}" height="16" fill="#111" rx="2"/>')
        s.append(f'<rect x="{self._bot_x(8) - 8}" y="{y + h - 22}" width="{6 * P + 2}" height="16" fill="#111" rx="2"/>')
        for i, n in enumerate(self.TOP):
            px = self._top_x(i)
            s.append(f'<rect x="{px - 3}" y="{y + 11}" width="6" height="6" fill="#555"/>')
            s.append(f'<text transform="translate({px + 3.5},{y + 28}) rotate(90)" class="pinl" text-anchor="start">{esc(n)}</text>')
        for i, n in enumerate(self.BOT):
            px = self._bot_x(i)
            s.append(f'<rect x="{px - 3}" y="{y + h - 17}" width="6" height="6" fill="#555"/>')
            s.append(f'<text transform="translate({px + 3.5},{y + h - 28}) rotate(-90)" class="pinl" text-anchor="start">{esc(n)}</text>')
        s.append(f'<text x="{self._top_x(14)}" y="{y + 82}" class="pinl2">DIGITAL (PWM ~)</text>')
        s.append(f'<text x="{self._bot_x(3)}" y="{y + h - 72}" class="pinl2">POWER</text>')
        s.append(f'<text x="{self._bot_x(10) + 8}" y="{y + h - 72}" class="pinl2">ANALOG IN</text>')
        for n in highlight:
            px, py = self.pin(n)
            s.append(f'<circle cx="{px}" cy="{py}" r="8" fill="none" stroke="#ffd43b" stroke-width="3"/>')
        s.append('</g>')
        return "".join(s)


# ---------------------------------------------------------------- breadboard
class Breadboard:
    """Half-size view of an 830-point breadboard: 30 columns, rows a-e / f-j, top and bottom rails."""

    def __init__(self, x, y, cols=30):
        """Place the breadboard.

        @param x left edge  @param y top edge  @param cols number of columns drawn
        """
        self.x, self.y, self.cols = x, y, cols
        self.w = 72 + (cols - 1) * P
        self.rows = {}
        for i, r in enumerate("abcde"):
            self.rows[r] = y + 96 + i * P
        for i, r in enumerate("fghij"):
            self.rows[r] = y + 182 + i * P
        self.rows["top+"] = y + 22
        self.rows["top-"] = y + 36
        self.rows["bot+"] = y + 290
        self.rows["bot-"] = y + 304
        self.h = 326

    def cx(self, c):
        """X of column c (1-based).

        @param c column
        @returns x
        """
        return self.x + 36 + (c - 1) * P

    def hole(self, name):
        """Centre of a hole: 'j17', 'bot-:20', 'top+:3'.

        @param name hole id
        @returns (x, y)
        """
        if ":" in name:
            r, c = name.split(":")
            return self.cx(int(c)), self.rows[r]
        return self.cx(int(name[1:])), self.rows[name[0]]

    def svg(self, highlight=()):
        """Draw the breadboard.

        @param highlight hole ids to ring
        @returns svg fragment
        """
        x, y = self.x, self.y
        s = [f'<g class="bb"><rect x="{x}" y="{y}" width="{self.w}" height="{self.h}" rx="8" fill="#f5f5f0" stroke="#c9c9c0" stroke-width="2"/>',
             f'<rect x="{x + 8}" y="{y + 163}" width="{self.w - 16}" height="10" rx="3" fill="#e2e2da"/>']
        # rails
        for key, col, sign in (("top+", COL["red"], "+"), ("top-", COL["blue"], "−"),
                               ("bot+", COL["red"], "+"), ("bot-", COL["blue"], "−")):
            ry = self.rows[key]
            off = -8 if key.endswith("+") else 8
            s.append(f'<line x1="{x + 26}" y1="{ry + off}" x2="{x + self.w - 26}" y2="{ry + off}" stroke="{col}" stroke-width="2"/>')
            s.append(f'<text x="{x + 14}" y="{ry + 4}" class="rail" fill="{col}">{sign}</text>')
            s.append(f'<text x="{x + self.w - 14}" y="{ry + 4}" class="rail" fill="{col}">{sign}</text>')
            for c in range(1, self.cols + 1):
                if (c - 1) % 6 == 5:
                    continue  # rail holes come in groups of 5
                s.append(f'<rect x="{self.cx(c) - 3}" y="{ry - 3}" width="6" height="6" rx="1" fill="#3b3b3b"/>')
        # main grid
        for r in "abcdefghij":
            ry = self.rows[r]
            s.append(f'<text x="{x + 16}" y="{ry + 4}" class="rowl">{r}</text>')
            s.append(f'<text x="{x + self.w - 16}" y="{ry + 4}" class="rowl">{r}</text>')
            for c in range(1, self.cols + 1):
                s.append(f'<rect x="{self.cx(c) - 3}" y="{ry - 3}" width="6" height="6" rx="1" fill="#3b3b3b"/>')
        for c in range(1, self.cols + 1):
            cls = "coll b" if c % 5 == 0 or c == 1 else "coll"
            s.append(f'<text x="{self.cx(c)}" y="{self.rows["a"] - 12}" class="{cls}">{c}</text>')
            s.append(f'<text x="{self.cx(c)}" y="{self.rows["j"] + 20}" class="{cls}">{c}</text>')
        for hname in highlight:
            hx, hy = self.hole(hname)
            s.append(f'<circle cx="{hx}" cy="{hy}" r="7" fill="none" stroke="#ffd43b" stroke-width="3"/>')
        s.append('</g>')
        return "".join(s)


# ---------------------------------------------------------------- parts
def buzzer(bb: Breadboard, col_plus: int, row="f"):
    """Buzzer with + leg at (row, col_plus) and - leg 3 columns to the right.

    @param bb breadboard  @param col_plus column of the + leg  @param row row of both legs
    @returns svg fragment
    """
    x1, y1 = bb.hole(f"{row}{col_plus}")
    x2, _ = bb.hole(f"{row}{col_plus + 3}")
    cx, cy = (x1 + x2) / 2, y1 - 14
    return (f'<g><circle cx="{cx}" cy="{cy}" r="27" fill="#1f1f1f" stroke="#000" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="5" fill="#444"/>'
            f'<circle cx="{x1}" cy="{y1}" r="4" fill="#bbb"/><circle cx="{x2}" cy="{y1}" r="4" fill="#bbb"/>'
            f'<text x="{x1 - 2}" y="{cy - 6}" class="partw" text-anchor="middle">+</text>'
            f'<text x="{x2 + 2}" y="{cy - 6}" class="partw" text-anchor="middle">−</text>'
            f'<text x="{cx}" y="{cy - 34}" class="part">Buzzer 5V</text></g>')


def reed(x, y):
    """MC-38 magnetic reed switch (wired part) + magnet below it.

    @param x left of the switch body  @param y top of the switch body
    @returns (svg fragment, lead-1 exit point, lead-2 exit point)
    """
    s = (f'<g><rect x="{x}" y="{y}" width="110" height="30" rx="5" fill="#f8f9fa" stroke="#868e96" stroke-width="2"/>'
         f'<text x="{x + 55}" y="{y + 20}" class="part">MC-38 (switch)</text>'
         f'<rect x="{x}" y="{y + 52}" width="110" height="30" rx="5" fill="#f8f9fa" stroke="#868e96" stroke-width="2"/>'
         f'<text x="{x + 55}" y="{y + 72}" class="part">Magnet</text>'
         f'<line x1="{x + 118}" y1="{y + 30}" x2="{x + 118}" y2="{y + 52}" stroke="#495057" stroke-width="1.5" marker-start="url(#arr)" marker-end="url(#arr)"/>'
         f'<text x="{x + 126}" y="{y + 45}" class="note" text-anchor="start">≤ 10 mm</text></g>')
    return s, (x, y + 9), (x, y + 21)


def lcd(x, y, l1="Security:ARMED", l2="Window:  CLOSED"):
    """16x2 LCD seen from the front with the I2C backpack pins on its left edge.

    @param x left edge  @param y top edge  @param l1,l2 text shown on the screen
    @returns (svg fragment, dict pin -> (x, y))
    """
    pins = {}
    s = [f'<g><rect x="{x}" y="{y}" width="300" height="140" rx="6" fill="#1f6b3a" stroke="#134526" stroke-width="2"/>',
         f'<rect x="{x + 22}" y="{y + 26}" width="256" height="84" rx="4" fill="#2b2f36"/>',
         f'<rect x="{x + 32}" y="{y + 36}" width="236" height="64" rx="2" fill="#2149c9"/>',
         f'<text x="{x + 40}" y="{y + 62}" class="lcdt">{esc(l1)}</text>',
         f'<text x="{x + 40}" y="{y + 90}" class="lcdt">{esc(l2)}</text>',
         f'<text x="{x + 150}" y="{y + 132}" class="partw">LCD 16×2 + I2C backpack</text>',
         f'<rect x="{x - 14}" y="{y + 22}" width="16" height="70" fill="#111" rx="2"/>']
    for i, n in enumerate(("GND", "VCC", "SDA", "SCL")):
        py = y + 32 + i * 17
        s.append(f'<rect x="{x - 26}" y="{py - 2}" width="14" height="4" fill="#c0a050"/>')
        s.append(f'<text x="{x + 6}" y="{py + 4}" class="pinw" text-anchor="start">{n}</text>')
        pins[n] = (x - 26, py)
    s.append('</g>')
    return "".join(s), pins


# ---------------------------------------------------------------- wires
def wire(points, color, num=None, label_at=None):
    """Draw a jumper wire through a list of points (rounded polyline) with an optional number badge.

    @param points [(x, y), ...] from start to end
    @param color colour key or hex
    @param num badge number linking to the table
    @param label_at index of the segment to put the badge on (default middle)
    @returns svg fragment
    """
    c = COL.get(color, color)
    d = "M%.1f,%.1f " % points[0] + " ".join("L%.1f,%.1f" % p for p in points[1:])
    s = [f'<path d="{d}" fill="none" stroke="#00000055" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>',
         f'<path d="{d}" fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>']
    for (px, py) in (points[0], points[-1]):
        s.append(f'<circle cx="{px}" cy="{py}" r="4.5" fill="{c}" stroke="#000" stroke-width="1"/>')
    if num is not None:
        i = label_at if label_at is not None else max(0, len(points) // 2 - 1)
        (ax, ay), (bx, by) = points[i], points[i + 1]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        s.append(f'<circle cx="{mx}" cy="{my}" r="11" fill="#fff" stroke="{c}" stroke-width="3"/>')
        s.append(f'<text x="{mx}" y="{my + 4.5}" class="badge">{num}</text>')
    return "".join(s)


def tag(x, y, text, anchor="middle", dy=0):
    """Small text tag (pin / hole names next to wire ends).

    @param x,y position  @param text label  @param anchor text-anchor  @param dy vertical offset
    @returns svg fragment
    """
    w = 7.2 * len(text) + 10
    bx = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
    return (f'<rect x="{bx}" y="{y + dy - 11}" width="{w}" height="16" rx="3" fill="#fff" stroke="#adb5bd"/>'
            f'<text x="{bx + w / 2}" y="{y + dy + 1}" class="tag">{esc(text)}</text>')


DEFS = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#495057"/></marker></defs>')

STYLE = """<style>
.chip{font:600 11px 'DejaVu Sans',sans-serif;fill:#333;text-anchor:middle}
.chipw{font:600 11px 'DejaVu Sans',sans-serif;fill:#ddd;text-anchor:middle}
.unologo{font:700 20px 'DejaVu Sans',sans-serif;fill:#e9f7f8;letter-spacing:2px}
.pinl{font:600 8.5px 'DejaVu Sans Mono',monospace;fill:#fff;text-anchor:middle}
.pinl2{font:600 10px 'DejaVu Sans',sans-serif;fill:#bfeff2;text-anchor:middle}
.rail{font:700 15px 'DejaVu Sans',sans-serif;text-anchor:middle}
.rowl{font:600 10px 'DejaVu Sans Mono',monospace;fill:#666;text-anchor:middle}
.coll{font:500 8px 'DejaVu Sans Mono',monospace;fill:#777;text-anchor:middle}
.coll.b{font-weight:700;fill:#222;font-size:9px}
.part{font:600 12px 'DejaVu Sans',sans-serif;fill:#212529;text-anchor:middle}
.partw{font:700 12px 'DejaVu Sans',sans-serif;fill:#fff;text-anchor:middle}
.pinw{font:700 11px 'DejaVu Sans Mono',monospace;fill:#fff}
.lcdt{font:600 19px 'DejaVu Sans Mono',monospace;fill:#eef3ff;letter-spacing:1px}
.badge{font:700 12px 'DejaVu Sans',sans-serif;fill:#111;text-anchor:middle}
.tag{font:700 11px 'DejaVu Sans Mono',monospace;fill:#111;text-anchor:middle}
.note{font:600 11px 'DejaVu Sans',sans-serif;fill:#495057}
.title{font:700 15px 'DejaVu Sans',sans-serif;fill:#212529}
</style>"""


def frame(w, h, body, title):
    """Wrap a diagram body in an <svg>.

    @param w,h canvas size  @param body svg content  @param title caption drawn top-left
    @returns svg string
    """
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" class="diagram">'
            f'{STYLE}{DEFS}<rect width="{w}" height="{h}" fill="#ffffff"/>'
            f'<text x="18" y="26" class="title">{esc(title)}</text>{body}</svg>')


# ---------------------------------------------------------------- diagram 1: buzzer
def diagram_buzzer():
    """Buzzer alone: D8 -> j17 (+ column), j20 (- column) -> GND.

    @returns svg string
    """
    bb = Breadboard(320, 46)
    uno = Uno(300, 440)
    d6 = uno.pin("D8")
    gnd = uno.pin("GND_TOP")
    h1, h2 = bb.hole("j17"), bb.hole("j20")
    body = [bb.svg(highlight=["j17", "j20", "f17", "f20"]), uno.svg(highlight=["D8", "GND_TOP"]), buzzer(bb, 17)]
    body.append(wire([d6, (d6[0], bb.y + bb.h + 30), (h1[0], bb.y + bb.h + 30), h1], "orange", 1, label_at=0))
    body.append(wire([h2, (h2[0], bb.y + bb.h + 14), (gnd[0], bb.y + bb.h + 14), gnd], "black", 2, label_at=2))
    body += [tag(d6[0] + 14, d6[1] - 26, "D8", "start"), tag(gnd[0] - 6, gnd[1] - 26, "GND", "end"),
             tag(h1[0] - 8, h1[1] - 12, "j17", "end"), tag(h2[0] + 8, h2[1] - 12, "j20", "start")]
    body.append(f'<text x="{bb.x + bb.w + 20}" y="{bb.y + 160}" class="note" text-anchor="start">Long leg (+) → column 17</text>')
    body.append(f'<text x="{bb.x + bb.w + 20}" y="{bb.y + 180}" class="note" text-anchor="start">Short leg (−) → column 20</text>')
    return frame(1060, 770, "".join(body), "1) Buzzer alone  —  D8 → Buzzer(+) , Buzzer(−) → GND")


# ---------------------------------------------------------------- diagram 2: LCD
def diagram_lcd():
    """LCD alone, straight to the UNO with male-to-female wires.

    @returns svg string
    """
    uno = Uno(60, 120)
    lsvg, lp = lcd(660, 150, "  SMART HOME", "  MCT331s Team")
    p5, pg, a4, a5 = uno.pin("5V"), uno.pin("GND_BOT"), uno.pin("A4"), uno.pin("A5")
    body = [uno.svg(highlight=["5V", "GND_BOT", "A4", "A5"]), lsvg]
    yb = 500
    body.append(wire([lp["GND"], (600, lp["GND"][1]), (600, yb + 60), (pg[0], yb + 60), pg], "black", 1, label_at=2))
    body.append(wire([lp["VCC"], (585, lp["VCC"][1]), (585, yb + 45), (p5[0], yb + 45), p5], "red", 2, label_at=1))
    body.append(wire([lp["SDA"], (570, lp["SDA"][1]), (570, yb + 30), (a4[0], yb + 30), a4], "blue", 3, label_at=2))
    body.append(wire([lp["SCL"], (555, lp["SCL"][1]), (555, yb + 15), (a5[0], yb + 15), a5], "green", 4, label_at=1))
    for n, p in (("GND", pg), ("5V", p5), ("A4", a4), ("A5", a5)):
        left = n in ("5V", "A4")
        body.append(tag(p[0] + (-12 if left else 12), p[1] + 30, n, "end" if left else "start"))
    body.append(f'<text x="660" y="330" class="note" text-anchor="start">Blue pot on the back = contrast</text>')
    body.append(f'<text x="660" y="350" class="note" text-anchor="start">Black boxes / no text → turn it with a screwdriver</text>')
    return frame(1060, 640, "".join(body), "2) LCD 16×2 I2C alone  —  GND→GND , VCC→5V , SDA→A4 , SCL→A5")


# ---------------------------------------------------------------- diagram 3: full
def diagram_full():
    """Full system: rails powered from the UNO, LCD + buzzer + MC-38 reed.

    @returns svg string
    """
    bb = Breadboard(320, 46)
    uno = Uno(300, 450)
    lsvg, lp = lcd(800, 480)
    rsvg, r1, r2 = reed(900, 150)
    p5, pg = uno.pin("5V"), uno.pin("GND_BOT")
    d6, d3 = uno.pin("D8"), uno.pin("D2")
    a4, a5 = uno.pin("A4"), uno.pin("A5")
    holes = ["bot+:2", "bot-:1", "j17", "j20", "bot-:20", "f17", "f20", "h24", "j24", "bot-:27", "bot+:29", "bot-:30"]
    body = [bb.svg(highlight=holes), uno.svg(highlight=["5V", "GND_BOT", "D8", "D2", "A4", "A5"]),
            buzzer(bb, 17), lsvg, rsvg]
    yb = bb.y + bb.h          # bottom edge of the breadboard
    ybot = uno.y + uno.h      # bottom edge of the UNO
    # power rails
    rp, rm = bb.hole("bot+:2"), bb.hole("bot-:1")
    body.append(wire([p5, (p5[0], ybot + 40), (270, ybot + 40), (270, rp[1]), rp], "red", 1, label_at=2))
    body.append(wire([pg, (pg[0], ybot + 56), (252, ybot + 56), (252, rm[1]), rm], "black", 2, label_at=1))
    # buzzer
    j17, j20, m20 = bb.hole("j17"), bb.hole("j20"), bb.hole("bot-:20")
    body.append(wire([d6, (d6[0], yb + 40), (j17[0], yb + 40), j17], "orange", 3, label_at=1))
    body.append(wire([j20, m20], "black", 4, label_at=0))
    # reed
    h24, j24, m27 = bb.hole("h24"), bb.hole("j24"), bb.hole("bot-:27")
    body.append(wire([r1, (860, r1[1]), (h24[0] + 30, 200), h24], "#dee2e6", 5, label_at=1))
    body.append(wire([r2, (875, r2[1]), (m27[0] + 40, 300), m27], "#adb5bd", 6, label_at=1))
    body.append(wire([d3, (d3[0], yb + 24), (j24[0], yb + 24), j24], "purple", 7, label_at=1))
    # LCD
    p29, m30 = bb.hole("bot+:29"), bb.hole("bot-:30")
    body.append(wire([lp["GND"], (790, lp["GND"][1]), (790, m30[1]), m30], "black", 8, label_at=1))
    body.append(wire([lp["VCC"], (776, lp["VCC"][1]), (776, yb + 14), (p29[0], yb + 14), p29], "red", 9, label_at=1))
    body.append(wire([lp["SDA"], (745, lp["SDA"][1]), (745, ybot + 40), (a4[0], ybot + 40), a4], "blue", 10, label_at=2))
    body.append(wire([lp["SCL"], (730, lp["SCL"][1]), (730, ybot + 56), (a5[0], ybot + 56), a5], "green", 11, label_at=1))
    # tags: UNO pins
    body += [tag(d6[0] - 6, d6[1] - 24, "D8", "end"), tag(d3[0] + 10, d3[1] - 24, "D2", "start")]
    for n, p in (("5V", p5), ("GND", pg), ("A4", a4), ("A5", a5)):
        left = n in ("5V", "A4")
        body.append(tag(p[0] + (-12 if left else 12), p[1] + 30, n, "end" if left else "start"))
    # tags: breadboard holes (two staggered rows under the board)
    for name, hp, anc in (("j17", j17, "end"), ("j24", j24, "start")):
        ty = yb + 20
        body.append(f'<line x1="{hp[0]}" y1="{yb}" x2="{hp[0]}" y2="{ty - 6}" stroke="#868e96" stroke-dasharray="2 2"/>')
        body.append(tag(hp[0] + (-4 if anc == "end" else 4), ty, name, anc))
    body += [tag(m20[0] + 8, m20[1] + 17, "− 20", "start"), tag(m27[0] - 8, m27[1] + 17, "− 27", "end"),
             tag(j20[0] + 8, j20[1] - 12, "j20", "start")]
    body += [tag(rp[0] + 12, rp[1] - 12, "+ col 2", "start"), tag(rm[0] + 12, rm[1] + 17, "− col 1", "start"),
             tag(bb.x + bb.w + 8, p29[1] - 2, "+ col 29", "start"), tag(bb.x + bb.w + 8, m30[1] + 16, "− col 30", "start"),
             tag(h24[0] + 10, h24[1] - 14, "h24", "start")]
    body.append(f'<text x="{bb.x + 4}" y="{bb.y - 8}" class="note" text-anchor="start">Bottom red (+) rail = 5V   ·   bottom blue (−) rail = GND</text>')
    return frame(1180, 840, "".join(body), "3) Full system  —  LCD + Buzzer + MC-38 window sensor")


# ---------------------------------------------------------------- breadboard explainer
def diagram_bb_explain():
    """How a breadboard is connected inside (columns of 5, rails along the length).

    @returns svg string
    """
    bb = Breadboard(30, 46, cols=20)
    body = [bb.svg()]
    for r_top, r_bot, c, col in (("a", "e", 5, "#2b8a3e"), ("f", "j", 12, "#7b2cbf")):
        x0, y0 = bb.hole(f"{r_top}{c}")
        _, y1 = bb.hole(f"{r_bot}{c}")
        body.append(f'<rect x="{x0 - 7}" y="{y0 - 7}" width="14" height="{y1 - y0 + 14}" rx="6" fill="{col}33" stroke="{col}" stroke-width="2.5"/>')
    for key, col in (("bot+", COL["red"]), ("bot-", COL["blue"])):
        x0, y0 = bb.hole(f"{key}:1")
        x1, _ = bb.hole(f"{key}:20")
        body.append(f'<rect x="{x0 - 7}" y="{y0 - 7}" width="{x1 - x0 + 14}" height="14" rx="6" fill="{col}22" stroke="{col}" stroke-width="2.5"/>')
    tx = bb.x + bb.w + 24
    body.append(f'<text x="{tx}" y="160" class="note" text-anchor="start" fill="#2b8a3e">Green: a5 … e5 are ONE connection (a column of 5)</text>')
    body.append(f'<text x="{tx}" y="240" class="note" text-anchor="start" fill="#7b2cbf">Purple: f12 … j12 are ONE connection</text>')
    body.append(f'<text x="{tx}" y="262" class="note" text-anchor="start">Top half (a–e) is NOT connected to bottom half (f–j)</text>')
    body.append(f'<text x="{tx}" y="340" class="note" text-anchor="start" fill="#d62828">Whole + rail is ONE connection along its length</text>')
    body.append(f'<text x="{tx}" y="358" class="note" text-anchor="start" fill="#1971c2">Whole − rail is ONE connection along its length</text>')
    return frame(980, 390, "".join(body), "How the breadboard is connected inside")
