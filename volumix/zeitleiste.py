# -*- coding: utf-8 -*-
"""Der laufende Titel mit seinem Fortschritt, in der Taskleiste.

Windows hat fuer den freien Platz in der Taskleiste keine Schnittstelle: Die
Deskbands aus frueheren Fassungen gibt es seit Windows 11 nicht mehr. Der
Streifen ist deshalb ein eigenes, rahmenloses Fenster, das genau dort liegt
und der Taskleiste nachgefuehrt wird. Klicks gehen hindurch – darunter liegt
die Taskleiste, und die soll bedienbar bleiben.

Gefunden wird der Platz ueber die Fenster, aus denen die Taskleiste besteht:

    Shell_TrayWnd      die Leiste selbst
      MSTaskSwWClass   die Programmsymbole (in Windows 11 mittig)
      TrayNotifyWnd    der Bereich mit Uhr und kleinen Symbolen

Dazwischen ist frei. Gemessen auf diesem Rechner: Leiste 0..2560, Symbole
949..1302, Uhr ab 2319 – also gut tausend Pixel Platz.

Die Spielposition kommt von derselben Stelle wie Titel und Coverbild, aber
nur alle anderthalb Sekunden. Dazwischen wird sie hochgerechnet, sonst
ruckelt der Balken im Sekundentakt.
"""
import ctypes
import time
from ctypes import wintypes

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QFontMetricsF,
                           QLinearGradient, QPainter)
from PySide6.QtWidgets import QWidget

from .sprache import T
from .theme import glaettung, schrift

_user32 = ctypes.WinDLL("user32", use_last_error=True)

# Die Typen muessen erklaert werden, sonst reicht ctypes alles als C-int
# durch – 32 Bit, wo Windows 64 erwartet. Gemessen: SetWindowPos gab
# Fehler 1400 (ungueltiges Fenster) zurueck und tat nichts; der Streifen
# blieb hinter der Taskleiste, sobald man sie angeklickt hatte. Mit
# erklaerten Typen meldet derselbe Aufruf Erfolg.
_user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND,
                                  wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.FindWindowExW.restype = wintypes.HWND
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_uint]
_user32.SetWindowPos.restype = wintypes.BOOL

# Breite des Streifens in logischen Pixeln. Mehr braucht es nicht: Titel und
# Interpret werden gekuerzt, und der Platz gehoert eigentlich der Taskleiste.
BREITE = 300
ABSTAND = 12            # Luft zum Bereich mit der Uhr
MINDESTPLATZ = 160      # darunter lohnt sich die Anzeige nicht

# Wie oft Platz und Reihenfolge nachgezogen werden. Beides ist billig – ein
# paar Abfragen und ein SetWindowPos ohne Bewegung.
NACHZIEHEN = 400        # Millisekunden

_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_SWP_NOOWNERZORDER = 0x0200


class _RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


def _suchen(eltern, klasse):
    """Ein Kindfenster dieser Klasse finden, auch tiefer im Baum.

    `FindWindowEx` sieht nur die unmittelbaren Kinder. Die Leiste mit den
    Programmsymbolen haengt in Windows 11 aber eine Ebene tiefer, unter
    `ReBarWindow32` – ohne die Suche in die Tiefe faende man sie nie.
    """
    treffer = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def besuch(kind, _):
        name = ctypes.create_unicode_buffer(64)
        _user32.GetClassNameW(kind, name, 64)
        if name.value == klasse:
            treffer.append(kind)
            return False
        return True

    _user32.EnumChildWindows(eltern, besuch, 0)
    return treffer[0] if treffer else None


def _rechteck(fenster):
    r = _RECT()
    if not _user32.GetWindowRect(fenster, ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)


