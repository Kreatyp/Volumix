# -*- coding: utf-8 -*-
"""Tastenkuerzel fuer den Profilwechsel: Speicherform, Anmeldung, Aufnahme."""
import os
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

import ctypes                                                  # noqa: E402

ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

from PySide6.QtCore import QEvent, Qt                          # noqa: E402
from PySide6.QtGui import QKeyEvent                            # noqa: E402
from PySide6.QtWidgets import QApplication                     # noqa: E402

from volumix import config, sprache                            # noqa: E402
_TEST = os.path.join(_TESTS, "testcfg")
os.makedirs(_TEST, exist_ok=True)
config.CONFIG_DIR = _TEST
config.CONFIG_PATH = os.path.join(_TEST, "config-profiltasten.json")
if os.path.exists(config.CONFIG_PATH):
    os.remove(config.CONFIG_PATH)

from volumix import tastenkuerzel as tk                        # noqa: E402

fehler = 0


def pruefe(name, bedingung, zusatz=""):
    global fehler
    fehler += 0 if bedingung else 1
    print("  {} {}{}".format("OK  " if bedingung else "FEHL", name,
                             "  " + zusatz if zusatz else ""))


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)


def warten(n=15):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.02)


# Eine Kombination, die im Alltag niemand belegt: Strg+Alt+Umschalt+F13
MODS = tk.MOD_CONTROL | tk.MOD_ALT | tk.MOD_SHIFT
VK_F13 = 0x7C
KUERZEL = tk.zusammensetzen(MODS, VK_F13)


def druecken(mods=MODS, vk=VK_F13):
    """Kombination als echte Eingabe senden - so, als kaeme sie von der Tastatur."""
    u = ctypes.windll.user32
    zusatz = [(tk.MOD_CONTROL, 0x11), (tk.MOD_ALT, 0x12), (tk.MOD_SHIFT, 0x10)]
    gedrueckt = []
    try:
        for bit, taste in zusatz:
            if mods & bit:
                u.keybd_event(taste, 0, 0, 0)
                gedrueckt.append(taste)
        u.keybd_event(vk, 0, 0, 0)
        u.keybd_event(vk, 0, 2, 0)
    finally:
        # Immer loslassen - sonst haengt Strg im restlichen System
        for taste in reversed(gedrueckt):
            u.keybd_event(taste, 0, 2, 0)
    warten(25)


print("=== Speicherform ===")
sprache.setzen("de")
for mods, vk in ((tk.MOD_CONTROL | tk.MOD_ALT, 0x27), (0, 0x78),
                 (tk.MOD_WIN | tk.MOD_SHIFT, 0x21), (MODS, VK_F13)):
    text = tk.zusammensetzen(mods, vk)
    pruefe("hin und zurueck: " + text, tk.zerlegen(text) == (mods, vk))
pruefe("Reihenfolge der Zusatztasten steht fest",
       tk.zusammensetzen(tk.MOD_SHIFT | tk.MOD_CONTROL, 0x41) == "ctrl+shift+65")
for kaputt in ("", "ctrl+", "ctrl+xyz+5", "ctrl+999", "abc", None, 7):
    pruefe("Unfug abgelehnt: {!r}".format(kaputt), tk.zerlegen(kaputt) is None)

print("\n=== Anzeige ===")
pruefe("deutsch", tk.anzeige("ctrl+alt+39") == "Strg+Alt+→",
       tk.anzeige("ctrl+alt+39"))
pruefe("F-Taste", tk.anzeige("120") == "F9")
pruefe("benannte Taste", tk.anzeige("ctrl+shift+36") == "Strg+Umschalt+Pos1")
pruefe("Reihenfolge beim Lesen egal", tk.anzeige("shift+ctrl+36") == "Strg+Umschalt+Pos1")
sprache.setzen("en")
pruefe("englisch", tk.anzeige("ctrl+shift+33") == "Ctrl+Shift+PgUp",
       tk.anzeige("ctrl+shift+33"))
sprache.setzen("de")
pruefe("leer bleibt leer", tk.anzeige("") == "")

print("\n=== Pruefung ===")
pruefe("F9 allein erlaubt", tk.pruefen(0, 0x78) is None)
pruefe("Buchstabe allein abgelehnt", tk.pruefen(0, 0x51) is not None)
pruefe("Umschalt+Buchstabe abgelehnt (ist bloss ein Grossbuchstabe)",
       tk.pruefen(tk.MOD_SHIFT, 0x51) is not None)
