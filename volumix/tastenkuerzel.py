"""Globale Tastenkuerzel ueber RegisterHotKey.

Der Tastatur-Hook in hooks.py sieht jede einzelne Taste und muss sie selbst
weiterreichen. Hier nicht: Windows erkennt die angemeldete Kombination und
stellt nur sie als WM_HOTKEY zu, alles andere geht an Volumix vorbei. Ein
Kuerzel kann deshalb keine Tasten verschlucken und das Loslassen anderer
Tasten nicht aufhalten.

Gespeichert wird ein Kuerzel als Text wie "ctrl+alt+39": die Zusatztasten in
fester Reihenfolge, zuletzt der virtuelle Tastencode von Windows. Das haengt
weder an der Sprache noch an der Tastaturbelegung.
"""

import ctypes
import itertools
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, Qt, QTimer, Signal
from PySide6.QtWidgets import QPushButton

from . import config
from .sprache import T

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# (Speichername, Windows-Bit, Qt-Modifier, Text "mod_...") in Anzeigereihenfolge
ZUSATZ = (
    ("ctrl", MOD_CONTROL, Qt.ControlModifier, "strg"),
    ("alt", MOD_ALT, Qt.AltModifier, "alt"),
    ("shift", MOD_SHIFT, Qt.ShiftModifier, "umschalt"),
    ("win", MOD_WIN, Qt.MetaModifier, "win"),
)

# Tastencode einer Zusatztaste -> ihr Bit. Beim Druck auf die Zusatztaste
# selbst fehlt dieses Bit in QKeyEvent.modifiers() noch; es muss deshalb aus
# dem Code kommen, sonst zeigt die Vorschau "Strg+" erst beim naechsten Druck.
_ZUSATZTASTE = {
    0x10: MOD_SHIFT, 0xA0: MOD_SHIFT, 0xA1: MOD_SHIFT,
    0x11: MOD_CONTROL, 0xA2: MOD_CONTROL, 0xA3: MOD_CONTROL,
    0x12: MOD_ALT, 0xA4: MOD_ALT, 0xA5: MOD_ALT,
    0x5B: MOD_WIN, 0x5C: MOD_WIN,
}
# Tastencodes, die nur Zusatz sind und allein kein Kuerzel ergeben
NUR_ZUSATZ = frozenset(_ZUSATZTASTE)
VK_BACK = 0x08
VK_ESCAPE = 0x1B
VK_DELETE = 0x2E
# F1 bis F24 tippen nichts und duerfen ohne Zusatz stehen
F_TASTEN = range(0x70, 0x88)

_PFEILE = {0x25: "←", 0x26: "↑", 0x27: "→", 0x28: "↓"}
# Text "tname_..."
_BENANNT = {
    0x08: "ruecktaste", 0x09: "tab", 0x0D: "enter",
    0x13: "pause", 0x20: "leer", 0x21: "bild_auf",
    0x22: "bild_ab", 0x23: "ende", 0x24: "pos1",
    0x2C: "druck", 0x2D: "einfg", 0x2E: "entf",
}
# Tasten, die Windows als "erweitert" fuehrt. Ohne das Kennzeichen liefert
# GetKeyNameText die Namen der gleichnamigen Ziffernblock-Tasten.
_ERWEITERT = frozenset((0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
                        0x2D, 0x2E, 0x6F, 0x90))

# Eigene Instanz: Die argtypes unten sollen nicht auf windll.user32 abfaerben,
# das an anderen Stellen mit anderen Aufrufkonventionen benutzt wird.
_u32 = ctypes.WinDLL("user32")
_u32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)
_u32.GetKeyboardLayout.restype = ctypes.c_void_p
_u32.MapVirtualKeyExW.argtypes = (wintypes.UINT, wintypes.UINT, ctypes.c_void_p)
_u32.MapVirtualKeyExW.restype = wintypes.UINT
_u32.ToUnicodeEx.argtypes = (wintypes.UINT, wintypes.UINT,
                             ctypes.POINTER(ctypes.c_ubyte), wintypes.LPWSTR,
                             ctypes.c_int, wintypes.UINT, ctypes.c_void_p)
_u32.ToUnicodeEx.restype = ctypes.c_int
_u32.GetKeyNameTextW.argtypes = (wintypes.LONG, wintypes.LPWSTR, ctypes.c_int)
_u32.GetKeyNameTextW.restype = ctypes.c_int
_u32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int,
                                wintypes.UINT, wintypes.UINT)
