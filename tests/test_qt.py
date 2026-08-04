"""Fachliche Tests der Qt-Fassung – ohne Fenster.

Prueft die Rechenregeln, die beim Umbau mitgewandert sind, plus die neuen
Profile.
"""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)
import math

sys.path.insert(0, _PROJEKT)

from volumix.audio import AudioEngine, huebscher_name      # noqa: E402
from volumix.theme import PALETTE, Theme, mix              # noqa: E402
from volumix import config                                 # noqa: E402

fehler = 0


def pruefe(name, ist, soll):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}".format("OK  " if ok else "FEHL", name))
    if not ok:
        print("       ist  {}\n       soll {}".format(ist, soll))


class FakeSav:
    def __init__(self, st, key):
        self.st, self.key = st, key

    def GetMasterVolume(self):
        return self.st["a"][self.key]

    def SetMasterVolume(self, v, _):
        self.st["a"][self.key] = float(v)


def bauen(modus, master_db, apps, spielt=()):
    e = AudioEngine.__new__(AudioEngine)
    e.switch_mode = modus
    st = {"db": master_db, "a": dict(apps), "spuren": []}

    def snap():
        g = 10.0 ** (st["db"] / 20.0)
        st["spuren"].append({k: v * g for k, v in st["a"].items()})

    def set_app(k, v):
        st["a"][k] = float(v)
        snap()

    st["set_app"] = set_app
    e.master_gain = lambda: 10.0 ** (st["db"] / 20.0)
    e.set_master_gain = lambda g: (st.__setitem__(
        "db", 20.0 * math.log10(max(1e-5, min(1.0, g)))), snap())
    e.set_master_scalar = lambda v: (st.__setitem__("db", 0.0), snap())
    e.master_scalar = lambda: 10.0 ** (st["db"] / 20.0)
    e.set_volume = lambda k, v: set_app(k, v)
    e.prozent = lambda k, by=None: st["a"][k] * 100.0
    e._by_key = lambda max_alter=2.0: {k: [FakeSav(st, k)] for k in st["a"]}
    e._spielende = lambda ausser=(), **kw: {
        k: FakeSav(st, k) for k in spielt if k not in ausser}
    e._setzen_lassen = lambda s=0.08: None
    e._ziel, e._jetzt, e._schritt = {}, {}, {}
    snap()
    return e, st


def hoerbar(st):
    g = 10.0 ** (st["db"] / 20.0)
    return {k: round(v * g * 100, 2) for k, v in st["a"].items()}


def kein_knall(st):
    start, ende = st["spuren"][0], st["spuren"][-1]
    for i, s in enumerate(st["spuren"]):
        for k, v in s.items():
            grenze = max(start.get(k, 0), ende.get(k, 0)) + 1e-9
            if v > grenze:
                return "Schritt {}: {} zu laut".format(i, k)
    return "ok"


print("\n=== Pegel-Umrechnung (aus der Tk-Fassung uebernommen) ===")
# 40 % Regler entsprechen auf diesem Geraet -13,8 dB
e, st = bauen("carry", -13.8, {"chrome.exe": 1.0, "spotify.exe": 1.0,
                               "discord.exe": 1.0}, spielt=["spotify.exe"])
vor = hoerbar(st)
e._pegel_angleichen("apps", ["chrome.exe"])
pruefe("Chrome bleibt gleich laut", hoerbar(st)["chrome.exe"],
       vor["chrome.exe"])
pruefe("Spotify (spielt) wird mitgezogen", hoerbar(st)["spotify.exe"],
       vor["spotify.exe"])
pruefe("Discord (still) unberuehrt", st["a"]["discord.exe"], 1.0)
pruefe("kein lauter Zwischenschritt", kein_knall(st), "ok")

e, st = bauen("carry", 0.0, {"spotify.exe": 0.2})
vor = hoerbar(st)
e._pegel_angleichen("master", ["spotify.exe"])
pruefe("App -> Gesamt gleich laut", hoerbar(st), vor)
pruefe("kein lauter Zwischenschritt", kein_knall(st), "ok")

e, st = bauen("none", -13.8, {"spotify.exe": 0.6})
e._pegel_angleichen("apps", ["spotify.exe"])
pruefe("Modus „nichts aendern“ fasst nichts an", st["a"]["spotify.exe"], 0.6)

print("\n=== Profile (neu) ===")
e, st = bauen("none", 0.0, {"spotify.exe": 1.0, "chrome.exe": 1.0})
e._profil_anwenden({"master": 0.3, "apps": {"spotify.exe": 0.2,
                                            "chrome.exe": 0.8}})
pruefe("Spotify auf 20 %", round(st["a"]["spotify.exe"], 3), 0.2)
pruefe("Chrome auf 80 %", round(st["a"]["chrome.exe"], 3), 0.8)
pruefe("kein lauter Zwischenschritt", kein_knall(st), "ok")

print("\n=== Namen und Farben ===")
pruefe("Programmname huebsch", huebscher_name("Spotify.exe"), "Spotify")
pruefe("unbekannt wird lesbar", huebscher_name("wispr flow.exe"), "Wispr flow")
t = Theme("dark", "violet")
pruefe("Akzent dunkel", t.accent, "#7C5CFF")
t.set("light", "amber")
pruefe("Akzent hell", t.accent, "#D97706")
pruefe("Stilvorlage ist gefuellt", len(t.qss()) > 2000, True)
pruefe("alle Farben erreichbar",
       all(t.accent_of(p[0]) for p in PALETTE), True)

print("\n=== Einstellungen ===")
cfg = config.load()
pruefe("Profile-Feld vorhanden", isinstance(cfg["profiles"], dict), True)
pruefe("Live-Pegel-Schalter vorhanden", "meters" in cfg, True)
pruefe("alte Einstellungen uebernommen", cfg["speed"] > 0, True)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
