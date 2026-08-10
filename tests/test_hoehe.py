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

print("\n=== Symbole bei krummer Bildschirmskalierung ===")
# 125 % Windows-Skalierung ergibt keine glatte Bilddichte. Wurde die
# Pixelzahl dabei abgeschnitten, war das Symbol bis zu einem halben Pixel zu
# klein – Qt musste es beim Zeichnen wieder hochrechnen, und genau davon
# wird es weich.
from volumix import icons                                       # noqa: E402
schief = []
for dpr in (1.0, 1.25, 1.5, 1.75, 1.875, 2.0, 2.25):
    for groesse in (16, 17, 19, 20, 22, 24, 30, 32, 40, 64):
        pm = icons.pixmap("gear", groesse, "#FFFFFF", dpr)
        logisch = pm.width() / pm.devicePixelRatio()
        if abs(logisch - groesse) > 0.01:
            schief.append("{}px@{}: {:.2f}".format(groesse, dpr, logisch))
        if pm.width() < groesse * dpr:
            schief.append("{}px@{}: zu wenig Pixel".format(groesse, dpr))
pruefe("jede Groesse kommt genau an", not schief, ", ".join(schief[:4]))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
