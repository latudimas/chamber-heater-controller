# Duct designs

Three layouts of the same heater, one per folder. All three share the same
parts and rules (ADR-018, ADR-019, ADR-021):

- 2 × Nidec 40 × 40 × 28 fans feeding **one shared plenum**, so any heating
  needs both fans (`F_FAN_STALL`, `E_INTERLOCK`).
- 2 × PTC bolted by their tabs to a flat metal plate whose windows expose only
  the fins (no bypass).
- **Plastic only upstream of the gasket.** Everything downstream is metal.
- Parametric SolidCraft model, STL/3MF for the printed parts, STEP of the
  whole assembly, 1:1 SVG cutting templates for the metal parts.

> **All three use placeholder PTC sizes** from the previous project's 220 V
> 50 W heater. The 12 V 100 W parts have not arrived. Measure them and update
> the parameters before printing or cutting anything. None of the designs has
> been printed, assembled or heated yet.

| | [Horizontal](horizontal/README.md) | [Vertical upflow](vertical/README.md) | [Folded slab](folded/README.md) |
|---|---|---|---|
| Picture | ![](horizontal/images/duct-inlet-view.png) | ![](vertical/images/outlet-view.png) | ![](folded/images/front-view.png) |
| Air path | straight through, horizontal | straight up, one turn at the outlet | in at the front, up, out at the front |
| Size (W × D × H) | 162 × 131 × 100 mm | 100 × 86 × 126 mm | 196 × 50 × 114 mm |
| Volume | ~2.1 L | ~1.1 L | ~1.1 L |
| Turns in the hot path | 0 | 1 (outlet) | 1 (outlet), plus 1 before the PTCs |
| Intake / outlet | opposite ends | slots around the base / one side of the hood | same front face |
| Printed parts | transition + fan guard | shroud + inlet base | fan box |
| Metal parts | plate + outlet box (tube) | plate + hood | plate + hood |
| Good for | floor-standing in a large shelter | dryer boxes, small enclosures, anywhere with floor space | against a wall: dryer box side, behind a printer |
| Watch out for | length; taper between fans and PTCs | intake slots need free space around the base | hot outlet air re-entering the intake on the same face |

The vertical design is the recommended first build: it is the most compact,
keeps the fans in the coolest air, and lets residual heat rise away from the
fans and the printed parts after a stop.

## Folder layout

```
hardware/duct/
  README.md            this file
  horizontal/          v1: fans → taper → PTC plate → outlet box (ADR-018)
  vertical/            fans at the bottom blowing up through the PTCs (ADR-021)
  folded/              slim slab, intake and outlet on the front face (ADR-021)
```

Each design folder has the same structure:

```
  README.md            parts, hardware, print settings, assembly, verify-first list
  duct-<name>.sc       SolidCraft design (parametric)
  exports/             STL / 3MF of the printed parts, STEP of the assembly
  images/              renders
  templates/           1:1 SVG cutting templates + gen_templates.py
```

Template values are copied from the CAD parameters by hand. When you change a
size in a `.sc` file, change it in that design's `templates/gen_templates.py`
too and rerun it:

```bash
python3 hardware/duct/vertical/templates/gen_templates.py
```