def taskleiste_platz():
    """Der freie Bereich in der Taskleiste, in echten Bildschirmpunkten.

    Gibt `(links, oben, rechts, unten)` zurueck oder None, wenn es ihn
    gerade nicht gibt: keine Taskleiste, zu wenig Platz, oder sie ist
    ausgeblendet und steht ausserhalb des Bildschirms.
    """
    leiste = _user32.FindWindowExW(None, None, "Shell_TrayWnd", None)
    if not leiste or not _user32.IsWindowVisible(leiste):
        return None
    aussen = _rechteck(leiste)
    if aussen is None:
        return None
    links, oben, rechts, unten = aussen
    # Eine eingefahrene Leiste steht fast vollstaendig unterhalb des
    # Bildschirms. Dann gibt es nichts anzuzeigen.
    hoehe = _user32.GetSystemMetrics(1)      # SM_CYSCREEN
    if oben >= hoehe - 2:
        return None
    # Senkrechte Leisten (links oder rechts am Rand) haben keinen Streifen
    # in dieser Form – dort ist nichts, was breit genug waere.
    if (rechts - links) < (unten - oben) * 3:
        return None

    symbole = _suchen(leiste, "MSTaskSwWClass")
    uhr = _user32.FindWindowExW(leiste, None, "TrayNotifyWnd", None)
    frei_links = links
    if symbole:
        r = _rechteck(symbole)
        if r:
            frei_links = max(frei_links, r[2])
    frei_rechts = rechts
    if uhr:
        r = _rechteck(uhr)
        if r:
            frei_rechts = min(frei_rechts, r[0])
    if frei_rechts - frei_links < MINDESTPLATZ:
        return None
    return (frei_links, oben, frei_rechts, unten)


def system_leiste_hell(_stand=[0.0, False]):
    """Ob die Taskleiste hell ist – nach dem Design von Windows, nicht dem
    von Volumix.

    Der Streifen liegt auf der Leiste von Windows. Wer Volumix auf Hell
    stellt, waehrend Windows dunkel bleibt, haette sonst dunkle Schrift auf
    dunkler Leiste. Windows fuehrt das getrennt: `SystemUsesLightTheme` gilt
    fuer Taskleiste und Infobereich, `AppsUseLightTheme` fuer die Fenster.

    Der Wert wird hoechstens alle drei Sekunden gelesen – er aendert sich
    selten, und der Streifen fragt oft.
    """
    jetzt = time.monotonic()
    if jetzt - _stand[0] < 3.0:
        return _stand[1]
    hell = False
    try:
        import winreg
        pfad = (r"Software\Microsoft\Windows\CurrentVersion"
                r"\Themes\Personalize")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, pfad) as schluessel:
            hell = bool(winreg.QueryValueEx(schluessel,
                                            "SystemUsesLightTheme")[0])
    except Exception:
        hell = False
    _stand[0], _stand[1] = jetzt, hell
    return hell


