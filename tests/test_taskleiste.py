# -*- coding: utf-8 -*-
"""Das angeheftete Taskleistensymbol folgt der Akzentfarbe.

Geprueft in einem eigenen Ordner mit eigenen Verknuepfungen – die echte
Taskleiste bleibt dabei unberuehrt.
"""
import os
import shutil
import struct
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from PySide6.QtGui import QColor, QImage                       # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


app = QApplication(sys.argv)
from volumix import taskleiste                                 # noqa: E402
from volumix.config import _lnk_schreiben                      # noqa: E402

ORT = os.path.join(_TESTS, "testcfg", "taskleiste")
shutil.rmtree(ORT, ignore_errors=True)
PINS = os.path.join(ORT, "TaskBar")
SYMBOLE = os.path.join(ORT, "symbole")
os.makedirs(PINS)

# Eine Attrappe fuer die .exe: Eine Verknuepfung braucht ein Ziel, das es
# gibt, sonst loest Windows den Pfad beim Lesen anders auf.
EXE = os.path.join(ORT, "Volumix.exe")
open(EXE, "wb").close()
ANDERE = os.path.join(ORT, "Anderes.exe")
open(ANDERE, "wb").close()

ROT = "#EF4444"
BLAU = "#3B82F6"

print("=== Symboldatei ===")
pfad = taskleiste.symbol_datei(ROT, SYMBOLE)
daten = open(pfad, "rb").read()
reserviert, art, anzahl = struct.unpack("<HHH", daten[:6])
pruefe("ist eine .ico", reserviert == 0 and art == 1,
       "Kopf {} {}".format(reserviert, art))
pruefe("mit allen Groessen", anzahl == len(taskleiste.GROESSEN),
       "{} Bilder".format(anzahl))
# Die Groessen aus dem Verzeichnis lesen und mit dem Soll vergleichen
seiten = []
for i in range(anzahl):
    breite = daten[6 + 16 * i]
    seiten.append(256 if breite == 0 else breite)
pruefe("in der richtigen Reihenfolge",
       tuple(seiten) == taskleiste.GROESSEN, str(seiten))

bild = QImage()
pruefe("Qt kann sie lesen", bild.loadFromData(daten, "ICO"))
# Die Farbe muss im Bild stecken: der kraeftigste Punkt liegt nahe am Akzent
kraeftigster = max((QColor(bild.pixelColor(x, y))
                    for y in range(0, bild.height(), 4)
                    for x in range(0, bild.width(), 4)),
                   key=lambda c: c.alpha() * c.saturation())
soll = QColor(ROT)
abstand = abs(kraeftigster.hue() - soll.hue())
pruefe("und sie ist rot", min(abstand, 360 - abstand) <= 12,
       "Farbton {} statt {}".format(kraeftigster.hue(), soll.hue()))

zweite = taskleiste.symbol_datei(BLAU, SYMBOLE)
pruefe("je Farbe eine eigene Datei", zweite != pfad)
stand = os.path.getmtime(pfad)
taskleiste.symbol_datei(ROT, SYMBOLE)
pruefe("vorhandene wird nicht neu geschrieben",
       os.path.getmtime(pfad) == stand)

print("\n=== Verknuepfungen ===")
UNSERE = os.path.join(PINS, "Volumix.lnk")
FREMDE = os.path.join(PINS, "Anderes.lnk")
_lnk_schreiben(UNSERE, EXE)
_lnk_schreiben(FREMDE, ANDERE)

import comtypes.client                                         # noqa: E402
shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)


def symbol_von(lnk):
    return shell.CreateShortcut(lnk).IconLocation


fremd_vorher = symbol_von(FREMDE)
n = taskleiste.verknuepfungen_faerben(ROT, SYMBOLE, exe=EXE, ordner=PINS)
pruefe("eine geaendert", n == 1, "{}".format(n))
pruefe("unsere zeigt auf das rote Symbol",
       os.path.normcase(symbol_von(UNSERE)).startswith(
           os.path.normcase(taskleiste.symbol_datei(ROT, SYMBOLE))),
       symbol_von(UNSERE))
pruefe("die fremde bleibt, wie sie war", symbol_von(FREMDE) == fremd_vorher)

# Nichts schreiben, wenn nichts zu tun ist: Jedes Schreiben laesst die
# Taskleiste ihre Symbole neu laden.
stand = os.path.getmtime(UNSERE)
n = taskleiste.verknuepfungen_faerben(ROT, SYMBOLE, exe=EXE, ordner=PINS)
pruefe("gleiche Farbe: nichts geschrieben",
       n == 0 and os.path.getmtime(UNSERE) == stand, "{}".format(n))

n = taskleiste.verknuepfungen_faerben(BLAU, SYMBOLE, exe=EXE, ordner=PINS)
pruefe("Farbwechsel: wieder geaendert", n == 1, "{}".format(n))
pruefe("jetzt blau", "3B82F6" in symbol_von(UNSERE).upper(),
       symbol_von(UNSERE))

pruefe("ohne Ordner kein Fehler",
       taskleiste.verknuepfungen_faerben(
           ROT, SYMBOLE, exe=EXE, ordner=os.path.join(ORT, "gibtsnicht")) == 0)

shutil.rmtree(ORT, ignore_errors=True)
print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
