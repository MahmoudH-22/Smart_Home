"""Flowchart of the security control loop (SVG)."""


def box(x, y, w, h, text, kind="proc"):
    """Draw a flowchart node.

    @param x,y centre  @param w,h size  @param text lines separated by '\\n'
    @param kind 'term' (rounded), 'proc' (rectangle), 'dec' (diamond), 'io' (parallelogram)
    @returns svg fragment
    """
    fill = {"term": "#e7f5ff", "proc": "#ffffff", "dec": "#fff4e6", "io": "#ebfbee"}[kind]
    stroke = {"term": "#1971c2", "proc": "#343a40", "dec": "#e8590c", "io": "#2b8a3e"}[kind]
    if kind == "term":
        shape = f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="{h / 2}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    elif kind == "dec":
        shape = (f'<polygon points="{x},{y - h / 2} {x + w / 2},{y} {x},{y + h / 2} {x - w / 2},{y}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    elif kind == "io":
        k = 14
        shape = (f'<polygon points="{x - w / 2 + k},{y - h / 2} {x + w / 2},{y - h / 2} {x + w / 2 - k},{y + h / 2} {x - w / 2},{y + h / 2}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    else:
        shape = f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    lines = text.split("\n")
    t = "".join(f'<text x="{x}" y="{y + (i - (len(lines) - 1) / 2) * 15 + 5}" class="ft">{ln}</text>'
                for i, ln in enumerate(lines))
    return shape + t


def arrow(pts, label=None, lx=0, ly=0):
    """Polyline arrow with an optional label near its start.

    @param pts list of points  @param label text  @param lx,ly label offset
    @returns svg fragment
    """
    d = "M" + " L".join(f"{a},{b}" for a, b in pts)
    s = f'<path d="{d}" fill="none" stroke="#495057" stroke-width="1.8" marker-end="url(#ah)"/>'
    if label:
        s += f'<text x="{pts[0][0] + lx}" y="{pts[0][1] + ly}" class="fl">{label}</text>'
    return s


def flowchart():
    """Security subsystem control flow.

    @returns svg string
    """
    W, H = 640, 860
    cx = 250
    b = []
    b.append(box(cx, 30, 120, 36, "START", "term"))
    b.append(box(cx, 100, 300, 58, "setup(): D2 & D7 = INPUT_PULLUP\nD8 = OUTPUT, Serial 9600\nLCD init + welcome (1.5 s)"))
    b.append(box(cx, 190, 150, 36, "loop()", "term"))
    b.append(box(cx, 260, 300, 46, "Read window sensor D2\n(debounced 30 ms)", "io"))
    b.append(box(cx, 340, 300, 46, "armed = ALWAYS_ARMED\nOR toggle D7 = LOW", "io"))
    b.append(box(cx, 440, 230, 100, "armed AND\nwindow open?", "dec"))
    # yes branch (right)
    yx = 500
    b.append(box(yx, 440, 200, 46, "Buzzer ON\ntone(D8, 2500 Hz)"))
    b.append(box(yx, 545, 170, 84, "Alarm just\nstarted?", "dec"))
    b.append(box(yx, 650, 210, 46, "Serial:\nALERT:WINDOW_OPEN", "io"))
    b.append(box(yx, 740, 210, 46, "LCD:\n!! INTRUSION !!"))
    # no branch (down)
    b.append(box(cx, 570, 220, 46, "Buzzer OFF\nnoTone(D8)"))
    b.append(box(cx, 660, 250, 46, "LCD: Security:ARMED/OFF\nWindow: OPEN/CLOSED"))
    # arrows
    b.append(arrow([(cx, 48), (cx, 71)]))
    b.append(arrow([(cx, 129), (cx, 172)]))
    b.append(arrow([(cx, 208), (cx, 237)]))
    b.append(arrow([(cx, 283), (cx, 317)]))
    b.append(arrow([(cx, 363), (cx, 390)]))
    b.append(arrow([(cx + 115, 440), (yx - 100, 440)], "YES", 8, -8))
    b.append(arrow([(cx, 490), (cx, 547)], "NO", 8, 22))
    b.append(arrow([(yx, 463), (yx, 503)]))
    b.append(arrow([(yx, 587), (yx, 627)], "YES", 8, 22))
    b.append(arrow([(yx + 85, 545), (608, 545), (608, 740), (yx + 105, 740)], "NO", 4, -8))
    b.append(arrow([(yx, 673), (yx, 717)]))
    b.append(arrow([(cx, 593), (cx, 637)]))
    # back to loop
    b.append(arrow([(cx, 683), (cx, 800), (40, 800), (40, 190), (cx - 75, 190)]))
    b.append(arrow([(yx, 763), (yx, 800), (cx, 800)]))
    b.append('<text x="48" y="500" class="fl" transform="rotate(-90 48 500)">repeat forever (thousands of times per second)</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="flow">'
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" fill="#495057"/></marker></defs>'
            '<style>.ft{font:600 12.5px "DejaVu Sans",sans-serif;fill:#212529;text-anchor:middle}'
            '.fl{font:700 12px "DejaVu Sans",sans-serif;fill:#e8590c}</style>'
            f'<rect width="{W}" height="{H}" fill="#fff"/>{"".join(b)}</svg>')
