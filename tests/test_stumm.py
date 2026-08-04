# -*- coding: utf-8 -*-
"""0 % schaltet stumm – und man kommt da per Rad auch wieder heraus."""
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

from PySide6.QtCore import QPoint, Qt                          # noqa: E402
from PySide6.QtGui import QWheelEvent                          # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix import icons                                      # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

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
for _ in range(120):
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)

zeilen = [r for r in f.rows.values() if r.key != "#master"]
pruefe("Mixer-Zeilen vorhanden", bool(zeilen))

if zeilen:
    z = zeilen[-1]

    def raddrehen(stufen):
        e = QWheelEvent(QPoint(10, 10), z.regler.mapToGlobal(QPoint(10, 10)),
                        QPoint(0, 0), QPoint(0, 120 * stufen),
                        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        app.sendEvent(z.regler, e)
        app.processEvents()

    print("\n=== Regler auf 0 schaltet stumm ===")
    z.set_muted(False)
    z.regler.setValue(30)
    app.processEvents()
    pruefe("Ausgangslage: nicht stumm", not z.muted)
    # so wie beim Ziehen mit der Maus: Regler auf 0, dann loslassen
    z.regler.setValue(0)
    z._geschoben(0)
    z._losgelassen()
    app.processEvents()
    pruefe("bei 0 % ist stumm", z.muted)
    pruefe("Anzeige zeigt „stumm“", z.prozent.text() == "stumm",
           repr(z.prozent.text()))

    print("\n=== Aus dem stummen Zustand wieder heraus ===")
    raddrehen(2)
    app.processEvents()
    pruefe("Rad dreht trotz stumm hoch", z.regler.value() > 0,
           "ist {}".format(z.regler.value()))
    pruefe("Stummschaltung ist aufgehoben", not z.muted)
    pruefe("Anzeige zeigt wieder Prozent", z.prozent.text().endswith("%"),
           repr(z.prozent.text()))

    print("\n=== Daumenrad-Weg (ueber die Audio-Schicht) ===")
    z.set_muted(False)
    z.regler.setValue(20)
    app.processEvents()
    f._volume_uebernehmen(z.key, 0)
    app.processEvents()
    pruefe("auch hier schaltet 0 % stumm", z.muted)
    f._volume_uebernehmen(z.key, 15)
    app.processEvents()
    pruefe("und hebt sich beim Hochfahren auf", not z.muted)
    z.set_muted(False)

print("\n=== Symbol fuer stumm ===")
stumm_bild = icons.speaker_pixmap(48, 0.0, "#FFFFFF", 1.0, stumm=True).toImage()
stufen = [icons.speaker_pixmap(48, p, "#FFFFFF", 1.0, stumm=False).toImage()
          for p in (0.0, 0.2, 0.5, 0.9)]
pruefe("unterscheidet sich von allen Pegelstufen",
       all(stumm_bild.constBits().tobytes() != s.constBits().tobytes()
           for s in stufen))


def deckung_rechts(img):
    """Wie viel Farbe liegt rechts vom Kegel? Dort sitzt das Kreuz."""
    summe = 0
    for x in range(int(img.width() * 0.58), img.width()):
        for y in range(img.height()):
            summe += img.pixelColor(x, y).alpha()
    return summe


# Das Kreuz ist deutlich kraeftiger als die blassen Wellen bei Pegel 0
d_stumm = deckung_rechts(stumm_bild)
d_leise = deckung_rechts(stufen[0])
pruefe("Kreuz ist kraeftiger als die schwachen Wellen",
       d_stumm > d_leise * 1.8,
       "stumm {} gegen {}".format(d_stumm, d_leise))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
