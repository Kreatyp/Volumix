# -*- coding: utf-8 -*-
"""Die Lautsprecher im Netz.

Laeuft ohne echte Box: Die vier Stellen, an denen das Modul ans Netz geht,
werden durch eine nachgemachte Box ersetzt. Geprueft wird dadurch das, was
tatsaechlich schiefgehen kann – wann gesetzt wird, wann eben nicht, und ob
ein stummer Netzfehler den Arbeitsthread mitnimmt.
"""
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from volumix import config                                     # noqa: E402

_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
# Eigene Datei, nicht die gemeinsame: Diese Reihe schaltet Boxen, legt
# Zielwerte ab und speichert dabei auch Profile mit. Auf der gemeinsamen
# Ablage hing dadurch das Ergebnis von test_profile.py an der Reihenfolge –
# und diese Reihe umgekehrt daran, was der vorige Lauf hinterlassen hatte.
config.CONFIG_PATH = os.path.join(_TEST, "config-boxen.json")
if os.path.exists(config.CONFIG_PATH):
    os.remove(config.CONFIG_PATH)      # jeder Lauf beginnt gleich

from volumix import boxen as B                                 # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


# ---------------------------------------------------------------------------
# Nachgemachte Box
# ---------------------------------------------------------------------------
class Attrappe:
    def __init__(self):
        self.wert = 50
        self.wach = True
        self.erreichbar = True
        self.geschrieben = 0
        self.gelesen = 0
        self.kaputt = False       # laesst jeden Aufruf scheitern
        self.ton = False          # laeuft gerade Ton am PC?
        self.geschaltet = []      # Verlauf der Standby-Befehle

    def einbauen(self):
        B.erreichbar = lambda ip, frist=0.6: bool(ip) and self.erreichbar
        B.suchen = lambda bekannt=None: "10.0.0.5" if self.erreichbar else None
        B.renderer = lambda host: [("Attrappe", "http://10.0.0.5/ctrl",
                                    "http://10.0.0.5/av")]
        B.wecken = self._wecken
        B.standby = self._standby
        B.ton_laeuft = lambda schwelle=0.004: self.ton
        B.lesen = self._lesen
        B.schreiben = self._schreiben
        B.an = self._an

    def _knacks(self):
        if self.kaputt:
            raise OSError("Netz weg")

    def _lesen(self, url):
        self._knacks()
        self.gelesen += 1
        return self.wert

    def _schreiben(self, url, wert):
        self._knacks()
        self.geschrieben += 1
        self.wert = int(wert)

    def _an(self, host):
        self._knacks()
        return self.wach

    def _wecken(self, url, frist=None):
        self._knacks()
        self.geschaltet.append("an")
        self.wach = True
        self.wert = 49        # die echte Box wacht auf ihrem Wert auf

    def _standby(self, url, frist=None):
        self._knacks()
        self.geschaltet.append("aus")
        self.wach = False


box = Attrappe()
box.einbauen()
B.NACHFASSEN = 0            # sonst kontrolliert jeder Durchgang 20 s lang nach
B.AUS_NACH = 900.0          # Werte wie im Betrieb, nur die Wartezeit nicht
B.STILL = 0.0
ruhe = [1.0]                # was `leerlauf()` zurueckgeben soll
B.leerlauf = lambda: ruhe[0]

verlauf = []
b = B.Boxen(on_status=lambda *a: verlauf.append(a))
b.ziel = 65
b.aktiv = True

print("=== Die Box geht an ===")
b._pruefen()
pruefe("wird auf den Zielwert gesetzt", box.wert, 65)
pruefe("genau einmal geschrieben", box.geschrieben, 1)
pruefe("Meldung geht nach aussen", verlauf[-1][0], "gesetzt")

print("\n=== Solange nichts passiert, passiert nichts ===")
vorher = box.geschrieben
for _ in range(5):
    b._pruefen()
pruefe("kein weiteres Schreiben", box.geschrieben, vorher)

print("\n=== Steht der Wert schon richtig, wird nicht geschrieben ===")
# Der Trick aus dem Modulkopf: Lesen kostet 5 ms, Schreiben 86.
box.wach = False
b._pruefen()
box.wach = True
gelesen_vorher, geschrieben_vorher = box.gelesen, box.geschrieben
b._pruefen()
pruefe("gelesen wurde", box.gelesen > gelesen_vorher)
pruefe("geschrieben nicht", box.geschrieben, geschrieben_vorher)

