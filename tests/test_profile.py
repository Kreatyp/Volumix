# -*- coding: utf-8 -*-
"""Profile: blaettern, anlegen, umbenennen – und Einstellungen je Profil."""
import os
import sys
import time

# Projekt- und Testordner selbst finden – laeuft dadurch von ueberall
_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config                                     # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config.json")
if os.path.exists(config.CONFIG_PATH):
    os.remove(config.CONFIG_PATH)

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
for _ in range(160):
    app.processEvents()
    if f.rows:
        break
    time.sleep(0.05)


def warten(n=15):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.02)


print("\n=== Es gibt immer ein offenes Profil ===")
pruefe("eins angelegt", len(f.profiles) == 1, str(list(f.profiles)))
pruefe("und geoeffnet", f.cfg["profil"] in f.profiles, repr(f.cfg["profil"]))
pruefe("Name steht in der Leiste",
       f.profil_name.text() == f.cfg["profil"], f.profil_name.text())
pruefe("Pfeile aus, solange es nur eins gibt",
       not f.btn_prof_zurueck.isEnabled() and not f.btn_prof_vor.isEnabled())

erstes = f.cfg["profil"]

print("\n=== Zweites Profil anlegen ===")
# Der Dialog wuerde blockieren – wir gehen den Weg dahinter.
f._profil_sichern()
f.profiles["Zocken"] = f._profil_abbild()
f.cfg["profil"] = "Zocken"
f._profilleiste_auffrischen()
f._speichern()
pruefe("zwei Profile da", len(f.profiles) == 2, str(sorted(f.profiles)))
pruefe("das neue ist offen", f.cfg["profil"] == "Zocken")
pruefe("Pfeile jetzt an",
       f.btn_prof_zurueck.isEnabled() and f.btn_prof_vor.isEnabled())

print("\n=== Einstellungen gehoeren zum Profil ===")
f._farbe_setzen("lime")
f._tempo_setzen(95)
f._tempo_apps_setzen(15)
warten()
pruefe("Farbe im offenen Profil gelandet",
       f.profiles["Zocken"]["accent"] == "lime",
       str(f.profiles["Zocken"].get("accent")))
pruefe("Geschwindigkeit ebenfalls",
       f.profiles["Zocken"]["speed"] == 95
       and f.profiles["Zocken"]["speed_apps"] == 15)
pruefe("das andere Profil blieb unberuehrt",
       f.profiles[erstes]["accent"] != "lime",
       str(f.profiles[erstes].get("accent")))

print("\n=== Blaettern ===")
f._profil_blaettern(1)
warten(30)
pruefe("anderes Profil offen", f.cfg["profil"] == erstes, f.cfg["profil"])
pruefe("Farbe mitgewandert", f.theme.accent_key != "lime",
       f.theme.accent_key)
pruefe("Geschwindigkeit mitgewandert", f.cfg["speed"] != 95,
       str(f.cfg["speed"]))

f._profil_blaettern(1)
warten(30)
pruefe("und wieder zurueck", f.cfg["profil"] == "Zocken", f.cfg["profil"])
pruefe("Farbe wieder da", f.theme.accent_key == "lime", f.theme.accent_key)
pruefe("Geschwindigkeit wieder da", f.cfg["speed"] == 95, str(f.cfg["speed"]))
pruefe("Leiste zeigt den Namen", f.profil_name.text() == "Zocken",
       f.profil_name.text())

print("\n=== Auf der Platte ===")
gespeichert = config.load()
pruefe("beide Profile gesichert", len(gespeichert["profiles"]) == 2)
pruefe("offenes Profil vermerkt", gespeichert["profil"] == "Zocken",
       repr(gespeichert.get("profil")))
pruefe("Farbe steht im Profil",
       gespeichert["profiles"]["Zocken"]["accent"] == "lime")

print("\n=== Umbenennen und Loeschen ===")
f.profiles["Neuer Name"] = f.profiles.pop("Zocken")
f.cfg["profil"] = "Neuer Name"
f._profilleiste_auffrischen()
f._speichern()
pruefe("Umbenennen laesst die Zahl gleich", len(f.profiles) == 2)
f._profil_loeschen("Neuer Name")
warten(30)
pruefe("geloescht", "Neuer Name" not in f.profiles, str(sorted(f.profiles)))
pruefe("das verbliebene ist offen", f.cfg["profil"] == erstes)
f._profil_loeschen(erstes)
pruefe("das letzte laesst sich nicht loeschen", len(f.profiles) == 1)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
