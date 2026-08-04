"""Prueft die Kette vom Audio-Thread bis in den Regler."""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)
import ctypes
import subprocess
import time

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
HIER = _TESTS
sys.path.insert(0, _PROJEKT)

from PySide6.QtCore import QTimer                              # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(HIER, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.widgets import VolumeSlider                       # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

PY = r"C:\Users\Luis\AppData\Local\Programs\Python\Python313\python.exe"
fehler = []
gesehen = {"meldungen": 0, "max_wert": 0.0, "max_halten": 0.0}

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()

echt = f._meter_uebernehmen


def mitschreiben(werte):
    gesehen["meldungen"] += 1
    if werte:
        gesehen["max_wert"] = max(gesehen["max_wert"], max(werte.values()))
    echt(werte)
    for row in f.rows.values():
        gesehen["max_halten"] = max(gesehen["max_halten"], row.regler._halten)


f._meter_uebernehmen = mitschreiben
f.meters_bereit.disconnect()
f.meters_bereit.connect(mitschreiben)

subprocess.Popen([PY, os.path.join(_TESTS, "hilfsmittel_ton.py"), "6"])


def auswerten():
    print("Messungen empfangen:      ", gesehen["meldungen"])
    print("groesster roher Pegel:     {:.3f}".format(gesehen["max_wert"]))
    print("groesster Balkenausschlag: {:.3f}".format(gesehen["max_halten"]))
    ok = True
    if gesehen["meldungen"] < 10:
        print("  FEHL zu wenige Messungen"); ok = False
    else:
        print("  OK   Messungen kommen laufend an")
    if gesehen["max_wert"] <= 0.005:
        print("  FEHL kein Pegel erkannt"); ok = False
    else:
        print("  OK   Pegel erkannt")
    if gesehen["max_halten"] <= 0.05:
        print("  FEHL Balken schlaegt nicht aus"); ok = False
    else:
        print("  OK   Balken schlaegt sichtbar aus")
    # Wurzelskala: aus 0,08 roh muessen ~0,28 werden
    print("\nWurzelskala: roh {:.3f} -> angezeigt {:.3f}".format(
        gesehen["max_wert"], gesehen["max_halten"]))
    print("\n{}".format("Alles gruen." if ok else "Fehler!"))
    f._beenden()
    app.exit(0 if ok else 1)


QTimer.singleShot(6000, auswerten)
sys.exit(app.exec())