print("\n=== Jemand dreht die Box von Hand herunter ===")
box.wert = 30
for _ in range(3):
    b._pruefen()
pruefe("das bleibt so", box.wert, 30, "solange niemand weg war")

print("\n=== Kurze Pause zaehlt nicht als Wiederkommen ===")
ruhe[0] = B.RUHE - 30
b._pruefen()
ruhe[0] = 1.0
b._pruefen()
pruefe("unveraendert", box.wert, 30)

print("\n=== Lange Pause, dann zurueck am Rechner ===")
ruhe[0] = B.RUHE + 60
b._pruefen()
ruhe[0] = 1.0
b._pruefen()
pruefe("wieder auf dem Zielwert", box.wert, 65)

print("\n=== Aus und wieder an ===")
box.wert = 50
box.wach = False
b._pruefen()
pruefe("Meldung -aus-", verlauf[-1][0], "aus")
box.wach = True
b._pruefen()
pruefe("beim Anschalten gesetzt", box.wert, 65)

print("\n=== Ausgeschaltet greift nichts ===")
b.aktiv = False
box.wert = 20
box.wach = False
b._pruefen()          # der Arbeitsthread ruft das gar nicht mehr auf,
b._pruefen()          # aber selbst wenn: der Wert bleibt unangetastet
box.wach = True
pruefe("Wert unberuehrt", box.wert, 20)
b.aktiv = True
b._war_da = True      # kein Einschalt-Anlass vortaeuschen

print("\n=== Netzfehler reissen nichts mit ===")
box.kaputt = True
b._war_da = False
try:
    b._pruefen()
    ueberlebt = True
except Exception as e:
    ueberlebt = False
    print("       Ausnahme:", e)
pruefe("kein Absturz", ueberlebt)
box.kaputt = False

print("\n=== Der Arbeitsthread selbst ===")
box.wert = 10
b2 = B.Boxen()
b2.ziel = 65
b2.aktiv = False        # nur der Auftrag, keine Ueberwachung
b2.start()
b2.jetzt_setzen()
ende = time.time() + 3
while time.time() < ende and box.wert != 65:
    time.sleep(0.05)
pruefe("Auftrag aus der Warteschlange gesetzt", box.wert, 65)
b2.stop()
time.sleep(0.2)
pruefe("Thread beendet sich", b2._thread.is_alive(), False)

# ---------------------------------------------------------------------------
# An- und Ausschalten
# ---------------------------------------------------------------------------
B.WACHZEIT = 0.0            # im Betrieb 2 s, bis der Zustand im Netz steht

print("\n=== Von Hand an und aus ===")
box.wach, box.wert, box.geschaltet = True, 65, []
s = B.Boxen(on_status=lambda *a: verlauf.append(a))
s.ziel = 65
s.aktiv = True
s._schalten_jetzt(False)
pruefe("Standby geschickt", box.geschaltet, ["aus"])
pruefe("Box ist aus", box.wach, False)
pruefe("Meldung -aus-", verlauf[-1][0], "aus")
s._schalten_jetzt(True)
pruefe("geweckt", box.geschaltet, ["aus", "an"])
pruefe("und gleich auf den Zielwert", box.wert, 65,
       "die Box wacht auf 49 auf")

print("\n=== Mit dem Rechner anschalten ===")
box.wach, box.wert, box.geschaltet = False, 49, []
s.schalten = True
s._war_weg = True
s._war_da = False
ruhe[0] = 1.0
s._pruefen()
pruefe("Box geht an", box.wach)
pruefe("Lautstaerke steht", box.wert, 65)

print("\n=== Ohne den Schalter passiert das nicht ===")
box.wach, box.geschaltet = False, []
s.schalten = False
s._war_weg = True
s._pruefen()
pruefe("nichts geschaltet", box.geschaltet, [])
s.schalten = True

print("\n=== Lange niemand da und still: geht aus ===")
box.wach, box.geschaltet, box.ton = True, [], False
s._war_da = True
s._still_ab = None
ruhe[0] = B.AUS_NACH + 60
s._pruefen()          # erster Durchgang merkt sich den Beginn der Stille
s._pruefen()          # der zweite schaltet ab (STILL steht im Test auf 0)
pruefe("ausgeschaltet", box.geschaltet, ["aus"])

