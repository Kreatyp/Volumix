# -*- coding: utf-8 -*-
"""
Volumix
=======
Lautstaerke-Mixer fuer einzelne Apps, gesteuert per Daumenrad oder
Lautstaerke-Tasten. Gebaut fuer die Logitech MX Master 4.

- Jede App hat einen eigenen Schieberegler (wie im Windows-Mixer) und ihr
  echtes Programm-Icon.
- Pro App ein Haken "per Daumenrad steuern"; das seitliche Daumenrad
  (horizontales Scrollen, WM_MOUSEHWHEEL) aendert die Lautstaerke aller so
  markierten Apps. Das normale, senkrechte Scrollrad bleibt unberuehrt.
- Alternativ lassen sich die Lautstaerke-Tasten abgreifen (Einstellungen).
- Fensterhoehe ist ziehbar, die Oberflaeche ist DPI-scharf.

Audio ueber pycaw, globaler Maus-Hook ueber pynput.
Autor: fuer Luis gebaut mit Claude Code.
"""

import os
import sys
import json
import math
import time
import queue
import hashlib
import colorsys
import threading
import ctypes
from ctypes import wintypes

# ---------------------------------------------------------------------------
# Nur eine Instanz zulassen; zweiter Start holt vorhandenes Fenster nach vorn.
# ---------------------------------------------------------------------------
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateMutexW.restype = wintypes.HANDLE
_k32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_k32.OpenEventW.restype = wintypes.HANDLE
_k32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
_k32.CreateEventW.restype = wintypes.HANDLE
_k32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
_k32.SetEvent.argtypes = [wintypes.HANDLE]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.WaitForSingleObject.restype = wintypes.DWORD
_k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

_ERROR_ALREADY_EXISTS = 183
_EVENT_MODIFY_STATE = 0x0002
_SHOW_EVENT_NAME = "Volumix_ShowEvent"

_mutex = _k32.CreateMutexW(None, False, "Volumix_SingleInstance")
if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
    _h = _k32.OpenEventW(_EVENT_MODIFY_STATE, False, _SHOW_EVENT_NAME)
    if _h:
        _k32.SetEvent(_h)
        _k32.CloseHandle(_h)
    sys.exit(0)
_show_event = _k32.CreateEventW(None, False, False, _SHOW_EVENT_NAME)

import tkinter as tk
import tkinter.font as tkfont

from pynput import mouse, keyboard
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CoInitialize, CoUninitialize
import pystray
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WM_MOUSEHWHEEL = 0x020E
WHEEL_DELTA = 120
SYSTEM_KEY = "#system"
MASTER_KEY = "#master"    # Windows-Gesamtlautstaerke

APP_NAME = "Volumix"
_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(_APPDATA, APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = APP_NAME

# --- Umzug vom frueheren Namen „ThumbwheelVolume“ -------------------------
# Muss VOR dem ersten Lesen laufen (_startup_theme liest die Datei direkt beim
# Import), sonst startet die App nach dem Umbenennen mit Standardwerten.
_OLD_DIR = os.path.join(_APPDATA, "ThumbwheelVolume")


def _migrate_config():
    """Uebernimmt einmalig die Einstellungen des alten Namens."""
    if os.path.exists(CONFIG_PATH) or not os.path.isdir(_OLD_DIR):
        return
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        alt = os.path.join(_OLD_DIR, "config.json")
        if os.path.exists(alt):
            with open(alt, "r", encoding="utf-8") as f:
                daten = f.read()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(daten)
    except Exception:
        pass          # im Zweifel lieber Standardwerte als gar kein Start


_migrate_config()

DEFAULTS = {
    "targets": [],
    "speed": 40,         # 10..100 % – wie schnell das Daumenrad regelt
    "step": 4,           # veraltet (wird in "speed" umgerechnet)
    "reverse": False,
    "suppress": True,
    "active": True,
    "osd_size": 45,      # 10..100 % – Groesse der Einblendung
    "osd_x": 50,         # 0..100 % – waagerechte Position
    "osd_y": 88,         # 0..100 % – senkrechte Position
    "osd_enabled": True,
    "media_keys": False,   # Lautstaerke-Tasten statt Daumenrad-Scrollen
    "switch_mode": "none",  # was beim Wechsel Gesamt <-> App passiert
    "skin": "default",   # Ordnername unter skins\
    "mode": "dark",      # "dark" oder "light"
    "hidden": None,      # ausgeblendete Apps (None = Standardliste nehmen)
    "known": [],         # je gesehene Apps, fuer die Sichtbarkeits-Liste
    "exes": {},          # key -> Pfad zur Programmdatei (fuer die Symbole)
}

# Verhalten beim Umschalten zwischen Gesamtlautstaerke und einzelnen Apps.
SWITCH_MODES = [
    ("none", "Nichts ändern"),
    ("carry", "Pegel mitnehmen"),
    ("apps100", "Apps auf 100 %"),
]
# Erklaerung hinter dem Fragezeichen. Feste Zeilenumbrueche, damit die Blase
# eine ruhige Breite behaelt – Tk bricht in einem Canvas nicht von selbst um.
SWITCH_HELP = (
    "Was du hörst, ist App-Pegel × Gesamtlautstärke. Beim Umschalten\n"
    "wandert die Steuerung von einem Regler auf den anderen.\n"
    "\n"
    "Nichts ändern – alle Pegel bleiben, wie sie sind.\n"
    "Pegel mitnehmen – es klingt nach dem Wechsel gleich laut,\n"
    "kein plötzlicher Sprung nach oben.\n"
    "Apps auf 100 % – beim Wechsel auf die Gesamtlautstärke gehen\n"
    "alle Apps auf 100 %."
)

# Prozesse, die zwar eine Audiositzung anlegen, aber praktisch nie Ton machen.
DEFAULT_HIDDEN = [
    "msedgewebview2.exe", "shellexperiencehost.exe", "textinputhost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "widgets.exe",
    "phoneexperiencehost.exe", "applicationframehost.exe",
]


# ---------------------------------------------------------------------------
# Skin-System
# ---------------------------------------------------------------------------
# Ein Skin ist ein Ordner unter skins\ mit einer theme.json (Farben, Masse,
# Schrift) und optional einem Unterordner images\ mit PNG-Dateien, die einzelne
# gezeichnete Elemente ersetzen. Farben/Masse bleiben in jeder Aufloesung
# gestochen scharf – PNGs sind nur fuer Sonderfaelle gedacht.
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


SKINS_DIR = os.path.join(app_dir(), "skins")

# --- Farbhelfer (muessen vor dem ersten load_skin() bereitstehen) ---
def _hex_rgb(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _mix(c1, c2, t):
    """Mischt zwei Farben. Ergebnis ist immer "#RRGGBB" – Tk versteht nur das."""
    a = _hex_rgb(c1) if isinstance(c1, str) else tuple(c1[:3])
    b = _hex_rgb(c2) if isinstance(c2, str) else tuple(c2[:3])
    v = [max(0, min(255, int(round(a[i] + (b[i] - a[i]) * t)))) for i in range(3)]
    return "#{:02X}{:02X}{:02X}".format(*v)


def _shift(color, factor):
    """Farbe aufhellen (factor > 1) oder abdunkeln (factor < 1)."""
    r, g, b = _hex_rgb(color) if isinstance(color, str) else tuple(color[:3])
    f = lambda v: max(0, min(255, int(round(v * factor))))
    return (f(r), f(g), f(b))


# Die neutralen Farben (Grautoene) kommen IMMER vom Modus – ein Skin bestimmt
# nur noch die bunten Anteile (siehe BASE_THEME["accent"]).
NEUTRAL = {
    "dark": {
        "bg": "#131419",            # Fensterhintergrund
        "card": "#1C1E26",          # Karten / Panels
        "card2": "#2B303C",         # Eingabeflaechen, Regler-Schiene
        "stroke": "#343A48",        # feine Linien, Hover
        "fg": "#F4F5F7",            # Haupttext
        "muted": "#A6ADBD",         # Sekundaertext (heller = besser lesbar)
        "knob": "#FFFFFF",          # Schieberegler-/Toggle-Knopf
        "off": "#3B4150",           # Schalter aus
    },
    "light": {
        "bg": "#EFF1F5",
        "card": "#FFFFFF",
        "card2": "#DFE4EC",
        "stroke": "#C9D0DC",
        "fg": "#181A20",
        "muted": "#5C6472",
        "knob": "#FFFFFF",
        "off": "#BFC6D2",
    },
}

BASE_THEME = {
    "name": "Violett",
    # Die bunten Anteile – das macht einen Skin aus.
    "accent": {"dark": "#7C5CFF", "light": "#6C4CF5"},
    "accent_hover": {"dark": "#8E72FF", "light": "#5B3CE0"},
    "red": {"dark": "#FF5C7C", "light": "#E5484D"},
    "metrics": {
        "window_w": 520,            # Fensterbreite
        "window_h": 720,            # Fensterhoehe
        "card_radius": 16,          # Eckenradius der Panels
        "button_radius": 10,
        "toggle_w": 48, "toggle_h": 27,
        "check_size": 24,           # Auswahl-Kaestchen im Mixer
        "slider_track": 6, "slider_knob": 19,
        "row_icon": 32,             # App-Symbol in der Mixer-Zeile
        "row_radius": 12,           # Eckenradius der Mixer-Zeile
        "osd_w": 340, "osd_h": 96, "osd_radius": 20, "osd_icon": 30,
        "osd_font_name": 18,        # Schriftgroesse App-Name in der Einblendung
        "osd_font_pct": 21,         # Schriftgroesse Prozentzahl
        "osd_shadow": 16,           # Schattenrand um die Einblendung
        "window_chrome": 152,       # Hoehe von Kopf + Statusleiste + Raendern
    },
    "fonts": {
        "family": "Segoe UI",
        "family_semi": "Segoe UI Semibold",
        "size_scale": 1.0,          # globaler Schriftgroessen-Faktor
    },
}


def _deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# Prozessnamen, die als Anzeigename wenig hergeben
_NAME_MAP = {
    "msedgewebview2": "Edge WebView",
    "shellexperiencehost": "Windows-Oberfläche",
    "javaw": "Java",
    "java": "Java",
    "steamwebhelper": "Steam",
    "explorer": "Windows-Explorer",
    "audiodg": "Audio-Dienst",
}


def speed_to_step(speed):
    """Geschwindigkeit (10..100 %) -> Prozentpunkte je Rastung.

    Die Aenderung wird nicht in einem Sprung gesetzt, sondern in
    1-Prozent-Schritten nachgefahren (siehe App._animate_volumes) – deshalb
    wirkt auch eine grosse Schrittweite fluessig.
    """
    s = max(10.0, min(100.0, float(speed)))
    return 0.8 + (s - 10.0) / 90.0 * 3.4        # 0,8 .. 4,2 Prozentpunkte


def _pretty_name(pname):
    """Prozessname -> Anzeigename ("chrome.exe" -> "Chrome")."""
    base = pname[:-4] if pname.lower().endswith(".exe") else pname
    mapped = _NAME_MAP.get(base.lower())
    if mapped:
        return mapped
    return base.capitalize() if base.islower() else base


THEME_NAMES = {}     # Ordnername -> Anzeigename aus der theme.json


def list_skins():
    names = []
    try:
        for d in sorted(os.listdir(SKINS_DIR)):
            path = os.path.join(SKINS_DIR, d, "theme.json")
            if os.path.isfile(path):
                names.append(d)
                if d not in THEME_NAMES:
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            THEME_NAMES[d] = json.load(f).get("name", d)
                    except Exception:
                        THEME_NAMES[d] = d
    except Exception:
        pass
    return names or ["default"]


# Auswahlfarben. Alle sind so gewaehlt, dass weisse Schrift darauf lesbar
# bleibt (Kontrast >= 3:1) – im hellen Modus entsprechend dunkler.
PALETTE = [
    ("violett", "Violett", "#7C5CFF", "#6641E8"),
    ("blau", "Blau", "#3B82F6", "#2563EB"),
    ("tuerkis", "Türkis", "#0EA5A5", "#0F8A8A"),
    ("gruen", "Grün", "#22A85B", "#15803D"),
    ("oliv", "Oliv", "#7A9A2E", "#5F7A22"),
    ("bernstein", "Bernstein", "#C97B10", "#A85F08"),
    ("orange", "Orange", "#E06A28", "#C2521A"),
    ("rot", "Rot", "#E0483F", "#C22F27"),
    ("pink", "Pink", "#DB3B7C", "#BE2963"),
    ("magenta", "Magenta", "#A855C7", "#8B3FA8"),
    ("stahl", "Stahl", "#5A7089", "#465A70"),
    ("grafit", "Grafit", "#6B7280", "#4B5563"),
]

CUSTOM_COLOR = None   # Schluessel aus PALETTE – ueberschreibt die Skin-Farbe


def palette_color(key, light=False):
    for k, _label, dark_c, light_c in PALETTE:
        if k == key:
            return light_c if light else dark_c
    return None


THEME = BASE_THEME
SKIN_NAME = "default"
SKIN_IMG_DIR = None
MODE = "dark"          # "dark" oder "light"
IS_LIGHT = False

# Farben/Masse als Modul-Globals, damit sie ueberall knapp nutzbar sind.
BG = CARD = CARD2 = STROKE = FG = MUTED = ACCENT = ACCENT_HOVER = RED = KNOB = OFF = "#000000"
FONT = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"
FONT_SCALE = 1.0
M = dict(BASE_THEME["metrics"])
BASE_W = 520

SCALE = 1.0     # System-DPI (fix nach Start)


def load_skin(name, mode="dark", color=-1):
    """`color`: -1 = unveraendert, None = Skin-Farbe, sonst Schluessel aus PALETTE."""
    global CUSTOM_COLOR
    if color != -1:
        CUSTOM_COLOR = color
    return _load_skin(name, mode)


def _load_skin(name, mode="dark"):
    """Laedt skins\\<name>\\theme.json. Fehlende Werte kommen aus BASE_THEME.

    Kann jederzeit erneut aufgerufen werden (Skin-/Modus-Wechsel im Betrieb) –
    die Oberflaeche muss danach neu aufgebaut und der Bild-Cache geleert werden.
    """
    global THEME, SKIN_NAME, SKIN_IMG_DIR, M, BASE_W, MODE, IS_LIGHT
    global BG, CARD, CARD2, STROKE, FG, MUTED, ACCENT, ACCENT_HOVER, RED, KNOB, OFF
    global FONT, FONT_SEMI, FONT_SCALE
    data = {}
    path = os.path.join(SKINS_DIR, name, "theme.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        name = "default"
    THEME = _deep_merge(BASE_THEME, data)
    SKIN_NAME = name
    MODE = "light" if mode == "light" else "dark"
    IS_LIGHT = (MODE == "light")
    img_dir = os.path.join(SKINS_DIR, name, "images")
    SKIN_IMG_DIR = img_dir if os.path.isdir(img_dir) else None

    def pick(entry, fallback):
        """Akzent kann je Modus gesetzt sein ({"dark":..,"light":..}) oder fest."""
        if isinstance(entry, dict):
            return entry.get(MODE, entry.get("dark", fallback))
        return entry or fallback

    c = dict(NEUTRAL[MODE])
    # Fortgeschrittene duerfen die neutralen Toene ueberschreiben
    c.update(THEME.get("colors_light" if IS_LIGHT else "colors", {}) or {})
    BG, CARD, CARD2, STROKE = c["bg"], c["card"], c["card2"], c["stroke"]
    FG, MUTED = c["fg"], c["muted"]
    KNOB, OFF = c["knob"], c["off"]
    custom = palette_color(CUSTOM_COLOR, IS_LIGHT) if CUSTOM_COLOR else None
    if custom:
        ACCENT = custom
        ACCENT_HOVER = _mix(ACCENT, "#FFFFFF" if not IS_LIGHT else "#000000", 0.16)
    else:
        ACCENT = pick(THEME.get("accent"), "#7C5CFF")
        ACCENT_HOVER = pick(THEME.get("accent_hover"), ACCENT)
    RED = pick(THEME.get("red"), "#FF5C7C")
    M = THEME["metrics"]
    BASE_W = M.get("window_w", 520)
    f = THEME["fonts"]
    FONT, FONT_SEMI = f["family"], f["family_semi"]
    FONT_SCALE = float(f.get("size_scale", 1.0))


# --- Verlaufsfarben (geben den Flaechen Tiefe, ohne aufdringlich zu wirken) ---
def card_top():
    """Oberkante einer Karte: im dunklen Modus leicht aufgehellt."""
    return CARD if IS_LIGHT else _mix(CARD, "#FFFFFF", 0.055)


def card_bottom():
    """Unterkante: im hellen Modus leicht abgedunkelt (Karte ist dort weiss)."""
    return _mix(CARD, BG, 0.45) if IS_LIGHT else CARD


def row_top():
    """Ausgewaehlte Zeile: leichter Akzent-Schimmer von oben."""
    return _mix(CARD2, ACCENT, 0.18 if not IS_LIGHT else 0.14)


def row_bottom():
    return _mix(CARD2, ACCENT, 0.03)


def _startup_theme():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("skin", "default"), d.get("mode", "dark"), d.get("color", None)
    except Exception:
        return "default", "dark", None


load_skin(*_startup_theme())


def px(v):
    return max(1, int(round(v * SCALE)))


def uifont(basepx, semi=False):
    return ((FONT_SEMI if semi else FONT), -px(basepx * FONT_SCALE))


def _round_pts(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if "targets" not in data and data.get("target"):
        data["targets"] = [data["target"]]
    for k in DEFAULTS:
        if k in data:
            cfg[k] = data[k]
    if not isinstance(cfg.get("targets"), list):
        cfg["targets"] = []
    if not isinstance(cfg.get("hidden"), list):
        cfg["hidden"] = list(DEFAULT_HIDDEN)
    if not isinstance(cfg.get("known"), list):
        cfg["known"] = []
    return cfg


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------
def _pythonw():
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.exists(cand) else exe


OLD_RUN_VALUE = "ThumbwheelVolume"


def get_autostart():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, RUN_VALUE)
            return bool(val)
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def migrate_autostart():
    """Alten Autostart-Eintrag ablegen und – falls aktiv – neu setzen.

    Der alte Eintrag zeigt auf `Thumbwheel-Lautstaerke.exe`, die es nach dem
    Umbenennen nicht mehr gibt. Bliebe er stehen, meldete Windows bei jedem
    Hochfahren einen Fehler.
    """
    import winreg
    war_an = False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_READ | winreg.KEY_SET_VALUE)
    except Exception:
        return
    try:
        try:
            val, _ = winreg.QueryValueEx(key, OLD_RUN_VALUE)
            war_an = bool(val)
            winreg.DeleteValue(key, OLD_RUN_VALUE)
        except FileNotFoundError:
            return
    except Exception:
        return
    finally:
        winreg.CloseKey(key)
    if war_an and not get_autostart():
        set_autostart(True)          # jetzt mit dem neuen Pfad


def set_autostart(enable):
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    try:
        if enable:
            # --tray: beim Hochfahren still in den Infobereich starten,
            # statt dem Nutzer das Fenster ins Gesicht zu setzen
            if getattr(sys, "frozen", False):
                cmd = '"{}" --tray'.format(sys.executable)
            else:
                cmd = '"{}" "{}" --tray'.format(_pythonw(), os.path.abspath(__file__))
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


# ---------------------------------------------------------------------------
# Tray-/Fenster-Icon
# ---------------------------------------------------------------------------
def _vertical_gradient(size, top, bottom):
    grad = Image.new("RGB", (1, size), top)
    px_ = grad.load()
    for y in range(size):
        t = y / float(max(1, size - 1))
        px_[0, y] = tuple(int(round(top[i] + (bottom[i] - top[i]) * t)) for i in range(3))
    return grad.resize((size, size), Image.BILINEAR)


def make_icon_image(size=256, color=None):
    """App-Logo: abgerundete Kachel mit Farbverlauf, darin Lautsprecher + Wellen."""
    base = color or (ACCENT if ACCENT.startswith("#") else "#7C5CFF")
    m = 4
    s = size * m
    top = _shift(base, 1.18)
    bottom = _shift(base, 0.78)

    # Kachel mit Verlauf
    tile = _vertical_gradient(s, top, bottom).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.235), fill=255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(tile, (0, 0), mask)

    # sanfter Glanz oben
    gloss = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([-s * 0.35, -s * 0.75, s * 1.35, s * 0.42],
                                  fill=(255, 255, 255, 26))
    img = Image.alpha_composite(img, Image.composite(
        gloss, Image.new("RGBA", (s, s), (0, 0, 0, 0)), mask))

    d = ImageDraw.Draw(img)
    w = (255, 255, 255, 255)

    def sc(x, y):
        return (x / 100.0 * s, y / 100.0 * s)

    # Lautsprecher: Korpus + Kegel
    d.rounded_rectangle([*sc(22, 41), *sc(35, 59)], radius=int(s * 0.025), fill=w)
    d.polygon([sc(33, 41), sc(50, 24), sc(50, 76), sc(33, 59)], fill=w)
    # Schallwellen
    lw = max(2, int(s * 0.042))
    d.arc([*sc(50, 33), *sc(70, 67)], -62, 62, fill=w, width=lw)
    d.arc([*sc(54, 22), *sc(84, 78)], -60, 60, fill=w, width=lw)

    return img.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Echte App-Icons aus der EXE extrahieren (Windows-API via ctypes)
# ---------------------------------------------------------------------------
_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HBITMAP),
                ("hbmColor", wintypes.HBITMAP)]


# 64-bit-sichere Signaturen (Handles sind zeigergross)
_user32.GetDC.restype = ctypes.c_void_p
_user32.GetDC.argtypes = [wintypes.HWND]
_user32.ReleaseDC.argtypes = [wintypes.HWND, ctypes.c_void_p]
_user32.GetIconInfo.restype = wintypes.BOOL
_user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ICONINFO)]
_user32.DestroyIcon.argtypes = [ctypes.c_void_p]
_user32.PrivateExtractIconsW.restype = ctypes.c_uint
_user32.PrivateExtractIconsW.argtypes = [
    wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT),
    wintypes.UINT, wintypes.DWORD]
