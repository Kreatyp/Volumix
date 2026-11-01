# -*- coding: utf-8 -*-
"""Wechselt Windows das Ausgabegeraet, muss Volumix alles neu holen.

Steckt jemand Kopfhoerer ein oder verbindet Bluetooth, zeigt alles
Gespeicherte auf das alte Geraet: der Regler der Gesamtlautstaerke, die
Sitzungen der Apps, die Kurve. Gemeldet wurde das so: „wenn ich AirPods
verbinde, aendert sich die Lautstaerke nicht" – Volumix regelte weiter die
Lautsprecher.

Geprueft wird mit einer Attrappe fuer die Kennung des Geraets. Ein zweites
Geraet an- und abzustecken geht in einer Testreihe nicht.
"""
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix import config                                     # noqa: E402
# Die Testreihe soll nicht ins echte Protokoll schreiben: Ein Wechsel, den
# es nie gab, steht sonst in `fehler.log` und verwirrt bei der Fehlersuche.
config.notiz = lambda *a, **k: None

from volumix.audio import AudioEngine                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


e = AudioEngine()
# Attrappe: Die Kennung kommt aus dieser Liste, nicht von Windows.
kennungen = ["{geraet-eins}"]
e._geraet_kennung = lambda: kennungen[0]

print("=== Erster Durchgang ===")
gewechselt = e._geraet_pruefen(takt=0.0)
pruefe("erste Abfrage meldet keinen Wechsel", gewechselt is False)
pruefe("Kennung ist gemerkt", e._geraet == "{geraet-eins}")

# Zustand, wie er nach einer Weile Betrieb aussieht
e._epv = "alter Regler"
e._sess_cache = (time.perf_counter(), {"spotify.exe": ["alt"]})
e._meter_cache = (time.perf_counter(), {"spotify.exe": "alt"})
e._ziel["spotify.exe"] = 50.0
e._jetzt["spotify.exe"] = 40.0
e._schritt["spotify.exe"] = 2.0

print("\n=== Ohne Wechsel bleibt alles stehen ===")
pruefe("kein Wechsel gemeldet", e._geraet_pruefen(takt=0.0) is False)
pruefe("Regler unberuehrt", e._epv == "alter Regler")
pruefe("Sitzungen unberuehrt", e._sess_cache is not None)

print("\n=== Jetzt kommen die Kopfhoerer ===")
kennungen[0] = "{geraet-zwei}"
gewechselt = e._geraet_pruefen(takt=0.0)
pruefe("Wechsel gemeldet", gewechselt is True)
pruefe("neue Kennung gemerkt", e._geraet == "{geraet-zwei}")
# Nicht None, sondern neu: Das Nachlesen der Kurve holt den Regler des
# neuen Geraets gleich wieder. Wichtig ist, dass der alte weg ist.
pruefe("Regler der Gesamtlautstaerke ist nicht mehr der alte",
       e._epv != "alter Regler")
pruefe("Sitzungen weggeworfen", e._sess_cache is None)
pruefe("Pegelmesser weggeworfen", e._meter_cache is None)
# Ein laufendes Nachfahren zeigte auf Regler, die es nicht mehr gibt.
pruefe("kein Nachfahren auf toten Reglern",
       not e._ziel and not e._jetzt and not e._schritt)

print("\n=== Takt ===")
# Die Abfrage kostet gemessen 10 ms - sie darf nicht in jedem Durchgang
# laufen, sonst frisst sie ein Fuenftel der Messzeit.
kennungen[0] = "{geraet-drei}"
pruefe("innerhalb des Takts wird nicht gefragt",
       e._geraet_pruefen(takt=5.0) is False)
pruefe("und die alte Kennung steht noch", e._geraet == "{geraet-zwei}")
time.sleep(0.05)
pruefe("nach Ablauf des Takts schon",
       e._geraet_pruefen(takt=0.01) is True, e._geraet)

print("\n=== Ohne Antwort von Windows ===")
e._geraet_kennung = lambda: None
pruefe("keine Kennung, kein Wechsel", e._geraet_pruefen(takt=0.0) is False)
pruefe("und die letzte bleibt stehen", e._geraet == "{geraet-drei}")

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
