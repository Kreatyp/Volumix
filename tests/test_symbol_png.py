# -*- coding: utf-8 -*-
"""Das App-Symbol als PNG-Bytes – der Weg zur Mod.

Warum eine eigene Testreihe fuer drei Zeilen Code: `QBuffer(QByteArray())`
laesst Volumix abstuerzen, und zwar unterhalb von Python. Kein `except`
faengt das ab, keine Fehlermeldung erscheint, die App ist einfach weg. Nur
ein eigener Prozess kann so etwas ueberhaupt bemerken - deshalb laeuft die
Pruefung hier abgetrennt und wird an ihrem Rueckgabewert gemessen.
"""
import os
import subprocess
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


KIND = r'''
import sys
sys.path.insert(0, r"{projekt}")
from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor

app = QApplication([])
pm = QPixmap(32, 32)
pm.fill(QColor("#FF00AA"))

# Genau der Weg aus window._symbol_png
daten = QByteArray()
puffer = QBuffer(daten)
puffer.open(QBuffer.WriteOnly)
pm.save(puffer, "PNG")
puffer.close()
roh = bytes(daten)

# Hundertmal, damit ein Fehler in der Lebensdauer sicher auffaellt
for _ in range(100):
    d2 = QByteArray()
    p2 = QBuffer(d2)
    p2.open(QBuffer.WriteOnly)
    pm.save(p2, "PNG")
    p2.close()
    assert bytes(d2)[:8] == b"\x89PNG\r\n\x1a\n"

print("LAENGE", len(roh))
print("KOPF", roh[:8].hex())
'''

print("=== Symbol wird zu PNG, ohne die App mitzunehmen ===")
lauf = subprocess.run([sys.executable, "-c", KIND.format(projekt=_PROJEKT)],
                      capture_output=True, text=True, timeout=120)
pruefe("Prozess ueberlebt", lauf.returncode, 0,
       "Rueckgabe {}".format(lauf.returncode))
if lauf.returncode != 0:
    print("       Ausgabe:", (lauf.stderr or "").strip()[:300])
else:
    zeilen = dict(z.split(" ", 1) for z in lauf.stdout.strip().splitlines()
                  if " " in z)
    pruefe("PNG-Kopf stimmt", zeilen.get("KOPF"), "89504e470d0a1a0a")
    pruefe("und es steckt etwas drin", int(zeilen.get("LAENGE", 0)) > 100, True,
           "{} Bytes".format(zeilen.get("LAENGE")))

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
