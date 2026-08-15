# -*- coding: utf-8 -*-
"""Was ein eigenes Fenster ist, muss deckend sein.

Seit die Flaechen Milchglas sind, leben sie davon, dass der Fenstergrund mit
seinem farbigen Licht durch sie hindurchscheint. Alles, was ein eigenes
Fenster ist – die Einblendung, der Auswahldialog –, hat darunter aber
nichts und waere fast durchsichtig. Genau das ist zweimal passiert.

Geprueft wird deshalb die Deckkraft in der Mitte solcher Flaechen.
"""
import json
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                    # noqa: E402
ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from PySide6.QtGui import QColor                                 # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

from volumix import config                                       # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")
json.dump({"sprache": "de", "accent": "violet", "mode": "dark"},
          open(config.CONFIG_PATH, "w", encoding="utf-8"))

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


def deckkraft(bild, ax, ay):
    """Alphawert an einer Stelle, 0 bis 255."""
    x = int(bild.width() * ax)
    y = int(bild.height() * ay)
    return QColor(bild.pixelColor(x, y)).alpha()


app = QApplication(sys.argv)
from volumix.osd import Osd                                      # noqa: E402
from volumix.theme import Theme                                  # noqa: E402
from volumix.window import AppsDialog, MainWindow                # noqa: E402

print("=== Einblendung ueber dem Schreibtisch ===")
th = Theme("dark", "violet")
osd = Osd(th)
osd.einstellen(45, 50, 88)
osd.zeigen([("spotify.exe", None, "Spotify")], 45)
for _ in range(30):
    app.processEvents()
    time.sleep(0.02)
bild = osd.grab().toImage()
osd.hide()
mitte = deckkraft(bild, 0.5, 0.5)
pruefe("Mitte ist deckend", mitte >= 250, True, "Alpha {}".format(mitte))
links = deckkraft(bild, 0.12, 0.5)
pruefe("auch am Rand des Inhalts", links >= 250, True,
       "Alpha {}".format(links))

print("\n=== Auswahldialog ===")
f = MainWindow()
f.show()
for _ in range(120):
    app.processEvents()
    if len(f.rows) > 1:
        break
    time.sleep(0.05)
f._takt.stop()
d = AppsDialog(f)
d.show()
for _ in range(40):
    app.processEvents()
    time.sleep(0.02)
bild = d.grab().toImage()
mitte = deckkraft(bild, 0.5, 0.5)
pruefe("Mitte ist deckend", mitte >= 250, True, "Alpha {}".format(mitte))
oben = deckkraft(bild, 0.5, 0.12)
pruefe("Kopfbereich ist deckend", oben >= 250, True, "Alpha {}".format(oben))
d.reject()
f._beenden()

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
