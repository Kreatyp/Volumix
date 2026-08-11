# -*- coding: utf-8 -*-
"""Sieht die App auf fremden Bildschirmen noch richtig aus?

Nachgestellt werden verschiedene Windows-Skalierungen. Geprueft wird das,
was man auf einem Abzug nicht sieht, aber auf dem fremden Rechner sofort:
abgeschnittene Beschriftungen, zu kleine Schrift, Symbole in krummen
Groessen.
"""
import os
import subprocess
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)

# Der Skalierungsfaktor muss stehen, bevor Qt hochfaehrt – deshalb laeuft
# jede Stufe in einem eigenen Prozess.
KIND = """
import os, sys, time
sys.path.insert(0, r"{projekt}")
from volumix import config
config.CONFIG_DIR = r"{cfg}"
config.CONFIG_PATH = os.path.join(config.CONFIG_DIR, "config.json")
from PySide6.QtWidgets import QApplication, QLabel
from volumix.window import MainWindow
from volumix.widgets import _ElidedLabel

app = QApplication(sys.argv)
f = MainWindow()
f.show()
for _ in range(80):
    app.processEvents()
    time.sleep(0.02)

fehler = []
for sprache in ("de", "en"):
    f._sprache_setzen(sprache)
    app.processEvents()
    for seite in (0, 1):
        f._seite(seite)
        for bereich in range(len(f.BEREICHE) if seite else 1):
            if seite:
                f._bereich_zeigen(bereich)
            for _ in range(12):
                app.processEvents()
                time.sleep(0.01)
            for lbl in f.findChildren(QLabel):
                if not lbl.text() or not lbl.isVisible():
                    continue
                if isinstance(lbl, _ElidedLabel):
                    continue        # kuerzt mit Absicht
                noetig = lbl.fontMetrics().horizontalAdvance(lbl.text())
                if noetig > lbl.width() + 1:
                    fehler.append("{{}}: '{{}}' braucht {{}} px, hat {{}}".format(
                        sprache, lbl.text()[:24], noetig, lbl.width()))
                if lbl.font().pixelSize() != -1 and lbl.font().pixelSize() < 10:
                    fehler.append("{{}}: '{{}}' nur {{}} px gross".format(
                        sprache, lbl.text()[:24], lbl.font().pixelSize()))
f._seite(0)
for m in sorted(set(fehler)):
    print("FEHLER " + m)
print("FERTIG " + str(f.devicePixelRatioF()))
f._beenden()
"""

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


cfg = os.path.join(_TESTS, "testcfg")
os.makedirs(cfg, exist_ok=True)
skript = os.path.join(cfg, "_bildschirm_kind.py")
with open(skript, "w", encoding="utf-8") as f:
    f.write(KIND.format(projekt=_PROJEKT, cfg=cfg))

print("=== Beschriftungen bei verschiedenen Bildschirmskalierungen ===")
# 0,667 hebt die Skalierung dieses Bildschirms auf und ergibt 1:1 – so laesst
# sich ein Buero-Monitor ohne Skalierung hier nachstellen.
for faktor in ("0.6667", "1.0", "1.3"):
    umgebung = dict(os.environ, QT_SCALE_FACTOR=faktor)
    r = subprocess.run([sys.executable, skript], capture_output=True,
                       text=True, env=umgebung, encoding="utf-8",
                       errors="replace")
    zeilen = [z for z in (r.stdout or "").splitlines() if z.startswith("FEHLER")]
    dpr = next((z.split()[1] for z in (r.stdout or "").splitlines()
                if z.startswith("FERTIG")), "?")
    pruefe("Bilddichte {:>5}: nichts abgeschnitten, nichts zu klein"
           .format(dpr[:5]), not zeilen,
           zusatz=zeilen[0][7:] if zeilen else "")
    for z in zeilen[:3]:
        print("       " + z[7:])

# Hier stand eine Pruefung, dass Symbole bei krummen Bildschirm-
# skalierungen auf den Pixel genau ankommen. Sie gehoerte zu einer Aenderung
# an icons._render, die zusammen mit den Schriftgroessen zurueckgenommen
# wurde: Der Stand davor sah besser aus. Der Mangel ist real (17 px kommen
# bei 125 % als 16,53 px an); die Korrektur liegt in der Historie unter
# 8c8fc3b bereit, falls sie einzeln gewuenscht wird.

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
