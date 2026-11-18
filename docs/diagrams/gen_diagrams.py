"""Draw simplified block diagrams for the docs with schemdraw.

These are explanatory pictures, NOT the design source. The schematic in
hardware/kicad/ is the source of truth; keep these in step with it.

Usage:  python docs/diagrams/gen_diagrams.py      (needs: pip install schemdraw==0.19)
"""
import os

import schemdraw
import schemdraw.elements as elm

schemdraw.use("svg")
HERE = os.path.dirname(os.path.abspath(__file__))


def heater_channel():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=12, unit=2.5)
        elm.Vdd().label("+12 V")
        k1 = elm.Switch().down().label("K1 contact\n(master relay)", loc="bottom")
        elm.Line().down().length(0.5).label("HEAT_12V", loc="bottom", ofst=0.1)
        elm.Fuse().down().label("F2  12 A", loc="bottom")
        elm.Dot()
        elm.Line().right().length(1.5).label("J2 pin 1", loc="right")
        elm.Line().left().length(1.5)
        elm.Line().down().length(0.75)
        tco = elm.Fuse().down().label("TCO ~110 °C\none-shot", loc="bottom")
        ptc = elm.ResistorIEC().down().label("PTC heater\n12 V 100 W", loc="bottom")
        elm.EncircleBox([tco, ptc], padx=0.4, pady=0.2).linestyle("--").label(
            "off-board\n(on the duct)", loc="left", halign="right")
        elm.Line().down().length(0.75)
        elm.Dot()
        elm.Line().right().length(1.5).label("J2 pin 2", loc="right")
        elm.Line().left().length(1.5)
        elm.Line().down().length(0.5)
        q = elm.NFet(anchor="drain").right().reverse().label("Q2\nIRLB8721", loc="right")
        elm.Ground().at(q.source)
        elm.Line().left().at(q.gate).length(1)
        g = elm.Dot()
        elm.Resistor().left().label("R3 100 Ω", loc="top")
        elm.Line().left().length(0.5).label("GPIO25\n(H1_GPIO)", loc="left")
        elm.Resistor().down().at(g.center).label("R4 10 k\npull-down", loc="bottom")
        elm.Ground()
        d.save(os.path.join(HERE, "heater-channel.svg"))


def master_relay():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=12, unit=2.5)
        elm.Vdd().label("+12 V")
        top = elm.Dot()
        coil = elm.Inductor2(loops=3).down().label("K1 coil\n~150 mA", loc="bottom")
        bot = elm.Dot()
        elm.Line().right().at(top.center).length(2.5)
        elm.Diode().down().reverse().toy(bot.center).label("D1 1N4007\nflyback", loc="bottom")
        elm.Line().left().tox(bot.center)
        q = elm.BjtNpn(circle=True).at(bot.center).anchor("collector").right().label("Q1\nBC337", loc="right")
        elm.Ground().at(q.emitter)
        elm.Line().left().at(q.base).length(0.5)
        elm.Resistor().left().label("R1 470 Ω", loc="top")
        b = elm.Dot()
        elm.Line().left().length(0.75).label("GPIO17\n(RELAY_EN)", loc="left")
        elm.Resistor().down().at(b.center).label("R2 10 k\npull-down\n(K1 open at boot)", loc="bottom")
        elm.Ground()

        # contacts, drawn apart on the right
        elm.Vdd().at((10, 0)).label("+12 V")
        elm.Switch().down().label("K1 contact\n30/40 A", loc="bottom")
        elm.Line().down().length(1)
        elm.Arrow().down().length(1).label("HEAT_12V\nto heater fuses\nF2 / F3", loc="bottom")
        d.save(os.path.join(HERE, "master-relay.svg"))


if __name__ == "__main__":
    heater_channel()
    master_relay()
    print("wrote heater-channel.svg, master-relay.svg")
