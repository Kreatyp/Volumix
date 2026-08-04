"""Prueft Sprachwechsel, Mausrad ueber der Zeile und den Autostart-Pfad."""
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

from PySide6.QtCore import QPoint, Qt                          # noqa: E402
from PySide6.QtGui import QWheelEvent                          # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel             # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(HIER, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")
# Diese Reihe prueft unter anderem die Werkseinstellung. Andere Reihen teilen
# sich dieselbe Ablage und stellen die Sprache um – deshalb hier vorher weg
# damit, sonst haengt das Ergebnis an der Reihenfolge.
if os.path.exists(config.CONFIG_PATH):
    os.remove(config.CONFIG_PATH)

from volumix import sprache                                    # noqa: E402
from volumix.config import MASTER_KEY                          # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


def texte_im_fenster(f):
    return {lbl.text() for lbl in f.findChildren(QLabel) if lbl.text()}


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
app.processEvents()

print("\n=== Sprachwechsel ===")
pruefe("startet auf Englisch", "VOLUME MIXER" in texte_im_fenster(f))
f._sprache_setzen("de")
app.processEvents()
texte = texte_im_fenster(f)
pruefe("Mixer-Ueberschrift deutsch", "LAUTSTÄRKE-MIXER" in texte)
pruefe("kein englischer Rest im Kopf", "VOLUME MIXER" not in texte)
pruefe("Statusknopf deutsch", f.btn_apps.text() == "Apps wählen")
pruefe("Einstellung gespeichert", f.cfg["sprache"] == "de")

f._seite(1)
app.processEvents()
texte = texte_im_fenster(f)
pruefe("Einstellungen deutsch", "STEUERUNG" in texte,
       "gefunden: {}".format(sorted(t for t in texte if t.isupper())[:4]))
pruefe("Sprachabschnitt vorhanden", "SPRACHE" in texte)

f._sprache_setzen("en")
app.processEvents()
texte = texte_im_fenster(f)
pruefe("zurueck auf Englisch", "CONTROL" in texte)
pruefe("Ansicht bleibt in den Einstellungen", f.einst_seite.isVisible())

f._seite(0)
app.processEvents()

print("\n=== Mausrad ueber einer Zeile ===")
# Auf die erste Rueckmeldung des Audio-Threads warten
import time
for _ in range(120):
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)
zeilen = [r for r in f.rows.values() if not r.muted]
pruefe("Mixer-Zeilen vorhanden", bool(zeilen),
       "{} Zeilen".format(len(f.rows)))
if zeilen:
    z = zeilen[-1]
    z.regler.setValue(50)
    app.processEvents()
    gemeldet = []
    z.volume_changed.connect(lambda k, w, e: gemeldet.append(w))

    def raddrehen(stufen):
        e = QWheelEvent(QPoint(10, 10), z.mapToGlobal(QPoint(10, 10)),
                        QPoint(0, 0), QPoint(0, 120 * stufen),
                        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        z.wheelEvent(e)
        app.processEvents()
        return e

    e1 = raddrehen(1)
    pruefe("hoch dreht lauter", z.regler.value() > 50,
           "ist {}".format(z.regler.value()))
    pruefe("Aenderung wird gemeldet", len(gemeldet) == 1)
    pruefe("Ereignis wird angenommen (Liste scrollt nicht)", e1.isAccepted())
    vorher = z.regler.value()
    raddrehen(-2)
    pruefe("runter dreht leiser", z.regler.value() < vorher,
           "ist {}".format(z.regler.value()))
    # Grenzen
    for _ in range(40):
        raddrehen(-1)
    pruefe("bleibt bei 0 stehen", z.regler.value() == 0)
    for _ in range(40):
        raddrehen(1)
    pruefe("bleibt bei 100 stehen", z.regler.value() == 100)

print("\n=== Kein Text haengt auf Deutsch fest ===")
# Vier Stellen waren frueher fest verdrahtet, obwohl es den Text gab.
f._sprache_setzen("en")


def master_name():
    """Name, den die Audio-Schicht fuer die Gesamtlautstaerke liefert."""
    for it in getattr(f, "_items", []):
        if it["key"] == MASTER_KEY:
            return it["name"]
    return None


for _ in range(120):
    app.processEvents()
    if master_name() == "Master volume":
        break
    time.sleep(0.05)
pruefe("Gesamtlautstaerke heisst englisch", master_name() == "Master volume",
       repr(master_name()))
zeilen = list(f.rows.values())
if zeilen:
    z = zeilen[0]
    pruefe("Hinweis am Lautsprecher englisch",
           z.lautsprecher.toolTip() == "Mute", repr(z.lautsprecher.toolTip()))
    z.set_muted(True)
    app.processEvents()
    pruefe("Anzeige bei stumm englisch", z.prozent.text() == "muted",
           repr(z.prozent.text()))
    z.set_muted(False)
f._sprache_setzen("de")
app.processEvents()

print("\n=== Modus-Knoepfe auch auf Englisch ===")
# Der Abgleich verglich die Knopfbeschriftung mit fest verdrahtetem
# „Hell“/„Dunkel“ – auf Englisch war danach kein Knopf mehr markiert.
for kuerzel in ("de", "en"):
    f._sprache_setzen(kuerzel)
    app.processEvents()
    for modus in ("light", "dark"):
        f._modus_setzen(modus)
        app.processEvents()
        an = [b for b in f.modus_gruppe.buttons() if b.isChecked()]
        pruefe("{}: genau ein Knopf markiert ({})".format(kuerzel, modus),
               len(an) == 1, "{} markiert".format(len(an)))
f._sprache_setzen("de")
app.processEvents()

print("\n=== Textliste ist aufgeraeumt ===")
quellen = ""
for _n in os.listdir(os.path.join(_PROJEKT, "volumix")):
    if _n.endswith(".py") and _n != "sprache.py":
        quellen += open(os.path.join(_PROJEKT, "volumix", _n),
                        encoding="utf-8").read()
import re                                                     # noqa: E402
gerufen = set(re.findall(r"""T\(\s*["']([^"']+)["']""", quellen))
# Schluessel, die im Code zusammengesetzt werden – z. B. T("wechsel_" + wert)
gebaut = set(re.findall(r"""T\(\s*["']([a-z_]+_)["']\s*\+""", quellen))
gerufen -= gebaut
tot = sorted(k for k in sprache.TEXTE
             if k not in gerufen
             and not any(k.startswith(p) for p in gebaut))
pruefe("kein unbenutzter Text uebrig", not tot, ", ".join(tot))
fehlt = sorted(k for k in gerufen if k not in sprache.TEXTE)
pruefe("kein Text fehlt in der Liste", not fehlt, ", ".join(fehlt))
unvollstaendig = sorted(k for k, v in sprache.TEXTE.items()
                        if len(v) < 2 or not v[0] or not v[1])
pruefe("alle Texte haben DE und EN", not unvollstaendig,
       ", ".join(unvollstaendig))

print("\n=== Autostart-Pfad ===")
befehl = config._startbefehl()
pruefe("zeigt auf die gebaute App", "Volumix.exe" in befehl,
       befehl[:70])
pruefe("startet in den Infobereich", "--tray" in befehl)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
