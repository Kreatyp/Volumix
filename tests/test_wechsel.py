# -*- coding: utf-8 -*-
"""Pegelabgleich beim Wechsel zwischen Gesamt und einzelnen Apps.

Kernpunkt ist der Gehoerschutz: Beim Sprung auf eine App wird die
Gesamtlautstaerke aufgezogen. Alles, was in dem Moment hoerbar spielt, muss
vorher heruntergeregelt sein – sonst knallt es.
"""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.audio import AudioEngine                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


class Regler:
    """Attrappe eines App-Reglers."""

    def __init__(self, amp=1.0, kaputt=False):
        self.amp = amp
        self.kaputt = kaputt

    def GetMasterVolume(self):
        return self.amp

    def SetMasterVolume(self, wert, ctx=None):
        if self.kaputt:
            raise OSError("Sitzung gibt es nicht mehr")
        self.amp = wert


def motor_bauen(regler, spielend=(), gain=0.25, kaputt=()):
    m = AudioEngine()
    m.switch_mode = "carry"
    objekte = {k: [Regler(v, k in kaputt)] for k, v in regler.items()}
    m._by_key = lambda max_alter=2.0: objekte
    m._cache_weg = lambda: None
    m.master_gain = lambda: gain
    m._spielende = lambda ausser=(), **rest: {
        k: objekte[k][0] for k in spielend if k not in ausser}
    m.gesetzt_master = []
    m.set_master_scalar = lambda w: m.gesetzt_master.append(w)
    m.set_master_gain = lambda w: m.gesetzt_master.append(("gain", w))
    return m, objekte


print("\n=== Gesamt -> App: spielende Apps kommen mit ===")
m, obj = motor_bauen({"chrome.exe": 1.0, "spotify.exe": 1.0,
                      "discord.exe": 1.0},
                     spielend=["spotify.exe"], gain=0.25)
m._pegel_angleichen("apps", ["chrome.exe"])
pruefe("Ziel wird dem Gain entsprechend leiser",
       abs(obj["chrome.exe"][0].amp - 0.25) < 1e-9,
       "{:.3f}".format(obj["chrome.exe"][0].amp))
pruefe("die spielende App ebenso",
       abs(obj["spotify.exe"][0].amp - 0.25) < 1e-9,
       "{:.3f}".format(obj["spotify.exe"][0].amp))
pruefe("die stille App bleibt unberuehrt",
       abs(obj["discord.exe"][0].amp - 1.0) < 1e-9,
       "{:.3f}".format(obj["discord.exe"][0].amp))
pruefe("Gesamtlautstaerke geht auf voll",
       m.gesetzt_master == [1.0], str(m.gesetzt_master))

print("\n=== Geht das Leiserstellen schief, bleibt die Gesamt stehen ===")
# Genau hier lag der Fehler: Der Sitzungsspeicher war veraltet, das
# Leiserstellen verpuffte still – und die Gesamtlautstaerke ging trotzdem hoch.
m, obj = motor_bauen({"chrome.exe": 1.0, "spotify.exe": 1.0},
                     spielend=["spotify.exe"], gain=0.25,
                     kaputt=["chrome.exe"])
m._pegel_angleichen("apps", ["chrome.exe"])
pruefe("Gesamtlautstaerke wurde NICHT aufgezogen",
       m.gesetzt_master == [], str(m.gesetzt_master))
pruefe("das Ziel steht unveraendert", obj["chrome.exe"][0].amp == 1.0)

print("\n=== Auch wenn eine spielende App nicht erreichbar ist ===")
m, obj = motor_bauen({"chrome.exe": 1.0, "spotify.exe": 1.0},
                     spielend=["spotify.exe"], gain=0.25,
                     kaputt=["spotify.exe"])
m._pegel_angleichen("apps", ["chrome.exe"])
pruefe("Gesamtlautstaerke bleibt ebenfalls stehen",
       m.gesetzt_master == [], str(m.gesetzt_master))

print("\n=== App -> Gesamt ===")
m, obj = motor_bauen({"chrome.exe": 0.25, "spotify.exe": 0.25},
                     spielend=["spotify.exe"], gain=1.0)
m._pegel_angleichen("master", ["chrome.exe"])
pruefe("Gesamtlautstaerke uebernimmt den Pegel",
       m.gesetzt_master and m.gesetzt_master[0][0] == "gain",
       str(m.gesetzt_master))
pruefe("die Apps gehen wieder auf voll",
       obj["chrome.exe"][0].amp == 1.0 and obj["spotify.exe"][0].amp == 1.0,
       "{:.2f} / {:.2f}".format(obj["chrome.exe"][0].amp,
                                obj["spotify.exe"][0].amp))

print("\n=== Modus „Nichts aendern“ ===")
m, obj = motor_bauen({"chrome.exe": 1.0, "spotify.exe": 1.0},
                     spielend=["spotify.exe"], gain=0.25)
m.switch_mode = "none"
m._pegel_angleichen("apps", ["chrome.exe"])
pruefe("nichts angefasst",
       obj["chrome.exe"][0].amp == 1.0 and obj["spotify.exe"][0].amp == 1.0
       and m.gesetzt_master == [])

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
