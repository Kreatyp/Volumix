# -*- coding: utf-8 -*-
"""Coverbild oder Programmsymbol?

Browser melden bei Seiten ohne eigenes Bild ihr Logo an Windows. Bei einer
Serie in Chrome stand dann das Chrome-Logo weichgezeichnet hinter dem
Fenster. Unterschieden wird ohne Liste von Programmen, nur an der Form: Ein
Cover deckt seine Flaeche, ein Symbol steht frei auf durchsichtigem Grund.

Die Bilder hier sind gezeichnet und nicht die echten – ein fremdes Logo und
ein fremdes Plattencover haben in einem Repository nichts verloren. Die
Masse sind dieselben, die an den echten gemessen wurden.
"""
import json
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402
ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter             # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config-cover.json")
json.dump({"sprache": "de", "accent": "violet", "mode": "dark",
           "cover_bg": True},
          open(config.CONFIG_PATH, "w", encoding="utf-8"))

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


app = QApplication(sys.argv)
import schirm                                                  # noqa: E402
from volumix.window import MainWindow, ist_programmsymbol      # noqa: E402

GROESSE = 256


def leer():
    bild = QImage(GROESSE, GROESSE, QImage.Format_ARGB32)
    bild.fill(Qt.transparent)
    return bild


def rund(rand=0.0):
    """Rundes Symbol, wie das Chrome-Logo – wahlweise mit Luft drumherum."""
    bild = leer()
    p = QPainter(bild)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(220, 60, 50))
    innen = GROESSE * rand
    p.drawEllipse(QRectF(innen, innen, GROESSE - 2 * innen,
                         GROESSE - 2 * innen))
    p.end()
    return bild


def kachel(rand, radius):
    """Eckiges Symbol mit runden Ecken und Rand – so sehen viele App-Symbole aus."""
    bild = leer()
    p = QPainter(bild)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(40, 110, 220))
    innen = GROESSE * rand
    p.drawRoundedRect(QRectF(innen, innen, GROESSE - 2 * innen,
                             GROESSE - 2 * innen),
                      GROESSE * radius, GROESSE * radius)
    p.end()
    return bild


def cover(radius=0.0):
    """Deckendes Bild mit Verlauf, wahlweise mit leicht runden Ecken."""
    bild = leer()
    p = QPainter(bild)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    for i in range(8):
        p.setBrush(QColor(30 + i * 25, 80, 160 - i * 12))
        streifen = QRectF(0, GROESSE * i / 8.0, GROESSE, GROESSE / 8.0 + 1)
        if radius:
            p.save()
            from PySide6.QtGui import QPainterPath
            pfad = QPainterPath()
            pfad.addRoundedRect(QRectF(0, 0, GROESSE, GROESSE),
                                GROESSE * radius, GROESSE * radius)
            p.setClipPath(pfad)
            p.drawRect(streifen)
            p.restore()
        else:
            p.drawRect(streifen)
    p.end()
    return bild


def als_datei(bild, format_):
    feld = QByteArray()
    puffer = QBuffer(feld)
    puffer.open(QIODevice.WriteOnly)
    bild.save(puffer, format_)
    puffer.close()
    return bytes(feld)


def geladen(bild, format_):
    """Durch Speichern und Laden, so wie die Daten von Windows ankommen."""
    zurueck = QImage()
    zurueck.loadFromData(als_datei(bild, format_))
    return zurueck


print("=== Symbole ===")
pruefe("rundes Symbol ohne Rand", ist_programmsymbol(geladen(rund(), "PNG")))
pruefe("rundes Symbol mit Rand", ist_programmsymbol(geladen(rund(0.08), "PNG")))
# Das knappste Symbol, das es gibt: eine Kachel, die fast bis an den Rand
# reicht. Mehr Flaeche kann ein freistehendes Symbol kaum belegen.
pruefe("Kachel mit wenig Rand", ist_programmsymbol(
    geladen(kachel(0.06, 0.18), "PNG")))

print("\n=== Cover ===")
pruefe("deckendes PNG", not ist_programmsymbol(geladen(cover(), "PNG")))
# Spotify liefert PNG mit leicht durchsichtigen Ecken (gemessen Alpha 133
# bis 194). Das darf nicht als Symbol gelten.
pruefe("PNG mit runden Ecken", not ist_programmsymbol(
    geladen(cover(0.04), "PNG")))
pruefe("JPEG", not ist_programmsymbol(geladen(cover(), "JPG")))

print("\n=== Welche Wiedergabe zaehlt ===")
# Windows fuehrt eine "aktuelle" Sitzung, und das ist meist die zuletzt
# gestartete. Laeuft ein Stream im Browser, waehrend daneben Musik spielt,
# zeigte Volumix den Stream - samt Browserlogo als Cover. Nachgemessen bei
# laufendem Spotify und laufendem Twitch: Windows sagte Chrome.
from volumix.titel import beste_sitzung                         # noqa: E402

MUSIK, STREAM, STILLE = "musik", "stream", "stille"
pruefe("Musik schlaegt den Stream", beste_sitzung([
    (MUSIK, True, 255.9, False),
    (STREAM, True, 0.0, True),
]) == MUSIK)
pruefe("laeuft nur der Stream, zaehlt der", beste_sitzung([
    (MUSIK, False, 255.9, False),
    (STREAM, True, 0.0, True),
]) == STREAM)
# Pausiert beides, bleibt der Titel mit Laenge stehen: Zu ihm gehoeren Cover,
# Zeit und Balken, zum Stream nichts davon.
pruefe("pausiert alles, bleibt es beim Titel", beste_sitzung([
    (MUSIK, False, 255.9, False),
    (STREAM, False, 0.0, True),
]) == MUSIK)
pruefe("zwei Titel mit Laenge: ebenso", beste_sitzung([
    (MUSIK, True, 255.9, False),
    (STILLE, True, 180.0, True),
]) == STILLE)
pruefe("nichts da, nichts gewaehlt", beste_sitzung([]) is None)

print("\n=== Im Fenster ===")
f = MainWindow()
f.show()
schirm.nebenan(f)
for _ in range(120):
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)
f._takt.stop()
f.titelwacht.stop()
pix, farbe = f._cover_bauen(als_datei(rund(), "PNG"))
pruefe("Symbol ergibt keinen Hintergrund", pix is None and farbe is None)
pix, farbe = f._cover_bauen(als_datei(cover(0.04), "PNG"))
pruefe("Cover ergibt einen", pix is not None and farbe is not None)

# Und der Wechsel: Laeuft erst Musik mit Cover und dann ein Film im Browser,
# muss das alte Bild verschwinden, statt stehen zu bleiben.
f._titel_uebernehmen("Lied", "Band", als_datei(cover(), "JPG"))
pruefe("mit Cover steht ein Bild da", f._cover_pix is not None)
f._titel_uebernehmen("Serie", "", als_datei(rund(), "PNG"))
pruefe("danach mit Symbol ist es weg", f._cover_pix is None,
       "Farbe {}".format(f._cover_farbe))
f._beenden()

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
