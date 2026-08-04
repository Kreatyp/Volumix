# -*- coding: utf-8 -*-
"""Globale Eingabe: seitliches Daumenrad oder Lautstaerke-Tasten."""
from pynput import keyboard, mouse

WM_MOUSEHWHEEL = 0x020E
WHEEL_DELTA = 120
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF


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
        self.hat_ziele = lambda: False
        self._listener = None

    def start(self):
        self.stop()
        self._listener = (self._tasten_hook() if self.media_keys
                          else self._maus_hook())

    def richtung(self, rastungen):
        """Dreht die Richtung, wenn eingestellt – fuer beide Eingabearten."""
        return -rastungen if self.reverse else rastungen

    def stop(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

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

    # ---- Lautstaerke-Tasten ---------------------------------------------
    def _tasten_hook(self):
        halter = []

        def filter_(msg, data):
            vk = data.vkCode
            if vk not in (VK_VOLUME_UP, VK_VOLUME_DOWN, VK_VOLUME_MUTE):
                return True
            if not (self.aktiv and self.hat_ziele()):
                return True
            if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # Die Aktion muss HIER passieren: suppress_event() bricht die
                # Verarbeitung ab, ein on_press-Handler laeuft nie.
                if vk in (VK_VOLUME_UP, VK_VOLUME_DOWN):
                    # „Richtung umkehren“ gilt fuer beide Eingabearten –
                    # nicht nur fuers Rad, sonst wirkt der Schalter hier
                    # ins Leere.
                    self.on_scroll(self.richtung(
                        1 if vk == VK_VOLUME_UP else -1))
                else:
                    self.on_mute()
            if halter:
                halter[0].suppress_event()     # Windows-Regler nicht doppelt
            return True

        listener = keyboard.Listener(win32_event_filter=filter_)
        halter.append(listener)
        listener.start()
        return listener
