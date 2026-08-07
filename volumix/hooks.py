# -*- coding: utf-8 -*-
"""Globale Eingabe: seitliches Daumenrad oder Lautstaerke-Tasten."""
import ctypes
import threading

from pynput import keyboard, mouse

WM_MOUSEHWHEEL = 0x020E
WHEEL_DELTA = 120
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF
VK_MEDIA_NEXT, VK_MEDIA_PREV, VK_MEDIA_PLAY = 0xB0, 0xB1, 0xB3

KEYEVENTF_KEYUP = 0x0002

# Erkennungszeichen fuer selbst gesendete Tasten. Ohne das faengt der eigene
# Hook die gerade gesendete Taste sofort wieder ab – eine Schleife, aus der
# niemand herauskommt.
#
# Es gaebe auch das Windows-Merkmal „injiziert“, aber das traegt jede
# simulierte Taste: Wer eine Maustaste in Logi Options+ auf Wiedergabe legt,
# wuerde damit gleich mit ausgesperrt. Ein eigenes Zeichen trifft genau uns.
VOLUMIX_MARKE = 0x564F4C58          # "VOLX"

# Wie lange auf einen weiteren Druck gewartet wird
DRUCK_FENSTER = 0.35

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte,
                                ctypes.c_uint32, ctypes.c_void_p]


def taste_senden(vk):
    """Eine Medientaste ans System schicken, mit unserem Zeichen daran."""
    _user32.keybd_event(vk, 0, 0, VOLUMIX_MARKE)
    _user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, VOLUMIX_MARKE)


class Mehrfachdruck:
    """Zaehlt Druecke innerhalb eines Zeitfensters.

    Wie bei Kopfhoerern: einmal, zweimal, dreimal – jedes Mal etwas anderes.
    Der Preis dafuer ist unvermeidbar: Erst wenn das Fenster ohne weiteren
    Druck verstrichen ist, steht fest, was gemeint war. Auch ein einzelner
    Druck wirkt deshalb erst danach.

    `melden(anzahl)` laeuft im Timer-Thread.
    """

    def __init__(self, melden, fenster=DRUCK_FENSTER, timer=threading.Timer):
        self.melden = melden
        self.fenster = fenster
        self._timer_bauen = timer
        self._zaehler = 0
        self._timer = None
        self._schloss = threading.Lock()

    def druck(self):
        with self._schloss:
            self._zaehler += 1
            if self._timer is not None:
                self._timer.cancel()
            self._timer = self._timer_bauen(self.fenster, self._ablauf)
            self._timer.daemon = True
            self._timer.start()

    def _ablauf(self):
        with self._schloss:
            anzahl, self._zaehler, self._timer = self._zaehler, 0, None
        if anzahl:
            self.melden(anzahl)

    def stop(self):
        with self._schloss:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._zaehler = 0


def _delta(mouse_data):
    """Oberes Wort von mouseData als vorzeichenbehaftete Zahl."""
    d = (mouse_data >> 16) & 0xFFFF
    return d - 0x10000 if d > 0x7FFF else d


