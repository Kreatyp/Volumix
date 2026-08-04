# -*- coding: utf-8 -*-
"""Einstellungen, Autostart und Ablageorte.

Bewusst ohne Oberflaechen-Bezug – dieses Modul kennt weder Qt noch Audio.
"""
import json
import os
import sys

APP_NAME = "Volumix"
SYSTEM_KEY = "#system"
MASTER_KEY = "#master"          # Windows-Gesamtlautstaerke

_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(_APPDATA, APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = APP_NAME
OLD_RUN_VALUE = "ThumbwheelVolume"      # Altlast vor der Umbenennung

DEFAULTS = {
    "targets": [],
    # 10..100 % – wie schnell geregelt wird. Zwei Werte, weil eine einzelne
    # App feiner dosiert werden will als die Gesamtlautstaerke.
    "speed": 40,             # Gesamtlautstaerke
    "speed_apps": 20,        # einzelne Apps
    "speed_curve": True,     # leise Pegel in kleineren Schritten regeln
    "reverse": False,
    "active": True,
    "media_keys": False,     # Lautstaerke-Tasten statt Daumenrad
    "switch_mode": "none",   # was beim Wechsel Gesamt <-> App passiert
    "meters": True,          # Live-Pegel neben den Reglern
    "osd_enabled": True,
    "osd_size": 45,
    "osd_x": 50,
    "osd_y": 88,
    "sprache": "en",         # "de" oder "en" – Voreinstellung Englisch
    "accent": "violet",      # Schluessel aus theme.PALETTE
    "mode": "dark",
    "hidden": None,          # ausgeblendete Apps (None = Standardliste)
    "known": [],             # je gesehene Apps (Namensspeicher)
    "exes": {},              # key -> Pfad zur Programmdatei
    "profiles": {},          # Name -> Profil, siehe PROFIL_TEILE
    "profil": "",            # Name des aktiven Profils
    "window_h": 720,
}

# Was zu einem Profil gehoert. Alles andere in DEFAULTS gilt fuer das ganze
# Programm – Sprache, Autostart, Eingabeart und so weiter aendern sich nicht
# mit dem Profil, weil sie am Rechner haengen und nicht an der Stimmung.
PROFIL_TEILE = ["mode", "accent", "speed", "speed_apps", "speed_curve"]

# Prozesse, die zwar eine Audiositzung anlegen, aber praktisch nie Ton machen.
DEFAULT_HIDDEN = [
    "msedgewebview2.exe", "shellexperiencehost.exe", "textinputhost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "widgets.exe",
    "phoneexperiencehost.exe", "applicationframehost.exe",
]


def app_dir():
    """Ordner der Anwendung – bei der gepackten .exe deren Ablageort."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            daten = json.load(f)
    except Exception:
        daten = {}
    for k in DEFAULTS:
        if k in daten:
            cfg[k] = daten[k]
    # Frueher gab es nur eine Geschwindigkeit. Wer von damals kommt, behaelt
    # sie fuer beides – sonst regelt es nach dem Update ploetzlich anders.
    if "speed_apps" not in daten and "speed" in daten:
        cfg["speed_apps"] = cfg["speed"]
    if not isinstance(cfg.get("targets"), list):
        cfg["targets"] = []
    if not isinstance(cfg.get("hidden"), list):
        cfg["hidden"] = list(DEFAULT_HIDDEN)
    for k in ("known", "exes", "profiles"):
        if not isinstance(cfg.get(k), type(DEFAULTS[k])):
            cfg[k] = type(DEFAULTS[k])()
    return cfg


def save(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------
def gebaute_app():
    """Pfad zur fertigen .exe, falls sie gebaut wurde."""
    p = os.path.join(app_dir(), "programm", APP_NAME, APP_NAME + ".exe")
    return p if os.path.exists(p) else None


def _startbefehl():
    if getattr(sys, "frozen", False):
        return '"{}" --tray'.format(sys.executable)
    # Aus dem Quelltext heraus trotzdem die gebaute App eintragen: sonst
    # haengt der Autostart an einer Python-Installation und an einem
    # fehlerfreien Quelltext – ein Tippfehler, und Windows startet nichts.
    fertig = gebaute_app()
    if fertig:
        return '"{}" --tray'.format(fertig)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    ziel = os.path.join(app_dir(), "volumix.pyw")
    return '"{}" "{}" --tray'.format(pyw, ziel)


def get_autostart():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            wert, _ = winreg.QueryValueEx(key, RUN_VALUE)
            return bool(wert)
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(an):
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    except Exception:
        return
    try:
        if an:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, _startbefehl())
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def autostart_pruefen():
    """Zeigt der Autostart-Eintrag noch auf etwas Sinnvolles?

    Wird er aus dem Quelltext heraus gesetzt (beim Entwickeln), traegt er den
    Weg ueber Python ein. Sobald die App gebaut ist, soll er auf diese zeigen.
    """
    import winreg
    fertig = gebaute_app()
    if not fertig:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_READ)
        try:
            wert, _ = winreg.QueryValueEx(key, RUN_VALUE)
        finally:
            winreg.CloseKey(key)
    except Exception:
        return
    if wert and fertig.lower() not in wert.lower():
        set_autostart(True)


def migrate():
    """Einmaliger Umzug vom frueheren Namen „ThumbwheelVolume“."""
    alt_dir = os.path.join(_APPDATA, "ThumbwheelVolume")
    if not os.path.exists(CONFIG_PATH) and os.path.isdir(alt_dir):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            alt = os.path.join(alt_dir, "config.json")
            if os.path.exists(alt):
                with open(alt, "r", encoding="utf-8") as f:
                    daten = f.read()
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    f.write(daten)
        except Exception:
            pass
    # Alter Autostart-Eintrag zeigt auf eine .exe, die es nicht mehr gibt
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_READ | winreg.KEY_SET_VALUE)
    except Exception:
        return
    war_an = False
    try:
        try:
            wert, _ = winreg.QueryValueEx(key, OLD_RUN_VALUE)
            war_an = bool(wert)
            winreg.DeleteValue(key, OLD_RUN_VALUE)
        except FileNotFoundError:
            return
    except Exception:
        return
    finally:
        winreg.CloseKey(key)
    if war_an and not get_autostart():
        set_autostart(True)
