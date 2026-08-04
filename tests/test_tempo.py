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
motor._by_key = lambda: {}
motor.prozent = lambda key, by=None: 50.0


def eine_rastung(ziele):
    motor.targets = set(ziele)
    motor._ziel.clear()
    motor._jetzt.clear()
    motor._scroll_anwenden(1)
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

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
