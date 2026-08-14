# -*- coding: utf-8 -*-
"""Eine kaputte Einstellungsdatei darf niemanden seine Profile kosten.

Der Fall ist wirklich passiert: Eine Datei mit BOM war fuer Volumix
unlesbar, es startete mit Werkseinstellungen und schrieb sie darueber.
Profile, Farbe und angehakte Apps waren weg, ohne Hinweis.
"""
import io
import json
import os
import shutil
import sys
import tempfile

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix import config                                      # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


ORDNER = tempfile.mkdtemp(prefix="volumix_test_")
config.CONFIG_DIR = ORDNER
config.CONFIG_PATH = os.path.join(ORDNER, "config.json")

ECHT = {"accent": "red", "sprache": "de", "mode": "dark",
        "targets": ["discord.exe"],
        "profiles": {"Normal": {"master": 0.5}, "Zocken": {"master": 0.7}}}

print("=== Datei mit BOM, wie Windows-Werkzeuge sie schreiben ===")
with io.open(config.CONFIG_PATH, "w", encoding="utf-8-sig") as f:
    json.dump(ECHT, f)
cfg = config.load()
pruefe("Akzentfarbe kommt an", cfg["accent"], "red")
pruefe("Profile kommen an", sorted(cfg["profiles"]), ["Normal", "Zocken"])
pruefe("angehakte Apps kommen an", cfg["targets"], ["discord.exe"])
pruefe("Datei liegt noch da", os.path.exists(config.CONFIG_PATH))

print("\n=== Datei ohne BOM ===")
with io.open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(ECHT, f)
pruefe("liest sich genauso", config.load()["accent"], "red")

print("\n=== Wirklich kaputte Datei ===")
with io.open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
    f.write('{"accent": "red", das hier ist kein JSON')
cfg = config.load()
pruefe("startet trotzdem", isinstance(cfg, dict))
pruefe("mit Werkseinstellungen", cfg["accent"], config.DEFAULTS["accent"])
pruefe("die kaputte Datei ist nicht mehr an ihrem Platz",
       os.path.exists(config.CONFIG_PATH), False)
gerettet = [n for n in os.listdir(ORDNER) if ".unlesbar-" in n]
pruefe("sondern beiseitegelegt", len(gerettet), 1,
       gerettet[0] if gerettet else "")
if gerettet:
    inhalt = io.open(os.path.join(ORDNER, gerettet[0]), encoding="utf-8").read()
    pruefe("und noch vollstaendig da", "red" in inhalt)

print("\n=== Speichern legt sie wieder an ===")
config.save({"accent": "blue"})
pruefe("Datei wieder da", os.path.exists(config.CONFIG_PATH))
pruefe("ohne BOM geschrieben",
       io.open(config.CONFIG_PATH, "rb").read(1), b"{")

print("\n=== Fehlende Datei ist kein Fehler ===")
os.remove(config.CONFIG_PATH)
vorher = len(os.listdir(ORDNER))
cfg = config.load()
pruefe("Werkseinstellungen", cfg["accent"], config.DEFAULTS["accent"])
pruefe("und nichts beiseitegelegt", len(os.listdir(ORDNER)), vorher)

shutil.rmtree(ORDNER, ignore_errors=True)
print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
