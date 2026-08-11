"""Prueft, ob die Schalter in den Einstellungen wirklich schalten."""
import os
import sys

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)
import ctypes

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
sys.path.insert(0, _PROJEKT)

from PySide6.QtCore import QPoint, Qt, QTimer                  # noqa: E402
from PySide6.QtTest import QTest                               # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

# Eigene Ablage – sonst verstellt der Test Luis' echte Einstellungen
import os                                                      # noqa: E402
from volumix import config                                     # noqa: E402
_TEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")

from volumix.widgets import ToggleSwitch                       # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

fehler = 0


def pruefe(name, ist, soll):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}".format("OK  " if ok else "FEHL", name))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
# Diese Reihe sucht Schalter an ihrer Beschriftung – dafuer muss die Sprache
# feststehen. Ab Werk startet die App auf Englisch.
f._sprache_setzen("de")
f._seite(1)
app.processEvents()


def schalter_finden(text):
    """Den Schalter neben einer Beschriftung heraussuchen."""
    from PySide6.QtWidgets import QLabel
    for lbl in f.einst_seite.findChildren(QLabel):
        if lbl.text() == text:
            eltern = lbl.parent()
            for sw in eltern.findChildren(ToggleSwitch):
                # nur der Schalter in derselben Zeile
                if abs(sw.y() - lbl.y()) < 30:
                    return sw
    return None