pruefe("Strg+Alt+Pfeil erlaubt", tk.pruefen(tk.MOD_CONTROL | tk.MOD_ALT, 0x27) is None)
at = tk.altgr_zeichen(tk.MOD_CONTROL | tk.MOD_ALT, 0x51)
if at:
    pruefe("Strg+Alt+Q tippt auf dieser Belegung {!r} und wird abgelehnt".format(at),
           tk.pruefen(tk.MOD_CONTROL | tk.MOD_ALT, 0x51) == ("tippt", {"zeichen": at}))
else:
    print("  --   Strg+Alt+Q tippt auf dieser Belegung nichts, Pruefung entfaellt")

print("\n=== Anmeldung bei Windows ===")
g = tk.GlobaleTasten()
app.installNativeEventFilter(g)
gerufen = []
pruefe("anmelden", g.setzen("test", KUERZEL, lambda: gerufen.append(1)))
pruefe("ist angemeldet", g.angemeldet("test"))
druecken()
pruefe("Kombination kommt an, genau einmal", gerufen == [1], str(gerufen))

h = tk.GlobaleTasten()
pruefe("dieselbe Kombination ein zweites Mal wird verweigert",
       not h.setzen("anderes", KUERZEL, lambda: None))
pruefe("und ist danach dort auch nicht vorgemerkt", not h.angemeldet("anderes"))

g.aussetzen()
pruefe("ausgesetzt: nicht mehr angemeldet", not g.angemeldet("test"))
druecken()
pruefe("ausgesetzt: kommt nicht an", gerufen == [1], str(gerufen))
pruefe("fortsetzen gelingt", g.fortsetzen() == [])
druecken()
pruefe("nach fortsetzen wieder da", gerufen == [1, 1], str(gerufen))

pruefe("leeres Kuerzel gibt frei", g.setzen("test", "", None) and not g.angemeldet("test"))
druecken()
pruefe("freigegeben: kommt nicht an", gerufen == [1, 1], str(gerufen))

pruefe("Fehler im Rueckruf reisst nichts mit",
       g.setzen("test", KUERZEL, lambda: 1 / 0))
druecken()
pruefe("das Programm laeuft danach weiter", True)
g.alle_loesen()
pruefe("alle_loesen gibt frei", not g.angemeldet("test"))
app.removeNativeEventFilter(g)

print("\n=== Aufnahmeknopf ===")


def taste(feld, vk, mods=Qt.NoModifier, qt_taste=Qt.Key_unknown, los=False):
    typ = QEvent.KeyRelease if los else QEvent.KeyPress
    e = QKeyEvent(typ, qt_taste, mods, 0, vk, 0, "")
    (feld.keyReleaseEvent if los else feld.keyPressEvent)(e)


feld = tk.TastenFeld("")
aufnahmen, festgelegt = [], []
feld.aufnahme.connect(aufnahmen.append)
feld.festgelegt.connect(festgelegt.append)
pruefe("zeigt „Nicht belegt“", feld.text() == sprache.T("taste_nicht_belegt"))

feld.click()
pruefe("Klick startet die Aufnahme", feld.nimmt_auf() and aufnahmen == [True])
pruefe("zeigt die Aufforderung", feld.text() == sprache.T("taste_druecken"))
taste(feld, 0x11, Qt.ControlModifier, Qt.Key_Control)
pruefe("Zusatztaste allein: Vorschau, noch nichts festgelegt",
       feld.text() == "Strg+…" and not festgelegt, feld.text())
taste(feld, 0x12, Qt.ControlModifier, Qt.Key_Alt)
pruefe("zweite Zusatztaste dazu", feld.text() == "Strg+Alt+…", feld.text())
taste(feld, 0x12, Qt.ControlModifier | Qt.AltModifier, Qt.Key_Alt, los=True)
pruefe("Alt losgelassen", feld.text() == "Strg+…", feld.text())
taste(feld, 0x11, Qt.ControlModifier, Qt.Key_Control, los=True)
pruefe("alles losgelassen: wieder die Aufforderung",
       feld.text() == sprache.T("taste_druecken"), feld.text())
taste(feld, 0x51, Qt.NoModifier, Qt.Key_Q)
pruefe("Buchstabe ohne Zusatz: Einwand, Aufnahme laeuft weiter",
       feld.nimmt_auf() and not festgelegt and feld.text() == sprache.T("einwand_ohne_zusatz"))