print("\n=== Aber nicht, solange Ton laeuft ===")
box.wach, box.geschaltet, box.ton = True, [], True
s._war_da = True
s._still_ab = None
ruhe[0] = B.AUS_NACH + 600
for _ in range(4):
    s._pruefen()
pruefe("bleibt an", box.geschaltet, [], "Film ohne Tastendruck")
pruefe("und die Stille faengt bei null an", s._still_ab, None)

print("\n=== Auf dem Knopf herumdruecken schaltet nicht zehnmal ===")
box.wach, box.geschaltet = True, []
s._war_da = True
s._wunsch = None
s._zuletzt_geschaltet = 0.0
for i in range(10):
    (s.an_schalten if i % 2 else s.aus_schalten)()
    s._wunsch_umsetzen()
pruefe("nur ein Befehl an die Box", box.geschaltet, ["aus"],
       "zehn Klicks")
pruefe("der letzte Wunsch bleibt offen", s._wunsch, True)
s._zuletzt_geschaltet = 0.0          # Sperrzeit gedanklich abgelaufen
s._wunsch_umsetzen()
pruefe("und wird danach nachgeholt", box.geschaltet, ["aus", "an"])
pruefe("dann ist nichts mehr offen", s._wunsch, None)

print("\n=== Anschalten bringt die Lautstaerke mit ===")
# Auch ohne eingeschaltetes Nachziehen: Die Box wacht sonst auf ihren
# eigenen 49 auf, waehrend in der Kopfzeile 65 steht.
box.wach, box.wert, box.geschaltet = False, 49, []
s.aktiv = False
s._war_da = False
s._zuletzt_geschaltet = 0.0
s._schalten_jetzt(True)
pruefe("Box ist an", box.wach)
pruefe("und steht auf dem Zielwert", box.wert, 65)
s.aktiv = True

print("\n=== Ein Wunsch, der schon erfuellt ist, kostet nichts ===")
box.wach, box.geschaltet = True, []
s._war_da = True
s._zuletzt_geschaltet = 0.0
s.an_schalten()
s._wunsch_umsetzen()
pruefe("kein Befehl geschickt", box.geschaltet, [])
pruefe("Wunsch erledigt", s._wunsch, None)

print("\n=== Was von Hand ausgeschaltet wurde, bleibt aus ===")
box.wach, box.geschaltet, box.ton = True, [], False
ruhe[0] = 2.0
s._war_weg = False
s._schalten_jetzt(False)
box.geschaltet = []
for _ in range(4):
    s._pruefen()
pruefe("kein selbsttaetiges Anschalten", box.geschaltet, [],
       "erst nach einer Pause wieder")

# ---------------------------------------------------------------------------
# Schlafen und Aufwachen
# ---------------------------------------------------------------------------
print("\n=== Rechner geht schlafen ===")
box.wach, box.geschaltet = True, []
sch = B.Boxen(on_status=lambda *a: verlauf.append(a))
sch.ziel = 65
sch.schalten = True
sch.host = "10.0.0.5"
sch._renderer = B.renderer("10.0.0.5")
pruefe("meldet Erfolg", sch.schlafen())
pruefe("Standby-Befehl kam an", box.geschaltet, ["aus"])
pruefe("Box ist aus", box.wach, False)

print("\n=== ... aber nur mit dem Schalter ===")
box.wach, box.geschaltet = True, []
sch.schalten = False
pruefe("tut nichts", sch.schlafen(), False)
pruefe("kein Befehl", box.geschaltet, [])
sch.schalten = True

print("\n=== Aufwachen zaehlt als Wiederkommen ===")
# Wer den Rechner per Kurzbefehl schlafen legt, hat eine Sekunde vorher
# noch die Maus bewegt – die Leerlauf-Regel allein griffe hier nie.
sch._war_weg = False
ruhe[0] = 2.0
sch.aufwachen()
pruefe("gilt als weg gewesen", sch._war_weg)
pruefe("Adresse wird neu aufgeloest", sch._renderer, [])

# Das Aufwachen selbst schaltet an, nicht der Leerlaufzaehler: Wer
# den Rechner am Netzschalter weckt, drueckt dabei keine Taste.
box.wach, box.geschaltet, box.wert = False, [], 49
ruhe[0] = 3600.0            # laengst keine Eingabe mehr
sch._war_da = False
sch._nach_dem_schlaf()
pruefe("Box geht wieder an", box.wach)
pruefe("und auf den Zielwert", box.wert, 65)
ruhe[0] = 1.0