_u32.RegisterHotKey.restype = wintypes.BOOL
_u32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
_u32.UnregisterHotKey.restype = wintypes.BOOL


# ---- Speicherform -----------------------------------------------------------

def zusammensetzen(mods, vk):
    """Windows-Zusatzbits und Tastencode als Speichertext."""
    teile = [name for name, bit, _, _ in ZUSATZ if mods & bit]
    teile.append(str(int(vk)))
    return "+".join(teile)


def zerlegen(text):
    """Speichertext in (Zusatzbits, Tastencode); None, wenn er nicht passt."""
    if not text or not isinstance(text, str):
        return None
    *zusaetze, taste = text.split("+")
    try:
        vk = int(taste)
    except ValueError:
        return None
    if not 0 < vk < 0xFF:
        return None
    bits = {name: bit for name, bit, _, _ in ZUSATZ}
    mods = 0
    for z in zusaetze:
        if z not in bits:
            return None
        mods |= bits[z]
    return mods, vk


def zusatz_aus_qt(modifiers):
    """Qt-Modifier in Windows-Zusatzbits."""
    mods = 0
    for _, bit, qt_mod, _ in ZUSATZ:
        if modifiers & qt_mod:
            mods |= bit
    return mods


# ---- Anzeige ----------------------------------------------------------------

def _windows_name(vk):
    """Name der Taste laut Windows - fuer die Sonderzeichen der Belegung."""
    try:
        layout = _u32.GetKeyboardLayout(0)
        scan = _u32.MapVirtualKeyExW(vk, 0, layout)
        if not scan:
            return ""
        lparam = scan << 16
        if vk in _ERWEITERT:
            lparam |= 1 << 24
        puffer = ctypes.create_unicode_buffer(64)
        n = _u32.GetKeyNameTextW(lparam, puffer, 64)
        return puffer.value[:n] if n > 0 else ""
    except Exception:
        return ""


def tastenname(vk):
    if vk in _PFEILE:
        return _PFEILE[vk]
    if vk in F_TASTEN:
        return "F{}".format(vk - 0x6F)
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x60 <= vk <= 0x69:
        return "Num {}".format(vk - 0x60)
    if vk in _BENANNT:
        return T("tname_" + _BENANNT[vk])
    return _windows_name(vk) or "#{}".format(vk)


def _zusatznamen(mods):
    return [T("mod_" + s) for _, bit, _, s in ZUSATZ if mods & bit]


def anzeige(text):
    """Speichertext fuer die Oberflaeche, etwa "Strg+Alt+→"."""
    teile = zerlegen(text)
    if teile is None:
        return ""
    mods, vk = teile
    return "+".join(_zusatznamen(mods) + [tastenname(vk)])


# ---- Pruefen ----------------------------------------------------------------

def altgr_zeichen(mods, vk):
    """Zeichen, das diese Kombination auf der aktiven Belegung tippt, sonst "".

    Strg+Alt ist fuer Windows dasselbe wie AltGr. Ein Kuerzel wie Strg+Alt+Q
    nimmt auf deutscher Tastatur deshalb das @ weg - RegisterHotKey faengt
    die Kombination ab, bevor ein Programm das Zeichen bekommt.
    """
    if not (mods & MOD_CONTROL and mods & MOD_ALT):
        return ""
    try:
        zustand = (ctypes.c_ubyte * 256)()
        zustand[0x11] = 0x80            # VK_CONTROL
        zustand[0x12] = 0x80            # VK_MENU
        if mods & MOD_SHIFT:
            zustand[0x10] = 0x80        # VK_SHIFT
        layout = _u32.GetKeyboardLayout(0)
        scan = _u32.MapVirtualKeyExW(vk, 0, layout)
        puffer = ctypes.create_unicode_buffer(8)
        # Kennzeichen 4: den Tastaturzustand nicht veraendern. Ohne das
        # verbraucht der Aufruf eine vorher gedrueckte Tottaste.
        n = _u32.ToUnicodeEx(vk, scan, zustand, puffer, 8, 4, layout)
        if n > 0:
            zeichen = puffer.value[:n]
            return zeichen if zeichen.isprintable() else ""
        return ""
    except Exception:
        return ""


