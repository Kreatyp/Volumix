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
    "speed": 40,             # 10..100 % – wie weit eine Rastung regelt
    "reverse": False,
    "active": True,
    "media_keys": False,     # Lautstaerke-Tasten statt Daumenrad
    "titel_taste": False,    # Mehrfachdruck auf Wiedergabe/Pause
    # Tastenkuerzel fuer den Profilwechsel, leer = nicht belegt. Form siehe
    # tastenkuerzel.py, etwa "ctrl+alt+39" fuer Strg+Alt+Rechts.
    "taste_profil_vor": "",
    "taste_profil_zurueck": "",
    "switch_mode": "none",   # was beim Wechsel Gesamt <-> App passiert
    "meters": True,          # Live-Pegel neben den Reglern
    "cover_bg": False,       # Coverbild des laufenden Titels als Grund
    # Meldet Aenderungen an Programme auf demselben Rechner, damit sie die
    # Anzeige selbst zeichnen koennen – fuer Spiele im Vollbild, hinter
    # denen die Einblendung sonst liegt. Ab Werk aus: Was einen Lauscher
    # aufmacht, soll man einschalten muessen.
    "melder": False,
    "angleichen": [],        # Apps, deren Lautstaerke angeglichen wird
    # Lautsprecher im Netz (Raumfeld) auf einen festen Wert bringen. Die
    # Adresse wird gemerkt, damit nicht bei jedem Start das Netz abgesucht
    # werden muss – sie ist nur ein Startwert, gefunden wird auch ohne sie.
    "boxen": False,
    "boxen_ziel": 65,        # Prozent, 0..100
    "boxen_schalten": False,  # mit dem Rechner an- und ausschalten
    "boxen_host": "",
    "osd_enabled": True,
    "osd_size": 45,
    "osd_x": 50,
    "osd_y": 88,
    # Prozent Durchsicht der Einblendung. 0 steht auf deckend.
    "osd_klar": 50,
    # Laufender Titel mit Fortschritt im freien Platz der Taskleiste
    "leiste": False,
    "sprache": "en",         # "de" oder "en" – Voreinstellung Englisch
    "accent": "violet",      # Schluessel aus theme.PALETTE
    "mode": "dark",
    # Groesse der Oberflaeche in Prozent. Wird beim Start als
    # QT_SCALE_FACTOR gesetzt – Qt rechnet damit alles um, auch die
    # selbst gezeichneten Flaechen. Aenderbar nur mit Neustart, weil der
    # Wert feststehen muss, bevor Qt hochfaehrt.
    "skala": 100,            # 75..150
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
# Ein Profil haelt nur den Arbeitsstand: Pegel und welche Apps am Rad
# haengen. Farbe, Geschwindigkeit und alles andere gelten fuer das ganze
# Programm – sonst springt beim Blaettern das halbe Fenster um.
PROFIL_TEILE = []

# Zaehlt hoch, wenn sich die Bedeutung gespeicherter Pegel aendert.
# 1 = Pegel sind Reglerpositionen (vorher: rohe Amplituden).
PROFIL_FASSUNG = 1

# Windows' Gesamtlautstaerke daempft nicht linear: Amplitude = Position^gamma.
# Gemessener Wert; die Audio-Schicht liest den echten laufend vom Geraet.
GAMMA_STANDARD = 1.7


def pos_aus_amp(amp, gamma=GAMMA_STANDARD):
    """Amplitude -> Reglerposition."""
    return max(0.0, min(1.0, float(amp))) ** (1.0 / gamma)


def amp_aus_pos(pos, gamma=GAMMA_STANDARD):
    """Reglerposition -> Amplitude."""
    return max(0.0, min(1.0, float(pos))) ** gamma

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


def paket_pfad(*teile):
    """Pfad zu einer mitgelieferten Datei (Schrift, Bild).

    In der gepackten .exe liegen die Daten in einem Ordner, den PyInstaller
    beim Start entpackt; aus dem Quelltext heraus einfach neben den Modulen.
    """
    wurzel = getattr(sys, "_MEIPASS", None)
    if wurzel:
        return os.path.join(wurzel, "volumix", *teile)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *teile)


PROTOKOLL = "fehler.log"
ABSTURZ = "absturz.log"
PROTOKOLL_GRENZE = 200 * 1024        # darueber wird von vorn begonnen


def protokoll_pfad(name=PROTOKOLL):
    return os.path.join(CONFIG_DIR, name)


