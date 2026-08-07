# -*- coding: utf-8 -*-
"""Der kurze Ton, wenn der Regler oben ankommt.

Gespielt wird ueber `winsound` – das steckt in Python selbst und braucht
weder Qt-Multimedia noch eine weitere Bibliothek. Der Ton laeuft nebenher;
der Aufruf kehrt sofort zurueck und haelt den Audio-Thread nicht auf.
"""
import os
import threading
import time

from . import config

DATEI = "anschlag.wav"

# Kuerzeste Pause zwischen zwei Toenen. Wer am Anschlag hin und her wackelt,
# soll kein Geklapper ausloesen.
SPERRE = 0.4

_zuletzt = 0.0
_schloss = threading.Lock()
_pfad = None


def pfad():
    global _pfad
    if _pfad is None:
        _pfad = config.paket_pfad("toene", DATEI)
    return _pfad


def anschlag():
    """Einmal anschlagen – oder schweigen, wenn es zu kurz her ist."""
    global _zuletzt
    with _schloss:
        jetzt = time.monotonic()
        if jetzt - _zuletzt < SPERRE:
            return False
        _zuletzt = jetzt
    return spielen(pfad())


def spielen(datei):
    """Eine Klangdatei abspielen. Faellt still aus, wenn etwas fehlt –
    ein fehlender Ton darf das Regeln nicht aufhalten."""
    try:
        import winsound
        if not os.path.exists(datei):
            return False
        winsound.PlaySound(datei, winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_NODEFAULT)
        return True
    except Exception:
        return False


def zuruecksetzen():
    """Sperre aufheben – fuer Tests."""
    global _zuletzt
    _zuletzt = 0.0
