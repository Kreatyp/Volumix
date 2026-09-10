# -*- coding: utf-8 -*-
"""Was ein eigenes Fenster ist, muss sich selbst tragen.

Seit die Flaechen Milchglas sind, leben sie davon, dass der Fenstergrund mit
seinem farbigen Licht durch sie hindurchscheint. Alles, was ein eigenes
Fenster ist – die Einblendung, der Auswahldialog –, hat darunter aber
nichts und waere fast durchsichtig. Genau das ist zweimal passiert.

Geprueft wird deshalb die Deckkraft solcher Flaechen. Bei der Einblendung
nach beiden Seiten: Sie soll ueber fremdem Bild bestehen, aber auch etwas
durchscheinen lassen – und die Farbe des Coverbildes mittragen.
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

from PySide6.QtCore import QPoint                                # noqa: E402
from PySide6.QtGui import (QColor, QLinearGradient, QPainter,    # noqa: E402
                           QPixmap, QRadialGradient)
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
import schirm                                                  # noqa: E402
from volumix.window import (AppsDialog, COVER_GROESSE,           # noqa: E402
                            MainWindow)

def zeichnen(osd, app, cover=None, bild=None):
    osd.zeigen([("spotify.exe", None, "Spotify")], 45, cover=cover,
               coverbild=bild)
    for _ in range(30):
        app.processEvents()
        time.sleep(0.02)
    bild = osd.grab().toImage()
    osd.hide()
    app.processEvents()
    return bild


def farbe_an(bild, ax, ay):
    x = int(bild.width() * ax)
    y = int(bild.height() * ay)
    return QColor(bild.pixelColor(x, y))


def ueber(bild, grund, ax, ay):
    """Wie die Stelle aussieht, wenn dieser Untergrund durchscheint."""
    c = farbe_an(bild, ax, ay)
    a = c.alphaF()
    return [c.red() * a + grund[0] * (1 - a),
            c.green() * a + grund[1] * (1 - a),
            c.blue() * a + grund[2] * (1 - a)]


def kontrast(v1, v2):
    def rel(v):
        def kanal(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        return (0.2126 * kanal(v[0]) + 0.7152 * kanal(v[1])
                + 0.0722 * kanal(v[2]))
    a, b = sorted((rel(v1), rel(v2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


print("=== Einblendung ueber dem Schreibtisch ===")
th = Theme("dark", "violet")
osd = Osd(th)
osd.einstellen(45, 50, 88)
bild = zeichnen(osd, app)
mitte = deckkraft(bild, 0.5, 0.5)
# Nach unten: reines Glas ueber dem Schreibtisch war Alpha 13 und damit
# unsichtbar. Nach oben: die Durchsicht ist gewollt und soll nicht
# unbemerkt wieder zuwachsen.
pruefe("traegt sich selbst", mitte >= 180, True, "Alpha {}".format(mitte))
pruefe("laesst aber durchscheinen", mitte <= 240, True,
       "Alpha {}".format(mitte))
links = deckkraft(bild, 0.12, 0.5)
pruefe("auch am Rand des Inhalts", links >= 180, True,
       "Alpha {}".format(links))

# Ueber Weiss steigt der Grund am staerksten – dort entscheidet sich, ob die
# Durchsicht die Schrift kostet.
hell = ueber(bild, (255, 255, 255), 0.62, 0.62)
k = kontrast(hell, (255, 255, 255))
pruefe("Text bleibt ueber Weiss lesbar", k >= 4.5, True,
       "{:.1f}:1".format(k))

# Laeuft im Fenster ein Coverbild, soll die Einblendung mitfaerben statt als
# Einzige im Akzent stehen zu bleiben.
gruen = zeichnen(osd, app, QColor(90, 190, 130))
a = farbe_an(bild, 0.5, 0.2)
b = farbe_an(gruen, 0.5, 0.2)
abstand = ((a.red() - b.red()) ** 2 + (a.green() - b.green()) ** 2
           + (a.blue() - b.blue()) ** 2) ** 0.5
pruefe("Coverfarbe faerbt den Grund", abstand >= 8, True,
       "Abstand {:.1f}".format(abstand))

# Das Bild selbst gehoert dazu, nicht nur sein Mittelwert – und es haengt
# nicht an der Transparenz: Wer die Einblendung deckend stellt, soll das
# Cover trotzdem sehen, so wie er es im Fenster sieht.
buntes = QPixmap(320, 480)
maler = QPainter(buntes)
maler.fillRect(buntes.rect(), QColor(24, 18, 40))
for mx, my, ton in ((0.25, 0.2, QColor(220, 70, 90)),
                    (0.8, 0.45, QColor(240, 170, 60)),
                    (0.4, 0.9, QColor(60, 110, 220))):
    strahl = QRadialGradient(buntes.width() * mx, buntes.height() * my,
                             buntes.width() * 0.7)
    aussen = QColor(ton)
    aussen.setAlphaF(0.0)
    strahl.setColorAt(0.0, ton)
    strahl.setColorAt(1.0, aussen)
    maler.fillRect(buntes.rect(), strahl)
maler.end()
weiten = []
for klar in (0, 50, 100):
    osd.einstellen(45, 50, 88, klar=klar)
    a = farbe_an(zeichnen(osd, app, QColor(90, 190, 130)), 0.5, 0.25)
    b = farbe_an(zeichnen(osd, app, QColor(90, 190, 130), buntes), 0.5, 0.25)
    weiten.append(((a.red() - b.red()) ** 2 + (a.green() - b.green()) ** 2
                   + (a.blue() - b.blue()) ** 2) ** 0.5)
pruefe("Coverbild kommt durch, auch ohne Transparenz", weiten[0] >= 12, True,
       "Abstand {:.1f}".format(weiten[0]))
# Nach oben hin blasser: Wer die Einblendung durchsichtig stellt, will den
# Bildschirm dahinter sehen und nicht ein zweites Bild darueber.
pruefe("und wird mit der Transparenz blasser",
       weiten[0] > weiten[1] > weiten[2] > 0, True,
       "Abstand {:.1f} / {:.1f} / {:.1f}".format(*weiten))
osd.einstellen(45, 50, 88, klar=50)

# Der Regler in den Einstellungen oeffnet denselben Grund. Am Anschlag darf
# er ihn nicht ganz wegnehmen – sonst steht der Text auf blankem Bild.
stufen = []
for klar in (0, 50, 100):
    osd.einstellen(45, 50, 88, klar=klar)
    stufen.append(deckkraft(zeichnen(osd, app), 0.5, 0.5))
pruefe("Regler auf 0: deckend", stufen[0] >= 250, True,
       "Alpha {}".format(stufen[0]))
pruefe("Regler wirkt in eine Richtung",
       stufen[0] > stufen[1] > stufen[2], True,
       "Alpha {} / {} / {}".format(*stufen))
osd.einstellen(45, 50, 88, klar=100)
anschlag = ueber(zeichnen(osd, app), (255, 255, 255), 0.62, 0.62)
k = kontrast(anschlag, (255, 255, 255))
pruefe("auch am Anschlag noch lesbar", k >= 3.0, True, "{:.1f}:1".format(k))
osd.einstellen(45, 50, 88, klar=50)

print("\n=== Auswahldialog ===")
f = MainWindow()
f.show()
schirm.nebenan(f)
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

print("\n=== Coverfarbe erreicht die Einblendung ===")
# Genau das war einmal vergessen: Das Fenster kannte die Farbe des Covers,
# die Einblendung nicht – und blieb als Einzige im alten Ton stehen.
gemerkt = {}
f.osd.zeigen = lambda *a, **k: gemerkt.update(k)
f.cfg["osd_enabled"] = True
f._cover_farbe = QColor(90, 190, 130)
f.targets = set(list(f.rows)[:1])
f._osd_zeigen()
f._cover_pix = buntes
f._osd_zeigen()
pruefe("Fenster reicht die Coverfarbe weiter",
       gemerkt.get("cover") == QColor(90, 190, 130), True,
       "uebergeben: {}".format(gemerkt.get("cover")))
pruefe("und das Coverbild dazu", gemerkt.get("coverbild") is buntes)

print("\n=== Einstellungskopf ueber hellem Cover ===")
# Titel und Reiter stehen als Einzige ohne Karte auf dem Grund. Ueber einem
# hellen Coverbild stand der inaktive Reiter bei 1,4:1 und war nicht mehr zu
# lesen – deshalb dunkelt der Grund dort ab.
f.titelwacht.stop()
pm = QPixmap(COVER_GROESSE)
maler = QPainter(pm)
hell = QLinearGradient(0, 0, pm.width(), pm.height())
hell.setColorAt(0.0, QColor(198, 170, 110))
hell.setColorAt(0.5, QColor(232, 212, 158))
hell.setColorAt(1.0, QColor(180, 150, 95))
maler.fillRect(pm.rect(), hell)
maler.end()
f._cover_pix = pm
f._cover_alt = None
f._cover_mix = 1.0
f._seite(1)
for _ in range(40):
    app.processEvents()
    time.sleep(0.02)
bild = f.grab().toImage()
oben = f.reiter.mapTo(f, QPoint(0, f.reiter.height() // 2)).y()
proben = []
for x in range(6, bild.width() - 6, 4):
    c = farbe_an(bild, x / float(bild.width()), oben / float(bild.height()))
    proben.append([c.red(), c.green(), c.blue()])
# Der Grund ist der Mittelwert der Zeile: die Schrift belegt nur einen
# kleinen Teil davon und faellt so heraus.
proben.sort(key=lambda v: kontrast(v, (0, 0, 0)))
grund = proben[len(proben) // 2]
muted = QColor(f.theme.muted)
k = kontrast(grund, (muted.red(), muted.green(), muted.blue()))
pruefe("inaktiver Reiter bleibt lesbar", k >= 4.5, True,
       "{:.1f}:1".format(k))

f._beenden()

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