taste(feld, 0x27, Qt.ControlModifier | Qt.AltModifier, Qt.Key_Right)
pruefe("Strg+Alt+Rechts festgelegt", festgelegt == ["ctrl+alt+39"], str(festgelegt))
pruefe("Aufnahme beendet und gemeldet",
       not feld.nimmt_auf() and aufnahmen == [True, False], str(aufnahmen))

feld.setze("ctrl+alt+39")
pruefe("zeigt das Kuerzel", feld.text() == "Strg+Alt+→")
festgelegt.clear()
feld.click()
taste(feld, tk.VK_ESCAPE, Qt.NoModifier, Qt.Key_Escape)
pruefe("Esc bricht ab, nichts festgelegt",
       not feld.nimmt_auf() and not festgelegt and feld.text() == "Strg+Alt+→")
feld.click()
taste(feld, tk.VK_DELETE, Qt.NoModifier, Qt.Key_Delete)
pruefe("Entf loescht", festgelegt == [""], str(festgelegt))
festgelegt.clear()
feld.click()
taste(feld, 0x27, Qt.ControlModifier | Qt.AltModifier, Qt.Key_Right)
pruefe("dieselbe Kombination nochmal: keine Meldung", not festgelegt)

print("\n=== Im Fenster: festlegen, druecken, wechseln ===")
import schirm                                                  # noqa: E402
from volumix.window import MainWindow                          # noqa: E402
f = MainWindow()
f.show()
schirm.nebenan(f)
warten(40)

# Zwei Profile, damit es etwas zu blaettern gibt
f.btn_prof_neu.click()
f.profil_name.clearFocus()
warten(10)
namen = f._profil_namen()
pruefe("zwei Profile vorhanden", len(namen) >= 2, str(namen))

feld_vor = f.tastenfelder["taste_profil_vor"]
feld_zur = f.tastenfelder["taste_profil_zurueck"]
f._taste_festlegen("taste_profil_vor", feld_vor, KUERZEL)
pruefe("Kuerzel gespeichert", f.cfg["taste_profil_vor"] == KUERZEL)
pruefe("und bei Windows angemeldet", f.tasten.angemeldet("taste_profil_vor"))
pruefe("in der Einstellungsdatei",
       config.load().get("taste_profil_vor") == KUERZEL)

f._taste_festlegen("taste_profil_zurueck", feld_zur, KUERZEL)
pruefe("dieselbe Kombination fuer die andere Richtung abgelehnt",
       f.cfg["taste_profil_zurueck"] == "" and feld_zur.text() == sprache.T("taste_doppelt"),
       feld_zur.text())

vorher = f.cfg["profil"]
druecken()
pruefe("Tastendruck wechselt das Profil", f.cfg["profil"] != vorher,
       "{} -> {}".format(vorher, f.cfg["profil"]))
pruefe("die Einblendung zeigt den neuen Namen",
       f.osd.isVisible() and f.osd._text == f.cfg["profil"],
       "{!r}".format(f.osd._text))

# Waehrend einer Aufnahme darf die Taste nicht wechseln - sie gehoert dem Feld
feld_vor.click()
jetzt = f.cfg["profil"]
druecken()
pruefe("waehrend der Aufnahme: kein Wechsel", f.cfg["profil"] == jetzt)
taste(feld_vor, tk.VK_ESCAPE, Qt.NoModifier, Qt.Key_Escape)
pruefe("nach Abbruch wieder angemeldet", f.tasten.angemeldet("taste_profil_vor"))
druecken()
pruefe("und wechselt wieder", f.cfg["profil"] != jetzt)

f._taste_festlegen("taste_profil_vor", feld_vor, "")
pruefe("geloescht: nicht mehr angemeldet",
       not f.tasten.angemeldet("taste_profil_vor") and f.cfg["taste_profil_vor"] == "")

# Belegt ein anderer die Kombination, bleibt die alte Einstellung stehen
f._taste_festlegen("taste_profil_vor", feld_vor, "ctrl+alt+39")
fremd = tk.GlobaleTasten()
fremd.setzen("fremd", KUERZEL, lambda: None)
f._taste_festlegen("taste_profil_vor", feld_vor, KUERZEL)
pruefe("fremd belegt: alte Einstellung bleibt",
       f.cfg["taste_profil_vor"] == "ctrl+alt+39"
       and f.tasten.angemeldet("taste_profil_vor"))
pruefe("und der Knopf sagt es",
       feld_vor.text() == sprache.T("taste_vergeben", kuerzel=tk.anzeige(KUERZEL)),
       feld_vor.text())
fremd.alle_loesen()

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
f._beenden()
sys.exit(1 if fehler else 0)