_gdi32.GetDIBits.restype = ctypes.c_int
_gdi32.GetDIBits.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.POINTER(_BITMAPINFOHEADER), wintypes.UINT]
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]


def _dib_bytes(hbm, size):
    bmi = _BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(bmi)
    bmi.biWidth = size
    bmi.biHeight = -size
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0
    buf = (ctypes.c_ubyte * (size * size * 4))()
    hdc = _user32.GetDC(0)
    try:
        got = _gdi32.GetDIBits(hdc, hbm, 0, size, buf, ctypes.byref(bmi), 0)
    finally:
        _user32.ReleaseDC(0, hdc)
    return bytes(buf) if got else None


def _hicon_to_pil(hicon, size):
    ii = _ICONINFO()
    if not _user32.GetIconInfo(hicon, ctypes.byref(ii)):
        return None
    try:
        color = _dib_bytes(ii.hbmColor, size)
        if color is None:
            return None
        img = Image.frombuffer("RGBA", (size, size), color, "raw", "BGRA", 0, 1)
        if img.getextrema()[3][1] == 0:  # kein Alpha -> aus Maske ableiten
            mask = _dib_bytes(ii.hbmMask, size)
            if mask is not None:
                mimg = Image.frombuffer("RGBA", (size, size), mask, "raw", "BGRA", 0, 1)
                a = mimg.convert("L").point(lambda p: 0 if p > 127 else 255)
                img = Image.merge("RGBA", (*img.convert("RGB").split(), a))
        return img
    finally:
        if ii.hbmColor:
            _gdi32.DeleteObject(ii.hbmColor)
        if ii.hbmMask:
            _gdi32.DeleteObject(ii.hbmMask)


def _extract_exe_icon(path, size):
    if not path:
        return None
    try:
        _user32.PrivateExtractIconsW.restype = ctypes.c_uint
        hicon = wintypes.HICON()
        iconid = wintypes.UINT()
        n = _user32.PrivateExtractIconsW(ctypes.c_wchar_p(path), 0, size, size,
                                         ctypes.byref(hicon), ctypes.byref(iconid), 1, 0)
        if n < 1 or not hicon.value:
            return None
        try:
            return _hicon_to_pil(hicon.value, size)
        finally:
            _user32.DestroyIcon(hicon)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Anti-aliased Grafiken via Pillow -> Tk-PhotoImage (gecacht)
# ---------------------------------------------------------------------------
_PHOTO_CACHE = {}
_ICON_PIL = {}   # exe-Pfad -> PIL (Basisgroesse) oder None
_SS = 4


def _to_photo(pil_img):
    import io, base64
    bio = io.BytesIO()
    pil_img.save(bio, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(bio.getvalue()))


def skin_image(name, w, h):
    """PNG-Override aus skins\\<skin>\\images\\<name>.png (oder None)."""
    if SKIN_IMG_DIR is None:
        return None
    key = ("skin", SKIN_NAME, name, w, h)
    if key in _PHOTO_CACHE:
        return _PHOTO_CACHE[key]
    path = os.path.join(SKIN_IMG_DIR, name + ".png")
    if not os.path.isfile(path):
        _PHOTO_CACHE[key] = None
        return None
    try:
        im = Image.open(path).convert("RGBA")
        if im.size != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
        ph = _to_photo(im)
    except Exception:
        ph = None
    _PHOTO_CACHE[key] = ph
    return ph


_CORNER_CACHE = {}


def _corner_tile(r, fill, outline, ow):
    """2r x 2r grosses, geglaettetes Eck-Set – haengt NICHT von w/h ab."""
    key = (r, fill, outline, ow)
    tile = _CORNER_CACHE.get(key)
    if tile is None:
        s = 2 * r * _SS
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle(
            [0, 0, s - 1, s - 1], radius=r * _SS,
            fill=fill, outline=outline, width=max(1, ow * _SS) if outline else 0)
        tile = im.resize((2 * r, 2 * r), Image.LANCZOS)
        _CORNER_CACHE[key] = tile
    return tile


def rounded_photo(w, h, r, fill, outline=None, ow=0):
    """Abgerundetes Rechteck.

    Grosse Flaechen werden aus einer einfarbigen Basis plus vier gecachten
    Ecken zusammengesetzt, statt das ganze Bild vierfach hochaufgeloest zu
    rendern – sonst kostet jede Karte hunderte Millisekunden.
    """
    key = ("rr", w, h, r, fill, outline, ow)
    ph = _PHOTO_CACHE.get(key)
    if ph is not None:
        return ph
    r = max(0, min(r, w // 2, h // 2))
    if r < 2:
        im = Image.new("RGBA", (w, h), fill)
        if outline and ow:
            ImageDraw.Draw(im).rectangle([0, 0, w - 1, h - 1], outline=outline, width=ow)
    else:
        im = Image.new("RGBA", (w, h), fill)
        t = _corner_tile(r, fill, outline, ow)
        im.paste(t.crop((0, 0, r, r)), (0, 0))
        im.paste(t.crop((r, 0, 2 * r, r)), (w - r, 0))
        im.paste(t.crop((0, r, r, 2 * r)), (0, h - r))
        im.paste(t.crop((r, r, 2 * r, 2 * r)), (w - r, h - r))
        if outline and ow:
            d = ImageDraw.Draw(im)
            d.rectangle([r, 0, w - r - 1, ow - 1], fill=outline)
            d.rectangle([r, h - ow, w - r - 1, h - 1], fill=outline)
            d.rectangle([0, r, ow - 1, h - r - 1], fill=outline)
            d.rectangle([w - ow, r, w - 1, h - r - 1], fill=outline)
    ph = _to_photo(im)
    _PHOTO_CACHE[key] = ph
    return ph


_MASK_CACHE = {}


def _corner_mask(r):
    """Geglaettete Eckmaske (2r x 2r), unabhaengig von der Flaechengroesse."""
    mk = _MASK_CACHE.get(r)
    if mk is None:
        s = 2 * r * _SS
        im = Image.new("L", (s, s), 0)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, s - 1, s - 1],
                                             radius=r * _SS, fill=255)
        mk = im.resize((2 * r, 2 * r), Image.LANCZOS)
        _MASK_CACHE[r] = mk
    return mk


def _to_pil_gradient(w, h, c1, c2, horizontal=False):
    """Verlauf als PIL-Bild (fuer Kompositionen innerhalb anderer Grafiken)."""
    n = max(2, w if horizontal else h)
    strip = Image.new("RGB", (n, 1) if horizontal else (1, n))
    load = strip.load()
    for i in range(n):
        col = _hex_rgb(_mix(c1, c2, i / float(n - 1)))
        if horizontal:
            load[i, 0] = col
        else:
            load[0, i] = col
    return strip.resize((max(1, w), max(1, h)), Image.BILINEAR).convert("RGBA")