print("\n=== Aufwachen bei laufender Box setzt nur nach ===")
box.wach, box.geschaltet, box.wert = True, [], 20
sch.aktiv = True
sch._nach_dem_schlaf()
pruefe("nicht geschaltet", box.geschaltet, [])
pruefe("aber die Lautstaerke steht", box.wert, 65)

print("\n=== Bekannte Adresse wird nicht gleich verworfen ===")
# Sonst klopft Volumix nach jedem Aussetzer an 254 Adressen.
gesucht = []
echt_suchen = B.suchen
B.suchen = lambda bekannt=None: gesucht.append(1)
box.erreichbar = False
g = B.Boxen()
g.host = "10.0.0.5"
for _ in range(B.GEDULD):
    g._verbinden()
    g._naechste_suche = 0.0      # Wartezeit im Test ueberspringen
pruefe("erst geduldig an derselben Adresse", gesucht, [])
pruefe("und zwar GEDULD Mal", g._fehlschlaege, B.GEDULD)
g._verbinden()
pruefe("dann erst wird gesucht", len(gesucht), 1)
B.suchen = echt_suchen
box.erreichbar = True

print("\n=== Die Energiewacht entprellt ===")
from volumix.energie import (Energiewacht, PBT_APMSUSPEND,   # noqa: E402
                             PBT_APMRESUMESUSPEND)

ereignisse = []
wacht = Energiewacht(on_schlafen=lambda: ereignisse.append("schlafen"),
                     on_wecken=lambda: ereignisse.append("wecken"))
# Windows schickt die Botschaft an jedes Fenster der obersten Ebene;
# gemessen kam sie fuenfmal an.
for _ in range(5):
    wacht.melden(PBT_APMSUSPEND)
pruefe("fuenf Botschaften, ein Rueckruf", ereignisse, ["schlafen"])
wacht.melden(PBT_APMRESUMESUSPEND)
pruefe("das Aufwachen kommt durch", ereignisse, ["schlafen", "wecken"])

# ---------------------------------------------------------------------------
# Die Oberflaeche
# ---------------------------------------------------------------------------
from PySide6.QtWidgets import QApplication                     # noqa: E402
import schirm                                                  # noqa: E402
from volumix.window import MainWindow                          # noqa: E402

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
f = MainWindow()
f.show()
schirm.nebenan(f)
# Ohne aktives Fenster gibt es keinen echten Fokus – und ohne den
# weder Markierung noch focusOut, um die es hier zum Teil geht.
f.activateWindow()
f.raise_()
f._sprache_setzen("de")
app.processEvents()

# In der Sammelreihe laeuft diese Datei als Unterprozess im
# Hintergrund; Windows laesst das Fenster dann nicht nach vorn und
# es gibt keinen echten Tastaturfokus. Zwei Pruefungen haengen
# daran und werden dann ausgelassen statt falsch zu melden.
f.boxen_pille.feld.setFocus()
app.processEvents()
ECHTER_FOKUS = f.boxen_pille.feld.hasFocus()


def echter_fokus():
    """Hat dieser Lauf gerade wirklich Tastaturfokus?

    In der Sammelreihe laeuft die Datei als Unterprozess im Hintergrund;
    Windows laesst das Fenster dann nicht nach vorn, und ohne aktives
    Fenster gibt es weder Markierung noch focusOut. Einmal am Anfang zu
    messen genuegt nicht - der Fokus kann zwischendurch wegfallen.
    """
    f.boxen_pille.feld.setFocus()
    app.processEvents()
    return f.boxen_pille.feld.hasFocus()
f.boxen_pille.feld.clearFocus()
if not ECHTER_FOKUS:
    print("  --   kein Fenster im Vordergrund, Fokus-Pruefungen aus")

print("\n=== Schalter in der Boxen-Karte ===")
f._seite(1)
f.reiter.waehlen(f.bereich_nr("boxen"))
app.processEvents()
pruefe("Karte hat kein eigenes Zahlenfeld mehr",
       hasattr(f, "boxen_feld"), False, "die Kopfzeile hat sie")

box.wert = 33
f.sw_boxen.setChecked(True, melden=True)
app.processEvents()
pruefe("Nachziehen an wird gespeichert", f.cfg["boxen"], True)
# Der Zielwert kommt aus der Testablage und ist nicht immer 65.
ziel = f.boxen.ziel
grenze = time.time() + 3
while time.time() < grenze and box.wert != ziel:
    app.processEvents()
    time.sleep(0.05)
