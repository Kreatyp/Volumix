# -*- coding: utf-8 -*-
"""Der Titelstreifen in der Taskleiste.

Geprueft wird, was ohne echte Taskleiste pruefbar ist: das Hochrechnen der
Spielposition zwischen zwei Meldungen, die Zeitangabe, das Zeichnen des
Balkens, und dass der Streifen verschwindet, wenn nichts laeuft. Dazu die
Suche nach dem freien Platz – die liefert auf diesem Rechner echte Werte.
"""
import json
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402
from ctypes import wintypes                                    # noqa: E402
ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from PySide6.QtCore import Qt                                  # noqa: E402
from PySide6.QtGui import QColor                               # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config-leiste.json")
json.dump({"sprache": "de", "accent": "violet", "mode": "dark"},
          open(config.CONFIG_PATH, "w", encoding="utf-8"))

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


app = QApplication(sys.argv)
from volumix.theme import Theme                                # noqa: E402
from volumix import zeitleiste                                  # noqa: E402
from volumix.zeitleiste import (Zeitleiste, _zeit,              # noqa: E402
                                taskleiste_platz)

th = Theme("dark", "violet")

print("=== Zeitangabe ===")
pruefe("Sekunden", _zeit(7) == "0:07", _zeit(7))
pruefe("Minuten", _zeit(134.9) == "2:14", _zeit(134.9))
pruefe("lange Titel", _zeit(3725) == "62:05", _zeit(3725))
pruefe("nichts wird nicht negativ", _zeit(-5) == "0:00", _zeit(-5))

print("\n=== Position zwischen zwei Meldungen ===")
z = Zeitleiste(th)
z.zeit_setzen(100.0, 200.0, True)
z._gemeldet -= 3.0          # so tun, als waere die Meldung 3 s alt
pruefe("laeuft weiter", 102.9 < z.position() < 103.1,
       "{:.2f}".format(z.position()))
z.zeit_setzen(100.0, 200.0, False)
z._gemeldet -= 3.0
pruefe("pausiert steht still", abs(z.position() - 100.0) < 0.01,
       "{:.2f}".format(z.position()))
# Am Ende darf sie nicht ueber die Laenge hinauslaufen: Der Titelwechsel
# kommt erst beim naechsten Durchgang, bis dahin bleibt der Balken voll.
z.zeit_setzen(199.0, 200.0, True)
z._gemeldet -= 30.0
pruefe("nicht ueber das Ende hinaus", abs(z.position() - 200.0) < 0.01,
       "{:.2f}".format(z.position()))

print("\n=== Streifen zeichnen ===")
z.setFixedSize(300, 48)
z.titel_setzen("Breathing - orbit Remix", "Nomis", None)
z.zeit_setzen(120.0, 240.0, False)
bild = z.grab().toImage()
dichte = bild.width() / 300.0
akzent = QColor(th.accent)


def farbige_breite(bild, akzent):
    """Wie weit der Balken in Akzentfarbe reicht, in Anteilen der Breite."""
    weit = 0
    for y in range(bild.height()):
        for x in range(bild.width()):
            c = QColor(bild.pixelColor(x, y))
            if c.alpha() > 200 and abs(c.hue() - akzent.hue()) < 12 \
                    and c.saturation() > 80:
                weit = max(weit, x)
    return weit / float(bild.width())


anteil = farbige_breite(bild, akzent)
pruefe("Balken steht auf der Haelfte", 0.45 < anteil < 0.55,
       "{:.0%}".format(anteil))
z.zeit_setzen(24.0, 240.0, False)
anteil = farbige_breite(z.grab().toImage(), akzent)
pruefe("und bei einem Zehntel entsprechend", 0.05 < anteil < 0.16,
       "{:.0%}".format(anteil))

print("\n=== Livestream ===")
# Windows meldet fuer einen Stream keine brauchbare Laenge - gemessen kam aus
# Chrome ein Ende von minus einem Tag. Die Position laeuft trotzdem mit. Ein
# Balken waere dann eine Behauptung ueber eine Stelle, die es nicht gibt.
z.zeit_setzen(134.0, 268.0, True)
pruefe("Titel mit Laenge ist kein Stream", not z.ist_live())
z.zeit_setzen(3600.0, 0.0, True)
pruefe("Position ohne Laenge heisst live", z.ist_live())
z.zeit_setzen(0.0, 0.0, False)
pruefe("gar keine Angaben sind nicht live", not z.ist_live())

z.zeit_setzen(3600.0, 0.0, True)
bild_live = z.grab().toImage()
anteil = farbige_breite(bild_live, akzent)
pruefe("kein Balken im Stream", anteil < 0.05, "{:.0%}".format(anteil))


def rote_punkte(bild):
    """Wie viele deutlich rote Bildpunkte es gibt - das Live-Kennzeichen."""
    zahl = 0
    for y in range(bild.height()):
        for x in range(bild.width()):
            c = QColor(bild.pixelColor(x, y))
            ton = c.hue()
            if c.alpha() > 150 and c.saturation() > 90 and \
                    (ton < 12 or ton > 348):
                zahl += 1
    return zahl


