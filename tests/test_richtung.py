"""Prueft die Richtungsumkehr – der Fehler lag im Tasten-Modus."""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.hooks import InputHook                            # noqa: E402

fehler = 0


def pruefe(name, ist, soll):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}".format("OK  " if ok else "FEHL", name))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


h = InputHook(on_scroll=lambda r: None, on_mute=lambda: None)

print("\n=== normal ===")
h.reverse = False
pruefe("Rad vorwaerts bleibt vorwaerts", h.richtung(1.0), 1.0)
pruefe("Rad rueckwaerts bleibt rueckwaerts", h.richtung(-1.0), -1.0)
pruefe("Lauter-Taste macht lauter", h.richtung(1), 1)
pruefe("Leiser-Taste macht leiser", h.richtung(-1), -1)

print("\n=== umgekehrt ===")
h.reverse = True
pruefe("Rad vorwaerts wird rueckwaerts", h.richtung(1.0), -1.0)
pruefe("Rad rueckwaerts wird vorwaerts", h.richtung(-1.0), 1.0)
pruefe("Lauter-Taste macht leiser", h.richtung(1), -1)
pruefe("Leiser-Taste macht lauter", h.richtung(-1), 1)

print("\n=== beide Eingabearten nutzen dieselbe Stelle ===")
quelle = open(os.path.join(_PROJEKT, "volumix", "hooks.py"),
              encoding="utf-8").read()
pruefe("Rad-Hook ruft richtung()", "self.richtung(d / WHEEL_DELTA)" in quelle,
       True)
pruefe("Tasten-Hook ruft richtung()", quelle.count("self.richtung(") == 2, True)
pruefe("keine doppelte Logik mehr", "if self.reverse else" not in
       quelle.split("def richtung")[1].split("def stop")[1], True)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
