# -*- coding: utf-8 -*-
"""
Volumix
=======
Lautstaerke-Mixer fuer einzelne Apps, gesteuert per Daumenrad oder
Lautstaerke-Tasten.

Oberflaeche: PySide6 (Qt). Audio: pycaw. Eingabe: pynput.
"""
import ctypes
import os
import sys
import time
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

def _sperre_holen():
    """Die Einzelinstanz-Sperre nehmen – beim Neustart mit Geduld.

    Startet Volumix sich selbst neu (geaenderte Groesse), laeuft die alte
    Instanz noch, waehrend die neue schon hochfaehrt. Ohne Warten haelt die
    neue sich fuer die ueberfluessige zweite und beendet sich sofort – aus
    dem Neustart wuerde ein Beenden.

    Bewusst hier und nicht in der alten Instanz: Die muesste ihre Sperre
    dafuer vorher loslassen, und ob das in der gepackten App zuverlaessig
    gelingt, haengt an Dingen, die man nicht in der Hand hat. Warten kann
    die neue Instanz immer.
    """
    frist = 8.0 if "--neustart" in sys.argv else 0.0
    ende = time.monotonic() + frist
    while True:
        griff = _k32.CreateMutexW(None, False, "Volumix_SingleInstance")
        if ctypes.get_last_error() != _ERROR_ALREADY_EXISTS:
            return griff
        _k32.CloseHandle(griff)
        if time.monotonic() >= ende:
            return None
        time.sleep(0.2)


_mutex = _sperre_holen()


def mutex_freigeben():
    """Die Sperre loslassen – vor einem selbst ausgeloesten Neustart.

    Ohne das sieht die neue Instanz die alte noch, haelt sich fuer die
    zweite und beendet sich sofort wieder.
    """
    try:
        _k32.CloseHandle(_mutex)
    except Exception:
        pass
if _mutex is None:
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

from volumix import config                                 # noqa: E402

# Die Groesse der Oberflaeche muss feststehen, bevor Qt hochfaehrt –
# danach laesst sie sich nicht mehr aendern. Deshalb hier, vor dem
# ersten Fenster und vor der QApplication.
_skala = 100
try:
    _skala = int(config.load().get('skala', 100))
except Exception:
    pass
# Immer setzen, auch bei 100 %. Beim selbst ausgeloesten Neustart erbt die
# neue Instanz die Umgebung der alten – stuende dort noch der alte Faktor und
# wir setzten ihn nur bei Abweichung, kaeme man von 115 nie wieder auf 100.
os.environ['QT_SCALE_FACTOR'] = '%.4g' % (max(50, min(200, _skala)) / 100)

from volumix.window import MainWindow                      # noqa: E402

def _fehler_festhalten():
    """Unbehandelte Fehler in eine Datei schreiben.

    Die App laeuft ohne Konsole. Ohne das hier geht jede Meldung ins Nichts –
    und ein Programm, das sich stumm schliesst, laesst sich hinterher nicht
    mehr untersuchen.

    Zwei Dateien, mit Absicht:

    `fehler.log` haelt fest, was wirklich zaehlt – wann die App lief, wann
    sie beendet wurde, und jeden Python-Fehler mit vollem Weg.

    `absturz.log` bekommt der `faulthandler`, der auch Abstuerze unterhalb
    von Python sieht. Er meldet allerdings jede Windows-Ausnahme, auch die
    ordnungsgemaess behandelten: Schon das blosse Oeffnen eines Fensters
    erzeugt eine (0x8001010D). Stuenden beide in derselben Datei, ginge die
    eine echte Meldung in diesem Rauschen unter.
    """
    import datetime
    import faulthandler
    import os
    import traceback
    try:
        os.makedirs(config.CONFIG_DIR, exist_ok=True)
        for name in (config.PROTOKOLL, config.ABSTURZ):
            pfad = config.protokoll_pfad(name)
            if (os.path.exists(pfad)
                    and os.path.getsize(pfad) > config.PROTOKOLL_GRENZE):
                os.remove(pfad)
        datei = open(config.protokoll_pfad(), "a", encoding="utf-8",
                     buffering=1)
        tief = open(config.protokoll_pfad(config.ABSTURZ), "a",
                    encoding="utf-8", buffering=1)
    except Exception:
        return
    faulthandler.enable(tief)

    def schreiben(art, wert, spur):
        try:
            datei.write("\n=== FEHLER {} ===\n".format(
                datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")))
            traceback.print_exception(art, wert, spur, file=datei)
        except Exception:
            pass

    sys.excepthook = schreiben
    threading.excepthook = lambda a: schreiben(a.exc_type, a.exc_value,
                                               a.exc_traceback)
    config.notiz("gestartet")


def _auf_zweitstart_warten(fenster):
    """Zweiter Programmstart soll das Fenster nach vorn holen."""
    ereignis = _k32.CreateEventW(None, False, False, _SHOW_EVENT)

    def schleife():
        while True:
            if _k32.WaitForSingleObject(ereignis, 0xFFFFFFFF) == 0:
                QTimer.singleShot(0, fenster._nach_vorn)

    threading.Thread(target=schleife, daemon=True).start()


def main():
    _fehler_festhalten()
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