def _zeit(sekunden):
    sekunden = max(0, int(sekunden))
    return "{}:{:02d}".format(sekunden // 60, sekunden % 60)


class Zeitleiste(QWidget):
    """Titel, Interpret und Fortschritt – als Streifen in der Taskleiste."""

    def __init__(self, theme, parent=None):
        super().__init__(None)
        self.theme = theme
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                            | Qt.Tool | Qt.WindowTransparentForInput
                            | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._titel = ""
        self._interpret = ""
        self._dauer = 0.0
        self._stand = 0.0          # Position, wie zuletzt gemeldet
        self._gemeldet = 0.0       # wann das war (eigene Uhr)
        self._laeuft = False
        self._an = False           # ob der Nutzer den Streifen will
        self._farbe = None         # Coverfarbe, wenn eine da ist

        # Zwei Takte: Der Platz in der Taskleiste aendert sich selten, der
        # Balken laeuft dauernd.
        self._platz_takt = QTimer(self)
        self._platz_takt.setInterval(NACHZIEHEN)
        self._platz_takt.timeout.connect(self._platzieren)
        self._lauf_takt = QTimer(self)
        self._lauf_takt.setInterval(250)
        self._lauf_takt.timeout.connect(self.update)

    # ---- Aussenseite -----------------------------------------------------
    def anschalten(self, an):
        self._an = bool(an)
        if an:
            self._platzieren()
            self._platz_takt.start()
        else:
            self._platz_takt.stop()
            self._lauf_takt.stop()
            self.hide()

    def theme_wechseln(self, theme):
        self.theme = theme
        self.update()

    def titel_setzen(self, titel, interpret, farbe=None):
        self._titel = titel or ""
        self._interpret = interpret or ""
        self._farbe = farbe
        self.update()

    def zeit_setzen(self, position, dauer, laeuft):
        """Was Windows zuletzt gemeldet hat – der Rest wird hochgerechnet."""
        self._stand = max(0.0, float(position or 0.0))
        self._dauer = max(0.0, float(dauer or 0.0))
        self._gemeldet = time.monotonic()
        vorher = self._laeuft
        self._laeuft = bool(laeuft)
        if self._laeuft:
            self._lauf_takt.start()
        else:
            self._lauf_takt.stop()
        # Der Streifen zeigt, was laeuft. Haelt jemand an, hat er nichts mehr
        # zu sagen – und soll das sofort tun, nicht erst beim naechsten Takt.
        if vorher != self._laeuft and self._an:
            self._platzieren()
        self.update()

    def ist_live(self):
        """Ob gerade etwas laeuft, das kein Ende hat.

        Windows meldet fuer einen Livestream keine brauchbare Laenge –
        gemessen kam aus Chrome ein Ende von minus einem Tag. Die Position
        laeuft trotzdem mit und zaehlt, wie lange man schon zusieht. Beides
        zusammen, Position ohne Laenge, ist das Merkmal: Dann gibt es keinen
        Fortschritt, den ein Balken zeigen koennte, und statt der Restzeit
        steht dort „Live“.
        """
        return self._dauer <= 0 and self._stand > 0

    def position(self):
        """Wo der Titel jetzt steht, zwischen zwei Meldungen hochgerechnet."""
        if not self._laeuft:
            return self._stand
        weiter = self._stand + (time.monotonic() - self._gemeldet)
        return min(weiter, self._dauer) if self._dauer else weiter

    # ---- Platz in der Leiste ---------------------------------------------
    def _platzieren(self):
        platz = taskleiste_platz()
        # Pausiert heisst weg: Ein stehender Balken neben der Uhr behauptet
        # eine laufende Wiedergabe, die es gerade nicht gibt.
        if platz is None or not self._titel or not self._laeuft:
            if self.isVisible():
                self.hide()
                self._lauf_takt.stop()
            return
        links, oben, rechts, unten = platz
        # Win32 rechnet in echten Bildschirmpunkten, Qt in logischen.
        dpr = self.devicePixelRatioF() or 1.0
        schirm = self.screen()
        if schirm is not None:
            dpr = schirm.devicePixelRatio() or 1.0
        breite = min(BREITE, int((rechts - links) / dpr) - ABSTAND)
        hoehe = int((unten - oben) / dpr)
        x = int(rechts / dpr) - breite - ABSTAND
        y = int(oben / dpr)
        self.setGeometry(x, y, breite, hoehe)
        if not self.isVisible():
            self.show()
        self._nach_oben()
        if self._laeuft:
            self._lauf_takt.start()

    def _nach_oben(self):
        """Vor die Taskleiste holen. Gibt zurueck, ob es geklappt hat.

        Ein Klick in die Taskleiste holt sie nach vorn, und sie ist selbst
        immer oben – danach liegt sie ueber dem Streifen, und der scheint
        verschwunden zu sein. Deshalb wird die Reihenfolge im Takt erneuert.
        Ohne Aktivierung: Der Streifen darf niemals den Eingabefokus
        bekommen, sonst verliert ihn das Fenster, in dem gerade getippt wird.
        """
        griff = int(self.winId())
        if not griff:
            return False
        return bool(_user32.SetWindowPos(
            griff, _HWND_TOPMOST, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_NOOWNERZORDER))

    # ---- Zeichnen --------------------------------------------------------
    def _farben(self):
        """Schrift- und Bahnfarben – nach dem Design der Taskleiste.

        Nicht nach dem von Volumix: Der Streifen liegt auf der Leiste von
        Windows, und die folgt ihrer eigenen Einstellung. Nur der Balken
        nimmt die Farbe von Volumix – er ist kraeftig genug, um auf beiden
        Untergruenden zu stehen.
        """
        if system_leiste_hell():
            return (QColor(24, 24, 27), QColor(0, 0, 0, 185),
                    QColor(0, 0, 0, 140), QColor(0, 0, 0, 38),
                    QColor(196, 32, 42))
        return (QColor(255, 255, 255), QColor(255, 255, 255, 195),
                QColor(255, 255, 255, 150), QColor(255, 255, 255, 46),
                QColor(255, 106, 106))

    def paintEvent(self, e):
        """Titel fett, Interpret daneben, rechts Zeit oder Live-Kennzeichen.

        Die Taskleiste setzt ihre eigene Schrift in 12 px. Gleich grosser,
        gleich heller Text daneben sah aus wie ein zweiter Programmname –
        der Titel steht deshalb fett, der Rest gleich gross, aber ruhiger.
        Kleiner darf nichts davon sein: In einer Leiste von 48 Punkten Hoehe
        liest man 10 px nicht mehr im Vorbeigehen.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        breite, hoehe = self.width(), self.height()
        rand = 4.0
        bahn_hoehe = 3.0
        luft = 5.0
        vorn, neben, blass, bahn_farbton, live_farbe = self._farben()

        dick = glaettung(QFont(schrift()))
        dick.setPixelSize(12)
        dick.setWeight(QFont.Bold)
        duenn = glaettung(QFont(schrift()))
        duenn.setPixelSize(12)
        klein = glaettung(QFont(schrift()))
        klein.setPixelSize(11)
        mass_dick = QFontMetricsF(dick)
        mass_duenn = QFontMetricsF(duenn)
        mass_klein = QFontMetricsF(klein)

        dauer = self._dauer
        jetzt = self.position()
        live = self.ist_live()
        if live:
            rechts_text = T("live")
        elif dauer > 0:
            rechts_text = "{} / {}".format(_zeit(jetzt), _zeit(dauer))
        elif jetzt > 0:
            rechts_text = _zeit(jetzt)
        else:
            rechts_text = ""
        rechts_breite = (mass_klein.horizontalAdvance(rechts_text)
                         if rechts_text else 0.0)
        punkt = 6.0 if live else 0.0     # der Punkt vor „Live“
        rechts_voll = rechts_breite + (punkt + 5.0 if live else 0.0)

        zeile = max(mass_dick.height(), mass_duenn.height())
        # Ohne Balken steht der Text in der Mitte, mit Balken darueber.
        if live or dauer <= 0:
            oben_y = (hoehe - zeile) / 2.0
        else:
            oben_y = (hoehe - bahn_hoehe - luft - zeile) / 2.0
        raum = breite - 2 * rand - (rechts_voll + 10 if rechts_text else 0)

        titel = mass_dick.elidedText(self._titel, Qt.ElideRight,
                                     max(20.0, raum))
        titel_breite = mass_dick.horizontalAdvance(titel)
        p.setFont(dick)
        p.setPen(vorn)
        p.drawText(QRectF(rand, oben_y, titel_breite + 2, zeile),
                   Qt.AlignLeft | Qt.AlignVCenter, titel)

        rest = raum - titel_breite - 10
        if self._interpret and rest > 40:
            p.setFont(duenn)
            p.setPen(neben)
            name = mass_duenn.elidedText(self._interpret, Qt.ElideRight, rest)
            p.drawText(QRectF(rand + titel_breite + 10, oben_y, rest, zeile),
                       Qt.AlignLeft | Qt.AlignVCenter, name)

        if rechts_text:
            x = breite - rand - rechts_breite
            p.setFont(klein)
            p.setPen(live_farbe if live else blass)
            p.drawText(QRectF(x, oben_y, rechts_breite, zeile),
                       Qt.AlignRight | Qt.AlignVCenter, rechts_text)
            if live:
                p.setPen(Qt.NoPen)
                p.setBrush(live_farbe)
                mitte = oben_y + zeile / 2.0
                p.drawEllipse(QRectF(x - punkt - 5.0, mitte - punkt / 2.0,
                                     punkt, punkt))

        # Ein Livestream hat keinen Fortschritt: Ein Balken wuerde eine
        # Stelle im Titel behaupten, die es nicht gibt.
        if live or dauer <= 0:
            return
        bahn_y = oben_y + zeile + luft
        bahn = QRectF(rand, bahn_y, breite - 2 * rand, bahn_hoehe)
        p.setPen(Qt.NoPen)
        p.setBrush(bahn_farbton)
        p.drawRoundedRect(bahn, bahn_hoehe / 2.0, bahn_hoehe / 2.0)
        anteil = max(0.0, min(1.0, jetzt / dauer))
        voll = QRectF(bahn)
        voll.setWidth(bahn.width() * anteil)
        if voll.width() > bahn_hoehe:
            farbe = QColor(self._farbe or self.theme.accent)
            verlauf = QLinearGradient(voll.topLeft(), voll.topRight())
            verlauf.setColorAt(0.0, farbe.lighter(125))
            verlauf.setColorAt(1.0, farbe)
            p.setBrush(verlauf)
            p.drawRoundedRect(voll, bahn_hoehe / 2.0, bahn_hoehe / 2.0)
