# -*- coding: utf-8 -*-
"""Zwei Geschwindigkeiten: eine fuer die Gesamtlautstaerke, eine fuer Apps."""
import json
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

from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.audio import AudioEngine                          # noqa: E402
from volumix.config import MASTER_KEY                          # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


print("\n=== Werkseinstellung ===")
pruefe("beide Werte vorhanden",
       "speed" in config.DEFAULTS and "speed_apps" in config.DEFAULTS)
pruefe("Apps ab Werk feiner als Gesamt",
       config.DEFAULTS["speed_apps"] < config.DEFAULTS["speed"],
       "{} gegen {}".format(config.DEFAULTS["speed_apps"],
                            config.DEFAULTS["speed"]))

print("\n=== Alte Einstellungsdatei ohne den neuen Wert ===")
# Wer von frueher kommt, hatte nur „speed“. Der Wert muss fuer beides gelten,
# sonst regelt es nach dem Update ploetzlich anders als gewohnt.
alt = os.path.join(_TEST, "alt.json")
with open(alt, "w", encoding="utf-8") as f:
    json.dump({"speed": 70, "active": True}, f)
merk = config.CONFIG_PATH
config.CONFIG_PATH = alt
geladen = config.load()
config.CONFIG_PATH = merk
pruefe("Gesamt bleibt beim alten Wert", geladen["speed"] == 70,
       str(geladen["speed"]))
pruefe("Apps uebernehmen denselben Wert", geladen["speed_apps"] == 70,
       str(geladen["speed_apps"]))
os.remove(alt)

print("\n=== Die Audio-Schicht waehlt die richtige Schrittweite ===")
motor = AudioEngine()          # nicht gestartet – wir rufen direkt hinein
motor.speed_step = 4.0         # Gesamt: grob
motor.speed_step_apps = 1.0    # Apps: fein
motor.speed_curve = False      # erst ohne Pegelanpassung pruefen
motor._by_key = lambda: {}
_pegel = {"wert": 50.0}
motor.prozent = lambda key, by=None: _pegel["wert"]


def eine_rastung(ziele, start=50.0, delta=1):
    _pegel["wert"] = start
    motor.targets = set(ziele)
    motor._ziel.clear()
    motor._jetzt.clear()
    motor._scroll_anwenden(delta)
    return {k: round(v, 2) for k, v in motor._ziel.items()}


nur_master = eine_rastung([MASTER_KEY])
pruefe("Gesamt springt um 4 Punkte", nur_master.get(MASTER_KEY) == 54.0,
       str(nur_master))
nur_apps = eine_rastung(["spotify.exe"])
pruefe("eine App nur um 1 Punkt", nur_apps.get("spotify.exe") == 51.0,
       str(nur_apps))
mehrere = eine_rastung(["spotify.exe", "chrome.exe"])
pruefe("mehrere Apps ebenfalls fein",
       all(v == 51.0 for v in mehrere.values()), str(mehrere))

print("\n=== Leise feiner regeln ===")
motor.speed_curve = True
leise = eine_rastung(["spotify.exe"], start=5.0)["spotify.exe"] - 5.0
mitte = eine_rastung(["spotify.exe"], start=50.0)["spotify.exe"] - 50.0
laut = eine_rastung(["spotify.exe"], start=90.0)["spotify.exe"] - 90.0
pruefe("in der Mitte bleibt der eingestellte Schritt",
       abs(mitte - 1.0) < 0.01, "{:.2f} Punkte".format(mitte))
pruefe("leise deutlich kleiner", leise < mitte * 0.45,
       "{:.2f} gegen {:.2f} Punkte".format(leise, mitte))
pruefe("laut etwas groesser", laut > mitte * 1.4,
       "{:.2f} gegen {:.2f} Punkte".format(laut, mitte))
pruefe("nach unten genauso", eine_rastung(["spotify.exe"], 5.0, -1)["spotify.exe"] > 5.0 - mitte,
       "bei 5 % bremst es auch abwaerts")

motor.speed_curve = False
ohne = eine_rastung(["spotify.exe"], start=5.0)["spotify.exe"] - 5.0
pruefe("ausgeschaltet wieder ueberall gleich", abs(ohne - 1.0) < 0.01,
       "{:.2f} Punkte".format(ohne))

print("\n=== Einstellungen im Fenster ===")
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
for _ in range(80):
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)

print("\n--- Reglerskala ---")
langsam = f._schrittweite(10)
schnell = f._schrittweite(100)
pruefe("100 % bleibt bei 4,2 Punkten", abs(schnell - 4.2) < 0.01,
       "{:.2f}".format(schnell))
pruefe("10 % ist deutlich langsamer als frueher (war 0,8)", langsam <= 0.25,
       "{:.2f} Punkte".format(langsam))
# Gleiche Reglerwege sollen sich gleich stark anfuehlen, nicht gleich viel
# Prozentpunkte bedeuten – deshalb waechst die Skala geometrisch.
v = [f._schrittweite(p) for p in (10, 40, 70, 100)]
paare = [v[i + 1] / v[i] for i in range(3)]
pruefe("Skala waechst gleichmaessig (nicht linear)",
       max(paare) - min(paare) < 0.01,
       "Faktoren " + ", ".join("{:.2f}".format(x) for x in paare))

f._tempo_setzen(100)
f._tempo_apps_setzen(10)
app.processEvents()
pruefe("Gesamt gespeichert", f.cfg["speed"] == 100, str(f.cfg["speed"]))
pruefe("Apps gespeichert", f.cfg["speed_apps"] == 10, str(f.cfg["speed_apps"]))
pruefe("Schrittweiten unterscheiden sich",
       f.engine.speed_step > f.engine.speed_step_apps,
       "{:.2f} gegen {:.2f}".format(f.engine.speed_step,
                                    f.engine.speed_step_apps))
pruefe("Anzeige folgt", f.tempo_wert.text() == "100 %"
       and f.tempo_apps_wert.text() == "10 %",
       "{} / {}".format(f.tempo_wert.text(), f.tempo_apps_wert.text()))
pruefe("auf der Platte gelandet", config.load()["speed_apps"] == 10)

f._tempo_kurve_setzen(False)
pruefe("Kurve abschaltbar",
       not f.cfg["speed_curve"] and not f.engine.speed_curve)
f._tempo_kurve_setzen(True)
pruefe("und wieder an",
       f.cfg["speed_curve"] and f.engine.speed_curve
       and config.load()["speed_curve"])

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
