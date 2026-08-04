"""Prueft Einblendung (Schaerfe, Nachlauf) und das blasse Symbol bei stumm."""
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

from volumix import icons                                      # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

PY = r"C:\Users\Luis\AppData\Local\Programs\Python\Python313\python.exe"
fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
app.processEvents()

print("\n=== Symbole in der Einblendung ===")
# In der Einblendung werden Symbole in ~42 px gebraucht (Groesse 45 %)
gross = icons.exe_icon(r"C:\Windows\explorer.exe", 42, 1.5)
klein = icons.exe_icon(r"C:\Windows\explorer.exe", 32, 1.5)
if gross is not None and klein is not None:
    pruefe("Symbol wird in der Zielgroesse geholt",
           gross.width() > klein.width(),
           "{} px statt {} px".format(gross.width(), klein.width()))
    pruefe("Bildpunktdichte beruecksichtigt",
           abs(gross.devicePixelRatio() - 1.5) < 0.01)

print("\n=== Nachlauf des Balkens ===")
osd = f.osd
osd.einstellen(45, 50, 88)
osd.zeigen([("#master", None, "Gesamt")], 20)
app.processEvents()
pruefe("frisch eingeblendet: sofort auf dem Wert", osd._gezeigt == 20.0,
       "ist {}".format(osd._gezeigt))
osd.zeigen([("#master", None, "Gesamt")], 80)
app.processEvents()
pruefe("springt nicht sofort auf den neuen Wert", osd._gezeigt < 80.0,
       "ist {:.1f}".format(osd._gezeigt))
for _ in range(30):
    app.processEvents()
    time.sleep(0.012)
pruefe("erreicht den Wert nach der Bewegung", abs(osd._gezeigt - 80.0) < 1.0,
       "ist {:.1f}".format(osd._gezeigt))
osd.hide()

print("\n=== Schriftgroesse in der Einblendung ===")
quelle = open(os.path.join(_PROJEKT, "volumix", "osd.py"),
              encoding="utf-8").read()
pruefe("Zahl deutlich groesser als vorher", 'QFont("Segoe UI", int(14 * f))'
       in quelle)

print("\n=== Blasses Symbol bei stumm ===")
zeilen = list(f.rows.values())
if zeilen:
    z = zeilen[-1]
    z.set_muted(False)
    app.processEvents()
    hell = z.symbol.pixmap().toImage()
    z.set_muted(True)
    app.processEvents()
    blass = z.symbol.pixmap().toImage()

    def mittlere_deckkraft(img):
        summe = anzahl = 0
        for y in range(0, img.height(), 3):
            for x in range(0, img.width(), 3):
                summe += img.pixelColor(x, y).alpha()
                anzahl += 1
        return summe / max(1, anzahl)

    a_hell = mittlere_deckkraft(hell)
    a_blass = mittlere_deckkraft(blass)
    pruefe("Symbol wird blasser", a_blass < a_hell * 0.6,
           "{:.0f} statt {:.0f}".format(a_blass, a_hell))
    z.set_muted(False)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
