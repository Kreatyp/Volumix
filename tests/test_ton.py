# -*- coding: utf-8 -*-
"""Der Ton am Anschlag – vor allem: wann er NICHT kommen darf.

Ein Ton, der bei jeder Rastung am oberen Ende erneut klopft, waere nach
zwei Minuten unertraeglich. Deshalb steht hier vor allem das Schweigen.
"""
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix import klang                                      # noqa: E402
from volumix.audio import AudioEngine                          # noqa: E402
from volumix.config import MASTER_KEY                          # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


gespielt = []


def bauen(start_prozent, schritt=10.0):
    """Motor-Attrappe: nur so viel, wie das Regeln braucht."""
    e = AudioEngine.__new__(AudioEngine)
    e.targets = {MASTER_KEY}
    e.speed_step = schritt
    e.ton_am_anschlag = True
    e._ziel, e._jetzt, e._schritt = {}, {}, {}
    e._by_key = lambda max_alter=2.0: {}
    e.prozent = lambda k, by=None: start_prozent
    return e


echt = klang.anschlag
klang.anschlag = lambda: gespielt.append(1) or True
import volumix.audio as audio_modul                            # noqa: E402
audio_modul.klang = klang

print("=== Der Ton kommt beim Ankommen ===")
e = bauen(85.0)
e._scroll_anwenden(2)               # 85 + 20 -> begrenzt auf 100
pruefe("bei 85 -> 100 klingt es", len(gespielt), 1)
pruefe("und das Ziel steht auf 100", e._ziel[MASTER_KEY], 100.0)

print("\n=== Weiterdrehen am Anschlag bleibt still ===")
gespielt.clear()
for _ in range(5):
    e._scroll_anwenden(2)
pruefe("fuenf Rastungen obendrauf: kein Ton", len(gespielt), 0)

print("\n=== Runter und wieder hoch klingt erneut ===")
gespielt.clear()
e._scroll_anwenden(-3)              # auf 70
pruefe("runterdrehen ist still", len(gespielt), 0)
e._scroll_anwenden(5)               # wieder hoch an die Grenze
pruefe("erneutes Ankommen klingt", len(gespielt), 1)

print("\n=== Genau auf 100 treffen zaehlt auch ===")
gespielt.clear()
e2 = bauen(90.0)
e2._scroll_anwenden(1)              # 90 + 10 = genau 100
pruefe("Punktlandung klingt", len(gespielt), 1)

print("\n=== Unterhalb der Grenze schweigt es ===")
gespielt.clear()
e3 = bauen(20.0)
e3._scroll_anwenden(1)              # auf 30
pruefe("mittendrin kein Ton", len(gespielt), 0)

print("\n=== Abgeschaltet bleibt abgeschaltet ===")
gespielt.clear()
e4 = bauen(85.0)
e4.ton_am_anschlag = False
e4._scroll_anwenden(2)
pruefe("Schalter aus: kein Ton", len(gespielt), 0)
pruefe("geregelt wird trotzdem", e4._ziel[MASTER_KEY], 100.0)

klang.anschlag = echt
audio_modul.klang = klang

print("\n=== Die Sperre im Klang-Modul ===")
klang.zuruecksetzen()
gespielt_echt = []
echt_spielen = klang.spielen
klang.spielen = lambda d: gespielt_echt.append(d) or True
try:
    pruefe("erster Anschlag geht durch", klang.anschlag(), True)
    pruefe("gleich danach nicht", klang.anschlag(), False)
    klang.zuruecksetzen()
    pruefe("nach der Sperre wieder", klang.anschlag(), True)
    pruefe("gespielt wurden {} Toene".format(len(gespielt_echt)),
           len(gespielt_echt), 2)
finally:
    klang.spielen = echt_spielen

print("\n=== Die Klangdatei liegt im Paket ===")
pfad = klang.pfad()
pruefe("Datei vorhanden", os.path.exists(pfad), True, pfad)
if os.path.exists(pfad):
    import wave
    with wave.open(pfad, "rb") as f:
        ms = f.getnframes() * 1000.0 / f.getframerate()
    pruefe("kurz genug fuer etwas, das oft kommt", ms <= 200, True,
           "{:.0f} ms".format(ms))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
