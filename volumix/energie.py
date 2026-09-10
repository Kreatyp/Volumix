# -*- coding: utf-8 -*-
"""Schlafen und Aufwachen des Rechners mitbekommen.

Windows schickt `WM_POWERBROADCAST` an alle Fenster der obersten Ebene –
auch an versteckte, Volumix bekommt es also im Infobereich ebenso. Qt
reicht solche Botschaften nur ueber einen `QAbstractNativeEventFilter`
heraus; die Struktur dahinter muss man sich selbst aus dem Zeiger holen.

Wichtig ist, was beim Einschlafen passiert: Windows wartet danach nicht
lange. Was dort getan werden soll, muss sofort geschehen und darf nicht in
einer Warteschlange landen, deren Thread gleich mit eingefroren wird.
"""
import ctypes
import time
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter

WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007      # Aufwachen nach einem Schlafbefehl
PBT_APMRESUMEAUTOMATIC = 0x0012    # Aufwachen ohne Zutun des Benutzers


class _MSG(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", ctypes.c_size_t),
                ("lParam", ctypes.c_ssize_t),
                ("time", wintypes.DWORD),
                ("pt_x", wintypes.LONG),
                ("pt_y", wintypes.LONG)]


class Energiewacht(QAbstractNativeEventFilter):
    """Meldet Einschlafen und Aufwachen ueber zwei Rueckrufe.

    Beide werden im Oberflaechen-Thread gerufen. Was beim Einschlafen darin
    geschieht, haelt Windows kurz auf – also nur Kurzes, mit Zeitgrenze.
    """

    # Windows schickt die Botschaft an *jedes* Fenster der obersten Ebene.
    # Volumix hat mehrere – Hauptfenster, Einblendung, Erklaerblasen –, der
    # Rueckruf kaeme also mehrfach. Gemessen: fuenf Mal fuer einen Rundruf.
    ENTPRELLUNG = 5.0

    def __init__(self, on_schlafen=None, on_wecken=None):
        super().__init__()
        self.on_schlafen = on_schlafen
        self.on_wecken = on_wecken
        self._zuletzt = (None, 0.0)

    # `message` steht in der Struktur direkt hinter `hwnd`.
    _VERSATZ = ctypes.sizeof(wintypes.HWND)

    def nativeEventFilter(self, art, zeiger):
        """Laeuft fuer *jede* Windows-Botschaft des Programms.

        Deshalb so frueh wie moeglich aussteigen und nur die Nummer lesen,
        statt die ganze Struktur nachzubauen: Maus, Tastatur, Zeichnen –
        alles kommt hier vorbei, und das Zusammensetzen einer
        ctypes-Struktur je Botschaft ist dafuer zu teuer.
        """
        if art != b"windows_generic_MSG":
            return False, 0
        try:
            adresse = int(zeiger)
            nummer = ctypes.c_uint.from_address(adresse + self._VERSATZ).value
            if nummer != WM_POWERBROADCAST:
                return False, 0
            msg = _MSG.from_address(adresse)
        except Exception:
            return False, 0
        self.melden(msg.wParam)
        # Immer durchlassen: Diese Botschaft geht auch andere etwas an.
        return False, 0

    def melden(self, wParam):
        """Getrennt vom Filter, damit Tests sie ohne Fenster ausloesen."""
        if wParam == PBT_APMSUSPEND:
            was, rueckruf = "schlafen", self.on_schlafen
        elif wParam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
            was, rueckruf = "wecken", self.on_wecken
        else:
            return
        jetzt = time.monotonic()
        letztes, wann = self._zuletzt
        if letztes == was and jetzt - wann < self.ENTPRELLUNG:
            return
        self._zuletzt = (was, jetzt)
        if rueckruf:
            rueckruf()
