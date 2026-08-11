# -*- coding: utf-8 -*-
"""Lautstaerke angleichen – die Regelung an gestellten Verlaeufen.

Geprueft wird nicht nur, dass sie regelt, sondern vor allem, was sie NICHT
tun darf: ueber 100 % hinauswollen, in Pausen hochziehen, die Betonungen
innerhalb eines Sprechers einebnen oder beim Abschalten etwas verstellt
zuruecklassen.

Wichtig fuer das Verstaendnis der Attrappe: Der Pegelmesser von Windows
zeigt den Ton VOR dem Regler. Was die Regelung setzt, aendert die Messung
also nicht – nachgemessen an einer echten Sitzung, siehe audio.py.
"""
import math
import os
import random
import statistics as st
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.audio import AudioEngine                          # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


class FakeSav:
    """Ein Lautstaerkeregler, wie Windows ihn fuer eine App fuehrt."""

    def __init__(self, amp=1.0):
        self.amp = amp

    def GetMasterVolume(self):
        return self.amp

    def SetMasterVolume(self, v, _):
        self.amp = float(v)


def bauen(nutzer=0.8):
    e = AudioEngine.__new__(AudioEngine)
    e.angleichen = set()
    e._nutzer_amp, e._daempfung = {}, {}
    e._kurz, e._bezug = {}, {}
    e.gamma = 1.7
    sav = FakeSav(nutzer)
    e._by_key = lambda max_alter=2.0: {"app.exe": [sav]}
    e._peaks_wert = 0.0
    e._peaks = lambda max_alter=2.0, roh=False: {"app.exe": e._peaks_wert}
    return e, sav


def laufen(e, pegel, takte):
    """`takte` Durchgaenge mit diesem Ausgangspegel."""
    for _ in range(takte):
        e._peaks_wert = pegel
        e._angleichen_regeln()


def db(x):
    return 20.0 * math.log10(max(x, 1e-6))


def gespraech(dauer=300.0, saat=7):
    """(Sprecher, roher Spitzenpegel) im 50-ms-Takt.

    Drei Sprecher mit sehr verschiedenem Pegel, jeder mit Silben und
    Atempausen. Die Silbenstruktur ist der Grund, warum die Regelung nicht
    einfach auf die Messung losgehen darf.
    """
    takt = 0.05
    r = random.Random(saat)
    sprecher = [("laut", 0.62), ("mittel", 0.22), ("leise", 0.075)]
    reihe, t, wer = [], 0.0, 0
    while t < dauer:
        name, grund = sprecher[wer % 3]
        bis = t + r.uniform(3.5, 6.0)
        while t < bis and t < dauer:
            if r.random() < 0.10:
                fuer = r.uniform(0.2, 0.6)
                while t < min(bis, dauer) and fuer > 0:
                    reihe.append((name, 0.002))
                    t += takt
                    fuer -= takt
                continue
            laut = grund * r.uniform(0.45, 1.0)
            n = max(1, int(r.uniform(0.15, 0.35) / takt))
            for i in range(n):
                h = math.sin(math.pi * (i + 0.5) / n) ** 0.6
                reihe.append((name, max(0.002, laut * h)))
                t += takt
        wer += 1                    # der naechste ist dran
    return reihe


print("=== Am gestellten Gespraech ===")
e, sav = bauen(nutzer=0.5)
e.angleichen_setzen("app.exe", True)
reihe = gespraech()
verlauf = []
for wer, p in reihe:
    e._peaks_wert = p
    e._angleichen_regeln()
    verlauf.append((wer, p, p * sav.amp))

# Die ersten 30 Sekunden lernt die Regelung den Bezugspegel – erst danach
# ist ein Vergleich fair.
gesagt = [(w, v, n) for w, v, n in verlauf[600:] if v > 0.02]
vor, nach = {}, {}
for w, v, n in gesagt:
    vor.setdefault(w, []).append(v)
    nach.setdefault(w, []).append(n)


def spanne(m):
    mittel = [db(st.mean(m[w])) for w in m]
    return max(mittel) - min(mittel)


def spitzen(m):
    """Wie weit eine betonte Silbe ueber dem Mittelmass liegt, in dB.

    Die Streuung ueber alle Takte taugt dafuer nicht: Sie wird von den
    vielen leisen Silbenflanken beherrscht und bleibt fast gleich, auch
    wenn die Regelung jede Betonung wegbuegelt. Der Abstand vom oberen
    Ende zur Mitte zeigt es dagegen sofort.
    """
    aus = []
    for w in m:
        werte = sorted(db(x) for x in m[w])
        oben = werte[min(len(werte) - 1, int(len(werte) * 0.95))]
        mitte = werte[len(werte) // 2]
        aus.append(oben - mitte)
    return st.mean(aus)


sv, sn = spanne(vor), spanne(nach)
dv, dn = spitzen(vor), spitzen(nach)
print("  Sprecher untereinander: {:.1f} dB -> {:.1f} dB".format(sv, sn))
print("  Betonungen im Sprecher: {:.1f} dB -> {:.1f} dB".format(dv, dn))
pruefe("Unterschied zwischen Sprechern deutlich kleiner", sn < sv * 0.6, True,
       "{:.1f} statt {:.1f} dB".format(sn, sv))
# Ueber mehrere Gespraeche gemessen liegt das Verhaeltnis mit geglaetteter
# Messung bei 1,11 bis 1,15, ohne Glaettung bei 0,84 bis 0,87 – die Grenze
# bei 1,0 trennt beides mit Abstand.
pruefe("Betonungen bleiben erhalten", dn > dv, True,
       "{:.1f} gegen {:.1f} dB".format(dn, dv))

print("\n=== Nie ueber 100 Prozent ===")
e, sav = bauen(nutzer=0.9)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.5, 200)          # laut einlernen
laufen(e, 0.01, 100)         # dann sehr leise – hier will es hochziehen
laufen(e, 0.05, 400)
pruefe("Regler bleibt im erlaubten Bereich", sav.amp <= 1.0 + 1e-9, True,
       "ist {:.3f}".format(sav.amp))