class InputHook:
    """Greift die Eingabe systemweit ab.

    `on_scroll(rastungen)` bekommt +1/-1 je Rastung, `on_mute()` den Wunsch
    stumm zu schalten. Beide laufen im Hook-Thread – die Oberflaeche muss das
    ueber ein Signal in ihren eigenen Thread weiterreichen.
    """

    def __init__(self, on_scroll, on_mute, on_gesehen=None):
        self.on_scroll = on_scroll
        self.on_mute = on_mute
        self.on_gesehen = on_gesehen
        self.aktiv = True
        self.reverse = False
        self.media_keys = False
        self.titel_taste = False        # Mehrfachdruck auf Wiedergabe/Pause
        self.hat_ziele = lambda: False
        self._listener = None
        self._tasten = None
        self._druck = Mehrfachdruck(self._titel_schalten)

    def start(self):
        self.stop()
        # Der Tastatur-Hook wird fuer zweierlei gebraucht und laeuft deshalb
        # auch dann, wenn die Lautstaerke am Daumenrad haengt.
        if self.media_keys or self.titel_taste:
            self._tasten = self._tasten_hook()
        if not self.media_keys:
            self._listener = self._maus_hook()

    def richtung(self, rastungen):
        """Dreht die Richtung, wenn eingestellt – fuer beide Eingabearten."""
        return -rastungen if self.reverse else rastungen

    def _titel_schalten(self, anzahl):
        """Was nach dem Zaehlen passiert – wie bei Kopfhoerern.

        Einmal bleibt Wiedergabe/Pause. Da wir die Taste abgefangen haben,
        muessen wir sie hier selbst nachreichen.
        """
        if anzahl == 1:
            taste_senden(VK_MEDIA_PLAY)
        elif anzahl == 2:
            taste_senden(VK_MEDIA_NEXT)
        else:
            taste_senden(VK_MEDIA_PREV)

    def stop(self):
        self._druck.stop()
        for name in ("_listener", "_tasten"):
            hoerer = getattr(self, name, None)
            if hoerer is not None:
                try:
                    hoerer.stop()
                except Exception:
                    pass
                setattr(self, name, None)

    # ---- Daumenrad (horizontales Scrollen) -------------------------------
    def _maus_hook(self):
        # pynput erwartet eine Funktion mit (msg, data). Fuer suppress_event()
        # brauchen wir den Listener – deshalb die Umleitung ueber die Liste.
        halter = []

        def filter_(msg, data):
            if msg != WM_MOUSEHWHEEL:
                return True
            d = _delta(data.mouseData)
            if d:
                if self.on_gesehen:
                    self.on_gesehen()
                if self.aktiv and self.hat_ziele():
                    self.on_scroll(self.richtung(d / WHEEL_DELTA))
                    # Nur schlucken, wenn wir es auch benutzen – sonst verliert
                    # der Nutzer das seitliche Scrollen ganz.
                    if halter:
                        halter[0].suppress_event()
            return True

        listener = mouse.Listener(win32_event_filter=filter_)
        halter.append(listener)
        listener.start()
        return listener

    # ---- Tastatur --------------------------------------------------------
    def taste_behandeln(self, vk, msg, extra=0):
        """Entscheidet ueber einen Tastendruck.

        Liefert True, wenn Volumix ihn benutzt hat – dann darf Windows ihn
        nicht auch noch sehen, sonst wirkt alles doppelt.

        Die Aktion passiert HIER und nicht in einem on_press-Handler:
        suppress_event() bricht die Verarbeitung ab, ein Handler liefe nie.
        """
        # Was wir selbst gesendet haben, muss durch – sonst faengt der Hook
        # seine eigene Taste ab und zaehlt endlos weiter.
        if extra == VOLUMIX_MARKE:
            return False
        gedrueckt = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)
        if vk == VK_MEDIA_PLAY:
            if not self.titel_taste:
                return False
            if gedrueckt:
                self._druck.druck()
            return True
        if vk not in (VK_VOLUME_UP, VK_VOLUME_DOWN, VK_VOLUME_MUTE):
            return False
        if not (self.media_keys and self.aktiv and self.hat_ziele()):
            return False
        if gedrueckt:
            if vk in (VK_VOLUME_UP, VK_VOLUME_DOWN):
                # „Richtung umkehren“ gilt fuer beide Eingabearten – nicht
                # nur fuers Rad, sonst wirkt der Schalter hier ins Leere.
                self.on_scroll(self.richtung(1 if vk == VK_VOLUME_UP else -1))
            else:
                self.on_mute()
        return True

    def _tasten_hook(self):
        halter = []

        def filter_(msg, data):
            if self.taste_behandeln(data.vkCode, msg, data.dwExtraInfo):
                if halter:
                    halter[0].suppress_event()
            return True

        listener = keyboard.Listener(win32_event_filter=filter_)
        halter.append(listener)
        listener.start()
        return listener
