"""Prueft, dass sich die Einstellungen nicht ins Leere ziehen lassen."""
import os
import sys
import time

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)
import ctypes

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
HIER = _TESTS
sys.path.insert(0, _PROJEKT)

from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(HIER, "testcfg")
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
app.processEvents()

f._seite(1)
app.processEvents()
f._einst_hoehe()
app.processEvents()

grenze = f.maximumHeight()
inhalt = f._einst_inhalt.sizeHint().height()
schirm = f.screen().availableGeometry().height()
print("  Inhalt braucht {} px, Bildschirm {} px, Grenze {} px".format(
    inhalt, schirm, grenze))
pruefe("Grenze gesetzt (nicht unendlich)", grenze < 16000000)
pruefe("Grenze passt auf den Bildschirm", grenze <= schirm)
pruefe("Grenze deckt den Inhalt oder den Schirm", grenze >= min(inhalt, schirm - 100))

# Versuch, groesser zu ziehen
f.resize(f.width(), grenze + 500)
app.processEvents()
pruefe("laesst sich nicht ueberdehnen", f.height() <= grenze,
       "ist {}".format(f.height()))

print("\n=== Abblendung ===")
f._einst_fade()
app.processEvents()
s = f._einst_schleier
pruefe("Schleier liegt ueber dem Rollbereich", s.width() > 100)
scrollbar = f._einst_roll.verticalScrollBar()
if scrollbar.maximum() > 0:
    scrollbar.setValue(scrollbar.maximum() // 2)
    app.processEvents()
    f._einst_fade()
    pruefe("blendet oben UND unten ab", s.oben and s.unten)
else:
    pruefe("nichts zu scrollen -> keine Abblendung",
           not s.oben and not s.unten)

print("\n=== Abblendung im App-Auswahldialog ===")
# Bei genug Apps ist die Liste laenger als der Dialog. Ohne Abblendung sieht
# sie unten aus, als waere sie zu Ende.
from volumix.window import AppsDialog                           # noqa: E402
for i in range(20):
    key = "probe{}.exe".format(i)
    f.live.add(key)
    f._meta[key] = "Probe {}".format(i)
d = AppsDialog(f)
d.show()
for _ in range(30):
    app.processEvents()
    time.sleep(0.01)
leiste = d.roll.verticalScrollBar()
pruefe("Liste ist laenger als der Dialog", leiste.maximum() > 0,
       "Rollweg {} px".format(leiste.maximum()))
pruefe("Bildlaufleiste sichtbar", leiste.isVisible())
pruefe("unten wird abgeblendet", d.schleier.unten)
pruefe("oben noch nicht", not d.schleier.oben)
leiste.setValue(leiste.maximum() // 2)
app.processEvents()
pruefe("in der Mitte oben UND unten", d.schleier.oben and d.schleier.unten)
leiste.setValue(leiste.maximum())
app.processEvents()
pruefe("ganz unten nur noch oben", d.schleier.oben and not d.schleier.unten)
d.reject()

# Hier stand eine Pruefung, dass Symbole bei krummen Bildschirm-
# skalierungen auf den Pixel genau ankommen. Sie gehoerte zu einer Aenderung
# an icons._render, die zusammen mit den Schriftgroessen zurueckgenommen
# wurde: Der Stand davor sah besser aus. Der Mangel ist real (17 px kommen
# bei 125 % als 16,53 px an); die Korrektur liegt in der Historie unter
# 8c8fc3b bereit, falls sie einzeln gewuenscht wird.

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
