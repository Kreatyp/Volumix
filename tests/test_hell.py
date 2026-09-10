# -*- coding: utf-8 -*-
"""Heben sich die Flaechen vom Grund ab – in beiden Modi?

Im Dunkeln traegt das Glas die Trennung: die Scheibe ist heller als der
Grund, dazu ein Lichtsaum an der Oberkante. Im Hellen traegt weisse Milch
auf hellem Grund nichts. Dort war die Karte nur noch am Farbnebel des
Fensters zu erkennen, und der Nebel faerbte sie gleich mit – deshalb ist
sie dort ein deckendes Blatt mit feiner Kante.

Geprueft wird beides an derselben Stelle: Abstand zwischen Karte und Grund,
eine Kante dazwischen, und wie ruhig der Grund selbst ist.

Dazu die Schaerfe der Symbole: Wer eines baut, bevor sein Widget an einem
Fenster haengt, hat noch kein `devicePixelRatioF()`. Stand dort 1,0, wurde
das Symbol in halber Aufloesung gerendert und von Qt hochgezogen.
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

from PySide6.QtCore import QPoint                              # noqa: E402
from PySide6.QtGui import QColor                               # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config-hell.json")
json.dump({"sprache": "de", "accent": "violet", "mode": "light",
           "cover_bg": False},
          open(config.CONFIG_PATH, "w", encoding="utf-8"))

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


def lstern(farbe):
    def kanal(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    y = (0.2126 * kanal(farbe.red()) + 0.7152 * kanal(farbe.green())
         + 0.0722 * kanal(farbe.blue()))
    return 116 * (y ** (1 / 3.0)) - 16 if y > 0.008856 else 903.3 * y


def kontrast(a, b):
    def rel(farbe):
        def kanal(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        return (0.2126 * kanal(farbe.red()) + 0.7152 * kanal(farbe.green())
                + 0.0722 * kanal(farbe.blue()))
    x, y = sorted((rel(a), rel(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


app = QApplication(sys.argv)
from volumix import icons                                      # noqa: E402
from volumix.widgets import Flaeche                            # noqa: E402
import schirm                                                  # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

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


def messen(modus):
    """Karte, Grund und Kante im fertigen Bild."""
    f._modus_setzen(modus)
    f._seite(1)
    for _ in range(40):
        app.processEvents()
        time.sleep(0.02)
    f.osd.hide()
    app.processEvents()
    bild = f.grab().toImage()
    dichte = bild.width() / float(f.width())
    karten = [w for w in f.findChildren(Flaeche)
              if w.isVisible() and w.height() > 60 and w.width() > 200]
    karte = karten[0]
    ecke = karte.mapTo(f, QPoint(0, 0))

    def punkt(x, y):
        return QColor(bild.pixelColor(int(x * dichte), int(y * dichte)))

    mitte_y = ecke.y() + karte.height() // 2
    innen = punkt(ecke.x() + karte.width() // 2, mitte_y)
    # Der Grund liegt links neben der Karte, weit genug weg von ihrer Kante
    grund = punkt(max(2, ecke.x() - 8), mitte_y)
    # Die Kante selbst: der dunkelste Punkt im Band um die linke Kartenkante
    rand = min((punkt(ecke.x() + dx, mitte_y) for dx in range(-2, 3)),
               key=lstern)
    return innen, grund, rand


# Als Erstes gemessen: Ein Moduswechsel baut alle Symbole neu und wuerde
# genau den Fehler zudecken, um den es hier geht.
print("=== Schaerfe der Symbole ===")
dichte = app.primaryScreen().devicePixelRatio()
pm = icons.pixmap("gear", 20, "#888888")
pruefe("ohne Angabe in Bildschirmdichte", abs(pm.devicePixelRatio() - dichte)
       < 0.01, "{} statt {}".format(pm.devicePixelRatio(), dichte))
pruefe("und entsprechend viele Pixel", pm.width() == int(20 * dichte),
       "{} px".format(pm.width()))
# Der Knopf im Fenster nimmt die Dichte seines Bildschirms, nicht die des
# primaeren: Bei zwei Bildschirmen mit verschiedener Skalierung sind das
# verschiedene Werte, und das Fenster steht mal hier, mal dort.
knopf = f.btn_einst.icon().pixmap(20, 20)
pruefe("der Zahnradknopf folgt dem Fenster",
       abs(knopf.devicePixelRatio() - f.devicePixelRatioF()) < 0.01,
       "{} bei Fenster {}".format(knopf.devicePixelRatio(),
                                  f.devicePixelRatioF()))

for modus, name in (("light", "Hell"), ("dark", "Dunkel")):
    print("\n=== {} ===".format(name))
    innen, grund, rand = messen(modus)
    abstand = abs(lstern(innen) - lstern(grund))
    pruefe("Karte hebt sich vom Grund ab", abstand >= 3.0,
           "L* {:.1f} gegen {:.1f}, Abstand {:.1f}".format(
               lstern(innen), lstern(grund), abstand))
    # Eine Kante zwischen beiden: Ohne sie schwimmt die Karte im Grund, und
    # genau das war im hellen Modus der Fall.
    kante = abs(lstern(rand) - lstern(innen))
    pruefe("und hat eine Kante", kante >= 1.5,
           "L* {:.1f} gegen {:.1f}".format(lstern(rand), lstern(innen)))
    text = QColor(f.theme.fg)
    pruefe("Text auf der Karte lesbar", kontrast(innen, text) >= 7.0,
           "{:.1f}:1".format(kontrast(innen, text)))
    # Der Grund soll im Hellen tragen, nicht leuchten: Dort lag ein
    # violett-rosa Nebel, der jede Flaeche davor mitgefaerbt hat. Im Dunkeln
    # ist die Farbe im Grund dagegen der Sinn der Sache – ohne sie sieht
    # Milchglas aus wie Grau.
    if modus == "light":
        pruefe("Grund bleibt ruhig", grund.saturation() <= 40,
               "Saettigung {}".format(grund.saturation()))

f._beenden()
print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