def notiz(text):
    """Eine Zeile ins Protokoll.

    Damit laesst sich hinterher unterscheiden, ob die App beendet wurde oder
    einfach verschwunden ist – ohne diese Spur ist beides nicht auseinander-
    zuhalten, denn ein Programm im Infobereich schliesst sich lautlos.
    """
    import datetime
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        pfad = protokoll_pfad()
        if os.path.exists(pfad) and os.path.getsize(pfad) > PROTOKOLL_GRENZE:
            os.remove(pfad)
        with open(pfad, "a", encoding="utf-8") as f:
            f.write("{}  {}\n".format(
                datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass


def _kaputte_beiseite(grund):
    """Eine unlesbare Einstellungsdatei retten, statt sie zu ueberschreiben.

    Sie wandert mit Zeitstempel zur Seite. Wer seine Profile vermisst, findet
    sie dort wieder – und im Protokoll steht, was los war.
    """
    import datetime
    try:
        stempel = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        ziel = "{}.unlesbar-{}".format(CONFIG_PATH, stempel)
        os.replace(CONFIG_PATH, ziel)
        notiz("Einstellungen unlesbar ({}) – beiseitegelegt nach {}".format(
            grund, os.path.basename(ziel)))
    except Exception:
        # Selbst das Retten darf den Start nicht verhindern.
        pass


def load():
    """Einstellungen lesen – und im Zweifel lieber nichts wegwerfen.

    Zwei Dinge, die ohne Umschweife Daten kosten koennen:

    `utf-8-sig` statt `utf-8`: Wer die Datei mit einem Windows-Werkzeug
    bearbeitet – Notepad, PowerShells `Out-File`, viele Editoren – bekommt
    ein BOM an den Anfang geschrieben. Als `utf-8` gelesen steht dann ein
    unsichtbares Zeichen vor der ersten Klammer, `json` bricht ab, und alles
    faellt auf Werkseinstellung zurueck. `utf-8-sig` schluckt es.

    Und wenn die Datei doch unlesbar ist, wird sie beiseitegelegt statt
    ueberschrieben. Vorher passierte genau das: Volumix startete mit
    Standardwerten und speicherte sie beim naechsten Anlass darueber – die
    Profile, Farben und angehakten Apps waren weg, ohne dass jemand etwas
    davon mitbekam.
    """
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            daten = json.load(f)
    except FileNotFoundError:
        daten = {}
    except Exception as e:
        daten = {}
        _kaputte_beiseite(e)
    for k in DEFAULTS:
        if k in daten:
            cfg[k] = daten[k]
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


def autostart_lnk():
    """Wohin die Verknuepfung im Autostart-Ordner gehoert."""
    return os.path.join(
        _APPDATA, "Microsoft", "Windows", "Start Menu", "Programs",
        "Startup", APP_NAME + ".lnk")


def get_autostart():
    return os.path.exists(autostart_lnk())


def _lnk_schreiben(pfad, ziel, argumente="", symbol=None):
    """Eine Verknuepfung anlegen – ueber den Windows Script Host.

    Kein Fremdpaket noetig: WScript.Shell gehoert zu Windows und kann genau
    das. Ueber comtypes waere es umstaendlicher und braeuchte eine
    Typbibliothek.
    """
    import comtypes.client
    # `dynamic=True` ist Pflicht: Ohne das kommt ein nacktes IDispatch
    # zurueck, an dem schon `Save()` scheitert - die Verknuepfung waere
    # nie entstanden und der Autostart still wirkungslos.
    shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
    lnk = shell.CreateShortcut(pfad)
    lnk.TargetPath = ziel
    lnk.Arguments = argumente
    lnk.WorkingDirectory = os.path.dirname(ziel)
    lnk.Description = "Volumix – Lautstärke-Mixer für einzelne Apps"
    if symbol and os.path.exists(symbol):
        lnk.IconLocation = symbol
    lnk.Save()


def set_autostart(an):
    r"""Autostart ueber den Startup-Ordner, nicht ueber die Registry.

    Frueher stand hier ein Wert unter HKCU\...\CurrentVersion\Run. Das ist
    technisch dasselbe, aber es ist auch genau der Weg, auf dem sich
    Schadsoftware im System verankert - und Defender wertet ihn entsprechend.
    Zweimal hat er Volumix daraufhin in Quarantaene genommen, samt .exe und
    Taskleisten-Verknuepfung; beim zweiten Mal stand der Run-Schluessel
    ausdruecklich in der Fundmeldung.

    Eine Verknuepfung im Autostart-Ordner leistet dasselbe, ist fuer den
    Nutzer sichtbar und laesst sich dort auch von Hand wieder entfernen.
    """
    lnk = autostart_lnk()
    _run_key_entfernen()          # Altlast, egal in welche Richtung geschaltet
    if not an:
        try:
            os.remove(lnk)
        except FileNotFoundError:
            pass
        except OSError:
            pass
        return
    try:
        os.makedirs(os.path.dirname(lnk), exist_ok=True)
        fertig = gebaute_app()
        if fertig:
            _lnk_schreiben(lnk, fertig, "--tray", fertig)
        else:
            # Aus dem Quelltext heraus: ueber pythonw, damit kein Fenster
            # aufgeht.
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = sys.executable
            skript = os.path.join(app_dir(), "volumix.pyw")
            _lnk_schreiben(lnk, pyw, '"{}" --tray'.format(skript))
    except Exception as e:
        notiz("Autostart konnte nicht gesetzt werden: {}".format(e))


def _run_key_entfernen():
    """Den alten Registry-Eintrag loswerden, falls er noch da ist."""
    import winreg
    for name in (RUN_VALUE, OLD_RUN_VALUE):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                 winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, name)
                notiz("alter Autostart-Eintrag aus der Registry entfernt")
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass


def autostart_pruefen():
    """Zeigt die Verknuepfung noch auf etwas Sinnvolles?

    Wird sie aus dem Quelltext heraus gesetzt (beim Entwickeln), traegt sie
    den Weg ueber Python. Sobald die App gebaut ist, soll sie auf diese
    zeigen. Und wenn die .exe verschwunden ist - etwa weil ein Virenscanner
    sie geholt hat -, zeigt die Verknuepfung ins Leere und wird erneuert,
    sobald wieder eine da ist.
    """
    fertig = gebaute_app()
    if not fertig or not get_autostart():
        return
    try:
        import comtypes.client
        shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
        lnk = shell.CreateShortcut(autostart_lnk())
        ziel = (lnk.TargetPath or "").lower()
    except Exception:
        return
    if fertig.lower() != ziel:
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