pruefe("und setzt gleich einmal", box.wert, ziel)
f.sw_boxen.setChecked(False, melden=True)
app.processEvents()
pruefe("Nachziehen aus wird gespeichert", f.cfg["boxen"], False)

print("\n=== Neuaufbau vergisst den Zustand der Box nicht ===")
# Der Schalter wurde frueher fest auf "aus" erzeugt, und die Meldung
# kommt nur bei Wechsel – nach einem Sprach- oder Profilwechsel stand er
# deshalb auf "aus", waehrend die Box lief.
box.wach = True
f._box_status("an", "Attrappe", 62)
app.processEvents()
pruefe("Schalter zeigt an", f.sw_boxen_an.isChecked())
f._sprache_setzen("en")
f._sprache_setzen("de")
app.processEvents()
pruefe("nach dem Neuaufbau immer noch an", f.sw_boxen_an.isChecked())
pruefe("und die Pille auch", f.boxen_pille.ist_an())
pruefe("der Arbeitsthread meldet wieder", f.boxen._letzter, None)
f._seite(1)
f.reiter.waehlen(f.bereich_nr("boxen"))
app.processEvents()

print("\n=== Die Pille in der Kopfzeile ===")
# Die Sperrzeit ist oben geprueft; hier steht sie im Weg, weil die Reihe
# mehrmals hintereinander schaltet.
B.SCHALTSPERRE = 0.0
pille = f.boxen_pille
f._box_status("an", "Attrappe", 65)
app.processEvents()
# Nicht `isVisible()`: Die Kopfzeile ist auf der Einstellungsseite als
# Ganzes ausgeblendet, dann waere jedes Kind darin unsichtbar. Gefragt ist,
# ob die Pille fuer sich ausgeblendet wurde.
pruefe("wird sichtbar, sobald eine Box da ist", pille.isHidden(), False)
pruefe("zeigt an", pille.ist_an())
f._box_status("aus", "", 0)
app.processEvents()
pruefe("und folgt der Box nach aus", pille.ist_an(), False)

box.wach, box.geschaltet = False, []
# Erst abwarten, bis der Arbeitsthread den Zustand gesehen hat –
# sonst haelt er den Wunsch fuer schon erfuellt und verwirft ihn.
grenze = time.time() + 4
while time.time() < grenze and f.boxen._war_da:
    app.processEvents()
    time.sleep(0.05)
pille.knopf.click()
ende = time.time() + 3
while time.time() < ende and not (box.wach and pille.ist_an()):
    app.processEvents()
    time.sleep(0.05)
pruefe("Klick auf den Lautsprecher schaltet an", box.wach)
pruefe("Schalter in den Einstellungen zieht mit",
       f.sw_boxen_an.isChecked())
pruefe("Tray-Eintrag auch", f.a_boxen.isChecked())

box.geschaltet = []
pille.knopf.click()
ende = time.time() + 3
while time.time() < ende and box.wach:
    app.processEvents()
    time.sleep(0.05)
pruefe("noch ein Klick schaltet aus", box.wach, False)

box.wach, box.wert = True, 20
pille.feld.setText("62")
pille._uebernehmen()
grenze = time.time() + 3
while time.time() < grenze and box.wert != 62:
    app.processEvents()
    time.sleep(0.05)
pruefe("Enter in der Pille setzt die Box", box.wert, 62)

print("\n=== Laute Zahlen fragen einmal nach ===")
box.wert = 40
pille.feld.setText("80")
pille._uebernehmen()
app.processEvents()
pruefe("erstes Enter setzt noch nicht", box.wert, 40)
pruefe("sondern warnt", pille._gewarnt, 80)
pruefe("die Eingabe bleibt im Feld", pille.feld.text(), "80")
pille._uebernehmen()
grenze = time.time() + 3
while time.time() < grenze and box.wert != 80:
    app.processEvents()
    time.sleep(0.05)
pruefe("zweites Enter setzt", box.wert, 80)
pruefe("danach ist die Warnung weg", pille._gewarnt, None)

pille.feld.setText("62")
pille._uebernehmen()
grenze = time.time() + 3
while time.time() < grenze and box.wert != 62:
    app.processEvents()
    time.sleep(0.05)
pruefe("unter der Schwelle geht es sofort durch", box.wert, 62)