def gradient_photo(w, h, r, c1, c2, horizontal=False):
    """Abgerundete Flaeche mit weichem Farbverlauf."""
    key = ("gr", w, h, r, str(c1), str(c2), horizontal)
    ph = _PHOTO_CACHE.get(key)
    if ph is not None:
        return ph
    w, h = max(1, w), max(1, h)
    n = max(2, w if horizontal else h)
    strip = Image.new("RGB", (n, 1) if horizontal else (1, n))
    load = strip.load()
    for i in range(n):
        col = _hex_rgb(_mix(c1, c2, i / float(n - 1)))
        if horizontal:
            load[i, 0] = col
        else:
            load[0, i] = col
    img = strip.resize((w, h), Image.BILINEAR).convert("RGBA")

    r = max(0, min(r, w // 2, h // 2))
    if r >= 2:
        mask = Image.new("L", (w, h), 255)
        t = _corner_mask(r)
        mask.paste(t.crop((0, 0, r, r)), (0, 0))
        mask.paste(t.crop((r, 0, 2 * r, r)), (w - r, 0))
        mask.paste(t.crop((0, r, r, 2 * r)), (0, h - r))
        mask.paste(t.crop((r, r, 2 * r, 2 * r)), (w - r, h - r))
        img.putalpha(mask)
    ph = _to_photo(img)
    _PHOTO_CACHE[key] = ph
    return ph


def circle_photo(d, fill, outline=None, ow=0):
    key = ("ci", d, fill, outline, ow)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        m = _SS
        im = Image.new("RGBA", (d * m, d * m), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([m, m, d * m - m, d * m - m],
                                   fill=fill, outline=outline, width=ow * m)
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def toggle_photo(w, h, on):
    key = ("tg", w, h, on)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("toggle_on" if on else "toggle_off", w, h)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        m = _SS
        im = Image.new("RGBA", (w * m, h * m), (0, 0, 0, 0))
        # im An-Zustand ein leichter Verlauf in der Akzentfarbe
        if on:
            grad = _to_pil_gradient(w * m, h * m, _mix(ACCENT, "#FFFFFF", 0.22), ACCENT)
            mask = Image.new("L", (w * m, h * m), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * m - 1, h * m - 1],
                                                   radius=(h * m) // 2, fill=255)
            im.paste(grad, (0, 0), mask)
        else:
            ImageDraw.Draw(im).rounded_rectangle([0, 0, w * m - 1, h * m - 1],
                                                 radius=(h * m) // 2, fill=OFF)
        dr = ImageDraw.Draw(im)
        pad = int(h * m * 0.16)
        kd = h * m - 2 * pad
        kx = (w * m - pad - kd) if on else pad
        dr.ellipse([kx, pad, kx + kd, pad + kd], fill=KNOB)
        ph = _to_photo(im.resize((w, h), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


_AV_FONT = {}


def _avatar_font(size):
    f = _AV_FONT.get(size)
    if f is None:
        for name in ("segoeuib.ttf", "seguisb.ttf", "segoeui.ttf", "arialbd.ttf"):
            try:
                f = ImageFont.truetype(name, size)
                break
            except Exception:
                continue
        if f is None:
            f = ImageFont.load_default()
        _AV_FONT[size] = f
    return f


def avatar_photo(d, label):
    key = ("av", d, label)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        m = _SS
        letter = (label.strip()[:1] or "?").upper()
        hh = int(hashlib.md5(label.encode("utf-8")).hexdigest(), 16)
        r1, g1, b1 = colorsys.hsv_to_rgb((hh % 360) / 360.0, 0.5, 0.8)
        bg = (int(r1 * 255), int(g1 * 255), int(b1 * 255), 255)
        im = Image.new("RGBA", (d * m, d * m), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.rounded_rectangle([0, 0, d * m - 1, d * m - 1], radius=int(d * m * 0.30), fill=bg)
        fnt = _avatar_font(int(d * m * 0.56))
        try:
            bb = dr.textbbox((0, 0), letter, font=fnt)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            dr.text(((d * m - tw) / 2 - bb[0], (d * m - th) / 2 - bb[1]), letter,
                    font=fnt, fill=(255, 255, 255, 255))
        except Exception:
            pass
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def _tile_icon(d, base, tag, glyph):
    """Abgerundete Kachel mit Verlauf und weissem Symbol (wie das App-Logo)."""
    key = (tag, d, str(base))
    ph = _PHOTO_CACHE.get(key)
    if ph is not None:
        return ph
    m = _SS
    s = d * m
    top = _shift(base, 1.20)
    bottom = _shift(base, 0.80)
    tile = _to_pil_gradient(s, s, top, bottom)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.29), fill=255)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    im.paste(tile, (0, 0), mask)
    # feiner Glanz oben
    gloss = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([-s * 0.3, -s * 0.8, s * 1.3, s * 0.40],
                                  fill=(255, 255, 255, 30))
    im = Image.alpha_composite(im, Image.composite(
        gloss, Image.new("RGBA", (s, s), (0, 0, 0, 0)), mask))
    glyph(ImageDraw.Draw(im), s)
    ph = _to_photo(im.resize((d, d), Image.LANCZOS))
    _PHOTO_CACHE[key] = ph
    return ph


def _speaker_glyph(dr, s):
    w = (255, 255, 255, 255)

    def sc(x, y):
        return (x / 100.0 * s, y / 100.0 * s)
    dr.rounded_rectangle([*sc(22, 41), *sc(35, 59)], radius=int(s * 0.02), fill=w)
    dr.polygon([sc(33, 41), sc(50, 25), sc(50, 75), sc(33, 59)], fill=w)
    lw = max(2, int(s * 0.045))
    dr.arc([*sc(50, 33), *sc(70, 67)], -60, 60, fill=w, width=lw)
    dr.arc([*sc(55, 22), *sc(85, 78)], -58, 58, fill=w, width=lw)


def master_icon_photo(d):
    """Symbol der Gesamtlautstaerke – Kachel in der Akzentfarbe."""
    ph = skin_image("icon_master", d, d)
    if ph is not None:
        return ph
    return _tile_icon(d, ACCENT, "master", _speaker_glyph)


def system_icon_photo(d):
    ph = skin_image("icon_system", d, d)
    if ph is not None:
        return ph
    return _tile_icon(d, "#606676", "sys", _speaker_glyph)


def gear_photo(d, color=None):
    """Zahnrad-Symbol (anti-aliased)."""
    color = color if color is not None else FG
    key = ("gear", d, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("gear", d, d)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        import math
        m = _SS
        s = d * m
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        cx = cy = s / 2.0
        r_out = s * 0.46
        r_in = s * 0.32
        teeth = 8
        pts = []
        for i in range(teeth * 2):
            a0 = (i / float(teeth * 2)) * 2 * math.pi
            a1 = ((i + 1) / float(teeth * 2)) * 2 * math.pi
            r = r_out if i % 2 == 0 else r_in
            # jeweils zwei Punkte pro Segment -> kantige Zaehne
            pts.append((cx + r * math.cos(a0), cy + r * math.sin(a0)))
            pts.append((cx + r * math.cos(a1 - 0.001), cy + r * math.sin(a1 - 0.001)))
        dr.polygon(pts, fill=color)
        hole = s * 0.16
        dr.ellipse([cx - hole, cy - hole, cx + hole, cy + hole], fill=(0, 0, 0, 0))
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def help_photo(d, color=None):
    """Fragezeichen im Kreis – Hinweis, dass es hier eine Erklaerung gibt.

    Das Zeichen kommt aus der UI-Schrift statt als Pfad-Zeichnung: ein von Hand
    gesetztes Fragezeichen sieht bei diesen Groessen unweigerlich schief aus.
    """
    color = color if color is not None else MUTED
    key = ("help", d, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is not None:
        return ph
    m = _SS
    s = d * m
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    breite = max(1, int(s * 0.075))
    dr.ellipse([breite, breite, s - breite, s - breite], outline=color,
               width=breite)
    try:
        f = ImageFont.truetype("segoeui.ttf", int(s * 0.62))
    except Exception:
        f = ImageFont.load_default()
    l, t, r, b = dr.textbbox((0, 0), "?", font=f)
    dr.text(((s - (r - l)) / 2.0 - l, (s - (b - t)) / 2.0 - t), "?",
            font=f, fill=color)
    ph = _to_photo(im.resize((d, d), Image.LANCZOS))
    _PHOTO_CACHE[key] = ph
    return ph


def volume_photo(d, level, color=None):
    """Lautsprecher, dessen Wellen mit dem Pegel wachsen (wie in Windows).

    Nicht aktive Wellen bleiben schwach sichtbar – so springt das Symbol beim
    Regeln nicht in der Groesse.
    """
    color = color if color is not None else FG
    step = 0 if level <= 0.001 else (1 if level < 0.34 else (2 if level < 0.67 else 3))
    key = ("vol", d, step, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is not None:
        return ph
    m = _SS
    s = d * m
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rgb = _hex_rgb(color) if isinstance(color, str) else tuple(color[:3])
    full = rgb + (255,)
    faint = rgb + (48,)

    def sc(x, y):
        return (x / 100.0 * s, y / 100.0 * s)

    # Korpus + Kegel
    dr.rounded_rectangle([*sc(8, 38), *sc(24, 62)], radius=int(s * 0.02), fill=full)
    dr.polygon([sc(22, 38), sc(44, 18), sc(44, 82), sc(22, 62)], fill=full)
    lw = max(2, int(s * 0.055))
    waves = [((52, 33), (66, 67)), ((52, 22), (78, 78)), ((52, 11), (90, 89))]
    for i, (a, b) in enumerate(waves):
        col = full if i < step else faint
        dr.arc([*sc(*a), *sc(*b)], -58, 58, fill=col, width=lw)
    if step == 0:
        # stummer Zustand: kleines Kreuz statt Wellen
        dr.line([sc(58, 40), sc(80, 62)], fill=full, width=lw)
        dr.line([sc(80, 40), sc(58, 62)], fill=full, width=lw)
    ph = _to_photo(im.resize((d, d), Image.LANCZOS))
    _PHOTO_CACHE[key] = ph
    return ph


def reset_photo(d, color=None):
    """Rundpfeil – setzt die App-Lautstaerken zurueck."""
    color = color if color is not None else FG
    key = ("reset", d, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("reset", d, d)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        import math
        m = _SS
        s = d * m
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        w = max(2, int(s * 0.105))
        pad = s * 0.20
        # offener Kreis (Luecke oben rechts)
        dr.arc([pad, pad, s - pad, s - pad], 305, 215, fill=color, width=w)
        # Pfeilspitze am Ende des Bogens
        r = (s - 2 * pad) / 2.0
        c = s / 2.0
        a = math.radians(305)
        tipx, tipy = c + r * math.cos(a), c + r * math.sin(a)
        b = s * 0.15
        dr.polygon([(tipx + b * 0.15, tipy - b * 0.95),
                    (tipx + b * 1.05, tipy + b * 0.25),
                    (tipx - b * 0.75, tipy + b * 0.45)], fill=color)
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def moon_sun_photo(d, sun, color=None):
    """Sonne (heller Modus aktiv) bzw. Mond (dunkler Modus aktiv)."""
    color = color if color is not None else FG
    key = ("msun", d, sun, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("sun" if sun else "moon", d, d)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        import math
        m = _SS
        s = d * m
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        c = s / 2.0
        if sun:
            r = s * 0.23
            dr.ellipse([c - r, c - r, c + r, c + r], fill=color)
            w = max(2, int(s * 0.075))
            r1, r2 = s * 0.32, s * 0.45
            for i in range(8):
                a = i * math.pi / 4
                dr.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)),
                         (c + r2 * math.cos(a), c + r2 * math.sin(a))],
                        fill=color, width=w)
        else:
            r = s * 0.40
            full = Image.new("L", (s, s), 0)
            ImageDraw.Draw(full).ellipse([c - r, c - r, c + r, c + r], fill=255)
            cut = Image.new("L", (s, s), 0)
            off = s * 0.26
            ImageDraw.Draw(cut).ellipse([c - r + off, c - r - off * 0.55,
                                         c + r + off, c + r - off * 0.55], fill=255)
            mask = Image.composite(Image.new("L", (s, s), 0), full, cut)
            solid = Image.new("RGBA", (s, s), color)
            im = Image.composite(solid, Image.new("RGBA", (s, s), (0, 0, 0, 0)),
                                 mask.point(lambda p: 255 if p > 127 else 0))
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def check_photo(d, on, hover=False):
    """Auswahl-Kaestchen mit Haekchen (an) bzw. Umriss (aus)."""
    key = ("chk", d, on, hover, ACCENT, CARD2, STROKE)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("check_on" if on else "check_off", d, d)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        m = _SS
        s = d * m
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        r = int(s * 0.30)
        if on:
            base = ACCENT_HOVER if hover else ACCENT
            grad = _to_pil_gradient(s, s, _mix(base, "#FFFFFF", 0.25), base)
            mask = Image.new("L", (s, s), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
            im.paste(grad, (0, 0), mask)
            w = max(2, int(s * 0.11))
            dr.line([(s * 0.26, s * 0.52), (s * 0.44, s * 0.70)], fill=KNOB, width=w)
            dr.line([(s * 0.44, s * 0.70), (s * 0.75, s * 0.31)], fill=KNOB, width=w)
            dr.ellipse([s * 0.26 - w / 2, s * 0.52 - w / 2, s * 0.26 + w / 2, s * 0.52 + w / 2], fill=KNOB)
            dr.ellipse([s * 0.75 - w / 2, s * 0.31 - w / 2, s * 0.75 + w / 2, s * 0.31 + w / 2], fill=KNOB)
        else:
            dr.rounded_rectangle([0, 0, s - 1, s - 1], radius=r,
                                 fill=(STROKE if hover else CARD2),
                                 outline=STROKE, width=max(1, int(s * 0.05)))
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph


def arrow_photo(d, color=None):
    """Zurueck-Pfeil (anti-aliased)."""
    color = color if color is not None else FG
    key = ("arrow", d, color)
    ph = _PHOTO_CACHE.get(key)
    if ph is None:
        ph = skin_image("back", d, d)
        if ph is not None:
            _PHOTO_CACHE[key] = ph
            return ph
        m = _SS
        s = d * m
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        w = max(1, int(s * 0.10))
        cy = s / 2.0
        x0, x1 = s * 0.24, s * 0.78
        dr.line([(x0, cy), (x1, cy)], fill=color, width=w)
        dr.line([(x0, cy), (x0 + s * 0.24, cy - s * 0.24)], fill=color, width=w)
        dr.line([(x0, cy), (x0 + s * 0.24, cy + s * 0.24)], fill=color, width=w)
        dr.ellipse([x0 - w / 2, cy - w / 2, x0 + w / 2, cy + w / 2], fill=color)
        ph = _to_photo(im.resize((d, d), Image.LANCZOS))
        _PHOTO_CACHE[key] = ph
    return ph




def app_icon_photo(size, key, label, exe, dim=False):
    ck = ("app", size, exe if exe else ("L", key, label), dim)
    ph = _PHOTO_CACHE.get(ck)
    if ph is not None:
        return ph
    if dim:
        # Stumm: Symbol blass und entsaettigt
        base = app_icon_pil(size, key, label, exe).copy()
        alpha = base.getchannel("A").point(lambda a: int(a * 0.38))
        base = Image.merge("RGBA", (*base.convert("RGB")
                                    .convert("L").convert("RGB").split(), alpha))
        ph = _to_photo(base)
        _PHOTO_CACHE[ck] = ph
        return ph
    if key == MASTER_KEY:
        ph = master_icon_photo(size)
        _PHOTO_CACHE[ck] = ph
        return ph
    if key == SYSTEM_KEY:
        ph = system_icon_photo(size)
        _PHOTO_CACHE[ck] = ph
        return ph
    pil = None
    if exe:
        if exe not in _ICON_PIL:
            _ICON_PIL[exe] = _extract_exe_icon(exe, 64)
        base = _ICON_PIL[exe]
        if base is not None:
            pil = base if size == 64 else base.resize((size, size), Image.LANCZOS)
    if pil is None:
        ph = avatar_photo(size, label)
    else:
        ph = _to_photo(pil)
    _PHOTO_CACHE[ck] = ph
    return ph


# ---------------------------------------------------------------------------
# Custom-Widgets
# ---------------------------------------------------------------------------
class Restylable:
    """Merkt sich, aus welchen Palettenrollen ein Widget gebaut wurde.

    Beim Wechsel von Skin oder Hell/Dunkel werden die Widgets dadurch nur
    umgefaerbt statt neu erzeugt – die Oberflaeche baut sich nicht neu auf.
    """
    _ROLES = ("bg", "card", "card2", "stroke", "fg", "muted",
              "accent", "accent_hover", "red", "knob", "off")

    @staticmethod
    def palette():
        return {"bg": BG, "card": CARD, "card2": CARD2, "stroke": STROKE,
                "fg": FG, "muted": MUTED, "accent": ACCENT,
                "accent_hover": ACCENT_HOVER, "red": RED, "knob": KNOB, "off": OFF}

    @classmethod
    def role_of(cls, color):
        """Rolle einer Farbe – oder die Farbe selbst, wenn sie fest gewaehlt ist."""
        for role, value in cls.palette().items():
            if value == color:
                return role
        return ("#", color)

    def _remember(self, **roles):
        self._roles = roles

    def _color(self, role, fallback=None):
        if isinstance(role, tuple):     # feste Farbe, nicht aus der Palette
            return role[1]
        return self.palette().get(role, fallback)


class RoundButton(tk.Canvas, Restylable):
    def __init__(self, parent, text, command, bg, fill, fill_hover, fg,
                 h=None, r=None, padx=None, fontpx=13):
        h = h or px(32)
        r = r or px(10)
        padx = padx or px(16)
        self.f = tkfont.Font(family=FONT_SEMI, size=-px(fontpx))
        w = self.f.measure(text) + 2 * padx
        super().__init__(parent, width=w, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.w, self.h, self.r = w, h, r
        self._remember(bg=self.role_of(bg), fill=self.role_of(fill),
                       hover=self.role_of(fill_hover), fg=self.role_of(fg))
        self._n = rounded_photo(w, h, r, fill)
        self._hov = rounded_photo(w, h, r, fill_hover)
        self._img = self.create_image(0, 0, anchor="nw", image=self._n)
        self._txt = self.create_text(w // 2, h // 2, text=text, fill=fg, font=self.f)
        self.bind("<Enter>", lambda e: self.itemconfig(self._img, image=self._hov))
        self.bind("<Leave>", lambda e: self.itemconfig(self._img, image=self._n))
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)

    def set_roles(self, fill, hover, fg):
        """Rollen tauschen (z. B. Chip wird aktiv/inaktiv)."""
        self._roles.update(fill=fill, hover=hover, fg=fg)
        self.restyle()

    def restyle(self):
        r = self._roles
        bg = self._color(r["bg"], BG)
        fill = self._color(r["fill"], CARD2)
        hover = self._color(r["hover"], STROKE)
        fg = self._color(r["fg"], FG)
        self.configure(bg=bg)
        self._n = rounded_photo(self.w, self.h, self.r, fill)
        self._hov = rounded_photo(self.w, self.h, self.r, hover)
        self.itemconfig(self._img, image=self._n)
        self.itemconfig(self._txt, fill=fg)


class ColorDot(tk.Canvas, Restylable):
    def __init__(self, parent, color, active, command, bg=None, size=None):
        bg = bg if bg is not None else CARD
        self.d = size or px(30)
        super().__init__(parent, width=self.d, height=self.d, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.color = color
        self.active = active
        self.command = command
        self._remember(bg=self.role_of(bg))
        self._draw()
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)

    def _draw(self):
        self.delete("all")
        ring = FG if self.active else STROKE
        self._img = circle_photo(self.d, self.color, ring, 3 if self.active else 1)
        self.create_image(0, 0, anchor="nw", image=self._img)

    def set_active(self, on):
        if self.active != bool(on):
            self.active = bool(on)
            self._draw()

    def restyle(self):
        self.configure(bg=self._color(self._roles["bg"], CARD))
        self._draw()


class ChipGroup(tk.Frame, Restylable):
    """Reihe von Auswahl-Chips, deren Markierung sich live umsetzen laesst."""
    def __init__(self, parent, items, current, command, bg=None):
        bg = bg if bg is not None else CARD
        super().__init__(parent, bg=bg)
        self.command = command
        self.value = current
        self.buttons = {}
        for value, label in items:
            b = RoundButton(self, label, lambda v=value: self._pick(v), bg=bg,
                            fill=CARD2, fill_hover=STROKE, fg=FG,
                            h=px(30), r=px(9), padx=px(14), fontpx=11)
            b.pack(side="left", padx=(0, px(8)))
            self.buttons[value] = b
        self._mark()

    def _mark(self):
        for value, b in self.buttons.items():
            on = (value == self.value)
            b.set_roles("accent" if on else "card2",
                        "accent_hover" if on else "stroke",
                        "knob" if on else "fg")

    def select(self, value):
        self.value = value
        self._mark()

    def _pick(self, value):
        if value != self.value:
            self.select(value)
        if self.command:
            self.command(value)

    def restyle(self):
        self.configure(bg=CARD)
        for b in self.buttons.values():
            b.restyle()


class IconButton(tk.Canvas, Restylable):
    """Runder Knopf mit gezeichnetem Symbol (z. B. Zahnrad)."""
    def __init__(self, parent, photo_fn, command, bg, fill, fill_hover,
                 size=None, icon=None):
        size = size or px(38)
        icon = icon or px(19)
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.photo_fn = photo_fn
        self.size, self.icon_d = size, icon
        self._remember(bg=self.role_of(bg), fill=self.role_of(fill),
                       hover=self.role_of(fill_hover))
        self._n = rounded_photo(size, size, size // 2, fill)
        self._hov = rounded_photo(size, size, size // 2, fill_hover)
        self._bgimg = self.create_image(0, 0, anchor="nw", image=self._n)
        self._ic = photo_fn(icon)
        self._icimg = self.create_image(size // 2, size // 2, image=self._ic)
        self.bind("<Enter>", lambda e: self.itemconfig(self._bgimg, image=self._hov))
        self.bind("<Leave>", lambda e: self.itemconfig(self._bgimg, image=self._n))
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)

    def set_icon(self, photo_fn):
        self.photo_fn = photo_fn
        self._ic = photo_fn(self.icon_d)
        self.itemconfig(self._icimg, image=self._ic)

    def restyle(self):
        r = self._roles
        self.configure(bg=self._color(r["bg"], BG))
        self._n = rounded_photo(self.size, self.size, self.size // 2,
                                self._color(r["fill"], CARD))
        self._hov = rounded_photo(self.size, self.size, self.size // 2,
                                  self._color(r["hover"], CARD2))
        self.itemconfig(self._bgimg, image=self._n)
        self._ic = self.photo_fn(self.icon_d)
        self.itemconfig(self._icimg, image=self._ic)


class CheckBox(tk.Canvas, Restylable):
    """Kaestchen zum An-/Abhaken."""
    def __init__(self, parent, value=False, command=None, bg=None, size=None):
        bg = bg if bg is not None else CARD
        d = size or px(M.get("check_size", 24))
        super().__init__(parent, width=d, height=d, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.value = bool(value)
        self.d = d
        self._remember(bg=self.role_of(bg))
        self._hover = False
        self._img = self.create_image(0, 0, anchor="nw",
                                      image=check_photo(d, self.value))
        self.bind("<Button-1>", self._toggle)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _render(self):
        self.itemconfig(self._img, image=check_photo(self.d, self.value, self._hover))

    def _set_hover(self, on):
        self._hover = on
        self._render()

    def _toggle(self, _e=None):
        self.value = not self.value
        self._render()
        if self.command:
            self.command(self.value)

    def set(self, value):
        if bool(value) != self.value:
            self.value = bool(value)
            self._render()

    def restyle(self):
        self.configure(bg=self._color(self._roles["bg"], CARD))
        self._render()


class Card(tk.Frame, Restylable):
    """Panel mit abgerundeten Ecken (Hintergrundbild hinter dem Inhalt)."""
    def __init__(self, parent, bg_outer=None, radius=None, pad=None):
        bg_outer = bg_outer if bg_outer is not None else BG
        super().__init__(parent, bg=bg_outer)
        self._r = radius if radius is not None else px(M.get("card_radius", 16))
        self._pad = pad if pad is not None else max(self._r // 2, px(6))
        self._bgl = tk.Label(self, bg=bg_outer, bd=0, highlightthickness=0)
        self._bgl.place(x=0, y=0, relwidth=1, relheight=1)
        self.inner = tk.Frame(self, bg=CARD)
        self.inner.pack(fill="both", expand=True, padx=self._pad, pady=self._pad)
        self._last = None
        self.bind("<Configure>", self._redraw)

    def _redraw(self, e):
        size = (e.width, e.height)
        if size == self._last or e.width < 4 or e.height < 4:
            return
        self._last = size
        self._paint(*size)

    def _paint(self, w, h):
        # Einfarbig: In dieser Karte liegen normale Widgets (Schalter, Regler),
        # deren Flaechen einen Verlauf ohnehin verdecken wuerden.
        img = rounded_photo(w, h, self._r, CARD, STROKE, 1)
        self._bgl.configure(image=img)
        self._bgl.image = img

    def restyle(self):
        self.configure(bg=BG)
        self._bgl.configure(bg=BG)
        self.inner.configure(bg=CARD)
        if self._last:
            self._paint(*self._last)


class ToggleSwitch(tk.Canvas, Restylable):
    def __init__(self, parent, value=False, command=None, bg=None):
        bg = bg if bg is not None else CARD
        w, h = px(M["toggle_w"]), px(M["toggle_h"])
        super().__init__(parent, width=w, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.value = bool(value)
        self.w, self.h = w, h
        self._remember(bg=self.role_of(bg))
        self._img = self.create_image(0, 0, anchor="nw", image=toggle_photo(w, h, self.value))
        self.bind("<Button-1>", self._toggle)

    def _render(self):
        self.itemconfig(self._img, image=toggle_photo(self.w, self.h, self.value))

    def _toggle(self, _e=None):
        self.value = not self.value
        self._render()
        if self.command:
            self.command(self.value)

    def set(self, value):
        if bool(value) != self.value:
            self.value = bool(value)
            self._render()

    def restyle(self):
        self.configure(bg=self._color(self._roles["bg"], CARD))
        self._render()


class Slider(tk.Canvas, Restylable):
    def __init__(self, parent, width, on_change, bg=None):
        bg = bg if bg is not None else CARD
        h = px(26)
        super().__init__(parent, width=width, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.on_change = on_change
        self.value = 0.0
        self.w, self.h = width, h
        self._remember(bg=self.role_of(bg))
        self.kd = px(M["slider_knob"])
        self.pad = self.kd // 2
        self.th = px(M["slider_track"])
        cy = h // 2
        track_len = width - 2 * self.pad
        self._track_len = track_len
        self._track_img = rounded_photo(track_len, self.th, self.th // 2, CARD2)
        self._track_id = self.create_image(self.pad, cy - self.th // 2, anchor="nw",
                                           image=self._track_img)
        self._grad_full = _to_pil_gradient(track_len, self.th,
                                           _mix(ACCENT, "#FFFFFF", 0.30), ACCENT,
                                           horizontal=True)
        self._grad_ref = None
        self._grad_id = self.create_image(self.pad, cy - self.th // 2, anchor="nw")
        # feiner Rand, sonst geht der helle Knopf im hellen Modus unter
        knob = (skin_image("slider_knob", self.kd, self.kd)
                or circle_photo(self.kd, KNOB, STROKE, 1))
        self._knob_ref = knob
        self._knob_id = self.create_image(0, 0, anchor="nw", image=knob)
        self._place(0.0)
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)

    def _cx(self, v):
        return self.pad + v * (self.w - 2 * self.pad)

    def _set_fill(self, v):
        """Fuellung als zugeschnittener Farbverlauf."""
        fw = int(round(self._track_len * max(0.0, min(1.0, v))))
        if fw < self.th:
            self.itemconfig(self._grad_id, image="")
            self._grad_ref = None
            return
        im = self._grad_full.crop((0, 0, fw, self.th))
        mask = Image.new("L", (fw, self.th), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, fw - 1, self.th - 1],
                                               radius=self.th // 2, fill=255)
        im.putalpha(mask)
        self._grad_ref = _to_photo(im)
        self.itemconfig(self._grad_id, image=self._grad_ref)

    def _place(self, v):
        cx = self._cx(v)
        self.coords(self._knob_id, cx - self.kd / 2, self.h / 2 - self.kd / 2)

    def set(self, v):
        v = max(0.0, min(1.0, v))
        self.value = v
        self._set_fill(v)
        self._place(v)

    def _from_x(self, x):
        return max(0.0, min(1.0, (x - self.pad) / float(self.w - 2 * self.pad)))

    def _drag(self, e):
        self.set(self._from_x(e.x))
        if self.on_change:
            self.on_change(self.value, False)

    def _release(self, e):
        if self.on_change:
            self.on_change(self.value, True)

    def restyle(self):
        self.configure(bg=self._color(self._roles["bg"], CARD))
        self._track_img = rounded_photo(self._track_len, self.th, self.th // 2, CARD2)
        self.itemconfig(self._track_id, image=self._track_img)
        self._grad_full = _to_pil_gradient(self._track_len, self.th,
                                           _mix(ACCENT, "#FFFFFF", 0.30), ACCENT,
                                           horizontal=True)
        self._set_fill(self.value)
        self._knob_ref = (skin_image("slider_knob", self.kd, self.kd)
                          or circle_photo(self.kd, KNOB, STROKE, 1))
        self.itemconfig(self._knob_id, image=self._knob_ref)


# ---------------------------------------------------------------------------
# On-Screen-Display (flackerfrei)
# ---------------------------------------------------------------------------
OSD_POSITIONS = [
    ("tl", "oben links"), ("tc", "oben mitte"), ("tr", "oben rechts"),
    ("ml", "mitte links"), ("mc", "Bildschirmmitte"), ("mr", "mitte rechts"),
    ("bl", "unten links"), ("bc", "unten mitte"), ("br", "unten rechts"),
]


class _BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class _LayeredWindow:
    """Zeigt ein RGBA-Bild als Fenster mit echter Pixel-Transparenz.

    Nur so werden abgerundete Ecken wirklich weich: Eine Fensterregion
    (SetWindowRgn) schneidet hart ab und laesst Treppen stehen, ein
    Transparenzschluessel hinterlaesst Farbfransen.
    """

    ULW_ALPHA = 0x00000002
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020    # Mausklicks gehen durch
    WS_EX_NOACTIVATE = 0x08000000     # nimmt nie den Fokus
    WS_EX_TOOLWINDOW = 0x00000080     # nicht in der Taskleiste
    GWL_EXSTYLE = -20

    def __init__(self, hwnd):
        self.hwnd = hwnd
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        u.GetWindowLongW.restype = ctypes.c_long
        style = u.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        # NOACTIVATE/TOOLWINDOW/TRANSPARENT: Die Einblendung darf niemals den
        # Fokus ziehen – sonst blinken Programme in der Taskleiste und
        # Vollbild-Anwendungen verlieren kurz die Eingabe.
        u.SetWindowLongW(hwnd, self.GWL_EXSTYLE,
                         style | self.WS_EX_LAYERED | self.WS_EX_TRANSPARENT
                         | self.WS_EX_NOACTIVATE | self.WS_EX_TOOLWINDOW)
        for fn, res, args in (
            (u.GetDC, ctypes.c_void_p, [wintypes.HWND]),
            (g.CreateCompatibleDC, ctypes.c_void_p, [ctypes.c_void_p]),
            (g.CreateDIBSection, ctypes.c_void_p,
             [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
              ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wintypes.DWORD]),
            (g.SelectObject, ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]),
            (u.ReleaseDC, ctypes.c_int, [wintypes.HWND, ctypes.c_void_p]),
            (g.DeleteDC, wintypes.BOOL, [ctypes.c_void_p]),
            (g.DeleteObject, wintypes.BOOL, [ctypes.c_void_p]),
        ):
            fn.restype, fn.argtypes = res, args
        # Ohne explizite Typen schneidet ctypes die 64-Bit-Handles ab
        u.UpdateLayeredWindow.restype = wintypes.BOOL
        u.UpdateLayeredWindow.argtypes = [
            wintypes.HWND, ctypes.c_void_p, ctypes.POINTER(wintypes.POINT),
            ctypes.POINTER(wintypes.SIZE), ctypes.c_void_p,
            ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
            ctypes.POINTER(_BLENDFUNCTION), wintypes.DWORD]
        self._dc = None
        self._bmp = None
        self._size = None

    def _ensure(self, w, h):
        if self._size == (w, h):
            return
        self._release()
        g, u = ctypes.windll.gdi32, ctypes.windll.user32
        screen = u.GetDC(None)
        self._dc = g.CreateCompatibleDC(screen)
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(bmi)
        bmi.biWidth, bmi.biHeight = w, -h        # top-down
        bmi.biPlanes, bmi.biBitCount = 1, 32
        bmi.biCompression = 0
        self._bits = ctypes.c_void_p()
        self._bmp = g.CreateDIBSection(self._dc, ctypes.byref(bmi), 0,
                                       ctypes.byref(self._bits), None, 0)
        g.SelectObject(self._dc, self._bmp)
        u.ReleaseDC(None, screen)
        self._size = (w, h)

    def _release(self):
        g = ctypes.windll.gdi32
        if self._bmp:
            g.DeleteObject(self._bmp)
        if self._dc:
            g.DeleteDC(self._dc)
        self._bmp = self._dc = self._size = None

    def show(self, img, x, y, alpha=255):
        """img: PIL-RGBA-Bild. Alpha wird premultipliziert (von Windows verlangt)."""
        w, h = img.size
        self._ensure(w, h)
        px_ = img.load()
        buf = (ctypes.c_ubyte * (w * h * 4)).from_address(self._bits.value)
        raw = img.tobytes("raw", "BGRA")
        # premultiplizieren
        mv = bytearray(raw)
        for i in range(0, len(mv), 4):
            a = mv[i + 3]
            if a != 255:
                mv[i] = mv[i] * a // 255
                mv[i + 1] = mv[i + 1] * a // 255
                mv[i + 2] = mv[i + 2] * a // 255
        ctypes.memmove(buf, bytes(mv), len(mv))
        # Pflicht nach direktem Schreiben in die DIB-Bits – sonst sieht GDI
        # die Aenderung nicht und zeigt die leere Bitmap.
        ctypes.windll.gdi32.GdiFlush()

        u = ctypes.windll.user32
        size = wintypes.SIZE(w, h)
        src = wintypes.POINT(0, 0)
        dst = wintypes.POINT(int(x), int(y))
        blend = _BLENDFUNCTION(0, 0, alpha, 1)   # AC_SRC_ALPHA
        # pptDst = None: Position/Groesse verwaltet Tk (sonst ueberschreibt Tk
        # die hier gesetzte Lage beim naechsten Layout wieder)
        ok = u.UpdateLayeredWindow(wintypes.HWND(self.hwnd), None,
                                   None, ctypes.byref(size),
                                   self._dc, ctypes.byref(src), 0,
                                   ctypes.byref(blend), self.ULW_ALPHA)
        self.last_error = 0 if ok else ctypes.get_last_error()
        return bool(ok)


_PIL_CACHE = {}


def _ui_font(size, semi=True):
    key = ("f", size, semi)
    f = _PIL_CACHE.get(key)
    if f is None:
        names = ("seguisb.ttf", "segoeuib.ttf", "segoeui.ttf") if semi else \
                ("segoeui.ttf", "seguisb.ttf")
        for n in names:
            try:
                f = ImageFont.truetype(n, size)
                break
            except Exception:
                continue
        if f is None:
            f = ImageFont.load_default()
        _PIL_CACHE[key] = f
    return f


def app_icon_pil(size, key, label, exe):
    """Programm-Symbol als PIL-Bild (fuer die Einblendung)."""
    ck = ("i", size, key, exe or "", str(ACCENT))
    im = _PIL_CACHE.get(ck)
    if im is not None:
        return im
    if key == MASTER_KEY:
        im = _tile_icon_pil(size, ACCENT)
    elif key == SYSTEM_KEY:
        im = _tile_icon_pil(size, "#606676")
    else:
        base = None
        if exe:
            if exe not in _ICON_PIL:
                _ICON_PIL[exe] = _extract_exe_icon(exe, 64)
            base = _ICON_PIL[exe]
        if base is not None:
            im = base.resize((size, size), Image.LANCZOS)
        else:
            im = _avatar_pil(size, label)
    _PIL_CACHE[ck] = im
    return im


def _avatar_pil(d, label):
    m = 4
    letter = (label.strip()[:1] or "?").upper()
    hh = int(hashlib.md5(label.encode("utf-8")).hexdigest(), 16)
    r1, g1, b1 = colorsys.hsv_to_rgb((hh % 360) / 360.0, 0.5, 0.8)
    im = Image.new("RGBA", (d * m, d * m), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([0, 0, d * m - 1, d * m - 1], radius=int(d * m * 0.30),
                         fill=(int(r1 * 255), int(g1 * 255), int(b1 * 255), 255))
    fnt = _ui_font(int(d * m * 0.56))
    bb = dr.textbbox((0, 0), letter, font=fnt)
    dr.text(((d * m - (bb[2] - bb[0])) / 2 - bb[0],
             (d * m - (bb[3] - bb[1])) / 2 - bb[1]), letter, font=fnt,
            fill=(255, 255, 255, 255))
    return im.resize((d, d), Image.LANCZOS)


def _tile_icon_pil(d, base):
    m = 4
    s = d * m
    tile = _to_pil_gradient(s, s, _shift(base, 1.20), _shift(base, 0.80))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.29), fill=255)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    im.paste(tile, (0, 0), mask)
    _speaker_glyph(ImageDraw.Draw(im), s)
    return im.resize((d, d), Image.LANCZOS)


def volume_pil(d, level, color):
    """Dynamischer Lautsprecher als PIL-Bild."""
    step = 0 if level <= 0.001 else (1 if level < 0.34 else (2 if level < 0.67 else 3))
    ck = ("v", d, step, str(color))
    im = _PIL_CACHE.get(ck)
    if im is not None:
        return im
    m = 4
    s = d * m
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rgb = _hex_rgb(color) if isinstance(color, str) else tuple(color[:3])
    full, faint = rgb + (255,), rgb + (55,)

    def sc(x, y):
        return (x / 100.0 * s, y / 100.0 * s)
    dr.rounded_rectangle([*sc(8, 38), *sc(24, 62)], radius=int(s * 0.02), fill=full)
    dr.polygon([sc(22, 38), sc(44, 18), sc(44, 82), sc(22, 62)], fill=full)
    lw = max(2, int(s * 0.055))
    for i, (a, b) in enumerate((((52, 33), (66, 67)), ((52, 22), (78, 78)),
                                ((52, 11), (90, 89)))):
        dr.arc([*sc(*a), *sc(*b)], -58, 58, fill=(full if i < step else faint), width=lw)
    if step == 0:
        dr.line([sc(58, 40), sc(80, 62)], fill=full, width=lw)
        dr.line([sc(80, 40), sc(58, 62)], fill=full, width=lw)
    im = im.resize((d, d), Image.LANCZOS)
    _PIL_CACHE[ck] = im
    return im


def _transparent_key(color):
    """Farbe, die optisch identisch zu `color` ist, aber exakt nie vorkommt.

    Wird als Transparenzschluessel benutzt: Die weichen (anti-aliased) Kanten
    der OSD-Karte mischen die Kartenfarbe mit dem Fensterhintergrund – waere der
    Schluessel kontrastreich (z. B. Magenta), blieben farbige Fransen stehen.
    """
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        b = b + 1 if b < 255 else b - 1
        return "#{:02X}{:02X}{:02X}".format(r, g, b)
    except Exception:
        return "#1C1E27"


class MixerRow(tk.Canvas, Restylable):
    """Eine Mixer-Zeile als EIN Canvas.

    Wichtig: Tk-Widgets sind nicht transparent. Wuerde die Zeile aus Frames und
    Labels bestehen, laegen deren einfarbige Flaechen ueber dem Verlauf und
    wuerden ihn verdecken. Auf einem Canvas ist alles – Hintergrund, Symbole,
    Text und Regler – frei uebereinander zeichenbar.
    """

    def __init__(self, parent, item, selected, on_toggle, on_volume, on_mute=None):
        self.h = px(54)
        super().__init__(parent, height=self.h, bg=CARD,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.key = item["key"]
        self.label = item["label"]
        self.exe = item.get("exe")
        self.muted = bool(item.get("muted"))
        self.on_mute = on_mute
        self.value = float(item["volume"])
        self.sel = bool(selected)
        self.hover = False
        self.spk_hover = False       # Zeiger steht auf dem Stummschalter
        self.on_toggle = on_toggle
        self.on_volume = on_volume
        self._dragging = False
        self._remember(bg=self.role_of(CARD))
        self._refs = {}
        self._ids = {}
        self._rw = 0
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_motion)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Motion>", self._on_hover_move)

    # ---- Geometrie -------------------------------------------------------
    def _metrics(self):
        pad = px(14)
        cd = px(M.get("check_size", 24))
        icd = px(M.get("row_icon", 32))
        pct_w = px(56)
        sl_w = px(118)
        spk = px(20)
        x_check = pad
        x_icon = x_check + cd + px(12)
        x_name = x_icon + icd + px(11)
        x_pct = self._rw - pad
        x_sl = x_pct - pct_w - sl_w
        x_spk = x_sl - spk - px(10)          # Stummschalter links vom Regler
        return dict(pad=pad, cd=cd, icd=icd, pct_w=pct_w, sl_w=sl_w, spk=spk,
                    x_check=x_check, x_icon=x_icon, x_name=x_name,
                    x_pct=x_pct, x_sl=x_sl, x_spk=x_spk)

    def _on_resize(self, e):
        if e.width == self._rw or e.width < 40:
            return
        self._rw = e.width
        self._draw()

    # ---- Zeichnen --------------------------------------------------------
    def set_fade(self, start):
        """Blendet die Zeile ab `start` (in Zeilen-Pixeln) nach unten aus.

        Der Verlauf wird als Canvas-Bild UEBER den Inhalt gelegt – innerhalb
        der Zeile sind alle Elemente Canvas-Items, deshalb funktioniert hier
        echte Transparenz.
        """
        if getattr(self, "_fade_start", None) == start:
            return
        self._fade_start = start
        self._draw_fade()

    def _draw_fade(self):
        fid = self._ids.get("fade")
        if fid:
            self.delete(fid)
            self._ids.pop("fade", None)
        start = getattr(self, "_fade_start", None)
        if start is None or self._rw < 40 or start >= self.h:
            return
        h = max(1, self.h - int(start))
        base = _hex_rgb(self._bd[1] if getattr(self, "_bd", None) else CARD)
        img = Image.new("RGBA", (self._rw, h))
        for i in range(h):
            a = int(255 * min(1.0, (i / float(max(1, h - 1))) ** 0.85))
            img.paste(base + (a,), (0, i, self._rw, i + 1))
        self._refs["fade"] = _to_photo(img)
        self._ids["fade"] = self.create_image(0, int(start), anchor="nw",
                                              image=self._refs["fade"])

    def set_backdrop(self, c1, c2, force=False):
        """Verlaufsausschnitt der Karte an dieser Position (nahtloser Untergrund)."""
        if not force and getattr(self, "_bd", None) == (c1, c2):
            return
        self._bd = (c1, c2)
        self.configure(bg=_mix(c1, c2, 0.5))
        if self._rw >= 40:
            self._draw()

    def _bg_image(self):
        w, h, r = self._rw, self.h, px(M.get("row_radius", 12))
        if self.sel:
            return gradient_photo(w, h, r, row_top(), row_bottom())
        if self.hover:
            base = self._bd[0] if getattr(self, "_bd", None) else CARD
            return rounded_photo(w, h, r, _mix(base, FG, 0.07))
        bd = getattr(self, "_bd", None)
        if bd:
            # Ausschnitt des Kartenverlaufs – ohne Rundung, damit es nahtlos bleibt
            return gradient_photo(w, h, 0, bd[0], bd[1])
        return None

    def _draw(self):
        if self._rw < 40:
            return
        self.delete("all")
        self._refs.clear()
        m = self._metrics()
        cy = self.h // 2

        bg = self._bg_image()
        if bg is not None:
            self._refs["bg"] = bg
            self.create_image(0, 0, anchor="nw", image=bg)

        chk = check_photo(m["cd"], self.sel, self.hover and not self.sel)
        self._refs["chk"] = chk
        self._ids["chk"] = self.create_image(m["x_check"], cy, anchor="w", image=chk)

        ic = app_icon_photo(m["icd"], self.key, self.label, self.exe, dim=self.muted)
        self._refs["ic"] = ic
        self._ids["icon"] = self.create_image(m["x_icon"], cy, anchor="w", image=ic)

        name = self.label if len(self.label) <= 18 else self.label[:17] + "…"
        self._ids["name"] = self.create_text(m["x_name"], cy, anchor="w", text=name,
                                             fill=(MUTED if self.muted else FG),
                                             font=uifont(12, semi=self.sel))

        self._ids["pct"] = self.create_text(
            m["x_pct"], cy, anchor="e",
            text=("stumm" if self.muted else "{} %".format(int(round(self.value * 100)))),
            fill=(MUTED if self.muted else FG),
            font=uifont(12 if self.muted else 14, semi=True))

        self._draw_speaker()
        self._draw_slider()
        self._draw_fade()          # ggf. Abblendung wieder oben auflegen

    def _row_base_color(self):
        """Farbe des Zeilenhintergrunds – Grundlage fuer Hervorhebungen darauf."""
        if self.sel:
            return _mix(row_top(), row_bottom(), 0.5)
        bd = getattr(self, "_bd", None)
        base = _mix(bd[0], bd[1], 0.5) if bd else CARD
        return _mix(base, FG, 0.07) if self.hover else base

    def _draw_speaker(self):
        """Stummschalter: eigenes Symbol, damit die Funktion auffindbar ist.

        Die Farbe folgt der Prozentzahl rechts (FG bzw. MUTED bei stumm), damit
        die Zeile nicht unterschiedlich hell wirkt. Liegt der Zeiger darauf,
        kommt ein aufgehelltes Kaestchen dahinter – sonst sieht man dem
        Lautsprecher nicht an, dass er anklickbar ist.
        """
        m = self._metrics()
        cy = self.h // 2
        for k in ("spk_bg", "spk"):
            if k in self._ids:
                self.delete(self._ids.pop(k))
        if self.spk_hover:
            d = m["spk"] + px(13)
            box = rounded_photo(d, d, px(8),
                                _mix(self._row_base_color(), FG, 0.20))
            self._refs["spk_bg"] = box
            self._ids["spk_bg"] = self.create_image(
                m["x_spk"] + m["spk"] // 2, cy, image=box)
        col = ACCENT if self.muted else FG
        spk = volume_photo(m["spk"], 0.0 if self.muted else max(0.05, self.value), col)
        self._refs["spk"] = spk
        self._ids["spk"] = self.create_image(m["x_spk"], cy, anchor="w", image=spk)
        fade = self._ids.get("fade")
        if fade:
            self.tag_raise(fade)   # Abblendung bleibt ganz oben

    def _draw_slider(self):
        m = self._metrics()
        th = px(M.get("slider_track", 6))
        kd = px(M.get("slider_knob", 19))
        cy = self.h // 2
        x0 = m["x_sl"]
        track_len = m["sl_w"]
        inner = track_len - kd          # Laufweg des Knopfs
        for k in ("track", "fill", "knob"):
            if k in self._ids:
                self.delete(self._ids[k])

        # Die Schiene muss sich auch vom aufgehellten Hover-Hintergrund abheben
        track_col = CARD2
        if self.hover and not self.sel:
            track_col = _mix(CARD2, FG if IS_LIGHT else "#000000", 0.18)
        tr = rounded_photo(track_len, th, th // 2, track_col)
        self._refs["track"] = tr
        self._ids["track"] = self.create_image(x0, cy - th // 2, anchor="nw", image=tr)

        fw = int(round(kd / 2 + inner * self.value))
        if fw >= th:
            c1, c2 = (_mix(ACCENT, "#FFFFFF", 0.30), ACCENT)
            if self.muted:                       # stumm: Fuellung wird grau
                c1 = c2 = _mix(CARD2, FG, 0.22)
            grad = _to_pil_gradient(track_len, th, c1, c2,
                                    horizontal=True).crop((0, 0, fw, th))
            mask = Image.new("L", (fw, th), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, fw - 1, th - 1],
                                                   radius=th // 2, fill=255)
            grad.putalpha(mask)
            ph = _to_photo(grad)
            self._refs["fill"] = ph
            self._ids["fill"] = self.create_image(x0, cy - th // 2, anchor="nw", image=ph)

        # Im hellen Modus braucht der weisse Knopf einen kraeftigeren Rand,
        # sonst verschwindet er auf der hellen Karte.
        ring = _mix(STROKE, FG, 0.45) if IS_LIGHT else STROKE
        knob = (skin_image("slider_knob", kd, kd)
                or circle_photo(kd, KNOB, ring, 2 if IS_LIGHT else 1))
        self._refs["knob"] = knob
        kx = x0 + kd / 2 + inner * self.value
        self._ids["knob"] = self.create_image(kx, cy, image=knob)

    # ---- Interaktion -----------------------------------------------------
    def _in_slider(self, x):
        m = self._metrics()
        return m["x_sl"] - px(6) <= x <= m["x_sl"] + m["sl_w"] + px(6)

    def _value_from_x(self, x):
        m = self._metrics()
        kd = px(M.get("slider_knob", 19))
        inner = max(1, m["sl_w"] - kd)
        return max(0.0, min(1.0, (x - m["x_sl"] - kd / 2) / float(inner)))

    def _on_icon(self, x):
        """Trefferbereich des Stummschalters (Lautsprecher-Symbol)."""
        m = self._metrics()
        return m["x_spk"] - px(7) <= x <= m["x_spk"] + m["spk"] + px(7)

    def _on_press(self, e):
        if self._on_icon(e.x):
            if self.on_mute:
                self.on_mute(self.key, not self.muted)
        elif self._in_slider(e.x):
            self._dragging = True
            self.set_volume(self._value_from_x(e.x))
            if self.on_volume:
                self.on_volume(self.key, self.value, False)
        else:
            if self.on_toggle:
                self.on_toggle(self.key, not self.sel)

    def _on_motion(self, e):
        if self._dragging:
            self.set_volume(self._value_from_x(e.x))
            if self.on_volume:
                self.on_volume(self.key, self.value, False)

    def _on_release(self, e):
        if self._dragging:
            self._dragging = False
            if self.on_volume:
                self.on_volume(self.key, self.value, True)

    def _on_hover_move(self, e):
        self.configure(cursor="hand2")
        on = self._on_icon(e.x)
        if on != self.spk_hover:
            self.spk_hover = on
            self._draw_speaker()

    def _set_hover(self, on):
        if self.hover == on:
            return
        self.hover = on
        if not on:
            self.spk_hover = False
        self._draw()

    # ---- Zustand ---------------------------------------------------------
    def set_volume(self, v):
        v = max(0.0, min(1.0, float(v)))
        if abs(v - self.value) < 0.0005:
            return
        self.value = v
        if self._rw >= 40:
            self._draw_slider()
            if "pct" in self._ids:
                self.itemconfig(self._ids["pct"],
                                text="{} %".format(int(round(v * 100))))

    def set_selected(self, sel):
        if self.sel == bool(sel):
            return
        self.sel = bool(sel)
        self._draw()

    def update_item(self, item):
        self.label = item["label"]
        self.exe = item.get("exe")
        self.set_muted(bool(item.get("muted")))

    def set_muted(self, on):
        if self.muted == bool(on):
            return
        self.muted = bool(on)
        self._draw()

    def restyle(self):
        self.configure(bg=CARD)
        self._draw()


class Osd:
    """Lautstaerke-Einblendung als Layered Window.

    Das komplette Fenster ist EIN gerendertes RGBA-Bild. Dadurch sind die
    abgerundeten Ecken echt weich (kein hartes Clipping, keine Farbfransen) und
    ein Update ist ein einziger Aufruf – es flackert nichts.
    """

    MAX_ICONS = 7

    def __init__(self, root, size=45, xpct=50, ypct=88):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry("10x10+-4000+-4000")
        self.win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
        self._layer = _LayeredWindow(hwnd)
        self._visible = False
        self._hide_job = None
        self._last = None
        self.configure(size, xpct, ypct)
        # Das Fenster bleibt bestehen und wird ueber die Deckkraft aus- und
        # eingeblendet: withdraw()/deiconify() verwirft den Bildinhalt des
        # Layered Window, die Einblendung waere danach leer.
        self._blank()

    # ---- Geometrie -------------------------------------------------------
    def configure(self, size, xpct, ypct):
        self.size = max(10, min(100, int(size)))
        self.s = 0.55 + (self.size - 10) / 90.0 * 1.25
        self.xp = max(0, min(100, int(xpct)))
        self.yp = max(0, min(100, int(ypct)))
        # Das Bild ist rundum groesser als die Karte – dort liegt der Schatten.
        self.shadow = self._p(M.get("osd_shadow", 16))
        self.W = self._p(M.get("osd_w", 340)) + 2 * self.shadow
        self.H = self._p(M.get("osd_h", 96)) + 2 * self.shadow
        if self._last:
            self._paint(*self._last)

    def _p(self, v):
        return max(1, int(round(v * SCALE * self.s)))

    def _origin(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        m = self._p(24)
        x = m + (sw - self.W - 2 * m) * (self.xp / 100.0)
        y = m + (sh - self.H - 2 * m) * (self.yp / 100.0)
        return int(x), int(y)

    # ---- Zeichnen --------------------------------------------------------
    def _render(self, items, pct, sub):
        W, H = self.W, self.H
        m = 3                                   # Supersampling fuer weiche Ecken
        pad = self.shadow                       # Rand fuer den Schatten
        cw, ch = W - 2 * pad, H - 2 * pad       # eigentliche Kartenflaeche
        sw, sh = cw * m, ch * m
        rad = int(self._p(M.get("osd_radius", 20)) * m)

        card = _to_pil_gradient(sw, sh, card_top(), card_bottom())
        mask = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1],
                                               radius=rad, fill=255)
        big = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        big.paste(card, (0, 0), mask)
        # feine Kante
        ImageDraw.Draw(big).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=rad,
                                              outline=_mix(STROKE, FG, 0.10),
                                              width=max(1, m))
        card_img = big.resize((cw, ch), Image.LANCZOS)

        # Schatten: weich gezeichnete Silhouette leicht nach unten versetzt
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if pad > 2:
            sh_mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(sh_mask).rounded_rectangle(
                [pad, pad + pad // 3, W - pad, H - pad + pad // 3],
                radius=self._p(M.get("osd_radius", 20)), fill=120)
            sh_mask = sh_mask.filter(ImageFilter.GaussianBlur(pad * 0.55))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            shadow.putalpha(sh_mask)
            img = Image.alpha_composite(img, shadow)
        img.paste(card_img, (pad, pad), card_img)

        # Ab hier wird auf der Karte gezeichnet: alle Koordinaten liegen um den
        # Schattenrand (pad) versetzt.
        dr = ImageDraw.Draw(img)
        ipad = pad + self._p(20)
        icon_d = self._p(M.get("osd_icon", 30))
        row_y = pad + self._p(30)

        # Programm-Symbole
        x = ipad
        for key, label, exe in items[:self.MAX_ICONS]:
            ic = app_icon_pil(icon_d, key, label, exe)
            img.paste(ic, (int(x), int(row_y - icon_d / 2)), ic)
            x += icon_d + self._p(6)

        # Name links, Wert rechts: Zahl gross und ruhig, das "%" kleiner und
        # zurueckgenommen – das wirkt aufgeraeumter als beides gleich gross.
        if len(items) == 1:
            f = _ui_font(self._p(M.get("osd_font_name", 18)))
            dr.text((x + self._p(6), row_y), items[0][1], font=f,
                    fill=_mix(FG, MUTED, 0.15), anchor="lm")
        if pct is not None:
            big = _ui_font(self._p(M.get("osd_font_pct", 21)))
            small = _ui_font(self._p(int(M.get("osd_font_pct", 21) * 0.82)))
            num = str(pct)
            pw = dr.textlength("%", font=small)
            gap = self._p(3)
            dr.text((W - ipad, row_y), "%", font=small, fill=MUTED, anchor="rm")
            dr.text((W - ipad - pw - gap, row_y), num, font=big, fill=FG, anchor="rm")
        else:
            fp = _ui_font(self._p(int(M.get("osd_font_pct", 21) * 0.7)))
            dr.text((W - ipad, row_y), sub or "—", font=fp, fill=MUTED, anchor="rm")

        # Lautsprecher + Balken
        spk = self._p(M.get("osd_speaker", 34))
        ty = pad + self._p(64)
        th = self._p(9)
        level = (pct or 0) / 100.0
        sp = volume_pil(spk, level, FG)
        img.paste(sp, (ipad, int(ty + th / 2 - spk / 2)), sp)

        bx = ipad + spk + self._p(13)
        bw = W - ipad - bx
        if bw > th:
            track = Image.new("RGBA", (bw, th), (0, 0, 0, 0))
            ImageDraw.Draw(track).rounded_rectangle([0, 0, bw - 1, th - 1],
                                                    radius=th // 2, fill=CARD2)
            img.paste(track, (bx, ty), track)
            fw = int(bw * max(0.0, min(1.0, level)))
            if fw >= th:
                fill = _to_pil_gradient(bw, th, _mix(ACCENT, "#FFFFFF", 0.35),
                                        ACCENT, horizontal=True).crop((0, 0, fw, th))
                fmask = Image.new("L", (fw, th), 0)
                ImageDraw.Draw(fmask).rounded_rectangle([0, 0, fw - 1, th - 1],
                                                        radius=th // 2, fill=255)
                fill.putalpha(fmask)
                img.paste(fill, (bx, ty), fill)
        return img

    def _paint(self, items, pct, sub):
        """Reihenfolge ist wichtig: erst Tk (Geometrie, Einblenden), dann das Bild.

        Ruft Tk danach noch ein Layout aus, uebermalt es den Fensterinhalt und
        die Einblendung erscheint leer.
        """
        self._last = (items, pct, sub)
        img = self._render(items, pct, sub)
        x, y = self._origin()
        y += getattr(self, "_anim_off", 0)     # Ausfahrt nach unten
        geo = "{}x{}+{}+{}".format(self.W, self.H, x, y)
        if geo != getattr(self, "_geo", None):
            self._geo = geo
            self.win.geometry(geo)
        self.win.update_idletasks()
        self._layer.show(img, x, y, alpha=getattr(self, "_anim_alpha", 245))

    def _blank(self):
        """Unsichtbar schalten, ohne das Fenster zu zerstoeren."""
        x, y = self._origin()
        img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.win.geometry("{}x{}+{}+{}".format(self.W, self.H, x, y))
        self.win.update_idletasks()
        self._layer.show(img, x, y, alpha=0)

    # ---- Anzeige ---------------------------------------------------------
    def show(self, items, pct, sub=None, hold=1100):
        # kein lift()/topmost hier: das wuerde bei jeder Rastung versuchen, das
        # Fenster nach vorne zu holen – Windows laesst dann Programme in der
        # Taskleiste blinken. Die Fensterstile erledigen das bereits.
        # Beides zuruecksetzen: nach dem Ausfahren stehen Versatz und Deckkraft
        # noch auf den Endwerten – sonst bliebe die Einblendung unsichtbar.
        self._visible = True
        self._anim_off = 0
        self._anim_alpha = 245
        self._paint(items, pct, sub)
        if self._hide_job is not None:
            self.root.after_cancel(self._hide_job)
        self._hide_job = self.root.after(hold, self.hide)

    def hide(self):
        """Faehrt nach unten aus dem Bild – wie die Windows-Einblendung."""
        self._hide_job = None
        if not self._visible:
            return
        self._anim_off = 0
        self._slide_out()

    def _slide_out(self, step=0):
        total = 9
        if step > total or self._last is None:
            self._visible = False
            self._anim_off = 0
            self._blank()
            return
        t = step / float(total)
        self._anim_off = int((t ** 2) * self.H * 1.6)     # beschleunigt nach unten
        self._anim_alpha = int(245 * (1.0 - t ** 1.4))
        try:
            self._paint(*self._last)
        except Exception:
            pass
        self._hide_job = self.root.after(16, lambda: self._slide_out(step + 1))


class PositionPicker(tk.Canvas, Restylable):
    """3x3-Raster zur Auswahl der Einblendungs-Position (wie in OBS)."""
    def __init__(self, parent, value, command, bg=None):
        bg = bg if bg is not None else CARD
        self._bg_role = None
        self.cell = px(34)
        self.gap = px(5)
        w = 3 * self.cell + 2 * self.gap
        h = w
        super().__init__(parent, width=w, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.value = value
        self._remember(bg=self.role_of(bg))
        self._cells = {}
        for r in range(3):
            for c in range(3):
                key = "tmb"[r] + "lcr"[c]
                x = c * (self.cell + self.gap)
                y = r * (self.cell + self.gap)
                img = self.create_image(x, y, anchor="nw", image=self._cell_img(False))
                dot = self.create_image(x + self.cell // 2, y + self.cell // 2,
                                        image=self._dot_img(False))
                self._cells[key] = (img, dot)
                self.tag_bind(img, "<Button-1>", lambda e, k=key: self._pick(k))
                self.tag_bind(dot, "<Button-1>", lambda e, k=key: self._pick(k))
        self._render()

    def _cell_img(self, on):
        return rounded_photo(self.cell, self.cell, px(7), ACCENT if on else CARD2)

    def _dot_img(self, on):
        return rounded_photo(px(14), px(5), px(2), "#FFFFFF" if on else OFF)

    def _render(self):
        for key, (img, dot) in self._cells.items():
            on = (key == self.value)
            self.itemconfig(img, image=self._cell_img(on))
            self.itemconfig(dot, image=self._dot_img(on))

    def _pick(self, key):
        self.value = key
        self._render()
        if self.command:
            self.command(key)

    def restyle(self):
        self.configure(bg=self._color(self._roles["bg"], CARD))
        self._render()


# ---------------------------------------------------------------------------
# Haupt-App
# ---------------------------------------------------------------------------
class App:
    def __init__(self):
        self.cfg = load_config()
        self.targets = set(self.cfg["targets"])
        # Alte Configs kannten nur "step" (1..25 %) – daraus die Geschwindigkeit ableiten
        if "speed" in (self.cfg or {}) and self.cfg.get("speed"):
            self.speed = int(self.cfg["speed"])
        else:
            self.speed = int(max(10, min(100, round((int(self.cfg.get("step", 4)) - 0.6)
                                                    / 7.4 * 90 + 10))))
        self.reverse = bool(self.cfg["reverse"])
        self.suppress = bool(self.cfg["suppress"])
        self.active = bool(self.cfg["active"])
        self.osd_size = int(self.cfg.get("osd_size", 45))
        self.osd_x = int(self.cfg.get("osd_x", 50))
        self.osd_y = int(self.cfg.get("osd_y", 88))
        self.osd_enabled = bool(self.cfg.get("osd_enabled", True))
        self.use_media_keys = bool(self.cfg.get("media_keys", False))
        self.switch_mode = str(self.cfg.get("switch_mode", "none"))
        if self.switch_mode not in dict(SWITCH_MODES):
            self.switch_mode = "none"
        self.klistener = None
        self.hidden = set(self.cfg.get("hidden") or [])
        # key -> Anzeigename aller je gesehenen Apps (fuer die Sichtbarkeitsliste)
        self.known = {k: self._label_of(k) for k in (self.cfg.get("known") or [])}
        self.exes = dict(self.cfg.get("exes") or {})   # key -> Pfad (fuer Symbole)

        self.job_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self._stop = False
        self._dragging_key = None
        self.rows = {}
        self.listener = None
        self.icon = None
        self._epv = None   # IAudioEndpointVolume (Windows-Gesamtlautstaerke)
        self._meta = {}    # key -> (label, exe) fuer die Symbole in der Einblendung
        self._mix_items = []
        self._mix_content_h = 200
        self._vol_anim = {}     # key -> Ziel in Prozent (laufende Fahrt)
        self._vol_now = {}      # key -> aktueller Prozentwert
        self._vol_step = {}     # key -> Prozentpunkte je Schritt
        self._sess_cache = None

        migrate_autostart()     # Altlast aus der Zeit vor der Umbenennung
        self._build_gui()
        self._start_worker()
        self._start_hook()
        self._start_tray()
        self._start_show_waiter()

        self.job_queue.put(("refresh",))
        self.root.after(40, self._poll_ui)
        self._schedule_autorefresh()
        self._watch_dpi()

    # ---- Fenster-Grundgeruest --------------------------------------------
    def _set_dpi_awareness(self):
        """Bei Windows als „pro Monitor" anmelden.

        Ohne das zeichnet die App fuer die Skalierung des Hauptmonitors und
        Windows streckt das fertige Bild auf allen anderen hoch – das kostet
        Schaerfe und erzeugt helle Saeume an den Kanten. Mit „per monitor V2"
        bekommen wir stattdessen die echte Aufloesung des Monitors, auf dem das
        Fenster gerade liegt, und zeichnen selbst neu (siehe `_check_dpi`).
        Muss vor dem ersten Fenster passieren.
        """
        try:
            u = ctypes.windll.user32
            u.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
            u.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
            if u.SetProcessDpiAwarenessContext(-4):     # PER_MONITOR_AWARE_V2
                return
        except Exception:
            pass
        for versuch in (lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),
                        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(1),
                        lambda: ctypes.windll.user32.SetProcessDPIAware()):
            try:
                versuch()
                return
            except Exception:
                continue

    def _window_scale(self):
        """Skalierung des Monitors, auf dem das Fenster gerade liegt."""
        try:
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dpi = u.GetDpiForWindow(hwnd)
            if dpi:
                return max(1.0, dpi / 96.0)
        except Exception:
            pass
        try:
            return max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        except Exception:
            return 1.0

    def _build_gui(self):
        global SCALE
        self._set_dpi_awareness()
        self.root = tk.Tk()
        SCALE = self._window_scale()

        self.root.title("Volumix")
        self.root.configure(bg=BG)
        self.root.geometry("{}x{}".format(px(BASE_W), px(M.get("window_h", 720))))
        # Hoehe darf gezogen werden; die Breite bleibt fest und die Oberflaeche
        # skaliert bewusst NICHT mit (Groessen stehen in den Einstellungen).
        #
        # Die Breite wird ueber minsize == maxsize == px(BASE_W) festgehalten,
        # NICHT ueber resizable(False, ...). Tk behandelt „Breite gesperrt"
        # ueber einen eigenen Pfad, der sich mit der Per-Monitor-Umrechnung von
        # Windows beisst: Auf einem abweichend skalierten Monitor verliert das
        # Fenster dann bei jeder Mausbewegung zwei Pixel Breite und schnappt
        # beim Loslassen zurueck – es zittert sichtbar. Ueber die Grenzwerte
        # bleibt die Breite genauso fest, aber ohne diesen Nebeneffekt.
        self.root.resizable(True, True)
        self.root.minsize(px(BASE_W), px(320))
        self.root.maxsize(px(BASE_W), self.root.winfo_screenheight())
        try:
            self._icon_big = _to_photo(make_icon_image(px(64)))
            self.root.iconphoto(True, self._icon_big)
        except Exception:
            pass

        self.status_var = tk.StringVar(value="Bereit – Regler ziehen oder Daumenrad drehen.")
        self._status_trace = None
        self.osd = Osd(self.root, self.osd_size, self.osd_x, self.osd_y)
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.root.bind_all("<MouseWheel>", self._on_vwheel)

        self.view = "mixer"
        self.content = None
        self._show_view("mixer")
        self._apply_titlebar()

    # ---- Ansichtswechsel (Mixer <-> Einstellungen) -----------------------
    def _show_view(self, name):
        """Baut die neue Ansicht unsichtbar auf und tauscht sie erst dann ein.

        So entsteht kein Flackern: Der alte Inhalt bleibt stehen, bis der neue
        fertig ist – beides passiert in einem einzigen Bildaufbau.
        """
        self.view = name
        self.rows = {}
        old = self.content
        self.root.configure(bg=BG)
        new = tk.Frame(self.root, bg=BG)      # noch nicht gepackt = unsichtbar
        if name == "settings":
            # In den Einstellungen gilt die Hoehengrenze des Mixers nicht
            self.root.minsize(px(BASE_W), px(320))
            self.root.maxsize(px(BASE_W), self.root.winfo_screenheight())
            self._build_settings(new)
        else:
            self._sized = False               # Mixer bestimmt seine Hoehe neu
            self._build_mixer(new)
        new.update_idletasks()                # fertig zeichnen, bevor er sichtbar wird
        self.content = new
        if old is not None:
            try:
                old.pack_forget()
            except Exception:
                pass
        new.pack(fill="both", expand=True)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
        if name == "mixer":
            self.job_queue.put(("refresh",))
        else:
            # Hoehe an den Inhalt anpassen und nach oben begrenzen, damit das
            # Fenster nicht ueber den Bildschirm hinauswaechst.
            self.root.update_idletasks()
            need = 0
            try:
                box = self._scan.bbox("all")
                need = (box[3] - box[1]) if box else 0
            except Exception:
                pass
            chrome = px(96)              # Kopfzeile + Raender
            hard = self.root.winfo_screenheight() - px(90)
            want = max(px(360), min(px(M.get("settings_h", 780)), hard,
                                    need + chrome))
            self.root.maxsize(px(BASE_W), want)
            self.root.geometry("{}x{}".format(px(BASE_W), want))
            self.root.after(80, self._settings_bar)

    def _build_mixer(self, root_frame):
        OUT = px(18)

        # ----- Header -----
        header = tk.Frame(root_frame, bg=BG)
        header.pack(fill="x", padx=OUT, pady=(px(16), px(8)))
        try:
            self._hdr_icon = _to_photo(make_icon_image(px(40)))
            self._hdr_lbl = tk.Label(header, image=self._hdr_icon, bg=BG)
            self._hdr_lbl.pack(side="left")
        except Exception:
            pass
        htext = tk.Frame(header, bg=BG)
        htext.pack(side="left", padx=(px(12), 0))
        tk.Label(htext, text="Volumix", bg=BG, fg=FG,
                 font=uifont(17, semi=True)).pack(anchor="w")
        tk.Label(htext, text="Lautstärke-Mixer für einzelne Apps", bg=BG, fg=MUTED,
                 font=uifont(11)).pack(anchor="w")
        IconButton(header, lambda d: gear_photo(d, MUTED),
                   lambda: self._show_view("settings"),
                   bg=BG, fill=CARD, fill_hover=CARD2).pack(side="right")
        self._mode_btn = IconButton(header, lambda d: moon_sun_photo(d, IS_LIGHT, MUTED),
                                    self._toggle_mode,
                                    bg=BG, fill=CARD, fill_hover=CARD2)
        self._mode_btn.pack(side="right", padx=(0, px(8)))

        # ----- Statusleiste zuerst packen: so bleibt sie immer sichtbar,
        # auch wenn das Fenster sehr klein gezogen wird -----
        self._status_bar = tk.Canvas(root_frame, height=px(42), bg=BG,
                                     highlightthickness=0, bd=0)
        self._status_bar.pack(fill="x", padx=OUT, pady=(px(4), px(12)),
                              side="bottom")
        self._status_refs = []
        self._status_bar.bind("<Configure>", self._paint_status)
        if getattr(self, "_status_trace", None) is None:
            self._status_trace = self.status_var.trace_add(
                "write", lambda *a: self._paint_status())

        # ----- Mixer: EIN Canvas, damit der Verlauf durchgehend sichtbar ist -----
        self._scan = tk.Canvas(root_frame, bg=BG, highlightthickness=0, bd=0)
        self._scan.pack(fill="both", expand=True, padx=OUT, pady=(px(6), 0))
        self._scan_refs = []
        self._row_wins = []
        # Nur bei Breitenaenderung neu auslegen. Beim Ziehen der Fensterhoehe
        # wuerde ein Neuaufbau sichtbar flackern – noetig ist er dort nicht.
        self._scan.bind("<Configure>", self._on_scan_configure)

    def _toggle_row(self, parent, text, value, command, bg=None, compact=False):
        bg = bg if bg is not None else CARD
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=px(3) if compact else px(7))
        tk.Label(row, text=text, bg=bg, fg=FG, font=uifont(11), anchor="w").pack(side="left")
        sw = ToggleSwitch(row, value=value, command=command, bg=bg)
        sw.pack(side="right")
        return sw

    # ---- Einstellungs-Ansicht -------------------------------------------
    def _card(self, parent, title):
        card = Card(parent, bg_outer=BG)
        card.pack(fill="x", padx=px(18), pady=px(4))
        inner = tk.Frame(card.inner, bg=CARD)
        inner.pack(fill="x", padx=px(14), pady=(px(8), px(9)))
        tk.Label(inner, text=title, bg=CARD, fg=MUTED,
                 font=uifont(10, semi=True)).pack(anchor="w")
        return inner

    def _chip_row(self, parent, items, current, command):
        """Reihe auswaehlbarer Chips (Skin, Hell/Dunkel)."""
        row = ChipGroup(parent, items, current, command, bg=CARD)
        row.pack(fill="x", pady=(px(8), px(2)))
        return row

    def _slider_row(self, parent, title, value_text, frac, command,
                    width=None, tight=False):
        """Eine Zeile: Beschriftung, Regler, Wert – alles auf gleicher Hoehe."""
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(px(4) if tight else px(7), px(2)))
        tk.Label(row, text=title, bg=CARD, fg=FG, font=uifont(11),
                 anchor="w", width=15 if not tight else 11).pack(side="left")
        lbl = tk.Label(row, text=value_text, bg=CARD, fg=FG,
                       font=uifont(11, semi=True), width=6, anchor="e")
        lbl.pack(side="right")
        sl = Slider(row, width or px(230), command, bg=CARD)
        sl.pack(side="right", padx=(px(10), px(8)))
        sl.set(max(0.0, min(1.0, frac)))
        return lbl

    def _sub_scroll(self, parent, height, expand=False):
        """Scrollbarer Bereich mit eigener Leiste (fuer lange Listen).

        Der Bereich hebt sich farblich ab, damit erkennbar ist, wo gescrollt
        werden kann; das Mausrad wirkt lokal, solange der Zeiger darueber steht.

        Mit `expand=True` nimmt er den uebrigen Platz statt einer festen Hoehe.
        Das ist die robustere Variante: Wird der Text darueber laenger, schiebt
        sich die Liste sonst ueber die Knoepfe darunter.
        """
        wrap = tk.Frame(parent, bg=CARD2, height=height)
        wrap.pack_propagate(False)
        wrap.pack(fill="both" if expand else "x", expand=expand,
                  pady=(px(2), px(4)))
        bar = tk.Canvas(wrap, width=px(6), bg=CARD2, highlightthickness=0, bd=0)
        bar.pack(side="right", fill="y", padx=(0, px(5)), pady=px(6))
        can = tk.Canvas(wrap, bg=CARD2, highlightthickness=0, bd=0)
        can.pack(side="left", fill="both", expand=True, padx=(px(9), px(3)),
                 pady=px(6))
        inner = tk.Frame(can, bg=CARD2)
        win = can.create_window((0, 0), window=inner, anchor="nw")
        thumb = bar.create_rectangle(0, 0, 0, 0, width=0,
                                     fill=_mix(CARD2, FG, 0.34))

        def paint_bar():
            box = can.bbox("all")
            vh = can.winfo_height()
            if not box or vh < 10:
                return
            content = box[3] - box[1]
            if content <= vh + 2:
                bar.coords(thumb, 0, 0, 0, 0)
                return
            bh = max(px(24), int(vh * vh / float(content)))
            y = int((vh - bh) * can.yview()[0])
            bar.coords(thumb, px(1), y, px(5), y + bh)

        def resized(e=None):
            can.configure(scrollregion=can.bbox("all"))
            paint_bar()

        inner.bind("<Configure>", resized)
        can.bind("<Configure>", lambda e: (can.itemconfig(win, width=e.width),
                                           paint_bar()))

        def wheel(e):
            box = can.bbox("all")
            if box and (box[3] - box[1]) > can.winfo_height():
                can.yview_scroll(int(-e.delta / 120), "units")
                paint_bar()
            return "break"       # nie an die aeussere Seite weiterreichen

        for w in (wrap, can, inner, bar):
            w.bind("<MouseWheel>", wheel)
        self._sub_wheel = wheel          # auch fuer die Zeilen der Liste
        inner.bind("<Enter>", lambda e: setattr(self, "_inner_scroll", can))
        inner.bind("<Leave>", lambda e: setattr(self, "_inner_scroll", None))
        return inner

    def _skin_accent(self, name):
        """Akzentfarbe eines Skins fuer die Farbpunkte (ohne ihn zu laden)."""
        try:
            with open(os.path.join(SKINS_DIR, name, "theme.json"), "r",
                      encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        acc = data.get("accent", BASE_THEME["accent"])
        if isinstance(acc, dict):
            return acc.get(MODE, acc.get("dark", "#7C5CFF"))
        return acc or "#7C5CFF"

    def _build_settings(self, root_frame):
        OUT = px(18)

        # ----- Kopf mit Zurueck-Pfeil -----
        header = tk.Frame(root_frame, bg=BG)
        header.pack(fill="x", padx=OUT, pady=(px(16), px(8)))
        IconButton(header, lambda d: arrow_photo(d, FG),
                   lambda: self._show_view("mixer"),
                   bg=BG, fill=CARD, fill_hover=CARD2).pack(side="left")
        tk.Label(header, text="Einstellungen", bg=BG, fg=FG,
                 font=uifont(17, semi=True)).pack(side="left", padx=(px(12), 0))

        # ----- scrollbarer Inhalt -----
        wrap = tk.Frame(root_frame, bg=BG)
        wrap.pack(fill="both", expand=True)
        self._scan = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        self._scan.pack(side="left", fill="both", expand=True)
        body = tk.Frame(self._scan, bg=BG)
        win = self._scan.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: self._sync_scrollregion(self._scan))
        self._scan.bind("<Configure>", lambda e: (
            self._scan.itemconfig(win, width=e.width), self._settings_bar()))
        # als Widget, damit sie ueber dem eingebetteten Inhalt liegt
        self._set_bar = tk.Frame(self._scan, bg=_mix(CARD2, FG, 0.30),
                                 bd=0, highlightthickness=0)

        # ---- Design zuerst: Modus links, Farbraster rechts daneben ----
        c3 = self._card(body, "DESIGN")
        # Farbraster rechts NEBEN die Ueberschrift: dadurch beginnt es auf
        # gleicher Hoehe wie „DESIGN“ und die Karte bleibt flach.
        drow = tk.Frame(c3, bg=CARD)
        drow.pack(fill="x", pady=(0, px(2)))

        ccol = tk.Frame(drow, bg=CARD)
        ccol.pack(side="right", anchor="n")
        tk.Label(ccol, text="Farbe", bg=CARD, fg=MUTED,
                 font=uifont(10, semi=True)).pack(anchor="w")
        grid = tk.Frame(ccol, bg=CARD)
        grid.pack(anchor="w", pady=(px(4), 0))

        mcol = tk.Frame(drow, bg=CARD)
        mcol.pack(side="left", anchor="n")
        tk.Label(mcol, text="Modus", bg=CARD, fg=FG,
                 font=uifont(11)).pack(anchor="w", pady=(px(6), 0))
        self._mode_chips = ChipGroup(mcol, [("dark", "Dunkel"), ("light", "Hell")],
                                     MODE, self._pick_mode, bg=CARD)
        self._mode_chips.pack(anchor="w", pady=(px(4), 0))
        self._color_dots = {}
        for i, (key, label, dark_c, light_c) in enumerate(PALETTE):
            if i % 6 == 0:
                line = tk.Frame(grid, bg=CARD)
                line.pack(anchor="w", pady=px(1))
            dot = ColorDot(line, light_c if IS_LIGHT else dark_c,
                           key == CUSTOM_COLOR,
                           lambda k=key: self._pick_color(k), bg=CARD, size=px(30))
            dot.pack(side="left", padx=(0, px(7)))
            self._color_dots[key] = dot
        self._skin_chips = None

        # ---- Steuerung ----
        c1 = self._card(body, "STEUERUNG")
        self.speed_lbl = self._slider_row(
            c1, "Geschwindigkeit", "{} %".format(self.speed),
            (self.speed - 10) / 90.0, self._set_speed)

        self.sw_active = self._toggle_row(c1, "Steuerung aktiv", self.active,
                                          self._on_active, compact=True)
        # Eine Option statt zweier: an = Daumenrad (horizontales Scrollen wird
        # abgefangen), aus = Lautstärke-Tasten der Tastatur/Maus-Software.
        self._toggle_row(c1, "Horizontales Scrollen verwenden",
                         not self.use_media_keys, self._on_input_mode, compact=True)
        self._toggle_row(c1, "Scrollrichtung umkehren", self.reverse,
                         self._on_reverse, compact=True)
        self._toggle_row(c1, "Mit Windows starten", get_autostart(),
                         self._on_autostart, compact=True)

        # Beim Wechsel Gesamt <-> App: Pegel angleichen oder nicht.
        # Die Erklaerung steckt hinter dem Fragezeichen – ausgeschrieben
        # braeuchte sie vier Zeilen und macht die Einstellungen unruhig.
        zeile = tk.Frame(c1, bg=CARD)
        zeile.pack(fill="x", pady=(px(9), 0))
        tk.Label(zeile, text="Beim Wechsel Gesamt ↔ App", bg=CARD, fg=FG,
                 font=uifont(11), anchor="w").pack(side="left")
        hilfe = tk.Label(zeile, image=help_photo(px(16), MUTED), bg=CARD,
                         cursor="hand2")
        hilfe.image = help_photo(px(16), MUTED)
        hilfe.pack(side="left", padx=(px(7), 0))
        hilfe.bind("<Enter>", lambda e: self._show_tip(hilfe, SWITCH_HELP))
        hilfe.bind("<Leave>", lambda e: self._hide_tip())

        self._switch_chips = ChipGroup(c1, SWITCH_MODES, self.switch_mode,
                                       self._on_switch_mode, bg=CARD)
        self._switch_chips.pack(anchor="w", pady=(px(5), px(2)))

        # ---- Einblendung ----
        c2 = self._card(body, "LAUTSTÄRKE-EINBLENDUNG")
        self._toggle_row(c2, "Einblendung anzeigen", self.osd_enabled, self._on_osd_enabled)

        self.size_lbl = self._slider_row(
            c2, "Größe", "{} %".format(self.osd_size),
            (self.osd_size - 10) / 90.0, self._set_osd_size)

        self.posx_lbl = self._slider_row(
            c2, "Position waagerecht", "{} %".format(self.osd_x),
            self.osd_x / 100.0, self._set_osd_x)
        self.posy_lbl = self._slider_row(
            c2, "Position senkrecht", "{} %".format(self.osd_y),
            self.osd_y / 100.0, self._set_osd_y)


        tk.Frame(body, bg=BG, height=px(8)).pack()

    # ---- Design-Wechsel (ohne Neustart) ---------------------------------
    def _toggle_mode(self):
        self._apply_theme(SKIN_NAME, "dark" if IS_LIGHT else "light")

    def _pick_mode(self, mode):
        if mode == MODE:
            return
        self._apply_theme(SKIN_NAME, mode)

    def _pick_skin(self, name):
        if name == SKIN_NAME and CUSTOM_COLOR is None:
            return
        self._apply_theme(name, MODE, color=None)

    def _pick_color(self, key):
        """Farbe aus der Palette waehlen."""
        self._apply_theme(SKIN_NAME, MODE, color=key)
        for k, dot in getattr(self, "_color_dots", {}).items():
            if dot.winfo_exists():
                dot.set_active(k == key)

    def _apply_theme(self, skin, mode, color=-1):
        """Wechselt Skin/Modus/Farbe, ohne die Oberflaeche neu aufzubauen.

        Alle Widgets bleiben bestehen und werden nur umgefaerbt – sonst wuerde
        das Fenster bei jedem Klick sichtbar neu laden.
        """
        old = Restylable.palette()
        load_skin(skin, mode, color)
        # Farbabhaengige Grafiken verwerfen; die aus den Programmen extrahierten
        # App-Symbole bleiben erhalten (teuerster Teil).
        for k in [k for k in _PHOTO_CACHE if k[0] not in ("app", "av")]:
            del _PHOTO_CACHE[k]
        _CORNER_CACHE.clear()
        new = Restylable.palette()
        cmap = {old[r]: new[r] for r in old if old[r] != new[r]}

        self.cfg["skin"] = SKIN_NAME
        self.cfg["mode"] = MODE
        self._save()
        self.root.configure(bg=BG)
        self._recolor(self.root, cmap)
        # Canvas-Inhalte tragen die Farben als gezeichnete Bilder – neu auslegen
        self._layout_mixer()
        self._paint_status()
        self._update_status_summary()
        grp = getattr(self, "_mode_chips", None)
        if grp is not None and grp.winfo_exists():
            grp.select(MODE)
        # Farbpunkte tragen die Modus-Variante der Farbe
        for k, dot in getattr(self, "_color_dots", {}).items():
            if dot.winfo_exists():
                dot.color = palette_color(k, IS_LIGHT)
                dot.set_active(k == CUSTOM_COLOR)
                dot.restyle()
        btn = getattr(self, "_mode_btn", None)
        if btn is not None and btn.winfo_exists():
            btn.set_icon(lambda d: moon_sun_photo(d, IS_LIGHT, MUTED))
        # Logo traegt die Akzentfarbe -> mit erneuern
        lbl = getattr(self, "_hdr_lbl", None)
        if lbl is not None and lbl.winfo_exists():
            self._hdr_icon = _to_photo(make_icon_image(px(40)))
            lbl.configure(image=self._hdr_icon)
        try:
            self._icon_big = _to_photo(make_icon_image(px(64)))
            self.root.iconphoto(True, self._icon_big)
            if self.icon:
                self.icon.icon = make_icon_image(64)
        except Exception:
            pass
        self.osd.configure(self.osd_size, self.osd_x, self.osd_y)
        self._apply_titlebar()

    def _recolor(self, w, cmap):
        """Faerbt den Widget-Baum um: eigene Widgets per restyle(), Rest per Farbabbildung."""
        restyle = getattr(w, "restyle", None)
        if callable(restyle) and isinstance(w, Restylable):
            try:
                restyle()
            except Exception:
                pass
        else:
            for opt in ("background", "foreground", "selectbackground",
                        "selectforeground", "highlightbackground"):
                try:
                    cur = str(w.cget(opt))
                except Exception:
                    continue
                if cur in cmap:
                    try:
                        w.configure(**{opt: cmap[cur]})
                    except Exception:
                        pass
        for child in w.winfo_children():
            self._recolor(child, cmap)

    def _set_osd_size(self, frac, final):
        self.osd_size = int(round(10 + max(0.0, min(1.0, frac)) * 90))
        self._osd_changed(self.size_lbl, self.osd_size, final)

    def _set_osd_x(self, frac, final):
        self.osd_x = int(round(max(0.0, min(1.0, frac)) * 100))
        self._osd_changed(self.posx_lbl, self.osd_x, final)

    def _set_osd_y(self, frac, final):
        self.osd_y = int(round(max(0.0, min(1.0, frac)) * 100))
        self._osd_changed(self.posy_lbl, self.osd_y, final)

    def _osd_changed(self, label, value, final):
        try:
            label.config(text="{} %".format(value))
        except Exception:
            pass
        self.osd.configure(self.osd_size, self.osd_x, self.osd_y)
        self._preview_osd()
        if final:
            self._save()

    def _on_vwheel(self, e):
        """Nur scrollen, wenn der Inhalt ueberhaupt hoeher ist als die Flaeche."""
        try:
            inner = getattr(self, "_inner_scroll", None)
            if inner is not None and inner.winfo_exists():
                box = inner.bbox("all")
                if box and (box[3] - box[1]) > inner.winfo_height():
                    inner.yview_scroll(int(-e.delta / 120), "units")
                    return
            c = self._scan
            box = c.bbox("all")
            if not box:
                return
            if (box[3] - box[1]) <= c.winfo_height():
                c.yview_moveto(0)
                self._update_scroll_hints()
                return
            c.yview_scroll(int(-e.delta / 120), "units")
            self._update_scroll_hints()
            self._settings_bar()
        except Exception:
            pass

    def _settings_bar(self):
        """Schmale Scrollleiste in den Einstellungen (eigenes Widget)."""
        c = getattr(self, "_scan", None)
        bar = getattr(self, "_set_bar", None)
        if (c is None or bar is None or self.view != "settings"
                or not c.winfo_exists() or not bar.winfo_exists()):
            return
        box = c.bbox("all")
        vh = c.winfo_height()
        if not box or vh < 20:
            return
        content = box[3] - box[1]
        if content <= vh + px(4):
            bar.place_forget()
            return
        top = c.canvasy(0)
        track = vh - px(14)
        bh = max(px(30), int(track * vh / float(content)))
        frac = max(0.0, min(1.0, top / float(content - vh)))
        y = px(7) + int((track - bh) * frac)
        w = px(5)
        bar.place(relx=1.0, x=-w - px(4), y=y, width=w, height=bh)
        bar.lift()

    def _sync_scrollregion(self, canvas):
        """Scrollbereich exakt auf den Inhalt setzen – sonst laesst sich ins Leere scrollen."""
        box = canvas.bbox("all")
        if not box:
            return
        height = box[3] - box[1]
        canvas.configure(scrollregion=(0, 0, box[2], height))
        if height <= canvas.winfo_height():
            canvas.yview_moveto(0)

    def _apply_titlebar(self, win=None):
        """Titelleiste in die App-Farbe einfaerben (nahtloser Uebergang).

        Windows 11 erlaubt ueber DWM eine eigene Titelleisten- und Rahmenfarbe –
        damit muss die Leiste nicht nachgebaut werden und Verschieben,
        Minimieren und Schliessen verhalten sich weiterhin wie gewohnt.
        """
        win = win or self.root
        win.update_idletasks()
        user32, dwmapi = ctypes.windll.user32, ctypes.windll.dwmapi
        try:
            parent = user32.GetParent(win.winfo_id())
        except Exception:
            parent = 0

        def colorref(hexcolor):
            r, g, b = _hex_rgb(hexcolor)
            return ctypes.c_int(b << 16 | g << 8 | r)     # DWM erwartet 0x00BBGGRR

        dark = ctypes.c_int(0 if IS_LIGHT else 1)
        caption = colorref(BG)
        text = colorref(FG)
        border = colorref(BG)
        for hwnd in (h for h in (parent, win.winfo_id()) if h):
            for attr in (20, 19):                     # heller/dunkler Modus
                try:
                    dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(dark),
                                                 ctypes.sizeof(dark))
                except Exception:
                    pass
            for attr, val in ((35, caption), (36, text), (34, border)):
                try:
                    dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val),
                                                 ctypes.sizeof(val))
                except Exception:
                    pass
            try:
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
            except Exception:
                pass

    # ---- Mixer-Aufbau ----------------------------------------------------
    def _rebuild_rows(self, items):
        """Merkt sich die Daten und legt die Karte neu aus."""
        for row in self.rows.values():
            row.destroy()
        self.rows.clear()
        self._mix_items = list(items)
        for it in items:
            self.rows[it["key"]] = MixerRow(
                self._scan, it, it["key"] in self.targets,
                on_toggle=self._on_row_toggle, on_volume=self._on_slider,
                on_mute=self._on_mute)
        self._layout_mixer()
        self._update_status_summary()
        self._fit_height()

    def _on_scan_configure(self, e):
        alt = getattr(self, "_scan_w", None)
        # Beim Verschieben auf einem anders skalierten Monitor wackelt die
        # Breite staendig um ein, zwei Pixel (Rundung bei der DPI-Umrechnung).
        # Wuerde jeder Wackler die Karte neu auslegen, ruckelt das Ziehen.
        if alt is None or abs(e.width - alt) >= px(4):
            self._scan_w = e.width
            if alt is None:
                self._layout_mixer()          # erster Aufbau: sofort
            else:
                self._layout_mixer_bald()     # Ziehen: sammeln
        else:
            # Nur die Hoehe hat sich geaendert (Maximieren, Rand ziehen). Ein
            # voller Neuaufbau wuerde flackern – es reicht, die Karte auf die
            # neue Hoehe zu strecken und den Scrollbereich nachzuziehen.
            self._stretch_mixer_bg()
            c = self._scan
            box = c.bbox("all")
            if box and (box[3] - box[1]) <= c.winfo_height():
                c.yview_moveto(0)
            self._update_scroll_hints()

    def _layout_mixer_bald(self, ms=90):
        """Neuaufbau kurz aufschieben und mehrere Meldungen zusammenfassen.

        Beim Ziehen der Fenstergroesse kommen Configure-Meldungen im
        Millisekundentakt. Einmal neu auslegen, wenn die Bewegung zur Ruhe
        kommt, reicht voellig – und bleibt fluessig.
        """
        job = getattr(self, "_layout_job", None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

        def jetzt():
            # Solange gezogen wird, weiter aufschieben: waehrend der Bewegung
            # neu auszulegen bringt nichts und ruckelt nur.
            if self._maus_gedrueckt():
                self._layout_job = self.root.after(120, jetzt)
                return
            self._layout_job = None
            self._layout_mixer()

        self._layout_job = self.root.after(ms, jetzt)

    def _stretch_mixer_bg(self):
        """Kartenverlauf auf die aktuelle Fensterhoehe bringen – ohne Neuaufbau.

        Sonst bliebe das dunkle Rechteck beim Maximieren auf seiner alten Hoehe
        stehen: darunter klafft eine Luecke und die unteren runden Ecken sitzen
        mitten im Fenster. Getauscht wird nur das Hintergrundbild; die Zeilen
        bekommen den passenden Ausschnitt des neuen Verlaufs.
        """
        c = getattr(self, "_scan", None)
        bid = getattr(self, "_mix_bg_id", None)
        if c is None or bid is None or not c.winfo_exists() or self.view != "mixer":
            return
        w, ch = c.winfo_width(), c.winfo_height()
        if w < 60 or ch < 40:
            return
        total_h = max(getattr(self, "_mix_content_h", 0), ch)
        if total_h == getattr(self, "_mix_bg_h", None):
            return
        bg = gradient_photo(w, total_h, px(M.get("card_radius", 16)),
                            card_top(), card_bottom())
        try:
            c.itemconfig(bid, image=bg)
        except Exception:
            return
        self._mix_bg_ref = bg          # Referenz halten, sonst raeumt Tk sie ab
        self._mix_bg_h = total_h
        for kind, data, yy, hh in getattr(self, "_mix_plan", []):
            if kind != "row":
                continue
            row = self.rows.get(data)
            if row is None:
                continue
            t1 = max(0.0, min(1.0, yy / float(total_h)))
            t2 = max(0.0, min(1.0, (yy + hh) / float(total_h)))
            row.set_backdrop(_mix(card_top(), card_bottom(), t1),
                             _mix(card_top(), card_bottom(), t2))

    def _layout_mixer(self):
        """Zeichnet Karte, Ueberschriften und Zeilen auf ein einziges Canvas.

        Die Zeilen bekommen den zu ihrer Position passenden Ausschnitt des
        Kartenverlaufs als Untergrund – dadurch wirkt die Flaeche durchgehend,
        obwohl es einzelne Widgets sind.
        """
        c = getattr(self, "_scan", None)
        if c is None or not c.winfo_exists() or self.view != "mixer":
            return
        w = c.winfo_width()
        if w < 60:
            return
        items = getattr(self, "_mix_items", [])
        pad = px(14)
        rad = px(M.get("card_radius", 16))

        # --- Hoehen planen ---
        y = px(16)
        head_y = y
        y += px(26)
        plan = []                       # (art, daten, y, hoehe)
        master = [it for it in items if it["key"] == MASTER_KEY]
        apps = [it for it in items if it["key"] != MASTER_KEY]
        for title, group in (("ALLES", master), ("EINZELNE APPS", apps)):
            if not group:
                continue
            y += px(14)
            plan.append(("sec", title, y, px(16)))
            y += px(22)
            for it in group:
                row = self.rows.get(it["key"])
                h = row.h if row else px(54)
                plan.append(("row", it["key"], y, h))
                y += h + px(4)
        if not items:
            plan.append(("empty", "Keine Audio-Apps aktiv.", y, px(24)))
            y += px(30)
        content_h = y + px(14)
        # Der Verlauf deckt immer den ganzen Inhalt ab. Er haengt bewusst NICHT
        # an der Fensterhoehe – sonst muesste beim Ziehen alles neu gezeichnet
        # werden (und wuerde flackern).
        total_h = max(content_h, c.winfo_height())

        # --- zeichnen ---
        c.delete("all")
        self._scan_refs = []
        c.configure(bg=BG)
        bg = gradient_photo(w, total_h, rad, card_top(), card_bottom())
        self._mix_bg_ref = bg
        self._mix_bg_id = c.create_image(0, 0, anchor="nw", image=bg)
        self._mix_bg_h = total_h

        def col_at(yy):
            t = max(0.0, min(1.0, yy / float(max(1, total_h))))
            return _mix(card_top(), card_bottom(), t)

        # Kopfzeile
        c.create_text(pad, head_y, anchor="nw", text="LAUTSTÄRKE-MIXER",
                      fill=MUTED, font=uifont(10, semi=True))

        for kind, data, yy, hh in plan:
            if kind == "sec":
                c.create_text(pad, yy, anchor="nw", text=data,
                              fill=MUTED, font=uifont(10, semi=True))
                tw = tkfont.Font(family=FONT_SEMI, size=-px(10 * FONT_SCALE)).measure(data)
                lx = pad + tw + px(12)
                ly = yy + px(8)
                if w - pad > lx:
                    c.create_line(lx, ly, w - pad, ly, fill=STROKE)
            elif kind == "row":
                row = self.rows.get(data)
                if row is None:
                    continue
                row.set_backdrop(col_at(yy), col_at(yy + hh))
                self._row_wins.append(
                    c.create_window(px(6), yy, anchor="nw", window=row,
                                    width=w - px(12), height=hh))
            else:
                c.create_text(pad, yy, anchor="nw", text=data,
                              fill=MUTED, font=uifont(11))

        self._mix_content_h = content_h
        self._mix_plan = plan          # fuer _stretch_mixer_bg
        c.configure(scrollregion=(0, 0, w, content_h))
        if content_h <= c.winfo_height():
            c.yview_moveto(0)
        self._make_scroll_hints(c, w, content_h)
        self._fit_height()
        # nach dem Layout steht die endgueltige Hoehe erst fest
        self.root.after(60, self._update_scroll_hints)

    def _make_scroll_hints(self, c, w, content_h):
        """Scrollleiste anlegen. Die Abblendung zeichnet die Zeile selbst
        (siehe MixerRow.set_fade) – nur dort ist echte Transparenz moeglich."""
        # Als Widget, weil Canvas-Zeichnungen unter den eingebetteten Zeilen
        # liegen und damit unsichtbar waeren.
        self._bar_w = px(5)
        if getattr(self, "_bar_w_widget", None) is None or \
                not self._bar_w_widget.winfo_exists():
            self._bar_w_widget = tk.Frame(c, bd=0, highlightthickness=0)
        self._bar_w_widget.configure(bg=_mix(CARD2, FG, 0.30))
        self._update_scroll_hints()

    def _update_scroll_hints(self):
        """Blende und Leiste an die aktuelle Scrollstellung setzen."""
        c = getattr(self, "_scan", None)
        if c is None or not c.winfo_exists() or self.view != "mixer":
            return
        vh = c.winfo_height()
        content = self._mix_content_h
        try:
            top = c.canvasy(0)
        except Exception:
            return
        more = content - (top + vh)
        # Abblendung: die am unteren Rand angeschnittene Zeile blendet selbst
        # aus – so entsteht kein harter Uebergang.
        bottom = top + vh
        fade_h = px(40)
        for row in self.rows.values():
            if not row.winfo_exists():
                continue
            ry = row.winfo_y()
            if more > px(6) and ry < bottom < ry + row.h + px(2):
                row.set_fade(max(0, bottom - ry - fade_h))
            else:
                row.set_fade(None)

        bar = getattr(self, "_bar_w_widget", None)
        if bar is not None and bar.winfo_exists():
            if content > vh + px(4):
                track = vh - px(14)
                bh = max(px(30), int(track * vh / float(content)))
                frac = max(0.0, min(1.0, top / float(content - vh)))
                y = px(7) + int((track - bh) * frac)
                bar.place(relx=1.0, x=-self._bar_w - px(3), y=y,
                          width=self._bar_w, height=bh)
                bar.lift()
            else:
                bar.place_forget()

    def _fit_height(self):
        """Grenzen setzen und die Hoehe nur nachfuehren, wenn noetig.

        Die Hoehe darf der Nutzer selbst ziehen; sinnvoll ist hoechstens so
        viel, wie die Liste braucht.
        """
        if self.view != "mixer":
            return
        try:
            base = px(M.get("window_chrome", 150))    # Kopf + Statusleiste
            want = base + self._mix_content_h
            hard_max = self.root.winfo_screenheight() - px(80)
            hmax = max(px(340), min(hard_max, want))
            # nicht kleiner, sonst wird die Statusleiste unten verdraengt
            self.root.minsize(px(BASE_W), px(340))
            self.root.maxsize(px(BASE_W), hmax)
            cur = self.root.winfo_height()
            # nur verkleinern, wenn das Fenster mehr Platz hat als noetig,
            # und beim ersten Aufbau auf die passende Hoehe setzen
            if cur > hmax + px(4) or not getattr(self, "_sized", False):
                self._sized = True
                self.root.geometry("{}x{}".format(px(BASE_W), hmax))
        except Exception:
            pass

    def _update_rows(self, items):
        for it in items:
            self._meta[it["key"]] = (it["label"], it.get("exe"))
        if self.view != "mixer":
            return          # Mixer-Zeilen existieren nur in der Mixer-Ansicht
        keys = [it["key"] for it in items]
        if set(keys) != set(self.rows.keys()):
            self._rebuild_rows(items)
            return
        for it in items:
            row = self.rows.get(it["key"])
            if row is None:
                continue
            row.update_item(it)
            row.set_selected(it["key"] in self.targets)
            if self._dragging_key != it["key"]:
                row.set_volume(it["volume"])
        self._update_status_summary()

    def _note_known(self, items):
        """Merkt sich alle je gesehenen Apps – inklusive Pfad zum Symbol.

        Der Pfad wird mitgespeichert, damit die Leiste auch fuer gerade nicht
        laufende Apps das richtige Symbol zeigt statt einer Buchstabenkachel.
        """
        new = False
        for it in items:
            k = it["key"]
            if k == MASTER_KEY:
                continue
            if k not in self.known:
                self.known[k] = it["label"]
                new = True
            exe = it.get("exe")
            if exe and self.exes.get(k) != exe:
                self.exes[k] = exe
                new = True

        # `known` ist reines Gedaechtnis fuer die Haken und waechst ewig weiter.
        # Angezeigt wird dagegen nur, was gerade wirklich laeuft (`_live`) –
        # sonst stehen im Dialog Programme, die man vor Wochen mal offen hatte.
        live = {it["key"] for it in items if it["key"] != MASTER_KEY}
        geaendert = live != getattr(self, "_live", None)
        self._live = live
        if new:
            self._save()
        if new or geaendert:
            self._paint_status()
        # Steht der Auswahl-Dialog offen, Liste mitwachsen/schrumpfen lassen
        if (getattr(self, "_dim", None) is not None
                and live != getattr(self, "_apps_listed", None)):
            self._fill_apps_list()

    def _exe_of(self, key):
        """Pfad zur Programmdatei – erst aus den laufenden, dann aus dem Speicher."""
        meta = self._meta.get(key)
        if meta and meta[1]:
            return meta[1]
        return self.exes.get(key)

    def _on_hidden_toggle(self, key, visible):
        if visible:
            self.hidden.discard(key)
        else:
            self.hidden.add(key)
        self._save()
        self.job_queue.put(("refresh",))

    def _on_row_toggle(self, key, val):
        """„Gesamtlautstärke“ und einzelne Apps schliessen sich gegenseitig aus.

        Sonst wuerde man doppelt daempfen: erst die App, dann nochmal global.
        Was dabei mit den Pegeln passiert, legt `switch_mode` fest – ab Werk
        gar nichts (siehe `_switch_levels`).
        """
        if val:
            if key == MASTER_KEY:
                from_apps = [k for k in self.targets if k != MASTER_KEY]
                self.targets = {MASTER_KEY}
                if from_apps:
                    self.job_queue.put(("switch", "master", from_apps))
            else:
                from_master = MASTER_KEY in self.targets
                self.targets.discard(MASTER_KEY)
                self.targets.add(key)
                if from_master:
                    self.job_queue.put(("switch", "apps", [key]))
        else:
            self.targets.discard(key)
        self._save()
        # Zeilen direkt aktualisieren statt die Liste neu zu bauen
        for k, row in self.rows.items():
            row.set_selected(k in self.targets)
        self.job_queue.put(("refresh",))
        self._update_status_summary()

    def _reset_apps(self):
        """Alle App-Lautstaerken auf 100 % (die Windows-Gesamtlautstaerke bleibt)."""
        self.job_queue.put(("resetapps",))
        self._flash("Alle App-Lautstärken auf 100 % gesetzt")

    def _on_slider(self, key, value, final):
        self._dragging_key = None if final else key
        self.job_queue.put(("setvol", key, value))

    def _on_mute(self, key, on):
        """Klick auf das App-Symbol schaltet stumm."""
        row = self.rows.get(key)
        if row is not None:
            row.set_muted(on)          # sofort sichtbar, ohne auf den Worker zu warten
        self.job_queue.put(("mute", key, on))
        self._flash("{} {}".format(self._label_of(key),
                                   "stummgeschaltet" if on else "wieder hörbar"))

    def _paint_status(self, e=None):
        """Untere Leiste: Symbole aller bekannten Apps, direkt umschaltbar.

        Ersetzt den frueheren Dialog – die Sichtbarkeit laesst sich damit
        direkt dort aendern, wo man die Apps ohnehin sieht.
        """
        bar = getattr(self, "_status_bar", None)
        if bar is None or not bar.winfo_exists():
            return
        w, h = bar.winfo_width(), bar.winfo_height()
        if w < 20 or h < 10:
            return
        bar.delete("all")
        self._status_refs = []
        self._status_hits = []
        bar.configure(bg=BG)
        bg = gradient_photo(w, h, px(M.get("row_radius", 12)), card_top(), card_bottom())
        self._status_refs.append(bg)
        bar.create_image(0, 0, anchor="nw", image=bg)

        msg = getattr(self, "_flash_msg", None)
        if msg:
            bar.create_text(px(14), h // 2, anchor="w", text=msg,
                            fill=MUTED, font=uifont(11))
            return

        # Links nur ein kurzer Hinweis – die Symbole stehen ohnehin im Mixer
        # und in der Auswahlliste.
        cy = h // 2
        live = getattr(self, "_live", None) or set()
        visible = [k for k in live if k not in self.hidden]
        txt = ("Keine App aktiv" if not live else
               "{} von {} Apps sichtbar".format(len(visible), len(live)))
        bar.create_text(px(14), cy, anchor="w", text=txt,
                        fill=FG, font=uifont(12))

        # Knopf rechts – mit Hover, damit er als Knopf erkennbar ist
        bw, bh = px(96), px(28)
        bx = w - px(12) - bw
        by = cy - bh // 2
        btn = rounded_photo(bw, bh, px(8), _mix(card_bottom(), FG, 0.10))
        btn_hover = rounded_photo(bw, bh, px(8), _mix(card_bottom(), FG, 0.22))
        self._status_refs += [btn, btn_hover]
        b1 = bar.create_image(bx, by, anchor="nw", image=btn)
        b2 = bar.create_text(bx + bw // 2, cy, text="Apps wählen",
                             fill=FG, font=uifont(10, semi=True))

        def betreten(e=None):
            bar.itemconfig(b1, image=btn_hover)
            bar.configure(cursor="hand2")

        def verlassen(e=None):
            bar.itemconfig(b1, image=btn)
            bar.configure(cursor="")

        for item in (b1, b2):
            bar.tag_bind(item, "<Button-1>", lambda e: self._open_apps_dialog())
            bar.tag_bind(item, "<Enter>", betreten)
            bar.tag_bind(item, "<Leave>", verlassen)
        bar.configure(cursor="")

    def _open_apps_dialog(self):
        """Liste aller Apps zum An- und Abhaken, ueber unscharfem Hintergrund."""
        if getattr(self, "_dim", None) is not None:
            return
        self._pending_hidden = set(self.hidden)

        # Ruhige Abdunklung statt Bildschirmaufnahme: Eine Aufnahme muesste auf
        # Bildschirmkoordinaten umgerechnet werden und sass bei hoher
        # Skalierung verschoben.
        dim = tk.Frame(self.root, bg=_mix(BG, "#000000", 0.45))
        dim.place(x=0, y=0, relwidth=1, relheight=1)
        dim.bind("<Button-1>", lambda e: "break")
        dim.bind("<MouseWheel>", lambda e: "break")
        self._dim = dim

        # Das Panel muss IMMER ins Fenster passen – ein festes Mindestmass war
        # bei kleinem Fenster groesser als der Platz, dann ragte es oben und
        # unten heraus. Deshalb zuerst decken, dann erst ein Minimum.
        verfuegbar = max(px(150), self.root.winfo_height() - px(28))
        ph = min(px(440), verfuegbar)
        # `list_h` ist nur der Startwert: die Liste wird mit expand=True gepackt
        # und bekommt den Platz, der nach Kopf und Knoepfen uebrig bleibt.
        list_h = max(px(70), ph - px(140))
        # bg_outer muss die Farbe HINTER der Karte sein – sonst schimmern an
        # den runden Ecken helle Zipfel durch.
        panel = Card(dim, bg_outer=_mix(BG, "#000000", 0.45))
        panel.place(relx=0.5, rely=0.5, anchor="center",
                    width=px(BASE_W) - px(64), height=ph)
        inner = tk.Frame(panel.inner, bg=CARD)
        inner.pack(fill="both", expand=True, padx=px(16), pady=px(14))

        kopf = tk.Frame(inner, bg=CARD)
        kopf.pack(fill="x", pady=(0, px(10)))
        tk.Label(kopf, text="Sichtbare Apps", bg=CARD, fg=FG,
                 font=uifont(15, semi=True)).pack(side="left")

        # Erklaerung steckt hinter dem Fragezeichen, statt dauerhaft Platz
        # wegzunehmen – gebraucht wird sie ja nur einmal.
        hilfe = tk.Label(kopf, image=help_photo(px(18), MUTED), bg=CARD,
                         cursor="hand2")
        hilfe.image = help_photo(px(18), MUTED)
        hilfe.pack(side="right")
        erklaerung = ("Gelistet sind Apps, die gerade Ton ausgeben können.\n"
                      "Nur angehakte erscheinen im Mixer.\n"
                      "Deine Auswahl bleibt gespeichert – auch wenn du\n"
                      "eine App schließt und später neu startest.")
        hilfe.bind("<Enter>", lambda e: self._show_tip(hilfe, erklaerung))
        hilfe.bind("<Leave>", lambda e: self._hide_tip())

        # Knoepfe ZUERST am Boden verankern, die Liste nimmt danach den Rest.
        # Andersherum schoebe sie sich bei laengerem Text darueber.
        btns = tk.Frame(inner, bg=CARD)
        btns.pack(side="bottom", fill="x", pady=(px(10), 0))
        RoundButton(btns, "Anwenden", self._apply_apps_dialog, bg=CARD,
                    fill=ACCENT, fill_hover=ACCENT_HOVER, fg="#FFFFFF",
                    h=px(32), r=px(9), padx=px(16), fontpx=11).pack(side="right")
        RoundButton(btns, "Abbrechen", self._close_apps_dialog, bg=CARD,
                    fill=CARD2, fill_hover=STROKE, fg=FG,
                    h=px(32), r=px(9), padx=px(16), fontpx=11).pack(side="right",
                                                                     padx=(0, px(8)))

        self._apps_host = self._sub_scroll(inner, height=list_h, expand=True)
        self._fill_apps_list()

    def _show_tip(self, anker, text):
        """Erklaerblase neben `anker` einblenden.

        Bewusst ein Widget im Dialog statt eines eigenen Fensters: ein Toplevel
        wuerde beim Erscheinen kurz den Fokus ziehen und in der Taskleiste
        blinken. Gezeichnet wird auf ein Canvas, weil Tk-Widgets keine runden
        Ecken koennen.
        """
        self._hide_tip()
        # Im Dialog gehoert die Blase in die Abdunklung, sonst laege sie
        # darunter. Ausserhalb reicht das Hauptfenster als Elternteil.
        eltern = getattr(self, "_dim", None)
        if eltern is None or not eltern.winfo_exists():
            eltern = self.root
        if not eltern.winfo_exists():
            return
        f = tkfont.Font(family=FONT, size=-px(11))
        zeilen = text.split("\n")
        tw = max(f.measure(z) for z in zeilen)
        pad = px(10)
        w = tw + 2 * pad
        h = len(zeilen) * f.metrics("linespace") + 2 * pad

        tip = tk.Canvas(eltern, width=w, height=h, highlightthickness=0, bd=0,
                        bg=CARD)
        bg = rounded_photo(w, h, px(8), _mix(CARD2, FG, 0.12))
        tip._bg = bg                      # Referenz halten
        tip.create_image(0, 0, anchor="nw", image=bg)
        tip.create_text(pad, pad, anchor="nw", text=text, fill=FG, font=f,
                        justify="left")

        # Beginnt unter dem Fragezeichen und rutscht nur so weit nach links,
        # wie noetig ist, um im Fenster zu bleiben.
        ax = anker.winfo_rootx() - eltern.winfo_rootx()
        ay = anker.winfo_rooty() - eltern.winfo_rooty()
        x = max(px(8), min(ax, eltern.winfo_width() - w - px(8)))
        y = ay + anker.winfo_height() + px(6)
        # Kein Platz mehr nach unten? Dann oberhalb einblenden.
        if y + h > eltern.winfo_height() - px(8):
            y = max(px(8), ay - h - px(6))
        tip.place(x=x, y=y)
        self._tip = tip

    def _hide_tip(self):
        tip = getattr(self, "_tip", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
        self._tip = None

    def _fill_apps_list(self):
        """Baut die Zeilen der Sichtbarkeits-Liste auf.

        Gelistet wird nur, was gerade eine Audiositzung hat. Die Haken selbst
        merkt sich `hidden` dauerhaft – schliesst du eine App und startest sie
        Wochen spaeter neu, ist sie wieder so eingestellt wie zuletzt.

        Eigene Methode, damit die Liste mitwachsen und schrumpfen kann, waehrend
        der Dialog offen steht. Vorgemerkte Haken (`_pending_hidden`) ueberleben
        das, weil sie nicht an den Widgets haengen.
        """
        host = getattr(self, "_apps_host", None)
        if host is None or not host.winfo_exists():
            return
        # Scrollposition merken: sonst springt die Liste unter dem Zeiger weg,
        # waehrend man gerade Haken setzt.
        can = host.master
        try:
            pos = can.yview()[0]
        except Exception:
            can, pos = None, 0.0
        for w in host.winfo_children():
            w.destroy()
        wheel = self._sub_wheel
        live = getattr(self, "_live", None) or set()
        if not live:
            tk.Label(host, text="Gerade gibt keine App Ton aus.", bg=CARD2,
                     fg=MUTED, font=uifont(12), anchor="w").pack(anchor="w",
                                                                 pady=px(8))
        an_farbe = _mix(CARD2, FG, 0.07)      # Zeile unter dem Zeiger
        for key in sorted(live, key=lambda k: self._label_of(k).lower()):
            label = self.known.get(key) or self._label_of(key)
            row = tk.Frame(host, bg=CARD2)
            row.pack(fill="x", pady=px(1), ipady=px(4))
            box = CheckBox(row, value=(key not in self._pending_hidden), bg=CARD2,
                           command=lambda v, k=key: self._pending_visible(k, v))
            box.pack(side="left", padx=(px(6), 0))
            ic = app_icon_photo(px(24), key, label, self._exe_of(key))
            il = tk.Label(row, image=ic, bg=CARD2)
            il.image = ic
            il.pack(side="left", padx=(px(11), px(9)))
            nm = tk.Label(row, text=label, bg=CARD2, fg=FG, font=uifont(12),
                          anchor="w")
            nm.pack(side="left")

            # Die ganze Zeile schaltet um, nicht nur das Kaestchen – wie im
            # Mixer. Das Kaestchen behaelt seine eigene Bindung, sonst wuerde
            # ein Klick darauf zweimal umschalten.
            teile = (row, il, nm)

            def faerben(farbe, ws=teile, b=box):
                for w in ws:
                    w.configure(bg=farbe)
                b.configure(bg=farbe)

            def klick(_e=None, b=box):
                b._toggle()

            for w in teile:
                w.bind("<MouseWheel>", wheel)
                w.bind("<Button-1>", klick)
                w.bind("<Enter>", lambda e, f=faerben: f(an_farbe))
                w.bind("<Leave>", lambda e, f=faerben: f(CARD2))
                w.configure(cursor="hand2")
        self._apps_listed = set(live)
        if can is not None:
            host.update_idletasks()          # neue Hoehe muss erst feststehen
            try:
                can.yview_moveto(pos)
            except Exception:
                pass

    def _pending_visible(self, key, visible):
        """Aenderung nur vormerken – erst „Anwenden“ uebernimmt sie."""
        if visible:
            self._pending_hidden.discard(key)
        else:
            self._pending_hidden.add(key)

    def _apply_apps_dialog(self):
        self.hidden = set(getattr(self, "_pending_hidden", self.hidden))
        # Ausgeblendete Apps koennen nicht laenger Ziel des Daumenrads sein –
        # sonst steuert man weiter etwas, das im Mixer gar nicht mehr auftaucht.
        self.targets -= self.hidden
        self._save()
        self.job_queue.put(("refresh",))
        self._close_apps_dialog()

    def _close_apps_dialog(self):
        self._hide_tip()
        dim = getattr(self, "_dim", None)
        if dim is not None:
            try:
                dim.destroy()
            except Exception:
                pass
        self._dim = None
        self._inner_scroll = None
        self._paint_status()

    def _flash(self, text, ms=1600):
        """Kurze Meldung in der unteren Leiste, danach wieder die Symbole."""
        self._flash_msg = text
        self._paint_status()
        job = getattr(self, "_flash_job", None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

        def back():
            self._flash_msg = None
            self._paint_status()
        self._flash_job = self.root.after(ms, back)

    def _update_status_summary(self):
        # Die untere Leiste zeigt jetzt die App-Symbole; welche Apps gesteuert
        # werden, sieht man an den Haekchen im Mixer.
        return

    def _unused_status_summary(self):
        """Statusleiste: Symbole der gesteuerten Apps + Klartext."""
        if not self.targets:
            self.status_var.set("Kein Ziel gewählt – Zeile anklicken")
        else:
            names = [self._label_of(k) for k in sorted(self.targets)]
            self.status_var.set("Daumenrad steuert " + ", ".join(names))
        self._paint_status()

    def _label_of(self, key):
        if key == MASTER_KEY:
            return "Gesamtlautstärke"
        if key == SYSTEM_KEY:
            return "Systemklänge"
        known = getattr(self, "_meta", {}).get(key)
        if known:
            return known[0]
        return _pretty_name(key)

    def _set_speed(self, frac, final):
        # auf 10er-Schritte einrasten
        self.speed = int(round((10 + max(0.0, min(1.0, frac)) * 90) / 10.0) * 10)
        try:
            self.speed_lbl.config(text="{} %".format(self.speed))
        except Exception:
            pass
        if final:
            self._save()

    def _on_active(self, val):
        self.active = bool(val)
        self._save()
        if self.icon:
            self.icon.update_menu()

    def _on_input_mode(self, use_scroll):
        """An = Daumenrad (horizontales Scrollen), Aus = Lautstaerke-Tasten."""
        self.use_media_keys = not bool(use_scroll)
        self.suppress = bool(use_scroll)      # Scrollen nur im Daumenrad-Modus schlucken
        self._save()
        if self.use_media_keys:
            self._flash("Lautstärke-Tasten aktiv – Daumenrad in Logi Options+ "
                        "auf „Lautstärke“ legen", ms=4500)
        else:
            self._flash("Daumenrad (horizontales Scrollen) aktiv")

    def _on_switch_mode(self, mode):
        """Was passiert, wenn die Steuerung zwischen Gesamt und Apps wechselt."""
        self.switch_mode = mode
        self._save()

    def _on_suppress(self, val):
        self.suppress = bool(val)
        self._save()

    def _on_reverse(self, val):
        self.reverse = bool(val)
        self._save()

    def _on_autostart(self, val):
        try:
            set_autostart(bool(val))
        except Exception as e:
            self.status_var.set("Autostart-Fehler: {}".format(e))

    # ---- Einblendung (OSD) ----------------------------------------------
    def _on_osd_enabled(self, val):
        self.osd_enabled = bool(val)
        self._save()
        if self.osd_enabled:
            self._preview_osd()
        else:
            self.osd.hide()

    def _preview_osd(self):
        """Zeigt die Einblendung mit den aktuellen Einstellungen als Vorschau."""
        items = self._osd_items(sorted(self.targets)) if self.targets else []
        if not items:
            items = [(MASTER_KEY, "Gesamtlautstärke", None)]
        self.osd.show(items, 65, hold=1600)

    def _osd_items(self, keys):
        out = []
        for k in keys:
            label, exe = self._meta.get(k, (self._label_of(k), None))
            out.append((k, label, exe))
        return out

    def _save(self):
        self.cfg.update({
            "targets": sorted(self.targets),
            "speed": self.speed,
            "reverse": self.reverse,
            "suppress": self.suppress,
            "active": self.active,
            "osd_size": self.osd_size,
            "osd_x": self.osd_x,
            "osd_y": self.osd_y,
            "osd_enabled": self.osd_enabled,
            "media_keys": self.use_media_keys,
            "switch_mode": self.switch_mode,
            "skin": SKIN_NAME,
            "color": CUSTOM_COLOR,
            "mode": MODE,
            "hidden": sorted(self.hidden),
            "known": sorted(self.known.keys()),
            "exes": self.exes,
        })
        save_config(self.cfg)

    # ---- Tray ------------------------------------------------------------
    def _start_tray(self):
        def on_open(icon, item):
            self.ui_queue.put(("show",))

        def on_toggle(icon, item):
            self.ui_queue.put(("toggle_active",))

        def on_quit(icon, item):
            self.ui_queue.put(("quit",))

        menu = pystray.Menu(
            pystray.MenuItem("Öffnen", on_open, default=True),
            pystray.MenuItem("Steuerung aktiv", on_toggle, checked=lambda item: self.active),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", on_quit),
        )
        self.icon = pystray.Icon("volumix", make_icon_image(64),
                                 "Volumix", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _hide_to_tray(self):
        self.root.withdraw()

    def _start_show_waiter(self):
        def loop():
            while not self._stop:
                if _k32.WaitForSingleObject(_show_event, 500) == 0:
                    self.ui_queue.put(("show",))
        threading.Thread(target=loop, daemon=True).start()

    # ---- Maus-Hook -------------------------------------------------------
    def _start_hook(self):
        """Maus-Hook fuer das Daumenrad (horizontales Scrollen)."""
        def win32_event_filter(msg, data):
            # Laeuft im System-Hook: so frueh wie moeglich aussteigen, damit
            # die Maus im ganzen System fluessig bleibt.
            if msg != WM_MOUSEHWHEEL:
                return True
            if not (self.active and self.targets):
                return True
            raw = wintypes.SHORT(data.mouseData >> 16).value
            self.job_queue.put(("scroll", raw))
            if self.suppress:
                self.listener.suppress_event()
            return True

        self.listener = mouse.Listener(win32_event_filter=win32_event_filter)
        self.listener.start()
        self._start_key_hook()

    def _start_key_hook(self):
        """Alternative Eingabe: die Lautstaerke-Tasten.

        Ein Tastatur-Hook feuert nur bei Tastendruecken – der Maus-Hook dagegen
        bei jeder Bewegung. Wer das Daumenrad in Logi Options+ auf „Lautstärke"
        legt, bekommt dadurch eine spuerbar schonendere Steuerung.
        """
        VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF
        WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104

        def key_filter(msg, data):
            # Die Aktion MUSS hier passieren: suppress_event() bricht die
            # weitere Verarbeitung ab, ein on_press-Handler kaeme nie dran.
            vk = data.vkCode
            if vk not in (VK_VOLUME_UP, VK_VOLUME_DOWN, VK_VOLUME_MUTE):
                return True
            if not (self.use_media_keys and self.active and self.targets):
                return True
            if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
                if vk == VK_VOLUME_UP:
                    self.job_queue.put(("scroll", -WHEEL_DELTA))
                elif vk == VK_VOLUME_DOWN:
                    self.job_queue.put(("scroll", WHEEL_DELTA))
                else:
                    for k in list(self.targets):
                        self.job_queue.put(("mute", k, not self._get_mute(k)))
            self.klistener.suppress_event()   # Windows-Regler nicht doppelt
            return True

        try:
            self.klistener = keyboard.Listener(win32_event_filter=key_filter,
                                               suppress=False)
            self.klistener.start()
        except Exception:
            self.klistener = None

    # ---- Worker ----------------------------------------------------------
    def _start_worker(self):
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self):
        CoInitialize()
        try:
            while True:
                # Laeuft gerade eine Lautstaerke-Fahrt? Dann nur kurz warten,
                # damit die 1-Prozent-Schritte gleichmaessig weiterlaufen.
                if self._vol_anim:
                    try:
                        job = self.job_queue.get(timeout=0.007)
                    except queue.Empty:
                        self._animate_volumes()
                        continue
                else:
                    job = self.job_queue.get()
                jobs = [job]
                while True:
                    try:
                        jobs.append(self.job_queue.get_nowait())
                    except queue.Empty:
                        break
                scroll_delta = 0
                do_refresh = False
                do_quit = False
                do_reset = False
                switch = None
                setvols = {}
                mutes = {}
                for j in jobs:
                    k = j[0]
                    if k == "scroll":
                        scroll_delta += j[1]
                    elif k == "refresh":
                        do_refresh = True
                    elif k == "setvol":
                        setvols[j[1]] = j[2]
                    elif k == "mute":
                        mutes[j[1]] = j[2]
                    elif k == "resetapps":
                        do_reset = True
                    elif k == "switch":
                        switch = (j[1], j[2])
                    elif k == "quit":
                        do_quit = True
                if do_quit:
                    break
                if do_reset:
                    self._reset_app_volumes()
                    do_refresh = True
                if switch is not None:
                    self._switch_levels(*switch)
                    do_refresh = True
                if mutes:
                    for key, on in mutes.items():
                        self._set_mute(key, on)
                    # sofort neu einlesen, sonst ueberschreibt ein noch
                    # laufender Durchlauf die Anzeige mit dem alten Zustand
                    do_refresh = True
                for key, val in setvols.items():
                    # Regler von Hand bewegt -> laufende Fahrt verwerfen
                    self._vol_anim.pop(key, None)
                    self._vol_now[key] = val * 100.0
                    self._set_volume(key, val)
                if do_refresh:
                    self._do_refresh()
                if scroll_delta != 0:
                    self._apply_scroll(scroll_delta)
                if self._vol_anim:
                    self._animate_volumes()
        finally:
            CoUninitialize()

    def _animate_volumes(self):
        """Faehrt die Lautstaerke in 1-Prozent-Schritten an das Ziel heran.

        Dadurch bleibt die Anzeige fluessig, auch wenn eine Rastung mehrere
        Prozentpunkte umfasst.
        """
        done = []
        for key, target in list(self._vol_anim.items()):
            cur = self._vol_now.get(key)
            if cur is None:
                done.append(key)
                continue
            diff = target - cur
            if abs(diff) <= 1:
                new = target
                done.append(key)
            else:
                # Feste Schrittweite aus der Anfangsdistanz -> gleichmaessige
                # Fahrt in immer etwa gleicher Zeit (rund 40 ms)
                step = self._vol_step.get(key, 1)
                new = cur + (step if diff > 0 else -step)
                if (diff > 0 and new > target) or (diff < 0 and new < target):
                    new = target
                    done.append(key)
            self._vol_now[key] = new
            self._set_volume(key, new / 100.0)
            self.ui_queue.put(("vol", key, int(round(new))))
        for key in done:
            self._vol_anim.pop(key, None)
            self._vol_step.pop(key, None)
        self._show_osd_for_targets()      # Einblendung faehrt mit

    def _do_refresh(self):
        self._check_device()
        seen = {}
        order = []
        try:
            sessions = AudioUtilities.GetAllSessions()
        except Exception:
            sessions = []
        for s in sessions:
            try:
                sav = s.SimpleAudioVolume
            except Exception:
                sav = None
            if sav is None:
                continue
            exe = None
            if s.Process is None:
                key, label = SYSTEM_KEY, "Systemklänge"
            else:
                try:
                    pname = s.Process.name()
                except Exception:
                    continue
                key = pname.lower()
                label = _pretty_name(pname)
                try:
                    exe = s.Process.exe()
                except Exception:
                    exe = None
            if key in seen:
                continue
            try:
                vol = float(sav.GetMasterVolume())
            except Exception:
                vol = 1.0
            try:
                muted = bool(sav.GetMute())
            except Exception:
                muted = False
            seen[key] = True
            order.append({"key": key, "label": label, "volume": vol,
                          "exe": exe, "muted": muted})
        order.sort(key=lambda it: it["label"].lower())
        mv = self._read_master()
        master = {"key": MASTER_KEY, "label": "Gesamtlautstärke",
                  "volume": mv if mv is not None else 1.0, "exe": None,
                  "muted": self._get_mute(MASTER_KEY)}
        visible = [it for it in order if it["key"] not in self.hidden]
        self.ui_queue.put(("apps", [master] + visible, order))

    def _sessions_by_key(self, keys, max_age=2.0):
        """Audio-Sitzungen zu den Schluesseln – kurz gecacht.

        `GetAllSessions()` fragt ueber COM alle Sitzungen des Systems ab und
        kostet zweistellige Millisekunden. Ohne Cache liefe das bei jedem
        Rastungs- und Animationsschritt erneut – das Scrollen wirkt dann traege.
        """
        now = time.time()
        cache = getattr(self, "_sess_cache", None)
        if (cache and now - cache[0] < max_age
                and set(keys).issubset(cache[1])):
            return cache[2]
        keyset = set(keys)
        out = {}
        try:
            sessions = AudioUtilities.GetAllSessions()
        except Exception:
            sessions = []
        for s in sessions:
            try:
                sav = s.SimpleAudioVolume
            except Exception:
                sav = None
            if sav is None:
                continue
            if s.Process is None:
                key = SYSTEM_KEY
            else:
                try:
                    key = s.Process.name().lower()
                except Exception:
                    continue
            if key in keyset:
                out.setdefault(key, []).append(sav)
        self._sess_cache = (now, keyset, out)
        return out

    def _drop_session_cache(self):
        self._sess_cache = None

    def _check_device(self):
        """Erkennt einen Wechsel des Ausgabegeraets (z. B. Kopfhoerer einstecken).

        Der Verweis auf die Gesamtlautstaerke und die Sitzungsliste gehoeren zu
        einem bestimmten Geraet – nach einem Wechsel wuerden sie ins Leere zeigen.
        """
        try:
            dev_id = AudioUtilities.GetSpeakers().id      # nicht GetId()
        except Exception:
            return
        if not dev_id:
            return
        if dev_id != getattr(self, "_dev_id", None):
            self._dev_id = dev_id
            self._epv = None
            self._drop_session_cache()
            self._vol_now.clear()
            self._vol_anim.clear()

    def _endpoint(self):
        if self._epv is None:
            self._epv = AudioUtilities.GetSpeakers().EndpointVolume
        return self._epv

    def _read_master(self):
        try:
            return float(self._endpoint().GetMasterVolumeLevelScalar())
        except Exception:
            self._epv = None
            return None

    def _write_master(self, val):
        try:
            self._endpoint().SetMasterVolumeLevelScalar(float(val), None)
        except Exception:
            self._epv = None

    def _get_mute(self, key):
        try:
            if key == MASTER_KEY:
                return bool(self._endpoint().GetMute())
            vols = self._sessions_by_key([key]).get(key, [])
            return bool(vols[0].GetMute()) if vols else False
        except Exception:
            return False

    def _set_mute(self, key, on):
        try:
            if key == MASTER_KEY:
                self._endpoint().SetMute(bool(on), None)
                return
            for v in self._sessions_by_key([key]).get(key, []):
                v.SetMute(bool(on), None)
        except Exception:
            self._drop_session_cache()

    def _reset_app_volumes(self):
        """Setzt jede App-Sitzung auf 100 %. Die Gesamtlautstaerke bleibt unberuehrt."""
        for s in self._all_sessions():
            try:
                sav = s.SimpleAudioVolume
                if sav is not None:
                    sav.SetMasterVolume(1.0, None)
            except Exception:
                pass

    def _master_gain(self):
        """Was die Gesamtlautstaerke wirklich daempft, als linearer Faktor (0..1).

        Der Windows-Regler ist *nicht* linear: 40 % dort daempfen staerker als
        40 % bei einer App (App-Regler sind reine Amplitudenfaktoren). Nur ueber
        Dezibel lassen sich die beiden Skalen ueberhaupt verrechnen.
        """
        try:
            return 10.0 ** (float(self._endpoint().GetMasterVolumeLevel()) / 20.0)
        except Exception:
            self._epv = None
            return None

    def _set_master_gain(self, gain):
        """Stellt die Gesamtlautstaerke so, dass sie linear um `gain` daempft."""
        try:
            ep = self._endpoint()
            lo, hi, _ = ep.GetVolumeRange()
            db = 20.0 * math.log10(max(1e-5, min(1.0, float(gain))))
            ep.SetMasterVolumeLevel(max(lo, min(hi, db)), None)
        except Exception:
            self._epv = None

    def _all_sessions(self):
        try:
            return AudioUtilities.GetAllSessions()
        except Exception:
            return []

    def _session_key(self, s):
        """Schluessel einer Sitzung – dieselbe Regel wie im Mixer."""
        if s.Process is None:
            return SYSTEM_KEY
        try:
            return s.Process.name().lower()
        except Exception:
            return None

    def _playing_volumes(self, exclude=(), threshold=0.01, samples=4, gap=0.02):
        """Regler aller Sitzungen, die gerade hoerbar Ton ausgeben.

        Windows meldet je Sitzung einen Spitzenpegel (`IAudioMeterInformation`).
        Damit laesst sich „Spotify spielt Musik“ von „Discord ist nur offen“
        unterscheiden – nur Ersteres wird beim Wechsel mit angepasst. Gemessen
        wird mehrfach, weil ein einzelner Wert in die Pause zwischen zwei Toenen
        fallen kann.
        """
        vols, meters = {}, {}
        for s in self._all_sessions():
            key = self._session_key(s)
            if not key or key in exclude:
                continue
            try:
                sav = s.SimpleAudioVolume
                meter = s._ctl.QueryInterface(IAudioMeterInformation)
            except Exception:
                continue
            if sav is None or meter is None:
                continue
            vols[key], meters[key] = sav, meter
        peak = dict.fromkeys(meters, 0.0)
        for i in range(max(1, samples)):
            if i:
                time.sleep(gap)
            for key, m in meters.items():
                try:
                    peak[key] = max(peak[key], float(m.GetPeakValue()))
                except Exception:
                    pass
        return {k: v for k, v in vols.items() if peak.get(k, 0.0) >= threshold}

    def _scale_volumes(self, savs, factor):
        """Regler mit `factor` multiplizieren, oder auf 100 % setzen (factor=None)."""
        for sav in savs:
            try:
                neu = 1.0 if factor is None else float(sav.GetMasterVolume()) * factor
                sav.SetMasterVolume(max(0.0, min(1.0, neu)), None)
            except Exception:
                pass

    def _settle(self, seconds=0.08):
        """Kurz warten, bis eine Aenderung in der Ausgabe angekommen ist.

        Sitzungs- und Geraetelautstaerke greifen an verschiedenen Stellen der
        Audiokette und nicht im selben Moment. Ohne diese Pause steht fuer ein,
        zwei Puffer beides hoch – genau das hoert man als kurzen Knall. Laeuft
        im Arbeitsthread, die Oberflaeche bleibt fluessig.
        """
        time.sleep(seconds)

    def _switch_levels(self, direction, keys):
        """Pegel angleichen, wenn die Steuerung zwischen Gesamt und Apps wechselt.

        Was hoerbar ankommt, ist App-Pegel × Daempfung der Gesamtlautstaerke.
        Beim Wechsel wandert die Steuerung von einem Faktor auf den anderen –
        ohne Ausgleich springt die Lautstaerke dabei (der neue Faktor steht ja
        irgendwo). Angepasst werden **nur die betroffenen Apps** (`keys`) –
        alle anderen, nicht angehakten Apps bleiben unberuehrt, auch wenn sie
        dadurch lauter werden. Wer das nicht will, hakt sie mit an.

        **Reihenfolge ist entscheidend:** immer erst leiser stellen, dann
        lauter. Andersherum liegt zwischen den beiden Aufrufen ein Moment, in
        dem beide Faktoren hoch stehen – das hoert man als kurzen Knall.

        `direction` ist "master" (App -> Gesamt) oder "apps" (Gesamt -> App),
        `keys` sind die betroffenen Apps.
        """
        if self.switch_mode == "none":
            return
        keys = list(keys or [])
        if self.switch_mode == "apps100":
            if direction == "master":
                self._reset_app_volumes()   # altes Verhalten
            return
        if not keys:
            return

        # --- "carry": den hoerbaren Pegel mitnehmen, nur fuer `keys` ---
        gain = self._master_gain()
        if gain is None:
            return
        by = self._sessions_by_key(keys)
        levels = {k: p for k, p in ((k, self._current_percent(k, by)) for k in keys)
                  if p is not None}
        if not levels:
            return
        # Apps, die gerade wirklich spielen, muessen mitgezogen werden: fuer sie
        # aendert sich die Gesamtdaempfung ja genauso. Stille Apps bleiben in
        # Ruhe – Discord soll nicht angefasst werden, nur weil es offen ist.
        mit = self._playing_volumes(exclude=set(levels))
        if direction == "apps":
            # Gesamt -> App: die betroffenen Apps uebernehmen die bisherige
            # Daempfung, danach steht Gesamt auf 100 %. Erst runter, dann rauf.
            for key, pct in levels.items():
                self._set_volume(key, max(0.0, min(1.0, pct / 100.0 * gain)))
            self._scale_volumes(mit.values(), gain)
            self._settle()
            self._write_master(1.0)
        else:
            # App -> Gesamt: die Gesamtlautstaerke uebernimmt den *leisesten*
            # der bisherigen Pegel, danach gehen die betroffenen Apps auf
            # 100 %. Auch hier erst runter, dann rauf.
            self._set_master_gain(min(levels.values()) / 100.0 * gain)
            self._settle()
            for key in levels:
                self._set_volume(key, 1.0)
            self._scale_volumes(mit.values(), None)
        # laufende Fahrten verwerfen, sonst zieht die Animation auf alte Werte
        self._vol_anim.clear()
        self._vol_now.clear()
        self._vol_step.clear()

    def _set_volume(self, key, val):
        if key == MASTER_KEY:
            self._write_master(val)
            return
        vols = self._sessions_by_key([key]).get(key, [])
        for v in vols:
            try:
                v.SetMasterVolume(float(val), None)
            except Exception:
                # Sitzung ist weg -> Cache verwerfen, beim naechsten Mal neu holen
                self._drop_session_cache()

    def _current_percent(self, key, by=None):
        """Aktueller Pegel in Prozent (0..100) oder None."""
        if key == MASTER_KEY:
            cur = self._read_master()
            return None if cur is None else cur * 100.0
        vols = (by or self._sessions_by_key([key])).get(key, [])
        if not vols:
            return None
        try:
            return vols[0].GetMasterVolume() * 100.0
        except Exception:
            return None

    def _apply_scroll(self, delta):
        """Setzt nur das Ziel – gefahren wird in 1-Prozent-Schritten."""
        targets = list(self.targets)
        if not targets:
            return
        by = self._sessions_by_key(targets)
        sign = 1.0 if self.reverse else -1.0
        change = (delta / float(WHEEL_DELTA)) * speed_to_step(self.speed) * sign
        any_valid = False
        for key in targets:
            base = self._vol_anim.get(key)
            if base is None:
                base = self._current_percent(key, by)
                if base is None:
                    continue
                self._vol_now[key] = base
            any_valid = True
            target = max(0.0, min(100.0, base + change))
            self._vol_anim[key] = target
            # Schrittweite so waehlen, dass die Fahrt rund 5 Ticks dauert
            dist = abs(target - self._vol_now.get(key, target))
            self._vol_step[key] = max(1, int(dist / 5.0 + 0.5))
        if not any_valid:
            self.ui_queue.put(("osd", [targets[0]], None, "keine Wiedergabe"))

    def _show_osd_for_targets(self):
        """Einblendung nach Abschluss der Fahrt aktualisieren."""
        vals = [(k, int(round(v))) for k, v in self._vol_now.items()
                if k in self.targets]
        if not vals:
            return
        if len(vals) == 1:
            k, p = vals[0]
            self.ui_queue.put(("osd", [k], p, None))
            self.ui_queue.put(("status", "{}: {} %".format(self._label_of(k), p)))
        else:
            avg = int(round(sum(p for _, p in vals) / len(vals)))
            self.ui_queue.put(("osd", [k for k, _ in vals], avg, None))
            self.ui_queue.put(("status", "{} Apps: ~{} %".format(len(vals), avg)))

    # ---- UI-Poll ---------------------------------------------------------
    def _poll_ui(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == "osd":
                    if self.osd_enabled:
                        self.osd.show(self._osd_items(msg[1]), msg[2], msg[3])
                elif kind == "status":
                    self.status_var.set(msg[1])
                elif kind == "apps":
                    self._note_known(msg[2] if len(msg) > 2 else msg[1])
                    self._update_rows(msg[1])
                elif kind == "vol":
                    key, pct = msg[1], msg[2]
                    row = self.rows.get(key)
                    if row is not None and self._dragging_key != key:
                        row.set_volume(pct / 100.0)
                elif kind == "hwheel":
                    if not self.active:
                        self.status_var.set("Daumenrad erkannt — Steuerung ist AUS")
                    elif not self.targets:
                        self.status_var.set("Daumenrad erkannt — noch keine App ausgewählt")
                elif kind == "show":
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()
                elif kind == "toggle_active":
                    self.active = not self.active
                    try:
                        self.sw_active.set(self.active)
                    except Exception:
                        pass
                    self._save()
                    if self.icon:
                        self.icon.update_menu()
                elif kind == "quit":
                    self._shutdown()
                    return
        except queue.Empty:
            pass
        self.root.after(40, self._poll_ui)

    def _schedule_autorefresh(self):
        if not self._stop:
            self.job_queue.put(("refresh",))
            self.root.after(1500, self._schedule_autorefresh)

    def _watch_dpi(self):
        """Prueft regelmaessig, ob das Fenster auf einem anders skalierten
        Monitor gelandet ist.

        Windows meldet den Wechsel per WM_DPICHANGED – an diese Nachricht kommt
        man aus Tk aber nur ueber Fenster-Subclassing heran. Nachfragen ist
        billig (ein Win32-Aufruf) und tut es genauso.
        """
        if self._stop:
            return
        try:
            neu = self._window_scale()
            # Nicht mitten im Ziehen umbauen: Widgets zu zerstoeren und neu
            # aufzubauen, waehrend der Nutzer das Fenster in der Hand hat,
            # sieht aus wie ein Absturz. Nach dem Loslassen ist noch frueh
            # genug.
            if abs(neu - SCALE) > 0.01 and not self._maus_gedrueckt():
                self._apply_scale(neu)
        except Exception:
            pass
        self.root.after(300, self._watch_dpi)

    @staticmethod
    def _maus_gedrueckt():
        """Haelt der Nutzer die linke Maustaste? Dann zieht er vermutlich."""
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        except Exception:
            return False

    def _apply_scale(self, neu):
        """Oberflaeche in der Aufloesung des neuen Monitors neu aufbauen.

        Alle Masse haengen an `SCALE` (siehe `px`), und die gezeichneten Bilder
        sind in genau diesen Pixelgroessen gerendert. Nach einem Wechsel hilft
        deshalb nur: Faktor setzen, Bilder verwerfen, neu zeichnen. Der Nutzer
        sieht dabei denselben Aufbau wie bei einem Themawechsel.
        """
        global SCALE
        alt = SCALE
        SCALE = neu
        # Groessenabhaengige Grafiken verwerfen – App-Symbole sind unter ihrer
        # Groesse verschluesselt und duerfen bleiben (teuerste Zutat).
        for k in [k for k in _PHOTO_CACHE if k[0] not in ("app", "av")]:
            del _PHOTO_CACHE[k]
        _CORNER_CACHE.clear()

        hoehe = int(round(self.root.winfo_height() * neu / alt))
        self.root.minsize(px(BASE_W), px(320))
        self.root.maxsize(px(BASE_W), self.root.winfo_screenheight())
        self.root.geometry("{}x{}".format(px(BASE_W), max(px(340), hoehe)))
        self._sized = False
        self._show_view(self.view)          # baut alles in neuer Groesse auf
        self._apply_titlebar()
        try:
            self.osd.configure(self.osd_size, self.osd_x, self.osd_y)
        except Exception:
            pass
        self._flash("Bildschirm-Skalierung: {:.0f} %".format(neu * 100))

    def _shutdown(self):
        self._stop = True
        for fn in (lambda: self.listener and self.listener.stop(),
                   lambda: self.job_queue.put(("quit",)),
                   lambda: self.icon and self.icon.stop(),
                   lambda: self.root.destroy()):
            try:
                fn()
            except Exception:
                pass

    def run(self):
        self.root.after(120, self._apply_titlebar)
        self.root.after(400, self._apply_titlebar)
        if "--tray" in sys.argv:
            self.root.after(60, self.root.withdraw)   # Autostart: nur ins Tray
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