print("\n=== Auf 100 Prozent bleibt nur Daempfen ===")
e, sav = bauen(nutzer=1.0)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.1, 300)
pruefe("nichts angehoben, weil kein Platz da ist", round(sav.amp, 4), 1.0)

print("\n=== Laute Stelle wird gedaempft ===")
e, sav = bauen(nutzer=0.6)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.1, 400)          # so laut ist die App ueblicherweise
laufen(e, 0.8, 60)           # und jetzt schreit jemand
pruefe("gedaempft", e._daempfung["app.exe"] < 0.9, True,
       "Faktor {:.2f}".format(e._daempfung["app.exe"]))
pruefe("aber nie unter die Untergrenze",
       e._daempfung["app.exe"] >= e.ANGLEICH_TIEFSTENS, True)
pruefe("gesetzt wird Nutzerpegel mal Faktor", round(sav.amp, 3),
       round(0.6 * e._daempfung["app.exe"], 3))

print("\n=== Pausen bleiben unberuehrt ===")
e, sav = bauen(nutzer=0.8)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.3, 200)
laufen(e, 0.9, 30)
stand = e._daempfung["app.exe"]
laufen(e, 0.0, 200)          # Stille
pruefe("Stille aendert nichts", round(e._daempfung["app.exe"], 4),
       round(stand, 4))
pruefe("und zieht den Bezugspegel nicht mit", e._bezug["app.exe"] > 0.05)

print("\n=== Abschalten stellt zurueck ===")
e, sav = bauen(nutzer=0.75)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.2, 200)
laufen(e, 0.95, 80)
pruefe("waehrenddessen leiser", sav.amp < 0.75, True,
       "{:.3f}".format(sav.amp))
e.angleichen_setzen("app.exe", False)
pruefe("danach wieder genau der eingestellte Wert", round(sav.amp, 4), 0.75)
pruefe("nichts bleibt haengen",
       any(k in d for d in (e._nutzer_amp, e._daempfung, e._kurz, e._bezug)
           for k in ("app.exe",)), False)

print("\n=== Leiser geht schneller als lauter ===")
# Sonst schreit es bei jeder lauten Stelle kurz auf, oder es pumpt in
# Sprechpausen wieder hoch.
#
# Beide Richtungen bekommen denselben Weg von 0,5, sonst vergleicht man
# Strecken statt Geschwindigkeiten: einmal von 1,0 nach unten, einmal von
# 0,5 zurueck nach oben.
e, _ = bauen(nutzer=0.5)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.2, 300)
e._daempfung["app.exe"] = 1.0
laufen(e, 0.4, 3)                   # doppelt so laut -> Ziel geht auf 0,5
runter = 1.0 - e._daempfung["app.exe"]

e2, _ = bauen(nutzer=0.5)
e2.angleichen_setzen("app.exe", True)
laufen(e2, 0.2, 300)
e2._daempfung["app.exe"] = 0.5
laufen(e2, 0.2, 3)                  # unveraendert leise -> Ziel ist 1,0
hoch = e2._daempfung["app.exe"] - 0.5
pruefe("nach unten deutlich flotter", runter > hoch * 1.8, True,
       "{:.3f} gegen {:.3f}".format(runter, hoch))

print("\n=== Ein gleichmaessiger Ton wird in Ruhe gelassen ===")
# Musik mit konstantem Pegel darf nicht wandern – sonst hoert man ein Atmen.
e, sav = bauen(nutzer=0.6)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.4, 600)
pruefe("Regler steht praktisch still", abs(sav.amp - 0.6) < 0.02, True,
       "{:.3f}".format(sav.amp))

print("\n=== Von Hand gestellter Wert wird uebernommen ===")
e, sav = bauen(nutzer=0.8)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.5, 200)
e._nutzer_amp["app.exe"] = 0.4          # so, wie es der Auftrag „setvol“ tut
laufen(e, 0.5, 200)
pruefe("Regelung haengt am neuen Wert", abs(sav.amp - 0.4) < 0.05, True,
       "ist {:.3f}".format(sav.amp))

print("\n=== Stummgeschaltet passiert nichts ===")
e, sav = bauen(nutzer=0.0)
e.angleichen_setzen("app.exe", True)
laufen(e, 0.5, 100)
pruefe("bleibt auf null", round(sav.amp, 4), 0.0)

print("\n=== Ohne eingeschaltete Apps passiert nichts ===")
e, sav = bauen(nutzer=0.9)
laufen(e, 0.95, 30)
pruefe("Pegel unveraendert", round(sav.amp, 4), 0.9)

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
