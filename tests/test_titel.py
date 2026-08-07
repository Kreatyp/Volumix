# -*- coding: utf-8 -*-
"""Mehrfachdruck auf der Wiedergabe-Taste – einmal, zweimal, dreimal.

Der Zaehler bekommt hier eine Attrappe statt eines echten Timers: So laesst
sich Zeit vergehen lassen, ohne wirklich zu warten, und der Test bleibt
schnell und zuverlaessig.
"""
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.hooks import (DRUCK_FENSTER, Mehrfachdruck,        # noqa: E402
                           VK_MEDIA_NEXT, VK_MEDIA_PLAY, VK_MEDIA_PREV,
                           VOLUMIX_MARKE, InputHook)

fehler = 0


def pruefe(name, ist, soll=True):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}".format("OK  " if ok else "FEHL", name))
    if not ok:
        print("       ist  {}\n       soll {}".format(ist, soll))


class FakeTimer:
    """Timer, der nur laeuft, wenn der Test ihn laufen laesst."""

    offen = []

    def __init__(self, sekunden, was):
        self.sekunden, self.was, self.tot = sekunden, was, False
        FakeTimer.offen.append(self)

    def start(self):
        pass

    def cancel(self):
        self.tot = True

    @classmethod
    def zeit_vergeht(cls):
        """Alle noch lebenden Timer ausloesen."""
        for t in list(cls.offen):
            if not t.tot:
                t.tot = True
                t.was()
        cls.offen.clear()


print("=== Zaehlen der Druecke ===")
gemeldet = []
z = Mehrfachdruck(gemeldet.append, timer=FakeTimer)

z.druck()
pruefe("ein Druck meldet noch nichts", gemeldet, [])
FakeTimer.zeit_vergeht()
pruefe("nach Ablauf: einmal", gemeldet, [1])

gemeldet.clear()
z.druck()
z.druck()
FakeTimer.zeit_vergeht()
pruefe("zwei Druecke zaehlen als zwei", gemeldet, [2])

gemeldet.clear()
z.druck()
z.druck()
z.druck()
FakeTimer.zeit_vergeht()
pruefe("drei Druecke zaehlen als drei", gemeldet, [3])

gemeldet.clear()
z.druck()
z.druck()
z.druck()
z.druck()
z.druck()
FakeTimer.zeit_vergeht()
pruefe("mehr als drei geht auch (zurueck)", gemeldet, [5])

print("\n=== Nichts bleibt haengen ===")
gemeldet.clear()
z.druck()
z.stop()
FakeTimer.zeit_vergeht()
pruefe("abgebrochen wird nichts gemeldet", gemeldet, [])
z.druck()
FakeTimer.zeit_vergeht()
pruefe("danach zaehlt er wieder von vorn", gemeldet, [1])

print("\n=== Welche Taste wird gesendet ===")
gesendet = []
hook = InputHook(on_scroll=lambda r: None, on_mute=lambda: None)
import volumix.hooks as h                                       # noqa: E402
echt = h.taste_senden
h.taste_senden = gesendet.append
try:
    hook._titel_schalten(1)
    hook._titel_schalten(2)
    hook._titel_schalten(3)
finally:
    h.taste_senden = echt
pruefe("einmal = Wiedergabe/Pause", gesendet[0], VK_MEDIA_PLAY)
pruefe("zweimal = naechster Titel", gesendet[1], VK_MEDIA_NEXT)
pruefe("dreimal = vorheriger Titel", gesendet[2], VK_MEDIA_PREV)

print("\n=== Der Hook faengt nur ab, was er soll ===")
from volumix.hooks import (VK_VOLUME_UP, VK_VOLUME_MUTE,        # noqa: E402
                           WM_KEYDOWN)

hook.titel_taste = False
pruefe("Wiedergabe unberuehrt, solange die Funktion aus ist",
       hook.taste_behandeln(VK_MEDIA_PLAY, WM_KEYDOWN), False)

hook.titel_taste = True
FakeTimer.offen.clear()
h.taste_senden = gesendet.append
gesendet.clear()
try:
    hook._druck = Mehrfachdruck(hook._titel_schalten, timer=FakeTimer)
    pruefe("Wiedergabe wird abgefangen",
           hook.taste_behandeln(VK_MEDIA_PLAY, WM_KEYDOWN), True)
    hook.taste_behandeln(VK_MEDIA_PLAY, WM_KEYDOWN)
    FakeTimer.zeit_vergeht()
    pruefe("zweimal gedrueckt = naechster Titel", gesendet, [VK_MEDIA_NEXT])

    # Genau der Fall, der mit dem Windows-Merkmal „injiziert“ schiefginge:
    # eine Taste, die Logi Options+ simuliert, traegt unser Zeichen nicht.
    gesendet.clear()
    FakeTimer.offen.clear()
    hook.taste_behandeln(VK_MEDIA_PLAY, WM_KEYDOWN, extra=0x11223344)
    FakeTimer.zeit_vergeht()
    pruefe("Taste von fremder Software zaehlt mit", gesendet, [VK_MEDIA_PLAY])

    gesendet.clear()
    FakeTimer.offen.clear()
    pruefe("unsere eigene Taste laeuft durch",
           hook.taste_behandeln(VK_MEDIA_PLAY, WM_KEYDOWN,
                                extra=VOLUMIX_MARKE), False)
    FakeTimer.zeit_vergeht()
    pruefe("und loest nichts aus", gesendet, [])
finally:
    h.taste_senden = echt

print("\n=== Lautstaerke-Tasten bleiben davon unberuehrt ===")
gerollt = []
hook2 = InputHook(on_scroll=gerollt.append, on_mute=lambda: None)
hook2.titel_taste = True
hook2.media_keys = False              # Lautstaerke haengt am Daumenrad
pruefe("Lauter-Taste nicht abgefangen",
       hook2.taste_behandeln(VK_VOLUME_UP, WM_KEYDOWN), False)
pruefe("und nicht ausgewertet", gerollt, [])
hook2.media_keys = True
hook2.hat_ziele = lambda: True
pruefe("mit Tastensteuerung dann schon",
       hook2.taste_behandeln(VK_VOLUME_UP, WM_KEYDOWN), True)
pruefe("und ausgewertet", gerollt, [1])
stumm = []
hook2.on_mute = lambda: stumm.append(True)
hook2.taste_behandeln(VK_VOLUME_MUTE, WM_KEYDOWN)
pruefe("Stumm-Taste wirkt weiter", stumm, [True])



# Die selbst gesendete Taste traegt unser Zeichen und muss durchgelassen
# werden – sonst laeuft der Hook im Kreis: senden -> abfangen -> senden.
# Eine simulierte Taste von fremder Software (etwa Logi Options+) traegt es
# nicht und wird ganz normal verarbeitet.
pruefe("eigenes Zeichen erkannt", VOLUMIX_MARKE == 0x564F4C58)
pruefe("Zeichen passt in ein Maschinenwort", VOLUMIX_MARKE < 2 ** 32)
print("  (Wartefenster: {} s)".format(DRUCK_FENSTER))
pruefe("Fenster hoechstens eine halbe Sekunde", DRUCK_FENSTER <= 0.5)
frisch = InputHook(on_scroll=lambda r: None, on_mute=lambda: None)
pruefe("Titelwechsel ab Werk aus", frisch.titel_taste, False)
from volumix import config                                      # noqa: E402
pruefe("und auch in den Voreinstellungen",
       config.DEFAULTS["titel_taste"], False)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
