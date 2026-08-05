# -*- coding: utf-8 -*-
"""Alle Regler auf der Kurve der Windows-Gesamtlautstaerke.

Windows daempft nicht linear: halber Reglerweg bedeutet rund 30 % Amplitude.
Die Regler einzelner Apps sind dagegen reine Amplitudenfaktoren. Volumix
rechnet die Apps auf dieselbe Kurve um, damit sich ueberall ein Schritt
gleich anfuehlt.
"""
import os
import sys
import time

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.audio import AudioEngine                          # noqa: E402
from volumix.config import MASTER_KEY                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


motor = AudioEngine()

print("\n=== Hin und zurueck ===")
for p in (0.0, 0.05, 0.25, 0.5, 0.75, 1.0):
    zurueck = motor.pos_aus_amp(motor.amp_aus_pos(p))
    pruefe("Position {:.0%} uebersteht die Umrechnung".format(p),
           abs(zurueck - p) < 1e-9, "{:.6f}".format(zurueck))

print("\n=== Die Kurve wirkt in die richtige Richtung ===")
pruefe("halber Weg daempft deutlich staerker als die Haelfte",
       0.25 < motor.amp_aus_pos(0.5) < 0.38,
       "{:.1%}".format(motor.amp_aus_pos(0.5)))
pruefe("die Enden bleiben fest",
       motor.amp_aus_pos(0.0) == 0.0 and motor.amp_aus_pos(1.0) == 1.0)
pruefe("unten wird stark gestaucht",
       motor.amp_aus_pos(0.1) < 0.05, "{:.1%}".format(motor.amp_aus_pos(0.1)))
# Gleich grosse Reglerschritte, unterschiedliche Wirkung – genau darum geht es
unten = motor.amp_aus_pos(0.15) - motor.amp_aus_pos(0.10)
oben = motor.amp_aus_pos(0.95) - motor.amp_aus_pos(0.90)
pruefe("derselbe Schritt bewegt oben viel mehr Amplitude als unten",
       oben > unten * 4, "{:.4f} gegen {:.4f}".format(oben, unten))

print("\n=== Grenzen ===")
pruefe("ueber 1 wird abgeschnitten", motor.amp_aus_pos(1.5) == 1.0)
pruefe("unter 0 ebenso", motor.amp_aus_pos(-0.5) == 0.0)
pruefe("dasselbe rueckwaerts",
       motor.pos_aus_amp(2.0) == 1.0 and motor.pos_aus_amp(-1.0) == 0.0)

print("\n=== Exponent aus dem laufenden System ===")
pruefe("Rueckfallwert gesetzt", motor.gamma == config.GAMMA_STANDARD,
       str(motor.gamma))
motor._gamma_auffrischen()
print("   abgelesen: gamma = {:.3f}".format(motor.gamma))
pruefe("liegt im plausiblen Bereich", 1.0 <= motor.gamma <= 4.0,
       "{:.3f}".format(motor.gamma))
# Ein lineares Geraet (gamma 1) darf nichts veraendern
motor.gamma = 1.0
pruefe("bei linearem Geraet bleibt alles wie es ist",
       abs(motor.amp_aus_pos(0.37) - 0.37) < 1e-9)
motor.gamma = config.GAMMA_STANDARD

print("\n=== Gesamtlautstaerke bleibt Windows' eigene Skala ===")
# Der Master geht ueber den Windows-Regler; dort rechnet Windows selbst um.
# Deshalb darf Volumix ihn nicht noch einmal durch die Kurve schicken.
gelesen = motor.prozent(MASTER_KEY)
scalar = motor.master_scalar()
if gelesen is None or scalar is None:
    pruefe("Gesamtlautstaerke lesbar", False, "kein Ausgabegeraet")
else:
    pruefe("Anzeige entspricht der Windows-Reglerstellung",
           abs(gelesen - scalar * 100.0) < 0.01,
           "{:.2f} gegen {:.2f}".format(gelesen, scalar * 100.0))

print("\n=== Alte Profile werden umgerechnet ===")
# Frueher standen dort rohe Amplituden. 0,45 Amplitude sind rund 63 % Weg.
alt = config.pos_aus_amp(0.45)
pruefe("Amplitude 0,45 wird zu rund 63 % Weg", 0.60 < alt < 0.66,
       "{:.3f}".format(alt))
pruefe("und ergibt wieder dieselbe Amplitude",
       abs(config.amp_aus_pos(alt) - 0.45) < 1e-9)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
motor.stop()
sys.exit(1 if fehler else 0)