def pruefen(mods, vk):
    """Einwand gegen ein Kuerzel als (Grund, Werte), sonst None; Text "einwand_<Grund>"."""
    # Ohne Zusatz oder nur mit Umschalt ist es eine Taste zum Tippen.
    if (not mods or mods == MOD_SHIFT) and vk not in F_TASTEN:
        return "ohne_zusatz", {}
    zeichen = altgr_zeichen(mods, vk)
    if zeichen:
        return "tippt", {"zeichen": zeichen}
    return None


# ---- Anmelden bei Windows -----------------------------------------------------

# Anwendungen duerfen Kennungen von 0x0000 bis 0xBFFF vergeben
_KENNUNGEN = itertools.count(0x5601)


def _sicher(rueckruf):
    try:
        rueckruf()
    except Exception as e:
        config.notiz("Tastenkuerzel: {!r}".format(e))


class GlobaleTasten(QAbstractNativeEventFilter):
    """Meldet Kuerzel bei Windows an und verteilt die WM_HOTKEY-Meldungen.

    Angemeldet wird ohne Fensterhandle. Windows legt WM_HOTKEY dann in die
    Warteschlange des anmeldenden Threads; das muss der Qt-Hauptthread sein,
    und von dort kommt die Meldung im nativeEventFilter an.
    """

    def __init__(self):
        super().__init__()
        self._kennungen = {}        # Name -> feste Kennung fuer RegisterHotKey
        self._eintraege = {}        # Name -> (Kuerzel, Rueckruf)
        self._angemeldet = set()
        self._ausgesetzt = False

    def _kennung(self, name):
        # Kennungen gelten je Thread, nicht je Objekt. Vergeben zwei Objekte
        # dieselbe, laesst Windows beide Anmeldungen stehen - und ein
        # UnregisterHotKey trifft dann womoeglich die des anderen.
        if name not in self._kennungen:
            self._kennungen[name] = next(_KENNUNGEN)
        return self._kennungen[name]

    def _anmelden(self, name):
        teile = zerlegen(self._eintraege[name][0])
        if teile is None:
            return False
        mods, vk = teile
        if not _u32.RegisterHotKey(None, self._kennung(name),
                                   mods | MOD_NOREPEAT, vk):
            return False
        self._angemeldet.add(name)
        return True

    def _abmelden(self, name):
        if name in self._angemeldet:
            _u32.UnregisterHotKey(None, self._kennung(name))
            self._angemeldet.discard(name)

    def setzen(self, name, kuerzel, rueckruf):
        """Kuerzel fuer `name` anmelden; leerer Text gibt es nur frei.

        False heisst, Windows gibt die Kombination nicht her - meist, weil
        ein anderes Programm sie angemeldet hat. Fuer `name` ist dann nichts
        mehr angemeldet. Waehrend aussetzen() wird nur vorgemerkt.
        """
        self._abmelden(name)
        self._eintraege.pop(name, None)
        if not kuerzel:
            return True
        if zerlegen(kuerzel) is None:
            return False
        self._eintraege[name] = (kuerzel, rueckruf)
        if self._ausgesetzt or self._anmelden(name):
            return True
        self._eintraege.pop(name, None)
        return False

    def angemeldet(self, name):
        return name in self._angemeldet

    def aussetzen(self):
        """Alle Kuerzel voruebergehend freigeben, etwa waehrend einer Aufnahme.

        Solange eine Kombination angemeldet ist, faengt Windows sie ab - im
        Aufnahmefeld kaeme sie nie an.
        """
        self._ausgesetzt = True
        for name in list(self._angemeldet):
            self._abmelden(name)

    def fortsetzen(self):
        """Nach aussetzen() wieder anmelden. Liefert die Namen, die scheitern."""
        self._ausgesetzt = False
        gescheitert = []
        for name in list(self._eintraege):
            if name not in self._angemeldet and not self._anmelden(name):
                gescheitert.append(name)
        return gescheitert

    def alle_loesen(self):
        for name in list(self._angemeldet):
            self._abmelden(name)
        self._eintraege.clear()

    def nativeEventFilter(self, typ, nachricht):
        if bytes(typ) != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(nachricht))
        if msg.message != WM_HOTKEY:
            return False, 0
        for name, kennung in self._kennungen.items():
            if kennung == msg.wParam and name in self._eintraege:
                rueckruf = self._eintraege[name][1]
                # Nicht im Filter selbst arbeiten: Der laeuft mitten in der
                # Ereignisverarbeitung von Qt.
                QTimer.singleShot(0, lambda r=rueckruf: _sicher(r))
                return True, 0
        return False, 0


