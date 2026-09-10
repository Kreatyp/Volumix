# -*- coding: utf-8 -*-
r"""Autostart – und vor allem: NICHT ueber die Registry.

Der Weg ueber HKCU\...\CurrentVersion\Run hat Volumix zweimal in die
Quarantaene gebracht. Beim zweiten Mal stand der Run-Schluessel ausdruecklich
in Defenders Fundmeldung, neben der .exe und der Taskleisten-Verknuepfung.
Es ist derselbe Weg, auf dem sich Schadsoftware verankert - technisch
unauffaellig, fuer eine Heuristik aber ein Merkmal.

Diese Reihe haelt fest, dass es dabei bleibt: Verknuepfung ja, Run-Key nein.
"""
import os
import shutil
import sys
import tempfile
import winreg

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


def run_key_wert(name):
    """Was steht unter Run? None, wenn nichts."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, config.RUN_KEY, 0,
                             winreg.KEY_READ)
        try:
            wert, _ = winreg.QueryValueEx(key, name)
            return wert
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None


# Eigener APPDATA-Ordner: Der echte Autostart des Rechners bleibt unberuehrt.
ORDNER = tempfile.mkdtemp(prefix="volumix_auto_")
config._APPDATA = ORDNER
vorher_echt = run_key_wert(config.RUN_VALUE)

print("=== Einschalten legt eine Verknuepfung an ===")
config.set_autostart(True)
lnk = config.autostart_lnk()
pruefe("Verknuepfung liegt im Autostart-Ordner", os.path.exists(lnk), True,
       os.path.basename(lnk))
pruefe("und wird auch so gefunden", config.get_autostart())
pruefe("sie liegt unter Startup",
       "Startup" in lnk and "Start Menu" in lnk)

print("\n=== Sie zeigt auf etwas Ausfuehrbares ===")
try:
    import comtypes.client
    shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
    k = shell.CreateShortcut(lnk)
    ziel, args = k.TargetPath, k.Arguments
    pruefe("Ziel vorhanden", bool(ziel), True, ziel)
    pruefe("Ziel gibt es wirklich", os.path.exists(ziel))
    pruefe("startet in den Infobereich", "--tray" in (args or ""), True,
           args)
except Exception as e:
    pruefe("Verknuepfung lesbar", False, True, str(e))

print("\n=== Kein Registry-Eintrag, unter keinen Umstaenden ===")
pruefe("nichts unter Run", run_key_wert(config.RUN_VALUE), None)
pruefe("auch nicht unter dem alten Namen",
       run_key_wert(config.OLD_RUN_VALUE), None)

print("\n=== Ausschalten raeumt auf ===")
config.set_autostart(False)
pruefe("Verknuepfung weg", os.path.exists(lnk), False)
pruefe("und gilt als aus", config.get_autostart(), False)

print("\n=== Zweimal ausschalten stoert nicht ===")
config.set_autostart(False)
pruefe("bleibt aus", config.get_autostart(), False)

print("\n=== Ein alter Run-Eintrag wird mit entfernt ===")
# So sah es frueher aus – wer von einer aelteren Fassung kommt, hat das noch.
key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, config.RUN_KEY)
winreg.SetValueEx(key, config.OLD_RUN_VALUE, 0, winreg.REG_SZ,
                  r'"C:\alt\Volumix.exe" --tray')
winreg.CloseKey(key)
pruefe("Altlast angelegt", run_key_wert(config.OLD_RUN_VALUE) is not None)
config.set_autostart(True)
pruefe("beim Einschalten entfernt",
       run_key_wert(config.OLD_RUN_VALUE), None)
config.set_autostart(False)

shutil.rmtree(ORDNER, ignore_errors=True)
if vorher_echt is not None:
    print("\n  Hinweis: der echte Rechner hatte einen Run-Eintrag –"
          " unberuehrt geblieben")

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
