"""Faehrt die Regler der Einblendung durch – der Absturzfall von Luis.

Prueft ausserdem, dass die Einblendung wirklich gezeichnet werden kann: ein
Fehler im paintEvent wuerde sonst erst im Betrieb auffallen.
"""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)
import ctypes

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
HIER = _TESTS
sys.path.insert(0, _PROJEKT)

from PySide6.QtGui import QImage, QPainter                     # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(HIER, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.window import MainWindow                          # noqa: E402

fehler = []


def pruefe(name, fn):
    """Fuehrt `fn` aus und meldet, wenn es scheitert."""
    try:
        fn()
        print("  OK   {}".format(name))
    except Exception as e:
        fehler.append(name)
        print("  FEHL {}\n         {}: {}".format(name, type(e).__name__, e))


def zeichnen_kann(osd):
    """Zeichnet die Einblendung in ein Bild – deckt Fehler im paintEvent auf."""
    bild = QImage(osd.width(), osd.height(), QImage.Format.Format_ARGB32)
    bild.fill(0)
    osd.render(bild)


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
f._seite(1)
app.processEvents()

print("\n=== Regler „Groesse“ (Luis' Absturz) ===")
for wert in (10, 25, 45, 70, 100):
    pruefe("Groesse auf {} %".format(wert),
           lambda w=wert: (f._osd_groesse(w), app.processEvents(),
                           zeichnen_kann(f.osd)))

print("\n=== Regler „Position“ ===")
for wert in (0, 50, 100):
    pruefe("waagerecht {} %".format(wert),
           lambda w=wert: (f._osd_x(w), app.processEvents(),
                           zeichnen_kann(f.osd)))
    pruefe("senkrecht {} %".format(wert),
           lambda w=wert: (f._osd_y(w), app.processEvents(),
                           zeichnen_kann(f.osd)))

print("\n=== Einblendung im Betrieb ===")
pruefe("mit echten Zielen", lambda: (f._osd_zeigen(), app.processEvents(),
                                     zeichnen_kann(f.osd)))
pruefe("ohne Symbolpfad", lambda: (
    f.osd.zeigen([("spotify.exe", None, "Spotify")], 42),
    app.processEvents(), zeichnen_kann(f.osd)))
pruefe("mehrere Apps", lambda: (
    f.osd.zeigen([("a.exe", None, "A"), ("b.exe", None, "B"),
                  ("c.exe", None, "C")], 77),
    app.processEvents(), zeichnen_kann(f.osd)))
pruefe("mit Ersatztext", lambda: (
    f.osd.zeigen([("x.exe", None, "X")], None, text="keine Wiedergabe"),
    app.processEvents(), zeichnen_kann(f.osd)))

print("\n=== Falsche Eingaben duerfen nicht abstuerzen ===")
pruefe("Bild statt Angaben (der alte Fehler)", lambda: (
    f.osd.zeigen([object()], 50), app.processEvents(),
    zeichnen_kann(f.osd)))
pruefe("leere Liste", lambda: (f.osd.zeigen([], 50), app.processEvents(),
                               zeichnen_kann(f.osd)))
pruefe("None", lambda: (f.osd.zeigen(None, 50), app.processEvents(),
                        zeichnen_kann(f.osd)))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Fehler: {}".format(len(fehler), ", ".join(fehler))))
f._beenden()
sys.exit(1 if fehler else 0)