# ---- Aufnahmeknopf ------------------------------------------------------------

class TastenFeld(QPushButton):
    """Knopf, der ein Kuerzel zeigt und auf Klick ein neues aufnimmt.

    Esc bricht ab, Entf oder Ruecktaste ohne Zusatz loeschen das Kuerzel.
    Waehrend der Aufnahme haelt der Knopf die Tastatur fest, damit keine
    Taste nebenbei etwas im Fenster ausloest.
    """

    aufnahme = Signal(bool)
    festgelegt = Signal(str)

    def __init__(self, kuerzel="", parent=None):
        super().__init__(parent)
        self.setObjectName("Chip")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(150)
        self._kuerzel = kuerzel or ""
        self._nimmt_auf = False
        self._fehlerzeit = QTimer(self)
        self._fehlerzeit.setSingleShot(True)
        self._fehlerzeit.timeout.connect(lambda: self._text_setzen())
        self.clicked.connect(self._geklickt)
        self._text_setzen()

    def kuerzel(self):
        return self._kuerzel

    def nimmt_auf(self):
        return self._nimmt_auf

    def setze(self, kuerzel):
        self._kuerzel = kuerzel or ""
        self._fehlerzeit.stop()
        self._text_setzen()

    def fehler(self, text, ms=2400):
        """Einwand kurz im Knopf zeigen, danach wieder den normalen Text."""
        self.setText(text)
        self._fehlerzeit.start(ms)

    def _text_setzen(self, vorschau=None):
        if self._nimmt_auf:
            self.setText(vorschau or T("taste_druecken"))
        else:
            self.setText(anzeige(self._kuerzel) or T("taste_nicht_belegt"))

    def _geklickt(self):
        if self._nimmt_auf:
            self._beenden(None)
        else:
            self._starten()

    def _starten(self):
        self._nimmt_auf = True
        self._fehlerzeit.stop()
        self.setChecked(True)
        self.setFocus(Qt.MouseFocusReason)
        self.grabKeyboard()
        self._text_setzen()
        self.aufnahme.emit(True)

    def _beenden(self, neu):
        """Aufnahme schliessen; neu=None heisst abgebrochen."""
        if not self._nimmt_auf:
            return
        self._nimmt_auf = False
        self.releaseKeyboard()
        self.setChecked(False)
        self._fehlerzeit.stop()
        self._text_setzen()
        # Erst freigeben, dann melden: Wer auf festgelegt reagiert, meldet
        # das neue Kuerzel an - dafuer muessen die alten wieder stehen.
        self.aufnahme.emit(False)
        if neu is not None and neu != self._kuerzel:
            self.festgelegt.emit(neu)

    def _vorschau(self, mods):
        return "+".join(_zusatznamen(mods)) + "+…" if mods else None

    def keyPressEvent(self, e):
        if not self._nimmt_auf:
            super().keyPressEvent(e)
            return
        e.accept()
        if e.isAutoRepeat():
            return
        vk = e.nativeVirtualKey()
        mods = zusatz_aus_qt(e.modifiers())
        if not vk or vk in NUR_ZUSATZ:
            mods |= _ZUSATZTASTE.get(vk, 0)
            self._text_setzen(self._vorschau(mods))
            return
        if not mods and vk == VK_ESCAPE:
            self._beenden(None)
            return
        if not mods and vk in (VK_BACK, VK_DELETE):
            self._beenden("")
            return
        einwand = pruefen(mods, vk)
        if einwand:
            grund, werte = einwand
            self.fehler(T("einwand_" + grund, **werte))
            return
        self._beenden(zusammensetzen(mods, vk))

    def keyReleaseEvent(self, e):
        if not self._nimmt_auf:
            super().keyReleaseEvent(e)
            return
        e.accept()
        if not self._fehlerzeit.isActive():
            # Umgekehrt zum Druck: Beim Loslassen steht das Bit teils noch drin
            mods = zusatz_aus_qt(e.modifiers())
            mods &= ~_ZUSATZTASTE.get(e.nativeVirtualKey(), 0)
            self._text_setzen(self._vorschau(mods))

    def focusOutEvent(self, e):
        # Wer woanders hinklickt, will keine Aufnahme mehr.
        self._beenden(None)
        super().focusOutEvent(e)
