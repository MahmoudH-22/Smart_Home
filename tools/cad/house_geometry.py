"""
MCT331s Smart Home - laser-cut house geometry (3 mm MDF).

Single source of truth for:
  * DXF cut files (per part + nested sheets) for both roof variants
  * JSON scene data consumed by the Three.js simulation page
  * SVG panel drawings + feature tables

World frame (mm): x = left->right seen from the front, y = front->back,
z = up. z = 0 is the top face of the base plate. House footprint 300 x 220.

Variant A: gable roof (two slope panels + 2 trusses) hinged on the back eave.
Variant B: flat removable lid with a locating ring and a knob.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

import ezdxf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity

# ---------------------------------------------------------------- parameters
T = 3.0            # MDF thickness (measure your sheet! slots follow this)
CLR = 0.05         # per-side slot clearance (slot = T + 2*CLR)
W_HOUSE = 300.0    # outer width  (x)
D_HOUSE = 220.0    # outer depth  (y)
H_WALL = 150.0     # wall height  (z) - 150 lets variant B nest on 2 sheets
N_FINGERS = 7      # vertical corner finger segments (odd)
RIDGE_RISE = 80.0  # gable rise above the eaves (variant A)
SLOPE = RIDGE_RISE / (D_HOUSE / 2)
ROOF_OH = 11.0     # horizontal roof overhang at the eaves
BASE_MARGIN = 10.0
PART_Y = 139.0     # partition front face (electronics bay behind it)
PART_H = 135.0
SERVO_AXIS = (38.0, 12.0)   # door hinge / servo shaft (x, y)
SASH_AXIS_Y = 41.0          # window hinge line on right wall
FAN_C = (100.0, 85.0)       # fan centre on left wall (y, z)
UNO_ORIGIN = (230.0, 213.8)  # world x of board edge, world y of USB edge


# ---------------------------------------------------------------- helpers
def vsub(a, b):
    """Return a - b for 3-vectors.

    @param a first vector  @param b second vector
    @returns tuple difference
    """
    return tuple(x - y for x, y in zip(a, b))


def vdot(a, b):
    """Dot product of two 3-vectors.

    @param a vector  @param b vector
    @returns float
    """
    return sum(x * y for x, y in zip(a, b))


def vcross(a, b):
    """Cross product a x b.

    @param a vector  @param b vector
    @returns tuple
    """
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def rect(u0, u1, v0, v1):
    """Axis-aligned rectangle polygon in a part's local (u, v) plane.

    @param u0,u1 u range  @param v0,v1 v range
    @returns shapely Polygon
    """
    return box(min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1))


def crect(cu, cv, w, h):
    """Rectangle given by centre and size.

    @param cu,cv centre  @param w,h size
    @returns shapely Polygon
    """
    return rect(cu - w / 2, cu + w / 2, cv - h / 2, cv + h / 2)


@dataclass
class Placement:
    """Maps local (u, v, w) to world: P = O + u*U + v*V + w*(U x V), w in [0, T]."""
    O: tuple
    U: tuple
    V: tuple
    name: str = ""

    @property
    def W(self):
        """Extrusion direction (unit normal) of the sheet."""
        return vcross(self.U, self.V)

    def world(self, u, v, w=0.0):
        """Local -> world point.

        @param u,v,w local coordinates
        @returns world tuple
        """
        W = self.W
        return tuple(self.O[i] + u * self.U[i] + v * self.V[i] + w * W[i] for i in range(3))

    def local(self, p):
        """World -> local (u, v) for a point lying in/near this sheet.

        @param p world point
        @returns (u, v)
        """
        d = vsub(p, self.O)
        return vdot(d, self.U), vdot(d, self.V)


@dataclass
class Part:
    """One laser-cut part type (may have several identical instances)."""
    pid: str
    name: str
    poly: Polygon
    places: list
    circles: list = field(default_factory=list)      # (u, v, r, label)
    engrave_lines: list = field(default_factory=list)  # [(u0,v0,u1,v1)]
    engrave_rects: list = field(default_factory=list)  # Polygon outlines
    texts: list = field(default_factory=list)        # (u, v, h, text[, align 'C'|'L'|'R'[, bold]])
    tabs: list = field(default_factory=list)         # (Polygon, target pid)
    features: list = field(default_factory=list)     # (label, Polygon|circle) for tables
    mirror_dxf: bool = False                         # draw as seen from outside
    group: str = "struct"                            # animation group
    role: str = ""

    def add_hole(self, label, shape):
        """Subtract a polygonal opening and record it as a feature.

        @param label feature label  @param shape shapely Polygon
        """
        self.poly = self.poly.difference(shape)
        self.features.append((label, shape))

    def add_circle(self, label, u, v, d):
        """Add a round hole (kept as a true circle in DXF).

        @param label feature label  @param u,v centre  @param d diameter
        """
        self.circles.append((u, v, d / 2, label))
        self.features.append((label, ("circle", u, v, d)))


# ---------------------------------------------------------------- finger joints
def finger_cuts(u0, u1, keep_even: bool, height=H_WALL, n=N_FINGERS):
    """Material to remove from a vertical edge zone [u0,u1] so fingers interlock.

    @param u0,u1 edge zone (thickness wide)  @param keep_even True for front/back walls
    @param height wall height  @param n segment count
    @returns shapely geometry to subtract
    """
    h = height / n
    cuts = []
    for k in range(n):
        keep = (k % 2 == 0) == keep_even
        if not keep:
            lo = k * h - (1 if k == 0 else 0)
            hi = (k + 1) * h + (1 if k == n - 1 else 0)
            at_start = u0 <= 0.0
            cuts.append(rect(u0 - 1 if at_start else u0, u1 if at_start else u1 + 1, lo, hi))
    return unary_union(cuts)


def bottom_tabs(spans):
    """Tabs below v=0 that drop into base-plate slots.

    @param spans list of (u0, u1)
    @returns list of Polygons
    """
    return [rect(a, b, -T, 0.0) for a, b in spans]


# ---------------------------------------------------------------- part builders
TEAM = [("Mahmoud Hisham", "2400844"), ("Ziad Hany", "2301401"),
        ("Ahmed Hany", "2400311"), ("Moatasem Mohamed", "2400732")]


def add_team_plate(base):
    """Engrave the team name plate on the base underside.

    Layout is given in as-cut DXF coords (base seen from below, origin bottom-left)
    and converted to base-local coords (u = 310 - x, v = y - 10) so the mirrored
    export reads correctly.

    @param base the BASE Part (mirror_dxf=True)
    @returns None
    """
    m = BASE_MARGIN
    maxx, miny = W_HOUSE + m, -m

    def L(x, y):
        """As-cut DXF coords -> base local (u, v)."""
        return maxx - x, y + miny

    cx = (W_HOUSE + 2 * m) / 2
    base.texts.append((*L(cx, 126), 8.0, "MCT331s  SMART HOME", "C", True))
    base.texts.append((*L(cx, 114), 3.6, "Mechatronic System Integration  -  Ain Shams  -  Fall 2026", "C"))
    base.engrave_lines.append((*L(88, 108), *L(232, 108)))
    for i, (name, sid) in enumerate(TEAM):
        y = 96 - i * 12
        base.texts.append((*L(90, y), 5.0, name, "L"))
        base.texts.append((*L(230, y), 5.0, sid, "R"))
    x0, y0 = L(78, 52)
    x1, y1 = L(242, 140)
    base.engrave_rects.append(rect(x0, x1, y0, y1))


def build_parts(variant: str):
    """Build every part for one variant.

    @param variant "A" (gable roof) or "B" (flat lid)
    @returns list[Part]
    """
    parts: list[Part] = []
    h_seg = H_WALL / N_FINGERS

    # ---- front wall (seen from outside: u = x, v = z) ----
    p = rect(0, W_HOUSE, 0, H_WALL)
    p = p.difference(finger_cuts(0, T, True)).difference(finger_cuts(W_HOUSE - T, W_HOUSE, True))
    tabs = bottom_tabs([(12, 30), (140, 160), (252, 272)])
    p = unary_union([p] + tabs)
    front = Part("FRONT", "Front wall", p,
                 [Placement((0, T, 0), (1, 0, 0), (0, 0, 1))], role="wall")
    front.tabs = [(t, "BASE") for t in tabs]
    front.add_hole("Main door opening 60x100", rect(40, 100, -T - 1, 100))
    front.add_circle("Exterior light LED 5 mm", 22, 112, 5.2)
    front.add_circle("PIR HC-SR501 dome", 125, 125, 23.5)
    front.add_hole("LCD 16x2 window 72x25", crect(205, 122, 72, 25))
    for dx in (-37.5, 37.5):
        for dz in (-15.5, 15.5):
            front.add_circle("LCD M3 mount", 205 + dx, 122 + dz, 3.2)
    front.add_hole("Keypad ribbon slot 22x3", crect(205, 10, 22, 3))
    front.add_circle("Security ARM toggle", 275, 130, 6.2)
    front.add_hole("Light override button 12.4 sq", crect(275, 102, 12.4, 12.4))
    front.add_hole("Alarm mute button 12.4 sq", crect(275, 80, 12.4, 12.4))
    front.add_circle("Fan set-point pot (7 mm bush)", 275, 55, 7.2)
    front.engrave_rects.append(crect(205, 54, 69, 76))  # keypad sticker outline
    for (u, v, s) in [(275, 137.5, "ARM"), (275, 111.5, "LIGHT"), (275, 89.5, "MUTE"), (275, 63.5, "TEMP")]:
        front.texts.append((u, v, 3.2, s))
    parts.append(front)

    # ---- back wall (u = x, v = z; DXF mirrored to show outside) ----
    p = rect(0, W_HOUSE, 0, H_WALL)
    p = p.difference(finger_cuts(0, T, True)).difference(finger_cuts(W_HOUSE - T, W_HOUSE, True))
    tabs = bottom_tabs([(30, 50), (140, 160), (252, 272)])
    p = unary_union([p] + tabs)
    back = Part("BACK", "Back wall", p, [Placement((0, D_HOUSE, 0), (1, 0, 0), (0, 0, 1))],
                mirror_dxf=True, role="wall")
    back.tabs = [(t, "BASE") for t in tabs]
    ux, uy = UNO_ORIGIN
    back.add_hole("Arduino USB-B access", crect(ux + 38.1, 13.1, 13.5, 12.5))
    back.add_hole("Arduino DC jack access", crect(ux + 7.9, 13.1, 10.5, 12.5))
    back.add_circle("5V 2A panel jack (aux power)", 200, 15, 12.0)
    for z in (100, 110, 120):
        back.add_hole("Vent slot 50x4", crect(90, z, 50, 4))
    if variant == "A":
        for cx in (70, 230):
            back.engrave_rects.append(crect(cx, 152, 25, 14))
    parts.append(back)

    # ---- side walls (u = y, v = z) ----
    for pid, x0, name in (("LEFT", 0.0, "Left wall (fan)"), ("RIGHT", W_HOUSE - T, "Right wall (window)")):
        p = rect(0, D_HOUSE, 0, H_WALL)
        p = p.difference(finger_cuts(0, T, False)).difference(finger_cuts(D_HOUSE - T, D_HOUSE, False))
        if variant == "A":
            gable = Polygon([(T, H_WALL), (T, H_WALL + T * SLOPE), (D_HOUSE / 2, H_WALL + RIDGE_RISE),
                             (D_HOUSE - T, H_WALL + T * SLOPE), (D_HOUSE - T, H_WALL)])
            p = unary_union([p, gable])
        tabs = bottom_tabs([(25, 45), (100, 120), (175, 195)])
        p = unary_union([p] + tabs)
        part = Part(pid, name + (" + gable" if variant == "A" else ""), p,
                    [Placement((x0, 0, 0), (0, 1, 0), (0, 0, 1))],
                    mirror_dxf=(pid == "LEFT"), role="wall")
        part.tabs = [(t, "BASE") for t in tabs]
        if pid == "LEFT":
            part.add_circle("Exhaust fan opening", FAN_C[0], FAN_C[1], 62.0)
        else:
            part.add_hole("Window opening 70x55", rect(45, 115, 70, 125))
            part.add_circle("LDR 10 mm (ambient light)", 25, 133, 10.2)
            part.add_circle("MC-38 reed wire hole", 128, 80, 5.0)
        parts.append(part)

    # ---- partition / electronics bay wall (u = x, v = z) ----
    p = rect(T, W_HOUSE - T, 0, PART_H)
    side_tabs = [rect(0, T, 40, 60), rect(0, T, 90, 110),
                 rect(W_HOUSE - T, W_HOUSE, 40, 60), rect(W_HOUSE - T, W_HOUSE, 90, 110)]
    btabs = bottom_tabs([(100, 120), (180, 200)])
    p = unary_union([p] + side_tabs + btabs)
    part = Part("PARTITION", "Partition (bay wall)", p,
                [Placement((0, PART_Y + T, 0), (1, 0, 0), (0, 0, 1))], role="inner")
    part.tabs = [(t, "LEFT") for t in side_tabs[:2]] + [(t, "RIGHT") for t in side_tabs[2:]] + \
                [(t, "BASE") for t in btabs]
    part.add_hole("Cable notch 30x12", rect(45, 75, -1, 12))
    part.add_hole("Cable notch 30x12", rect(215, 245, -1, 12))
    part.add_hole("DHT11 sensor window", crect(50, 60, 16.2, 12.6))
    for x in (75, 150, 225):
        part.add_circle("Indoor light LED 5 mm", x, 124, 5.2)
    parts.append(part)

    # ---- fan plate (u = y, v = z) at x 33..36 ----
    p = rect(66, 134, 0, 120)
    btabs = bottom_tabs([(74, 89), (111, 126)])
    p = unary_union([p] + btabs)
    part = Part("FANPLATE", "Fan motor plate", p, [Placement((33, 0, 0), (0, 1, 0), (0, 0, 1))], role="inner")
    part.tabs = [(t, "BASE") for t in btabs]
    dhole = Polygon([(FAN_C[0] + 10.2 * math.cos(a), FAN_C[1] + 10.2 * math.sin(a))
                     for a in [i * 2 * math.pi / 72 for i in range(72)]]).intersection(
        rect(FAN_C[0] - 11, FAN_C[0] + 11, FAN_C[1] - 7.75, FAN_C[1] + 7.75))
    part.add_hole("F130 motor D-hole (20.4/15.5)", dhole)
    for du in (-24, 24):
        for dv in (-24, 24):
            part.add_circle("Air vent", FAN_C[0] + du, FAN_C[1] + dv, 10)
    parts.append(part)

    # ---- fan ribs x2 (u = x, v = z) ----
    p = rect(T, 33, 0, 120)
    wtabs = [rect(0, T, 8, 28), rect(0, T, 104, 118)]
    btabs = bottom_tabs([(10, 25)])
    p = unary_union([p] + wtabs + btabs)
    part = Part("FANRIB", "Fan duct rib", p,
                [Placement((0, 69, 0), (1, 0, 0), (0, 0, 1)), Placement((0, 134, 0), (1, 0, 0), (0, 0, 1))],
                role="inner")
    part.tabs = [(t, "LEFT") for t in wtabs] + [(t, "BASE") for t in btabs]
    parts.append(part)

    # ---- servo shelf (u = x, v = y) at z 120..123 ----
    p = rect(25, 65, T, 30)
    ftabs = [rect(26, 31, 0, T), rect(57, 63, 0, T)]
    p = unary_union([p] + ftabs)
    part = Part("SHELF", "Servo shelf", p, [Placement((0, 0, 120), (1, 0, 0), (0, 1, 0))], role="inner")
    part.tabs = [(t, "FRONT") for t in ftabs]
    part.add_hole("SG90 body cut-out 23x13", rect(32.0, 55.0, 5.5, 18.5))
    part.add_circle("SG90 screw", 29.7, 12, 2.0)
    part.add_circle("SG90 screw", 57.3, 12, 2.0)
    parts.append(part)

    # ---- door (u = x, v = z) at y 3.5..6.5, hinged on the servo axis ----
    door = Part("DOOR", "Main door", rect(37, 103, 0.5, 104),
                [Placement((0, 6.5, 0), (1, 0, 0), (0, 0, 1))], group="door", role="moving")
    door.add_circle("Handle hole", 95, 52, 4.0)
    door.engrave_rects += [rect(45, 95, 60, 96), rect(45, 95, 10, 48)]
    parts.append(door)

    # ---- window sash (u = y, v = z) outside the right wall ----
    p = rect(SASH_AXIS_Y, 119, 66, 129)
    sash = Part("SASH", "Window sash (frame)", p, [Placement((W_HOUSE, 0, 0), (0, 1, 0), (0, 0, 1))],
                group="sash", role="moving")
    sash.add_hole("Glazing opening (2 mm acrylic behind)", rect(47, 103, 72, 123))
    parts.append(sash)

    # ---- base plate (u = x, v = y) ----
    m = BASE_MARGIN
    p = box(-m + 6, -m + 6, W_HOUSE + m - 6, D_HOUSE + m - 6).buffer(6, resolution=8)
    # cut upside-down (mirror_dxf): the engraved face is the UNDERSIDE -> team name plate
    base = Part("BASE", "Base plate", p, [Placement((0, 0, -T), (1, 0, 0), (0, 1, 0))], role="base",
                mirror_dxf=True)
    base.add_circle("Door bottom pivot pin", SERVO_AXIS[0], SERVO_AXIS[1], 2.5)
    for xa, ya in ((13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)):
        base.add_circle("Arduino M3 standoff", ux + ya, uy - xa, 3.2)
    add_team_plate(base)
    parts.append(base)

    # ---- roof ----
    if variant == "A":
        L0 = math.hypot(D_HOUSE / 2, RIDGE_RISE)
        dy, dz = (D_HOUSE / 2) / L0, RIDGE_RISE / L0
        oh = ROOF_OH * L0 / (D_HOUSE / 2)
        p = rect(-10, W_HOUSE + 10, -oh, L0)
        roof = Part("ROOF", "Roof slope panel", p,
                    [Placement((0, 0, H_WALL), (1, 0, 0), (0, dy, dz), "front"),
                     Placement((W_HOUSE, D_HOUSE, H_WALL), (-1, 0, 0), (0, -dy, dz), "back")],
                    group="roof", role="roof")
        v = 0.0
        while v + 14 < L0:
            v += 14
            roof.engrave_lines.append((-10, v, W_HOUSE + 10, v))
        parts.append(roof)
        tri = Polygon([(3.5, H_WALL + 3.5 * SLOPE), (D_HOUSE / 2, H_WALL + RIDGE_RISE),
                       (D_HOUSE - 3.5, H_WALL + 3.5 * SLOPE)])
        inner = tri.buffer(-9, join_style=2)
        truss = Part("TRUSS", "Roof truss", tri.difference(inner),
                     [Placement((98.5, 0, 0), (0, 1, 0), (0, 0, 1)), Placement((198.5, 0, 0), (0, 1, 0), (0, 0, 1))],
                     group="roof", role="roof")
        parts.append(truss)
    else:
        lid = Part("LID", "Flat roof lid", rect(-T, W_HOUSE + T, -T, D_HOUSE + T),
                   [Placement((0, 0, H_WALL), (1, 0, 0), (0, 1, 0))], group="roof", role="roof")
        parts.append(lid)
        # 4 L-shaped corner locators glued under the lid: register it inside the walls with
        # ~0.4 m of cutting instead of ~2 m for full-length strips (cheapest option)
        L = unary_union([rect(0, 25, 0, 8), rect(0, 8, 0, 25)])
        locs = []
        for (cx, cy, U, V) in ((3.5, 3.5, (1, 0, 0), (0, 1, 0)), (W_HOUSE - 3.5, 3.5, (-1, 0, 0), (0, 1, 0)),
                               (W_HOUSE - 3.5, D_HOUSE - 3.5, (-1, 0, 0), (0, -1, 0)), (3.5, D_HOUSE - 3.5, (1, 0, 0), (0, -1, 0))):
            wz = vcross(U, V)[2]
            locs.append(Placement((cx, cy, H_WALL - T if wz > 0 else H_WALL), U, V))
        parts.append(Part("LOCATOR", "Lid corner locator", L, locs, group="roof", role="roof"))
        disc = Polygon([(150 + 15 * math.cos(a), 110 + 15 * math.sin(a))
                        for a in [i * 2 * math.pi / 64 for i in range(64)]])
        parts.append(Part("KNOB", "Lid knob disc", disc,
                          [Placement((0, 0, H_WALL + T), (1, 0, 0), (0, 1, 0)),
                           Placement((0, 0, H_WALL + 2 * T), (1, 0, 0), (0, 1, 0))], group="roof", role="roof"))

    # ---- cut slots for every tab into its target ----
    by_id = {pp.pid: pp for pp in parts}
    for pp in parts:
        for tab, target in pp.tabs:
            tgt = by_id[target]
            tp = tgt.places[0]
            for pl in pp.places:
                minx, miny, maxx, maxy = tab.bounds
                pts = [pl.world(u, v, w) for u in (minx, maxx) for v in (miny, maxy) for w in (0, T)]
                loc = [tp.local(q) for q in pts]
                us, vs = [a for a, _ in loc], [b for _, b in loc]
                slot = rect(min(us) - CLR, max(us) + CLR, min(vs) - CLR, max(vs) + CLR)
                tgt.poly = tgt.poly.difference(slot)
                if not any(f[0] == "Slot" and f[1].equals(slot) for f in tgt.features):
                    tgt.features.append(("Slot (tab of %s)" % pp.name, slot))
    for pp in parts:
        assert pp.poly.geom_type == "Polygon", (pp.pid, pp.poly.geom_type)
    return parts


# ---------------------------------------------------------------- components
def components():
    """3D primitives for every electronic / mechanical component.

    Each entry: id, name, cat (sensor/actuator/processing/interface/power/mech),
    mount (part it travels with in exploded view), owned (in purchased list),
    dims, func, where, prims (box/cyl/sph in world mm), optional anim keys.

    @returns list of dicts
    """
    ux, uy = UNO_ORIGIN
    sx, sy = SERVO_AXIS
    fy, fz = FAN_C
    C = []

    def add(**kw):
        """Append a component dict."""
        C.append(kw)

    add(id="uno", name="Arduino UNO R3 (clone)", cat="processing", mount="BASE", owned=True,
        dims="68.6 x 53.3 mm, on 4x M3 standoffs (6 mm)", func="Main controller: reads all sensors, runs the control logic, drives the actuators.",
        where="Electronics bay, USB + DC jack exposed through the back wall",
        prims=[dict(t="box", c=[ux + 26.67, uy - 34.29, 6.8], s=[53.34, 68.58, 1.6], col="#0f7f8a"),
               dict(t="box", c=[ux + 38.1, uy - 3.2, 13.1], s=[12, 16, 11], col="#c9ccd1"),
               dict(t="box", c=[ux + 7.9, uy - 5.5, 13.1], s=[9, 13, 11], col="#202226"),
               dict(t="box", c=[ux + 51.3, uy - 40, 11.6], s=[2.5, 48, 8.5], col="#18191b"),
               dict(t="box", c=[ux + 2.0, uy - 46, 11.6], s=[2.5, 38, 8.5], col="#18191b"),
               dict(t="box", c=[ux + 26, uy - 50, 9.3], s=[8, 35, 3.5], col="#222"),
               *[dict(t="cyl", c=[ux + ya, uy - xa, 3.0], r=2.6, h=6, axis="z", col="#c8a24a")
                 for xa, ya in ((13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56))]])
    add(id="bb", name="Breadboard 830 tie-point", cat="processing", mount="BASE", owned=True,
        dims="165.1 x 54.6 x 8.5 mm", func="Power rails + transistor/diode driver for the fan, LDR divider, button pull-ups.",
        where="Electronics bay floor, left of the Arduino",
        prims=[dict(t="box", c=[97.55, 179.3, 4.25], s=[165.1, 54.6, 8.5], col="#f2f2ee"),
               dict(t="box", c=[97.55, 179.3, 8.6], s=[160, 3, 0.4], col="#b9bbb5")])
    add(id="buzz", name="Buzzer 5V", cat="actuator", mount="BASE", owned=True,
        dims="Ø12 x 9.5 mm", func="Intrusion alarm sound.", where="On the breadboard",
        prims=[dict(t="cyl", c=[150, 165, 13.25], r=6, h=9.5, axis="z", col="#1a1a1a")], anim="buzzer")
    add(id="drv", name="Fan driver (TIP120/2N2222 + 1N4007 + 1k)", cat="power", mount="BASE", owned=False,
        dims="TO-220 / TO-92", func="Switches the F130 motor current; the diode absorbs motor back-EMF.",
        where="On the breadboard", prims=[dict(t="box", c=[120, 190, 15], s=[10, 4.5, 15], col="#222"),
                                          dict(t="box", c=[120, 191.8, 21], s=[10, 1.2, 8], col="#aab")])
    add(id="esp", name="ESP8266 (ESP-01 / NodeMCU) - alert link", cat="processing", mount="BASE", owned=False,
        dims="48 x 26 mm (NodeMCU)", func="Sends the window-intrusion alert to the designated recipient (Telegram / Firebase) over Wi-Fi. Talks to the UNO over serial.",
        where="Electronics bay, between breadboard and UNO",
        prims=[dict(t="box", c=[203, 175, 5], s=[26, 48, 1.6], col="#1d1d1d"),
               dict(t="box", c=[203, 190, 7], s=[15, 12, 2.5], col="#b8bcc4")])
    add(id="psu", name="5V 2A adapter + panel DC jack", cat="power", mount="BACK", owned=False,
        dims="Ø12 mm panel hole", func="Separate 5 V rail for the servo and fan so they don't brown-out the UNO (common GND).",
        where="Back wall, x = 200",
        prims=[dict(t="cyl", c=[200, 211, 15], r=6.5, h=12, axis="y", col="#2a2a2a"),
               dict(t="cyl", c=[200, 221, 15], r=8, h=2, axis="y", col="#9aa0a8")])
    # front wall
    add(id="lcd", name="LCD 16x2 + I2C backpack", cat="interface", mount="FRONT", owned=True,
        dims="PCB 80 x 36, window 71 x 24, depth ~22 mm", func="Real-time status: door, security mode, temperature, set-point, light, fan, alarm.",
        where="Front wall, right of the door, top",
        prims=[dict(t="box", c=[205, 10.8, 122], s=[80, 1.6, 36], col="#1f6b3a"),
               dict(t="box", c=[205, 5.5, 122], s=[71, 9, 24], col="#2b2f36"),
               dict(t="lcd", c=[205, 1.4, 122], s=[64.5, 0.2, 16]),
               dict(t="box", c=[205, 17, 120], s=[41.5, 11, 19], col="#163f78")])
    add(id="kp", name="Keypad 4x4 membrane", cat="interface", mount="FRONT", owned=True,
        dims="69 x 76 x 0.8 mm + ribbon", func="Enter the access code to open the main door.",
        where="Front wall under the LCD (self-adhesive), ribbon through a 22x3 slot",
        prims=[dict(t="keypad", c=[205, -0.45, 54], s=[69, 0.9, 76]),
               dict(t="box", c=[205, 1.5, 10], s=[20, 3.5, 3], col="#d9d9d9"),
               dict(t="box", c=[205, 10, 5], s=[20, 0.4, 10], col="#d9d9d9")])
    add(id="pir", name="PIR motion sensor HC-SR501", cat="sensor", mount="FRONT", owned=False,
        dims="32 x 24 mm, dome Ø23", func="Detects motion near the main door; turns the exterior light on while security is armed.",
        where="Front wall, right of the door, dome through a Ø23.5 hole",
        prims=[dict(t="box", c=[125, 4.0, 125], s=[32, 1.6, 24], col="#2e7d32"),
               dict(t="sph", c=[125, 3.2, 125], r=11.5, half="-y", col="#f4f4f0"),
               dict(t="box", c=[125, 9, 125], s=[20, 8, 10], col="#e7a31c")])
    add(id="extled", name="Exterior light (white LED 5 mm)", cat="actuator", mount="FRONT", owned=True,
        dims="Ø5 mm + 220 Ω", func="Porch light: ON when armed and PIR sees motion.",
        where="Front wall, left of the door",
        prims=[dict(t="led", c=[22, -2.5, 112], r=2.5, h=6, axis="y", light="ext")], anim="extled")
    add(id="servo", name="Servo SG90 (door actuator)", cat="actuator", mount="FRONT", owned=True,
        dims="22.8 x 12.6 x 22.5 mm (tabs 32.3)", func="Opens the door 90° on a correct code, closes after the preset delay.",
        where="Inverted in the servo shelf above the door; shaft on the door hinge axis",
        prims=[dict(t="box", c=[43.5, sy, 127.25], s=[22.8, 12.6, 22.5], col="#2457c5"),
               dict(t="box", c=[43.5, sy, 124.25], s=[32.3, 12.6, 2.5], col="#2457c5"),
               dict(t="cyl", c=[sx, sy, 113.5], r=5.5, h=5, axis="z", col="#2457c5"),
               dict(t="cyl", c=[sx, sy, 108.5], r=2.4, h=5, axis="z", col="#f0f0f0")])
    add(id="tog", name="Toggle switch (security ARM)", cat="interface", mount="FRONT", owned=True,
        dims="Ø6 bush, 2 position", func="Arms / disarms the security mode.", where="Front wall control column, top",
        prims=[dict(t="cyl", c=[275, -1, 130], r=3, h=2, axis="y", col="#b0b5bb"),
               dict(t="tog", c=[275, -1.6, 130], r=1.3, h=11, col="#d0d4d9"),
               dict(t="box", c=[275, 9, 130], s=[13, 12, 8], col="#30343a")], anim="toggle")
    for bid, z, nm, fn in (("btnL", 102, "Push button - light override", "Manual indoor-light override (toggles)."),
                           ("btnM", 80, "Push button - alarm mute", "Silences the alarm / resets the intrusion latch.")):
        add(id=bid, name=nm, cat="interface", mount="FRONT", owned=True, dims="12 x 12 x 7.3 mm + Omron cap",
            func=fn, where="Front wall control column",
            prims=[dict(t="box", c=[275, -2, z], s=[11.5, 4, 11.5], col="#121212"),
                   dict(t="box", c=[275, 5, z], s=[12, 4, 12], col="#2a2a2a")])
    add(id="pcbctl", name="Control perfboard (buttons)", cat="mech", mount="FRONT", owned=False,
        dims="20 x 48 mm veroboard", func="Holds the two tactile switches behind the front wall.",
        where="Behind control column", prims=[dict(t="box", c=[275, 8, 91], s=[20, 1.6, 48], col="#c49a5a")])
    add(id="pot", name="Potentiometer 10 kΩ (temp set-point knob)", cat="interface", mount="FRONT", owned=False,
        dims="Ø16 body, 6 mm shaft", func="User-defined temperature threshold for the fan.",
        where="Front wall control column, bottom",
        prims=[dict(t="cyl", c=[275, -7, 55], r=7, h=12, axis="y", col="#1b1b1b"),
               dict(t="cyl", c=[275, 8, 55], r=8, h=9, axis="y", col="#5d6066")], anim="pot")
    # right wall
    add(id="ldr", name="LDR 10 mm (ambient light)", cat="sensor", mount="RIGHT", owned=True,
        dims="Ø10 mm + 10 kΩ divider", func="Measures ambient light; indoor light turns on below the threshold.",
        where="Right wall, outside, near the front-top corner",
        prims=[dict(t="cyl", c=[301.2, 25, 133], r=5, h=2.4, axis="x", col="#c8573a")])
    add(id="reed", name="MC-38 reed switch (frame part)", cat="sensor", mount="RIGHT", owned=True,
        dims="27 x 14 x 10 mm", func="Window intrusion sensor (NC). Opens when the magnet leaves -> alarm if armed.",
        where="Right wall outside, beside the window free edge",
        prims=[dict(t="box", c=[305, 128, 97.5], s=[10, 14, 27], col="#f3f3f0")])
    add(id="mag", name="MC-38 magnet (sash part)", cat="sensor", mount="RIGHT", owned=True,
        dims="27 x 14 x 10 mm", func="Moves with the window sash.", where="Window sash free edge",
        prims=[dict(t="box", c=[308, 112, 97.5], s=[10, 14, 27], col="#f3f3f0")], group="sash")
    add(id="glass", name="Window glazing (2 mm clear acrylic)", cat="mech", mount="RIGHT", owned=False,
        dims="62 x 57 mm", func="Optional clear pane glued behind the sash frame.", where="Window sash",
        prims=[dict(t="glass", c=[300.0 + 3.6, 75, 97.5], s=[1.2, 60, 55])], group="sash")
    # left wall fan
    add(id="motor", name="DC motor 5V F130 + 56 mm propeller", cat="actuator", mount="LEFT", owned=True,
        dims="Ø20 x 25 mm body, prop Ø56", func="Exhaust fan: ON when temperature > set-point.",
        where="Left wall fan duct, held by the fan plate",
        prims=[dict(t="cyl", c=[38.5, fy, fz], r=10, h=25, axis="x", col="#c0c4ca"),
               dict(t="cyl", c=[22, fy, fz], r=1, h=8, axis="x", col="#ddd")])
    add(id="prop", name="Propeller 4-blade 56 mm", cat="actuator", mount="LEFT", owned=True,
        dims="Ø56 mm", func="Moves air out through the left wall.", where="Inside the Ø62 opening",
        prims=[dict(t="prop", c=[17, fy, fz], r=28)], anim="prop")
    # partition
    add(id="dht", name="DHT11 temperature/humidity", cat="sensor", mount="PARTITION", owned=True,
        dims="Sensor 15.5 x 12 x 5.5; module 28 x 12", func="Indoor temperature for the climate control loop.",
        where="Partition, living-room side, near the fan",
        prims=[dict(t="box", c=[50, 136.25, 60], s=[15.5, 5.5, 12], col="#2b7bd6"),
               dict(t="box", c=[50, 142.8, 60], s=[28, 1.6, 14], col="#1e5fae")])
    for i, x in enumerate((75, 150, 225)):
        add(id="inled%d" % (i + 1), name="Indoor light LED %d" % (i + 1), cat="actuator", mount="PARTITION",
            owned=True, dims="Ø5 mm + 220 Ω", func="Indoor lighting (LDR auto or manual override).",
            where="Partition top, facing the living room",
            prims=[dict(t="led", c=[x, 136.5, 124], r=2.5, h=6, axis="y", light="in", flip=True)], anim="inled")
    return C


# ---------------------------------------------------------------- exports
def ring_coords(ring):
    """Round a shapely ring to a list of [u, v] (closing point dropped).

    @param ring LinearRing
    @returns list
    """
    pts = list(ring.coords)[:-1]
    return [[round(a, 3), round(b, 3)] for a, b in pts]


def scene_json(parts):
    """Serialize parts for the 3D viewer.

    @param parts list[Part]
    @returns list of dicts
    """
    out = []
    for p in parts:
        poly = p.poly.buffer(0)
        out.append(dict(
            id=p.pid, name=p.name, group=p.group, role=p.role,
            outer=ring_coords(poly.exterior),
            holes=[ring_coords(r) for r in poly.interiors],
            circles=[[round(c[0], 3), round(c[1], 3), round(c[2], 3)] for c in p.circles],
            places=[dict(O=pl.O, U=pl.U, V=pl.V, W=pl.W, tag=pl.name) for pl in p.places],
            size=[round(poly.bounds[2] - poly.bounds[0], 1), round(poly.bounds[3] - poly.bounds[1], 1)],
            qty=len(p.places)))
    return out


def norm_transform(p: Part):
    """Return function mapping local (u,v) -> as-cut DXF coords (origin bottom-left).

    @param p Part
    @returns (fn, width, height)
    """
    minx, miny, maxx, maxy = p.poly.bounds
    if p.mirror_dxf:
        return (lambda u, v: (maxx - u, v - miny)), maxx - minx, maxy - miny
    return (lambda u, v: (u - minx, v - miny)), maxx - minx, maxy - miny


def emit_part(msp, p: Part, ox=0.0, oy=0.0, rot=False, label=True):
    """Draw one part into a DXF modelspace.

    @param msp modelspace  @param p Part  @param ox,oy offset  @param rot rotate 90°
    @param label add a small part label on the NOTE layer
    @returns None
    """
    f, w, h = norm_transform(p)

    def tr(u, v):
        """Local -> sheet coords."""
        x, y = f(u, v)
        if rot:
            x, y = h - y, x
        return (x + ox, y + oy)

    poly = p.poly
    for ring in [poly.exterior] + list(poly.interiors):
        msp.add_lwpolyline([tr(a, b) for a, b in list(ring.coords)[:-1]], close=True, dxfattribs={"layer": "CUT"})
    for (u, v, r, _) in p.circles:
        msp.add_circle(tr(u, v), r, dxfattribs={"layer": "CUT"})
    for (u0, v0, u1, v1) in p.engrave_lines:
        msp.add_line(tr(u0, v0), tr(u1, v1), dxfattribs={"layer": "ENGRAVE"})
    for er in p.engrave_rects:
        msp.add_lwpolyline([tr(a, b) for a, b in list(er.exterior.coords)[:-1]], close=True,
                           dxfattribs={"layer": "ENGRAVE"})
    for tx in p.texts:
        u, v, hh, s = tx[:4]
        align = tx[4] if len(tx) > 4 else "C"
        bold = tx[5] if len(tx) > 5 else False
        ix, iy = tr(u, v)
        for poly in text_outlines(s, hh, align, bold):
            pts = [(ix - y, iy + x) if rot else (ix + x, iy + y) for x, y in poly]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "ENGRAVE"})


def text_outlines(s, h, align="C", bold=False):
    """Convert a string to closed glyph outlines (so any laser software can engrave it).

    @param s text  @param h cap height mm  @param align 'C' centre, 'L' left, 'R' right (vertically centred)
    @param bold use the bold face
    @returns list of point lists relative to the insertion point
    """
    from ezdxf.addons import text2path
    from ezdxf.fonts import fonts
    A = ezdxf.enums.TextEntityAlignment
    al = {"C": A.MIDDLE_CENTER, "L": A.MIDDLE_LEFT, "R": A.MIDDLE_RIGHT}[align]
    face = fonts.FontFace(family="DejaVu Sans", weight=700 if bold else 400)
    out = []
    for path in text2path.make_paths_from_str(s, face, size=h, align=al):
        for sp in path.sub_paths():
            pts = [(q.x, q.y) for q in sp.flattening(0.03)]
            if len(pts) > 2:
                out.append(pts)
    return out


def new_doc():
    """Create a DXF doc in mm with CUT/ENGRAVE/NOTE layers.

    @returns (doc, msp)
    """
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CUT", color=1)
    doc.layers.add("ENGRAVE", color=5)
    doc.layers.add("NOTE", color=8)
    return doc, doc.modelspace()


def _pack_core(items, sheet_w, sheet_h, gap, margin, prefer_rot, score):
    """Greedy bottom-left nesting of bounding boxes for one item order.

    @param items list of (part, w, h)  @param sheet_w,sheet_h sheet size
    @param gap part spacing  @param margin sheet border
    @param prefer_rot try rotated first  @param score 'bl' bottom-first or 'lb' left-first
    @returns list of sheet dicts {rects, items}
    """
    def fits(rects, x, y, w, h):
        """True when the rectangle is on the sheet and clear of placed ones."""
        if x + w > sheet_w - margin + 1e-6 or y + h > sheet_h - margin + 1e-6:
            return False
        for (rx, ry, rw, rh) in rects:
            if x < rx + rw + gap - 1e-6 and rx < x + w + gap - 1e-6 and y < ry + rh + gap - 1e-6 and ry < y + h + gap - 1e-6:
                return False
        return True

    sheets = []
    for p, w, h in items:
        done = False
        for sh in sheets:
            best = None
            cands = {(margin, margin)}
            for (rx, ry, rw, rh) in sh["rects"]:
                cands |= {(rx + rw + gap, ry), (rx, ry + rh + gap), (rx + rw + gap, margin), (margin, ry + rh + gap)}
            orients = ((h, w, True), (w, h, False)) if prefer_rot else ((w, h, False), (h, w, True))
            for (cx, cy) in cands:
                for (ww, hh, rot) in orients:
                    if fits(sh["rects"], cx, cy, ww, hh):
                        key = (cy + hh, cx) if score == "bl" else (cx + ww, cy)
                        if best is None or key < best[0]:
                            best = (key, cx, cy, ww, hh, rot)
            if best:
                _, cx, cy, ww, hh, rot = best
                sh["rects"].append((cx, cy, ww, hh))
                sh["items"].append((p, cx, cy, rot))
                done = True
                break
        if not done:
            rot = w > sheet_w - 2 * margin
            ww, hh = (h, w) if rot else (w, h)
            sheets.append(dict(rects=[(margin, margin, ww, hh)], items=[(p, margin, margin, rot)]))
    return sheets


def pack(parts, sheet_w=600.0, sheet_h=400.0, gap=4.0, margin=5.0, tries=300, seed=7):
    """Nest part instances onto as few sheets as possible (randomised greedy search).

    @param parts list[Part]  @param sheet_w,sheet_h sheet size  @param gap spacing
    @param margin sheet border  @param tries random orderings  @param seed RNG seed
    @returns list of sheets, each a list of (part, x, y, rot)
    """
    import random
    items = []
    for p in parts:
        _, w, h = norm_transform(p)
        items += [(p, w, h)] * len(p.places)
    base = sorted(items, key=lambda it: -(it[1] * it[2]))
    rng = random.Random(seed)
    best = None
    for t in range(tries):
        order = base if t == 0 else sorted(base, key=lambda it: -(it[1] * it[2]) * rng.uniform(0.6, 1.4))
        for pr in (False, True):
            for sc in ("bl", "lb"):
                sheets = _pack_core(order, sheet_w, sheet_h, gap, margin, pr, sc)
                key = (len(sheets), sum(r[2] * r[3] for r in sheets[-1]["rects"]))
                if best is None or key < best[0]:
                    best = (key, sheets)
    return [s["items"] for s in best[1]]


def svg_part(p: Part, scale=1.0):
    """SVG drawing of one part (as cut) with overall dimensions.

    @param p Part  @param scale px per mm
    @returns svg string
    """
    f, w, h = norm_transform(p)
    pad = 26
    W, H = w + 2 * pad, h + 2 * pad

    def P(u, v):
        """Local -> svg coords (y flipped)."""
        x, y = f(u, v)
        return x + pad, h - y + pad

    def path_of(ring):
        """Ring -> SVG path data."""
        pts = [P(a, b) for a, b in list(ring.coords)[:-1]]
        return "M" + " L".join("%.2f,%.2f" % q for q in pts) + " Z"

    d = " ".join(path_of(r) for r in [p.poly.exterior] + list(p.poly.interiors))
    s = ['<svg viewBox="0 0 %.1f %.1f" xmlns="http://www.w3.org/2000/svg" class="panel">' % (W, H)]
    s.append('<path d="%s" class="cut" fill-rule="evenodd"/>' % d)
    for (u, v, r, _) in p.circles:
        x, y = P(u, v)
        s.append('<circle cx="%.2f" cy="%.2f" r="%.2f" class="hole"/>' % (x, y, r))
    for (u0, v0, u1, v1) in p.engrave_lines:
        a, b = P(u0, v0), P(u1, v1)
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="eng"/>' % (a + b))
    for er in p.engrave_rects:
        s.append('<path d="%s" class="eng"/>' % path_of(er.exterior))
    for tx in p.texts:
        u, v, hh, t = tx[:4]
        anchor = {"C": "middle", "L": "start", "R": "end"}[tx[4] if len(tx) > 4 else "C"]
        weight = ' font-weight="700"' if len(tx) > 5 and tx[5] else ""
        x, y = P(u, v)
        s.append('<text x="%.1f" y="%.1f" class="engt" font-size="%.1f" text-anchor="%s"%s>%s</text>' %
                 (x, y + hh / 2.8, hh, anchor, weight, t))
    # overall dims
    y0 = h + pad + 14
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="dim"/>' % (pad, y0, pad + w, y0))
    s.append('<text x="%.1f" y="%.1f" class="dimt">%.1f</text>' % (pad + w / 2, y0 - 3, w))
    x0 = pad + w + 14
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="dim"/>' % (x0, pad, x0, pad + h))
    s.append('<text x="%.1f" y="%.1f" class="dimt" transform="rotate(-90 %.1f %.1f)">%.1f</text>' %
             (x0 - 3, pad + h / 2, x0 - 3, pad + h / 2, h))
    s.append('</svg>')
    return "".join(s)


def feature_rows(p: Part):
    """Feature table rows in as-cut coordinates (origin = bottom-left of the DXF).

    @param p Part
    @returns list of [label, cx, cy, size]
    """
    f, _, _ = norm_transform(p)
    rows = []
    for label, g in p.features:
        if isinstance(g, tuple):
            _, u, v, dd = g
            x, y = f(u, v)
            rows.append([label, round(x, 1), round(y, 1), "Ø%.1f" % dd])
        else:
            minx, miny, maxx, maxy = g.bounds
            x, y = f((minx + maxx) / 2, (miny + maxy) / 2)
            rows.append([label, round(x, 1), round(y, 1), "%.1f x %.1f" % (maxx - minx, maxy - miny)])
    # merge duplicates
    merged = {}
    for r in rows:
        k = (r[0], r[3])
        merged.setdefault(k, []).append((r[1], r[2]))
    out = []
    for (lab, size), pts in merged.items():
        out.append(dict(label=lab, size=size, pts=pts))
    return out


def main(out_dir):
    """Generate DXFs, scene JSON and drawings for both variants.

    @param out_dir output folder
    @returns dict summary
    """
    os.makedirs(out_dir, exist_ok=True)
    data = {"params": dict(T=T, W=W_HOUSE, D=D_HOUSE, H=H_WALL, rise=RIDGE_RISE, part_y=PART_Y,
                           servo=SERVO_AXIS, sash_y=SASH_AXIS_Y, fan=FAN_C, oh=ROOF_OH,
                           finger=round(H_WALL / N_FINGERS, 2)),
            "variants": {}, "components": components()}
    for var in ("A", "B"):
        parts = build_parts(var)
        vdir = os.path.join(out_dir, "variant_%s_%s" % (var, "gable_roof" if var == "A" else "flat_roof"))
        os.makedirs(os.path.join(vdir, "parts"), exist_ok=True)
        for p in parts:
            doc, msp = new_doc()
            emit_part(msp, p)
            doc.saveas(os.path.join(vdir, "parts", "%s_x%d.dxf" % (p.pid.lower(), len(p.places))))
        sheets = pack(parts)
        sheet_meta = []
        for i, sh in enumerate(sheets):
            doc, msp = new_doc()
            msp.add_lwpolyline([(0, 0), (600, 0), (600, 400), (0, 400)], close=True, dxfattribs={"layer": "NOTE"})
            for (p, x, y, rot) in sh:
                emit_part(msp, p, x, y, rot)
            doc.saveas(os.path.join(vdir, "sheet_%d_of_%d_600x400.dxf" % (i + 1, len(sheets))))
            sheet_meta.append([[p.pid, x, y, rot] for (p, x, y, rot) in sh])
        area = sum(p.poly.area * len(p.places) for p in parts) / 1e6
        data["variants"][var] = dict(
            parts=scene_json(parts),
            drawings={p.pid: svg_part(p) for p in parts},
            features={p.pid: feature_rows(p) for p in parts},
            sheets=len(sheets), sheet_layout=sheet_meta,
            sheet_svgs=[sheet_svg(sh) for sh in sheets],
            area_m2=round(area, 3),
            cut_m=round(sum((p.poly.length + sum(2 * math.pi * c[2] for c in p.circles)) * len(p.places)
                            for p in parts) / 1000, 1))
    with open(os.path.join(out_dir, "scene.json"), "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    return data


def sheet_svg(sheet):
    """Thumbnail SVG of one nested 600x400 sheet.

    @param sheet list of (part, x, y, rot)
    @returns svg string
    """
    s = ['<svg viewBox="-4 -4 608 408" xmlns="http://www.w3.org/2000/svg" class="sheet">',
         '<rect x="0" y="0" width="600" height="400" class="sheetbg"/>']
    for (p, ox, oy, rot) in sheet:
        f, w, h = norm_transform(p)

        def tr(u, v):
            """Local -> sheet svg coords."""
            x, y = f(u, v)
            if rot:
                x, y = h - y, x
            return x + ox, 400 - (y + oy)
        d = []
        for ring in [p.poly.exterior] + list(p.poly.interiors):
            pts = [tr(a, b) for a, b in list(ring.coords)[:-1]]
            d.append("M" + " L".join("%.1f,%.1f" % q for q in pts) + " Z")
        s.append('<path d="%s" class="cut" fill-rule="evenodd"/>' % " ".join(d))
        for (u, v, r, _) in p.circles:
            x, y = tr(u, v)
            s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" class="hole"/>' % (x, y, r))
        cx, cy = tr(*[(a + b) / 2 for a, b in zip(p.poly.bounds[:2], p.poly.bounds[2:])])
        s.append('<text x="%.1f" y="%.1f" class="lbl">%s</text>' % (cx, cy, p.pid))
    s.append("</svg>")
    return "".join(s)


if __name__ == "__main__":
    import sys
    d = main(sys.argv[1] if len(sys.argv) > 1 else "out")
    for v, vd in d["variants"].items():
        print(v, "sheets:", vd["sheets"], "area m2:", vd["area_m2"], "cut m:", vd["cut_m"],
              [(p["id"], p["size"], p["qty"]) for p in vd["parts"]])