print("\n=== Danebenklicken verwirft die Eingabe ===")
pille.feld.setFocus()
app.processEvents()
pille.feld.setText("95")
pille._uebernehmen()          # warnt
app.processEvents()
pruefe("warnt", pille._gewarnt, 95)
pille.feld.clearFocus()       # entspricht einem Klick daneben
app.processEvents()
if echter_fokus():
    pruefe("Warnung faellt weg", pille._gewarnt, None)
    pruefe("Feld zeigt wieder den gesetzten Wert",
           pille.feld.text(), "62")
else:
    pille._abbrechen()
pruefe("und die Box blieb unberuehrt", box.wert, 62)

pille.feld.setText("300")
pille._uebernehmen()
app.processEvents()
pruefe("zu grosse Zahl wird geklemmt", pille.feld.text(), "100")
pruefe("und gilt als laut", pille._gewarnt, 100)
pille._abbrechen()

print("\n=== Beim Klick ins Feld steht die Zahl markiert ===")
from PySide6.QtCore import QPoint, Qt                          # noqa: E402
from PySide6.QtTest import QTest                               # noqa: E402

pille.feld.clearFocus()
app.processEvents()
QTest.mouseClick(pille.feld, Qt.LeftButton)
for _ in range(6):
    app.processEvents()
    time.sleep(0.02)
if echter_fokus():
    pruefe("ganze Zahl markiert", pille.feld.selectedText(),
           pille.feld.text())
pille.feld.clearFocus()

print("\n=== Steuerungsbereich aufmachen sucht einmal nach ===")
# Ohne das bliebe die Pille beim allerersten Start unsichtbar, bis jemand
# zufaellig einen Schalter anfasst.
box.wach, box.wert, box.geschaltet = True, 42, []
f.boxen.host = ""
f.boxen._renderer = []
f._boxen_gesucht = False
# erst weg vom Boxen-Reiter, sonst gibt es keinen Wechsel zu melden
f.reiter.waehlen(f.bereich_nr("allgemein"))
app.processEvents()
f.reiter.waehlen(f.bereich_nr("boxen"))
ende = time.time() + 4
while time.time() < ende and not f.boxen.host:
    app.processEvents()
    time.sleep(0.05)
pruefe("Box gefunden", f.boxen.host, "10.0.0.5")
pruefe("aber nichts an ihr verstellt", box.wert, 42)
pruefe("und nichts geschaltet", box.geschaltet, [])

print("\n=== Wer die Zahl anfasst, schaltet nichts ===")
box.wach, box.geschaltet = True, []
f._box_status("an", "Attrappe", 62)
app.processEvents()

QTest.mouseClick(pille.feld, Qt.LeftButton)
app.processEvents()
pruefe("Klick ins Zahlenfeld: kein Schaltbefehl", box.geschaltet, [])
pruefe("Box bleibt an", pille.ist_an())

QTest.mouseClick(pille.prozent, Qt.LeftButton)
app.processEvents()
pruefe("Klick aufs Prozentzeichen: auch nicht", box.geschaltet, [])

# Knapp neben dem Feld, auf dem rechten Rand der Pille
QTest.mouseClick(pille, Qt.LeftButton,
                 pos=QPoint(pille.width() - 4, pille.height() // 2))
app.processEvents()
pruefe("Klick auf den rechten Rand: auch nicht", box.geschaltet, [])
pruefe("stattdessen liegt die Eingabe im Feld",
       pille.focusWidget() is pille.feld or pille.feld.hasFocus())

# Und der Lautsprecher schaltet weiterhin. Vorher abwarten, bis der
# Arbeitsthread den von Hand gesetzten Zustand der Attrappe gesehen hat –
# sonst haelt er den Wunsch fuer schon erfuellt und verwirft ihn.
ende = time.time() + 4
while time.time() < ende and not f.boxen._war_da:
    app.processEvents()
    time.sleep(0.05)
pruefe("Arbeitsthread sieht die Box als an", f.boxen._war_da)
QTest.mouseClick(pille.knopf, Qt.LeftButton)
ende = time.time() + 3
while time.time() < ende and box.wach:
    app.processEvents()
    time.sleep(0.05)
pruefe("nur der Lautsprecher schaltet", box.wach, False)

f.boxen.stop()
f.hook.stop()
f.engine.on_apps = None
f.engine.on_volume = None
f.engine.on_meters = None
f.engine.stop()

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