pruefe("dafuer ein rotes Kennzeichen", rote_punkte(bild_live) > 40,
       "{} Punkte".format(rote_punkte(bild_live)))
z.zeit_setzen(134.0, 268.0, True)
pruefe("das beim normalen Titel fehlt", rote_punkte(z.grab().toImage()) < 10)

print("\n=== Design der Taskleiste ===")
# Der Streifen liegt auf der Leiste von Windows, nicht im Volumix-Fenster.
# Steht Windows auf Hell und Volumix auf Dunkel, waere weisse Schrift auf
# heller Leiste unsichtbar - die Farbe muss also von Windows kommen.
echt = zeitleiste.system_leiste_hell
zeitleiste.system_leiste_hell = lambda: False
z.titel_setzen("Ein Titel", "", None)
z.zeit_setzen(60.0, 120.0, False)
dunkel = z.grab().toImage()
zeitleiste.system_leiste_hell = lambda: True
hell = z.grab().toImage()
zeitleiste.system_leiste_hell = echt


def hellster_text(bild):
    """Der hellste Punkt der Schrift - der Balken zaehlt nicht mit."""
    beste = 0
    for y in range(bild.height()):
        for x in range(int(bild.width() * 0.6)):
            c = QColor(bild.pixelColor(x, y))
            if c.alpha() > 150 and c.saturation() < 60:
                beste = max(beste, c.value())
    return beste


pruefe("auf dunkler Leiste helle Schrift", hellster_text(dunkel) > 200,
       "{}".format(hellster_text(dunkel)))
pruefe("auf heller Leiste dunkle Schrift", hellster_text(hell) < 120,
       "{}".format(hellster_text(hell)))

print("\n=== Verhalten ===")
pruefe("nimmt keine Klicks an",
       bool(z.windowFlags() & Qt.WindowTransparentForInput))
z.titel_setzen("", "", None)
z.anschalten(True)
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)
pruefe("ohne Titel unsichtbar", not z.isVisible())

# Pausiert heisst weg: Ein stehender Balken neben der Uhr behauptet eine
# laufende Wiedergabe, die es gerade nicht gibt.
z.titel_setzen("Etwas", "Jemand", None)
z.zeit_setzen(30.0, 120.0, False)
z.anschalten(True)
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)
pruefe("pausiert unsichtbar", not z.isVisible())
z.zeit_setzen(30.0, 120.0, True)
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)
pruefe("und wieder da, sobald es laeuft", z.isVisible())

z.titel_setzen("Etwas", "Jemand", None)
z.zeit_setzen(30.0, 120.0, True)
z.anschalten(True)
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)
platz = taskleiste_platz()
if platz is None:
    print("  (keine waagerechte Taskleiste gefunden – Platzpruefung entfaellt)")
else:
    links, oben, rechts, unten = platz
    pruefe("freier Platz ist plausibel",
           rechts > links and unten > oben and (rechts - links) >= 160,
           "{} bis {}, Hoehe {}".format(links, rechts, unten - oben))
    pruefe("mit Titel sichtbar", z.isVisible())
    ecke = z.geometry()
    pruefe("und sitzt im freien Bereich",
           ecke.right() * z.screen().devicePixelRatio() <= rechts + 2,
           "rechts {} gegen {}".format(
               int(ecke.right() * z.screen().devicePixelRatio()), rechts))
z.anschalten(False)

print("\n=== Vor der Taskleiste ===")
# Die Taskleiste ist selbst immer oben. Ein Klick hinein holt sie nach vorn,
# und der Streifen verschwand dahinter. Gefangen wird hier die Ursache: Der
# Aufruf, der ihn zurueckholt, muss gelingen – ohne erklaerte Typen gab er
# Fehler 1400 zurueck und tat gar nichts.
z.titel_setzen("Etwas", "Jemand", None)
z.anschalten(True)
for _ in range(10):
    app.processEvents()
    time.sleep(0.02)
pruefe("der Aufruf gelingt", z._nach_oben() is True)

u = ctypes.WinDLL("user32", use_last_error=True)
u.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND,
                            wintypes.LPCWSTR, wintypes.LPCWSTR]
u.FindWindowExW.restype = wintypes.HWND
leiste = u.FindWindowExW(None, None, "Shell_TrayWnd", None)
ordnung = []


@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def _sammeln(h, _):
    ordnung.append(h)
    return True


u.EnumWindows(_sammeln, 0)


def _platz(h):
    """Wo ein Fenster in der Reihenfolge steht – kleiner heisst weiter vorn."""
    try:
        return ordnung.index(h)
    except ValueError:
        return len(ordnung)


vorn = _platz(int(z.winId())) < _platz(leiste)
pruefe("Streifen liegt vor der Taskleiste", vorn,
       "Streifen {} gegen Leiste {}".format(_platz(int(z.winId())),
                                            _platz(leiste)))
z.anschalten(False)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
