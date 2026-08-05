# -*- coding: utf-8 -*-
"""Die Geschwindigkeit: eine Einstellung, geometrisch verteilte Skala."""
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


print("\n=== Nur noch eine Geschwindigkeit ===")
pruefe("ein Wert in der Werkseinstellung", "speed" in config.DEFAULTS)
weg = [k for k in ("speed_apps", "speed_curve") if k in config.DEFAULTS]
pruefe("die alten Zusatzwerte sind fort", not weg, ", ".join(weg))

print("\n=== Schrittweite gilt fuer alles ===")
motor = AudioEngine()          # nicht gestartet – wir rufen direkt hinein
motor.speed_step = 3.0
motor._by_key = lambda: {}
_stand = {"wert": 50.0}
motor.prozent = lambda key, by=None: _stand["wert"]


def eine_rastung(ziele, start=50.0, delta=1):
    _stand["wert"] = start
    motor.targets = set(ziele)
    motor._ziel.clear()
    motor._jetzt.clear()
    motor._scroll_anwenden(delta)
    return {k: round(v, 2) for k, v in motor._ziel.items()}


master = eine_rastung([MASTER_KEY])[MASTER_KEY] - 50.0
app = eine_rastung(["spotify.exe"])["spotify.exe"] - 50.0
pruefe("Gesamt bewegt sich um den eingestellten Schritt",
       abs(master - 3.0) < 0.01, "{:.2f}".format(master))
pruefe("eine App genauso weit", abs(app - master) < 0.01,
       "{:.2f} gegen {:.2f}".format(app, master))
leise = eine_rastung(["spotify.exe"], start=5.0)["spotify.exe"] - 5.0
pruefe("und bei leisem Pegel ebenso – die Kurve steckt in der Skala",
       abs(leise - 3.0) < 0.01, "{:.2f}".format(leise))

print("\n=== Reglerskala ===")
app_qt = QApplication(sys.argv)
app_qt.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
for _ in range(80):
    app_qt.processEvents()
    if f.rows:
        break
    time.sleep(0.05)

langsam = f._schrittweite(10)
schnell = f._schrittweite(100)
pruefe("100 % bleibt bei 4,2 Punkten", abs(schnell - 4.2) < 0.01,
       "{:.2f}".format(schnell))
pruefe("10 % bleibt fein", langsam <= 0.25, "{:.2f} Punkte".format(langsam))
# Gleiche Reglerwege sollen sich gleich stark anfuehlen, nicht gleich viel
# Prozentpunkte bedeuten – deshalb waechst die Skala geometrisch.
v = [f._schrittweite(p) for p in (10, 40, 70, 100)]
paare = [v[i + 1] / v[i] for i in range(3)]
pruefe("Skala waechst gleichmaessig (nicht linear)",
       max(paare) - min(paare) < 0.01,
       "Faktoren " + ", ".join("{:.2f}".format(x) for x in paare))

print("\n=== Einstellung im Fenster ===")
f._tempo_setzen(63)
app_qt.processEvents()
pruefe("krumme Werte moeglich (kein Einrasten)", f.cfg["speed"] == 63,
       str(f.cfg["speed"]))
pruefe("Anzeige folgt", f.tempo_wert.text() == "63 %", f.tempo_wert.text())
pruefe("an die Audio-Schicht durchgereicht",
       abs(f.engine.speed_step - f._schrittweite(63)) < 0.001)
pruefe("auf der Platte gelandet", config.load()["speed"] == 63)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
