# -*- coding: utf-8 -*-
"""Mausrad ueber einer Zeile: der Wert darf danach nicht zurueckspringen.

Der Fehler: Die App liest die echten Pegel im Takt. Ein Durchlauf, der schon
unterwegs war, schrieb den alten Wert zurueck – der Regler sprang zurueck.
"""
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

for _ in range(120):                       # auf die erste Bestandsaufnahme warten
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)

zeilen = [r for r in f.rows.values() if not r.muted]
pruefe("Mixer-Zeilen vorhanden", bool(zeilen))

if zeilen:
    z = zeilen[-1]

    def raddrehen(stufen, ziel=None):
        """Rad ueber `ziel` drehen – wie im Betrieb, ueber die Ereigniskette.

        Wichtig: NICHT z.wheelEvent() direkt rufen. Der Regler faengt das
        Ereignis sonst ab, und genau das war der Fehler.
        """
        ziel = ziel or z
        e = QWheelEvent(QPoint(10, 10), ziel.mapToGlobal(QPoint(10, 10)),
                        QPoint(0, 0), QPoint(0, 120 * stufen),
                        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        app.sendEvent(ziel, e)
        app.processEvents()

    print("\n=== Rad ueber dem Regler selbst ===")
    gemeldet = []
    z.volume_changed.connect(
        lambda k, w, fertig: gemeldet.append((w, fertig)))
    z.regler.setValue(50)
    z._selbst_gestellt = 0.0
    app.processEvents()
    raddrehen(2, ziel=z.regler)
    pruefe("Wert geaendert", z.regler.value() != 50,
           "ist {}".format(z.regler.value()))
    pruefe("Aenderung wird gemeldet (Lautstaerke wird gesetzt)",
           bool(gemeldet), "{} Meldungen".format(len(gemeldet)))
    if gemeldet:
        pruefe("letzte Meldung ist endgueltig", gemeldet[-1][1] is True)
        pruefe("gemeldeter Wert passt zum Regler",
               round(gemeldet[-1][0] * 100) == z.regler.value())

    print("\n=== Rad neben dem Regler laesst die Lautstaerke in Ruhe ===")
    # Frueher schluckte die ganze Zeile das Rad. Dadurch liess sich die Liste
    # kaum scrollen, ohne unterwegs Lautstaerken zu verstellen.
    z.regler.setValue(50)
    z._selbst_gestellt = 0.0
    app.processEvents()
    e_zeile = QWheelEvent(QPoint(10, 10), z.mapToGlobal(QPoint(10, 10)),
                          QPoint(0, 0), QPoint(0, 360),
                          Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    app.sendEvent(z, e_zeile)
    app.processEvents()
    pruefe("Wert unveraendert", z.regler.value() == 50,
           "ist {}".format(z.regler.value()))
    pruefe("Ereignis wird weitergereicht (Liste kann scrollen)",
           not e_zeile.isAccepted())

    print("\n=== Wert bleibt nach dem Scrollen stehen ===")
    z.regler.setValue(50)
    z._selbst_gestellt = 0.0
    app.processEvents()
    raddrehen(3, ziel=z.regler)
    gewuenscht = z.regler.value()
    pruefe("Rad hat den Wert geaendert", gewuenscht != 50,
           "ist {}".format(gewuenscht))

    # Genau der Fall: ein Durchlauf mit dem ALTEN Wert kommt hinterher
    z.aktualisieren({"key": z.key, "name": z._name_text, "volume": 0.50,
                     "exe": z._exe, "muted": False})
    app.processEvents()
    pruefe("alter Wert wird nicht zurueckgeschrieben",
           z.regler.value() == gewuenscht,
           "ist {}, erwartet {}".format(z.regler.value(), gewuenscht))

    print("\n=== Nach der Sperrzeit zaehlt die Wirklichkeit wieder ===")
    z._selbst_gestellt = time.monotonic() - 1.5      # Sperre abgelaufen
    z.aktualisieren({"key": z.key, "name": z._name_text, "volume": 0.30,
                     "exe": z._exe, "muted": False})
    app.processEvents()
    pruefe("Aenderung von aussen kommt an", z.regler.value() == 30,
           "ist {}".format(z.regler.value()))

    print("\n=== Auch beim Ziehen mit der Maus ===")
    z.regler.setValue(70)
    z._geschoben(70)
    app.processEvents()
    z.aktualisieren({"key": z.key, "name": z._name_text, "volume": 0.30,
                     "exe": z._exe, "muted": False})
    app.processEvents()
    pruefe("gezogener Wert bleibt stehen", z.regler.value() == 70,
           "ist {}".format(z.regler.value()))

print("\n=== In den Einstellungen darf das Rad nichts verstellen ===")
# Dort soll gescrollt werden – ein versehentlich verschobener Regler waere
# aergerlich, weil man die Aenderung leicht uebersieht.
from volumix.widgets import Slider                             # noqa: E402
f._seite(1)
app.processEvents()
regler = [s for s in f.einst_seite.findChildren(Slider)]
pruefe("Regler in den Einstellungen gefunden", bool(regler),
       "{} Stueck".format(len(regler)))
if regler:
    s = regler[0]
    vorher = s.value()
    e = QWheelEvent(QPoint(10, 10), s.mapToGlobal(QPoint(10, 10)),
                    QPoint(0, 0), QPoint(0, 360),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    app.sendEvent(s, e)
    app.processEvents()
    pruefe("Wert unveraendert", s.value() == vorher,
           "war {}, ist {}".format(vorher, s.value()))
    pruefe("Ereignis wird weitergereicht (Seite kann scrollen)",
           not e.isAccepted())

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
