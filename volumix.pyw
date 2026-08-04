# -*- coding: utf-8 -*-
"""
Volumix
=======
Lautstaerke-Mixer fuer einzelne Apps, gesteuert per Daumenrad oder
Lautstaerke-Tasten. Gebaut fuer die Logitech MX Master 4.

Oberflaeche: PySide6 (Qt). Audio: pycaw. Eingabe: pynput.
Autor: fuer Luis gebaut mit Claude Code.
"""
import ctypes
import sys
from ctypes import wintypes

# --- Nur eine Instanz; zweiter Start holt das vorhandene Fenster nach vorn ---
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateMutexW.restype = wintypes.HANDLE
_k32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_k32.OpenEventW.restype = wintypes.HANDLE
_k32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
_k32.CreateEventW.restype = wintypes.HANDLE
_k32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL,
                              wintypes.LPCWSTR]
_k32.SetEvent.argtypes = [wintypes.HANDLE]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.WaitForSingleObject.restype = wintypes.DWORD
_k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

_ERROR_ALREADY_EXISTS = 183
_EVENT_MODIFY_STATE = 0x0002
_SHOW_EVENT = "Volumix_ShowEvent"

_mutex = _k32.CreateMutexW(None, False, "Volumix_SingleInstance")
if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
    _h = _k32.OpenEventW(_EVENT_MODIFY_STATE, False, _SHOW_EVENT)
    if _h:
        _k32.SetEvent(_h)
        _k32.CloseHandle(_h)
    sys.exit(0)

# Per-Monitor-DPI: Qt zeichnet dann auf jedem Bildschirm in dessen echter
# Aufloesung, statt vom System hochgestreckt zu werden. Muss vor Qt passieren.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

import threading                                          # noqa: E402

from PySide6.QtCore import QTimer                          # noqa: E402
from PySide6.QtWidgets import QApplication                 # noqa: E402

from volumix.window import MainWindow                      # noqa: E402


def _auf_zweitstart_warten(fenster):
    """Zweiter Programmstart soll das Fenster nach vorn holen."""
    ereignis = _k32.CreateEventW(None, False, False, _SHOW_EVENT)

    def schleife():
        while True:
            if _k32.WaitForSingleObject(ereignis, 0xFFFFFFFF) == 0:
                QTimer.singleShot(0, fenster._nach_vorn)

    threading.Thread(target=schleife, daemon=True).start()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Volumix")
    app.setQuitOnLastWindowClosed(False)     # laeuft im Infobereich weiter


    fenster = MainWindow()
    _auf_zweitstart_warten(fenster)
    if "--tray" not in sys.argv:
        fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
