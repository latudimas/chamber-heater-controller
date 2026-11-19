"""1:1 cutting templates for the hand-made duct parts (metal plate, gasket, outlet box).

Print the SVGs at 100 % (no "fit to page"), check the 50 mm scale bar with a
ruler, then glue or trace onto the sheet. Values match the CAD parameters in
hardware/duct/chamber-heater-duct.sc; change both together.

Usage: python hardware/duct/templates/gen_templates.py   (standard library only)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- CAD parameters (keep in step with chamber-heater-duct.sc) -------------
plate_W, plate_H = 124.0, 80.0      # PTC plate and gasket outline
bolt_y, bolt_z = 56.0, 30.0         # 4 x M3 clamp bolts
win_L, win_W = 54.0, 19.0           # window per PTC (fin area, ESTIMATED)
ptc_dz = 18.25                      # PTC centres above/below the duct axis
tab_pitch = 82.0                    # PTC tab hole pitch
out_in = 60.0                       # gasket window = printed duct outlet
box_in_W, box_in_H, box_L = 96.0, 72.0, 46.0
sheet_t = 1.0
tab_len = bolt_y + 4 - (box_in_W / 2 + sheet_t)   # outlet-box tab, 11 mm
tab_w = 12.0
probe_from_outlet = 10.0            # DS18B20 hole, from the outlet edge
M3 = 3.4

STYLE = ('<style>.cut{fill:none;stroke:#000;stroke-width:0.3}'
         '.bend{fill:none;stroke:#c00;stroke-width:0.3;stroke-dasharray:3 2}'
         '.cl{stroke:#08f;stroke-width:0.15;stroke-dasharray:6 2 1 2}'
         'text{font:3px sans-serif;fill:#000}</style>')


def svg(name, w, h, body, notes):
    margin = 12
    W, H = w + 2 * margin, h + 2 * margin + 6 * (len(notes) + 2)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
           f'viewBox="{-margin} {-margin} {W} {H}">', STYLE]
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


def hole(cx, cy, d):
    return (f'<circle class="cut" cx="{cx}" cy="{cy}" r="{d/2}"/>'
            f'<line class="cl" x1="{cx-d}" y1="{cy}" x2="{cx+d}" y2="{cy}"/>'
            f'<line class="cl" x1="{cx}" y1="{cy-d}" x2="{cx}" y2="{cy+d}"/>')


def centred(cx, cy):
    """Plate coordinates (origin at the duct axis, z up) -> SVG (origin top-left)."""
    return plate_W / 2 + cx, plate_H / 2 - cy


def ptc_plate():
    b = [rect(0, 0, plate_W, plate_H)]
    for s in (1, -1):
        x, y = centred(-win_L / 2, s * ptc_dz + win_W / 2)
        b.append(rect(x, y, win_L, win_W))
        for t in (1, -1):
            b.append(hole(*centred(t * tab_pitch / 2, s * ptc_dz), M3))
            b.append(hole(*centred(t * bolt_y, s * bolt_z), M3))
    svg("ptc-plate.svg", plate_W, plate_H, b, [
        f"PTC plate: 1 x scrap aluminium or steel, {plate_W:g} x {plate_H:g} mm, ~1 mm.",
        f"2 windows {win_L:g} x {win_W:g} (fin area: ESTIMATED, check against your PTC).",
        "Small holes: M3 (3.4). Inner 4 = PTC tabs; outer 4 = clamp bolts.",
        "Deburr all edges. PTC tabs bolt to the downstream (outlet) face.",
    ])


def gasket():
    b = [rect(0, 0, plate_W, plate_H)]
    x, y = centred(-out_in / 2, out_in / 2)
    b.append(rect(x, y, out_in, out_in))
    for s in (1, -1):
        for t in (1, -1):
            b.append(hole(*centred(t * bolt_y, s * bolt_z), M3))
            b.append(hole(*centred(t * tab_pitch / 2, s * ptc_dz), 8))
    svg("gasket.svg", plate_W, plate_H, b, [
        "Gasket: high-temperature silicone sheet (or ceramic-fibre paper), ~3 mm.",
        f"Window {out_in:g} x {out_in:g} = printed duct outlet. 8 mm holes clear the PTC tab nuts.",
        "Thermal break between the printed flange and the metal plate.",
    ])


def outlet_box():
    """Flat pattern: bottom | side | top | side | seam, each box_L long; the two
    side panels carry the clamp tabs on their upstream edge."""
    w_tb = box_in_W + 2 * sheet_t      # top/bottom panel width
    w_s = box_in_H + 2 * sheet_t       # side panel width
    seam = 10.0
    panels = [("bottom", w_tb), ("side", w_s), ("top", w_tb), ("side", w_s), ("seam", seam)]
    total = sum(w for _, w in panels)
    oy = tab_len                       # tabs stick out above the strip (upstream)
    b, x = [], 0.0
    outline = []
    for i, (name, w) in enumerate(panels):
        if i:
            b.append(f'<line class="bend" x1="{x}" y1="{oy}" x2="{x}" y2="{oy+box_L}"/>')
        b.append(f'<text x="{x+2}" y="{oy+box_L/2}">{name}</text>')
        if name == "side":
            for s in (1, -1):
                cx = x + w / 2 + s * bolt_z
                b.append(rect(cx - tab_w / 2, 0, tab_w, tab_len))
                b.append(f'<line class="bend" x1="{cx-tab_w/2}" y1="{oy}" x2="{cx+tab_w/2}" y2="{oy}"/>')
                b.append(hole(cx, tab_len - (bolt_y - box_in_W / 2 - sheet_t), M3))
        if name == "top":
            b.append(hole(x + w / 2, oy + box_L - probe_from_outlet, 6))
        x += w
    b.insert(0, rect(0, oy, total, box_L))
    svg("outlet-box.svg", total, oy + box_L, b, [
        f"Outlet box flat pattern: sheet ~1 mm, strip {total:g} x {box_L:g} mm + 4 clamp tabs.",
        "Red dashed = bend 90 deg. Fold into a tube (inner ~96 x 72), seam overlaps and is",
        "riveted/screwed. Tabs bend OUTWARD and are clamped by the 4 flange bolts.",
        "Bend allowance not included: cut slightly long and trim. 6 mm hole = DS18B20 probe.",
        "Upstream edge (tabs) faces the PTC plate; the other end is the hot-air outlet.",
    ])


if __name__ == "__main__":
    ptc_plate()
    gasket()
    outlet_box()
    print("wrote ptc-plate.svg, gasket.svg, outlet-box.svg")