def klicken(sw):
    QTest.mousePress(sw, Qt.LeftButton, Qt.NoModifier,
                     QPoint(sw.width() // 2, sw.height() // 2))
    app.processEvents()


print("\n=== Schalter „Live-Pegel“ ===")
sw = schalter_finden("Live-Pegel neben den Reglern")
pruefe("Schalter gefunden", sw is not None, True)
if sw:
    vorher = f.cfg["meters"]
    pruefe("Anzeige stimmt mit Einstellung", sw.isChecked(), vorher)
    klicken(sw)
    pruefe("Einstellung umgeschaltet", f.cfg["meters"], not vorher)
    pruefe("Audio-Engine informiert", f.engine.meters_an, not vorher)
    pruefe("Schalter zeigt neuen Wert", sw.isChecked(), not vorher)
    klicken(sw)
    pruefe("zurueckgeschaltet", f.cfg["meters"], vorher)

print("\n=== Schalter „Steuerung aktiv“ ===")
sw = schalter_finden("Steuerung aktiv")
if sw:
    vorher = f.cfg["active"]
    klicken(sw)
    pruefe("Einstellung umgeschaltet", f.cfg["active"], not vorher)
    pruefe("Hook informiert", f.hook.aktiv, not vorher)
    klicken(sw)

print("\n=== Schalter „Richtung umkehren“ ===")
# Hiess frueher „Scrollrichtung umkehren“. Nach der Umbenennung fand der Test
# den Schalter nicht mehr und uebersprang sich still – deshalb jetzt mit
# Pruefung, dass er ueberhaupt da ist.
sw = schalter_finden("Richtung umkehren")
pruefe("Schalter gefunden", sw is not None, True)
if sw:
    vorher = f.cfg["reverse"]
    klicken(sw)
    pruefe("Einstellung umgeschaltet", f.cfg["reverse"], not vorher)
    pruefe("Hook informiert", f.hook.reverse, not vorher)
    klicken(sw)
    pruefe("zurueckgeschaltet", f.cfg["reverse"], vorher)

print("\n=== Klick auf den Schalter darf NICHT doppelt zaehlen ===")
# Der Fehler: das Klick-Ereignis lief vom Schalter weiter an die Zeile,
# die ebenfalls umschaltete – unterm Strich passierte nichts.
sw = schalter_finden("Live-Pegel neben den Reglern")
if sw:
    zeile = sw.parent()
    zaehler = {"n": 0}
    sw.toggled.connect(lambda _: zaehler.__setitem__("n", zaehler["n"] + 1))
    vorher = sw.isChecked()
    QTest.mouseClick(sw, Qt.LeftButton, Qt.NoModifier,
                     QPoint(sw.width() // 2, sw.height() // 2))
    app.processEvents()
    pruefe("genau einmal gemeldet", zaehler["n"], 1)
    pruefe("Zustand hat sich geaendert", sw.isChecked(), not vorher)
    # Klick auf die Beschriftung muss ebenfalls wirken
    zaehler["n"] = 0
    QTest.mouseClick(zeile, Qt.LeftButton, Qt.NoModifier, QPoint(20, 12))
    app.processEvents()
    pruefe("Klick auf den Text wirkt", zaehler["n"], 1)
    pruefe("wieder im Ausgangszustand", sw.isChecked(), vorher)

print("\n=== Schalter darf beim Klicken nicht wegwandern ===")
# Der Fehler: die Animation hing an der Eigenschaft `pos` – das ist bei Qt
# die Fensterposition. Statt des Knopfs wanderte das ganze Widget nach links.
# Der Schalter sitzt im Bereich „Steuerung“; in einem versteckten Bereich
# haette er keine verlaessliche Position.
f._bereich_zeigen(f.bereich_nr("steuerung"))
app.processEvents()
sw = schalter_finden("Steuerung aktiv")
if sw:
    import time
    start = sw.pos()
    for i in range(4):
        klicken(sw)
        for _ in range(20):            # Animation durchlaufen lassen
            app.processEvents()
            time.sleep(0.015)
    pruefe("Position unveraendert", sw.pos(), start)
    pruefe("laesst sich mehrfach hin und her schalten",
           sw.isChecked(), f.cfg["active"])

print("\n=== Kaestchen einer frisch gebauten Zeile ===")
# Der Fehler: wurde die Liste neu aufgebaut, waehrend eine App schon angehakt
# war, leuchtete die Zeile als gewaehlt – das Kaestchen daneben blieb leer.
from volumix.widgets import MixerRow                            # noqa: E402
probe = {"key": "test.exe", "name": "Test", "volume": 0.5,
         "exe": None, "muted": False}
zeile_an = MixerRow(dict(probe), True, f.theme)
zeile_aus = MixerRow(dict(probe), False, f.theme)
pruefe("angehakt gebaut = Haken sichtbar", zeile_an.box.isChecked(), True)
pruefe("ohne Haken gebaut = leer", zeile_aus.box.isChecked(), False)
zeile_an.deleteLater()
zeile_aus.deleteLater()

print("\n=== Kopfzeile in den Einstellungen ===")
pruefe("Kopfzeile ausgeblendet", f.kopfzeile.isVisible(), False)
# Profile wechselt man im Mixer, nicht in den Einstellungen
pruefe("Profilleiste ausgeblendet", f.profilleiste.isVisible(), False)
f._seite(0)
app.processEvents()
pruefe("im Mixer wieder da", f.kopfzeile.isVisible(), True)
pruefe("Profilleiste wieder da", f.profilleiste.isVisible(), True)

print("\n=== Schrift der Oberflaeche ===")
from volumix import theme as th                                 # noqa: E402
pruefe("nutzt die Windows-Oberflaechenschrift",
       th.schrift().startswith("Segoe UI"), True)
pruefe("kleine Beschriftungen bekommen die Small-Fassung",
       "Segoe UI Variable Small" in f.theme.qss(), True)
pruefe("grosse die Display-Fassung",
       "Segoe UI Variable Display" in f.theme.qss(), True)
import re                                                        # noqa: E402
angaben = re.findall(r"font-family:\s*([^;]+);", f.theme.qss())
ohne_rueckfall = [a.strip() for a in angaben if '"Segoe UI"' not in a]
pruefe("jede Schriftangabe hat einen Rueckfall fuer Windows 10",
       not ohne_rueckfall, True)
if ohne_rueckfall:
    for a in ohne_rueckfall:
        print("       " + a)
print("       ({} Angaben geprueft)".format(len(angaben)))

# Was zaehlt, ist nicht die gewuenschte Schrift, sondern die tatsaechlich
# gezeichnete. Qt nimmt still eine andere Familie, wenn es das verlangte
# Gewicht in der eingestellten nicht findet – die Wortmarke (Gewicht 800)
# stand dadurch eine Zeit lang in einer anderen Schrift, ohne dass irgendetwas
# meckerte. Erlaubt ist alles aus der Segoe-Familie, denn die drei optischen
# Groessen sind Absicht; alles andere waere ein stiller Rueckfall.
from PySide6.QtGui import QFontInfo                              # noqa: E402
from PySide6.QtWidgets import QLabel                             # noqa: E402
falsch = []
for seite in (0, 1):
    f._seite(seite)
    app.processEvents()
    for lbl in f.findChildren(QLabel):
        if not lbl.text() or not lbl.isVisible():
            continue
        echt = QFontInfo(lbl.font()).family()
        if not echt.startswith("Segoe UI"):
            falsch.append("{} -> {}".format(lbl.text()[:18], echt))
f._seite(0)
pruefe("keine Beschriftung faellt auf eine fremde Schrift zurueck",
       not falsch, True)
if falsch:
    for m in sorted(set(falsch))[:4]:
        print("       " + m)
# Ohne Schriftdatei darf die App trotzdem starten – deshalb der Ersatz
pruefe("Ersatz ist eine Windows-Schrift",
       th.SCHRIFT_ERSATZ.startswith("Segoe"), True)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
