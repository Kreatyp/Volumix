# -*- coding: utf-8 -*-
"""„Pegel mitnehmen": Beim Umschalten muss es gleich laut bleiben.

Gemeldet wurde: „wenn ich von Gesamt auf Spotify wechsle, ist Spotify
deutlich lauter" – und zwar sofort beim Anhaken. Nachgestellt mit
Attrappen statt echter Tonsitzungen: Nur so lassen sich Faelle pruefen, die
am echten Rechner gerade nicht anliegen – vor allem eine App mit zwei
Sitzungen auf verschiedenen Staenden. Genau daran lag es: Gelesen wurde die
erste Sitzung, gesetzt wurden alle.

Gerechnet wird in Lautheit: Amplitude der Sitzung mal Daempfung der
Gesamtlautstaerke. Die muss vor und nach dem Umschalten dieselbe sein.
"""
import math
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.audio import AudioEngine                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


class Sitzung:
    """Attrappe einer Tonsitzung – merkt sich nur ihre Amplitude."""

    def __init__(self, amp):
        self.amp = float(amp)

    def GetMasterVolume(self):          # noqa: N802  (Name kommt von Windows)
        return self.amp

    def SetMasterVolume(self, wert, _):  # noqa: N802
        self.amp = float(wert)


def engine_mit(sitzungen, master_gain):
    """Eine Engine, deren Geraet und Sitzungen Attrappen sind."""
    e = AudioEngine()
    e.switch_mode = "carry"
    zustand = {"gain": float(master_gain)}

    e._by_key = lambda max_alter=2.0: sitzungen
    e._spielende = lambda ausser=(): {}
    e.master_gain = lambda: zustand["gain"]
    e.set_master_gain = lambda g: zustand.__setitem__("gain", float(g))
    e.set_master_scalar = lambda w: zustand.__setitem__(
        "gain", 1.0 if w >= 1.0 else float(w))
    e._setzen_lassen = lambda sekunden=0.0: None
    return e, zustand


def lautheit(sitzungen, zustand):
    """Was je Sitzung am Ohr ankommt."""
    return [s.amp * zustand["gain"]
            for liste in sitzungen.values() for s in liste]


def abstand(vorher, nachher):
    """Groesster Unterschied in Dezibel."""
    weit = 0.0
    for a, b in zip(vorher, nachher):
        if a <= 0 or b <= 0:
            continue
        weit = max(weit, abs(20.0 * math.log10(b / a)))
    return weit


print("=== Eine App, eine Sitzung ===")
s = {"spotify.exe": [Sitzung(1.0)]}
e, z = engine_mit(s, 0.2085)
vorher = lautheit(s, z)
e._pegel_angleichen("apps", ["spotify.exe"])
nachher = lautheit(s, z)
pruefe("gleich laut nach dem Anhaken", abstand(vorher, nachher) < 0.1,
       "{:.2f} dB, Amplitude {:.3f}".format(abstand(vorher, nachher),
                                            s["spotify.exe"][0].amp))
e._pegel_angleichen("master", ["spotify.exe"])
pruefe("und auf dem Rueckweg auch",
       abstand(vorher, lautheit(s, z)) < 0.1,
       "{:.2f} dB".format(abstand(vorher, lautheit(s, z))))

print("\n=== Eine App mit zwei Sitzungen auf verschiedenen Staenden ===")
# Genau der gemeldete Fall: Die zweite Sitzung steht leiser als die erste.
s = {"spotify.exe": [Sitzung(1.0), Sitzung(0.2)]}
e, z = engine_mit(s, 0.5)
vorher = lautheit(s, z)
e._pegel_angleichen("apps", ["spotify.exe"])
nachher = lautheit(s, z)
pruefe("keine Sitzung wird lauter", abstand(vorher, nachher) < 0.1,
       "{:.2f} dB, Amplituden {}".format(
           abstand(vorher, nachher),
           [round(x.amp, 3) for x in s["spotify.exe"]]))
pruefe("das Verhaeltnis bleibt",
       abs(s["spotify.exe"][0].amp / s["spotify.exe"][1].amp - 5.0) < 0.01)

print("\n=== Rueckweg mit zwei Sitzungen ===")
s = {"spotify.exe": [Sitzung(0.3), Sitzung(0.06)]}
e, z = engine_mit(s, 1.0)
vorher = lautheit(s, z)
e._pegel_angleichen("master", ["spotify.exe"])
nachher = lautheit(s, z)
pruefe("gleich laut", abstand(vorher, nachher) < 0.1,
       "{:.2f} dB, Daempfung {:.3f}, Amplituden {}".format(
           abstand(vorher, nachher), z["gain"],
           [round(x.amp, 3) for x in s["spotify.exe"]]))
pruefe("die lauteste Sitzung steht offen",
       abs(max(x.amp for x in s["spotify.exe"]) - 1.0) < 0.01)

print("\n=== Zwei Apps gleichzeitig ===")
s = {"spotify.exe": [Sitzung(0.8)], "discord.exe": [Sitzung(0.4)]}
e, z = engine_mit(s, 0.3)
vorher = lautheit(s, z)
e._pegel_angleichen("apps", ["spotify.exe", "discord.exe"])
pruefe("beide bleiben, wie sie waren",
       abstand(vorher, lautheit(s, z)) < 0.1,
       "{:.2f} dB".format(abstand(vorher, lautheit(s, z))))

print("\n=== Ohne Sitzung passiert nichts ===")
s = {"spotify.exe": []}
e, z = engine_mit(s, 0.25)
e._pegel_angleichen("apps", ["spotify.exe"])
pruefe("die Gesamtlautstaerke bleibt stehen", abs(z["gain"] - 0.25) < 0.001,
       "{:.3f}".format(z["gain"]))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
