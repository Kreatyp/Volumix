# -*- coding: utf-8 -*-
"""Lautstaerke angleichen – die Regelung an einem gestellten Verlauf.

Geprueft wird nicht nur, dass sie regelt, sondern vor allem, was sie NICHT
tun darf: ueber den eingestellten Pegel hinausgehen, in Pausen hochziehen
oder beim Abschalten etwas verstellt zuruecklassen.
"""
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.audio import AudioEngine                          # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


class FakeSav:
    """Ein Lautstaerkeregler, wie Windows ihn fuer eine App fuehrt."""

    def __init__(self, amp=1.0):
        self.amp = amp

    def GetMasterVolume(self):
        return self.amp

    def SetMasterVolume(self, v, _):
        self.amp = float(v)


def bauen(nutzer=0.8):
    e = AudioEngine.__new__(AudioEngine)
    e.angleichen = set()
    e._nutzer_amp, e._daempfung = {}, {}
    e.gamma = 1.7
    sav = FakeSav(nutzer)
    e._by_key = lambda max_alter=2.0: {"app.exe": [sav]}
    e._peaks_wert = 0.0
    e._peaks = lambda max_alter=2.0, roh=False: {"app.exe": e._peaks_wert}
    return e, sav


def laufen(e, pegel, takte):
    """`takte` Durchgaenge mit diesem Ausgangspegel."""
    for _ in range(takte):
        # Was gemessen wird, ist bereits gedaempft – wie in Wirklichkeit
        d = e._daempfung.get("app.exe", 1.0)
        e._peaks_wert = min(1.0, pegel * d)
        e._angleichen_regeln()


print("=== Laute Stelle wird gedaempft ===")
e, sav = bauen(nutzer=0.8)
e.angleichen_setzen("app.exe", True)
pruefe("Nutzerpegel gemerkt", round(e._nutzer_amp["app.exe"], 3), 0.8)
laufen(e, 0.9, 60)
pruefe("gedaempft", e._daempfung["app.exe"] < 0.9,
       True, "Daempfung {:.2f}".format(e._daempfung["app.exe"]))
pruefe("aber nie unter die Untergrenze",
       e._daempfung["app.exe"] >= e.ANGLEICH_TIEFSTENS, True)
pruefe("gesetzt wird Nutzerpegel mal Daempfung",
       round(sav.amp, 3), round(0.8 * e._daempfung["app.exe"], 3))

print("\n=== Nie lauter als eingestellt ===")
e, sav = bauen(nutzer=0.6)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.05, 200)          # sehr leise Quelle, ueber lange Zeit
pruefe("Daempfung bleibt bei hoechstens 1", e._daempfung["app.exe"] <= 1.0)
pruefe("Regler geht nicht ueber den Nutzerwert", sav.amp <= 0.6 + 1e-9,
       True, "ist {:.3f}".format(sav.amp))

print("\n=== Pausen bleiben unberuehrt ===")
e, sav = bauen(nutzer=0.8)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.9, 60)
gedaempft = e._daempfung["app.exe"]
laufen(e, 0.0, 100)           # Stille
pruefe("Stille aendert nichts", round(e._daempfung["app.exe"], 4),
       round(gedaempft, 4))

print("\n=== Abschalten stellt zurueck ===")
e, sav = bauen(nutzer=0.75)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.95, 80)
pruefe("waehrenddessen leiser", sav.amp < 0.75, True,
       "{:.3f}".format(sav.amp))
e.angleichen_setzen("app.exe", False)
pruefe("danach wieder genau der eingestellte Wert", round(sav.amp, 4), 0.75)
pruefe("nichts bleibt haengen",
       ("app.exe" in e._nutzer_amp) or ("app.exe" in e._daempfung), False)

print("\n=== Leiser geht schneller als zurueck ===")
# Sonst schreit es bei jeder lauten Stelle kurz auf, oder es pumpt in
# Sprechpausen wieder hoch.
e, _ = bauen()
e.angleichen_setzen("app.exe", True)
laufen(e, 0.9, 10)
schnell = 1.0 - e._daempfung["app.exe"]
e2, _ = bauen()
e2.angleichen_setzen("app.exe", True)
e2._daempfung["app.exe"] = 0.5
laufen(e2, 0.2, 10)
langsam = e2._daempfung["app.exe"] - 0.5
pruefe("nach unten deutlich flotter", schnell > langsam * 2, True,
       "{:.3f} gegen {:.3f}".format(schnell, langsam))

print("\n=== Von Hand gestellter Wert ist die neue Obergrenze ===")
e, sav = bauen(nutzer=0.8)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.9, 50)
e._nutzer_amp["app.exe"] = 0.4          # so, wie es der Auftrag „setvol“ tut
laufen(e, 0.9, 50)
pruefe("Regler bleibt unter dem neuen Wert", sav.amp <= 0.4 + 1e-9, True,
       "ist {:.3f}".format(sav.amp))

print("\n=== Ohne eingeschaltete Apps passiert nichts ===")
e, sav = bauen(nutzer=0.9)
laufen(e, 0.95, 30)
pruefe("Pegel unveraendert", round(sav.amp, 4), 0.9)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
