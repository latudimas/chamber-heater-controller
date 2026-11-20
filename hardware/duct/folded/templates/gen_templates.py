"""1:1 cutting templates for the hand-made parts of the folded slab duct
(PTC plate, gasket, hood flat pattern).

Print the SVGs at 100 % (no "fit to page"), check the 50 mm scale bar with a
ruler, then glue or trace onto the sheet. Values match the CAD parameters in
hardware/duct/folded/duct-folded.sc; change both together.

Usage: python hardware/duct/folded/templates/gen_templates.py   (standard library only)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- CAD parameters (keep in step with duct-folded.sc) ---------------------
W, D = 196.0, 50.0                  # plate / gasket outline (X x Y)
wall = 2.4                          # printed wall (gasket window = inner X)
bolt_xs = (-92.0, 0.0, 92.0)        # 6 x M3 clamp bolts at (bolt_xs, +-bolt_y)
bolt_y = 21.0
opX, opY = W - 2 * wall, 29.0       # gasket window = printed lip opening
win_L, win_W = 54.0, 19.0           # window per PTC (fin area, ESTIMATED)
ptc_cx = 49.25                      # PTC centres at X = +-ptc_cx, Y = 0
tab_pitch = 82.0                    # PTC tab hole pitch (along X)
hood_inX, hood_inY, hood_H = 193.0, 34.0, 50.0
sheet_t = 1.0
out_W, out_h, out_top = 176.0, 19.0, 2.0  # outlet in the front (-Y) wall
htab_w, htab_L = 10.0, 7.0          # hood clamp tabs (bent outward)
probe_y, probe_d = -8.0, 6.0        # DS18B20 hole in the hood roof
corner = 10.0                       # corner flaps that join the hood walls
M3 = 3.4

STYLE = ('<style>.cut{fill:none;stroke:#000;stroke-width:0.3}'
         '.bend{fill:none;stroke:#c00;stroke-width:0.3;stroke-dasharray:3 2}'
         '.cl{stroke:#08f;stroke-width:0.15;stroke-dasharray:6 2 1 2}'
         'text{font:3px sans-serif;fill:#000}</style>')


def svg(name, w, h, body, notes):
    margin = 12
    W_, H_ = w + 2 * margin, h + 2 * margin + 6 * (len(notes) + 2)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_}mm" height="{H_}mm" '
           f'viewBox="{-margin} {-margin} {W_} {H_}">', STYLE]
    out += body
    y = h + 8
    out.append(f'<line class="cut" x1="0" y1="{y}" x2="50" y2="{y}"/>'
               f'<line class="cut" x1="0" y1="{y-2}" x2="0" y2="{y+2}"/>'
               f'<line class="cut" x1="50" y1="{y-2}" x2="50" y2="{y+2}"/>'
               f'<text x="52" y="{y+1}">50 mm: check with a ruler before cutting</text>')
    for i, n in enumerate(notes):
        out.append(f'<text x="0" y="{y + 7 + 5*i}">{n}</text>')
    out.append('</svg>')
    with open(os.path.join(HERE, name), "w") as f:
        f.write("\n".join(out))


def rect(x, y, w, h, cls="cut"):
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>'


def line(x1, y1, x2, y2, cls="bend"):
    return f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'


def hole(cx, cy, d):
    return (f'<circle class="cut" cx="{cx}" cy="{cy}" r="{d/2}"/>'
            f'<line class="cl" x1="{cx-d}" y1="{cy}" x2="{cx+d}" y2="{cy}"/>'
            f'<line class="cl" x1="{cx}" y1="{cy-d}" x2="{cx}" y2="{cy+d}"/>')


def on_plate(x, y):
    """Top view (world X right, world Y up = towards the back) -> SVG."""
    return W / 2 + x, D / 2 - y


def ptc_plate():
    b = [rect(0, 0, W, D)]
    for s in (1, -1):
        x, y = on_plate(s * ptc_cx - win_L / 2, win_W / 2)
        b.append(rect(x, y, win_L, win_W))
        for t in (1, -1):
            b.append(hole(*on_plate(s * ptc_cx + t * tab_pitch / 2, 0), M3))
    for bx in bolt_xs:
        for s in (1, -1):
            b.append(hole(*on_plate(bx, s * bolt_y), M3))
    svg("ptc-plate.svg", W, D, b, [
        f"PTC plate: 1 x scrap aluminium or steel, {W:g} x {D:g} mm, ~1 mm. Seen from above.",
        f"2 windows {win_L:g} x {win_W:g} (fin area: ESTIMATED, check against your PTC).",
        "M3 (3.4) holes: 4 on the centre line = PTC tabs; 6 along the edges = clamp bolts.",
        "Deburr all edges. PTCs sit on TOP of the plate (downstream); nuts underneath.",
    ])


def gasket():
    b = [rect(0, 0, W, D)]
    x, y = on_plate(-opX / 2, opY / 2)
    b.append(rect(x, y, opX, opY))
    for bx in bolt_xs:
        for s in (1, -1):
            b.append(hole(*on_plate(bx, s * bolt_y), M3))
    svg("gasket.svg", W, D, b, [
        "Gasket: high-temperature silicone sheet (or ceramic-fibre paper), ~3 mm.",
        f"Window {opX:g} x {opY:g} = printed lip opening (a frame; the PTC tab nuts sit in it).",
        "Thermal break between the printed fan box and the metal plate. Cut in one piece.",
    ])


def hood():
    """Flat pattern of a closed-top box: roof in the middle, four walls folded
    down, corner flaps on the side walls riveted to the front/back walls,
    clamp tabs on the free edge of the front and back walls (bent outward)."""
    Lx, Ly = hood_inX + 2 * sheet_t, hood_inY + 2 * sheet_t   # roof (outer)
    h = hood_H - sheet_t                                       # wall height
    R = htab_L                                                 # room for tabs
    x0, y0 = h, R + h                                          # roof corner
    total_w, total_h = Lx + 2 * h, Ly + 2 * h + 2 * R
    b = []
    # one cut outline: back wall, right wall with its corner flaps, front wall,
    # left wall with its corner flaps (corner flaps belong to the side walls)
    xr, yb = x0 + Lx, y0 + Ly
    pts = [(x0, R), (xr, R), (xr, y0 - corner), (xr + h, y0 - corner),
           (xr + h, yb + corner), (xr, yb + corner), (xr, yb + h), (x0, yb + h),
           (x0, yb + corner), (0, yb + corner), (0, y0 - corner), (x0, y0 - corner)]
    b.append('<polygon class="cut" points="%s"/>' % " ".join(f"{x},{y}" for x, y in pts))
    # slits between each corner flap and the front/back wall next to it
    for xs in (x0, xr):
        b.append(line(xs, y0 - corner, xs, y0, "cut"))
        b.append(line(xs, yb, xs, yb + corner, "cut"))
    # bends: roof edges and the corner-flap folds
    b.append(rect(x0, y0, Lx, Ly, "bend"))
    for xa, xb in ((0, x0), (xr, xr + h)):
        b.append(line(xa, y0, xb, y0))
        b.append(line(xa, yb, xb, yb))
    # outlet window in the front wall, measured from the roof fold
    ox = x0 + Lx / 2 - out_W / 2
    b.append(rect(ox, y0 + Ly + out_top, out_W, out_h))
    b.append(f'<text x="{ox + 2}" y="{y0 + Ly + out_top + out_h/2}">outlet (front)</text>')
    # clamp tabs on the free edges of the back and front walls
    hole_off = bolt_y - (hood_inY / 2 + sheet_t)       # from the wall to the hole
    for bx in bolt_xs:
        cx = x0 + Lx / 2 + bx
        for edge, sgn in ((R, -1), (y0 + Ly + h, 1)):
            far = edge + sgn * htab_L
            xa, xb = cx - htab_w / 2, cx + htab_w / 2
            b.append(f'<polyline class="cut" points="{xa},{edge} {xa},{far} {xb},{far} {xb},{edge}"/>')
            b.append(line(xa, edge, xb, edge))
            b.append(hole(cx, edge + sgn * hole_off, M3))
    # probe hole in the roof (world Y = probe_y; front is down in this drawing)
    b.append(hole(x0 + Lx / 2, y0 + Ly / 2 - probe_y, probe_d))
    b.append(f'<text x="{x0 + 2}" y="{y0 + 5}">roof</text>')
    svg("hood.svg", total_w, total_h, b, [
        f"Hood flat pattern: sheet ~1 mm, {total_w:g} x {total_h:g} mm overall (print on A3 landscape).",
        "Red dashed = bend 90 deg. Fold the four walls DOWN from the roof, then fold the",
        "corner flaps onto the front/back walls and rivet or screw them.",
        "Clamp tabs on the free edges bend OUTWARD. Drill the tab holes after bending:",
        f"they sit only {hole_off:g} mm from the wall. 6 mm hole = DS18B20 probe.",
        "Bend allowance not included: cut slightly large and trim.",
    ])


if __name__ == "__main__":
    ptc_plate()
    gasket()
    hood()
    print("wrote ptc-plate.svg, gasket.svg, hood.svg")
