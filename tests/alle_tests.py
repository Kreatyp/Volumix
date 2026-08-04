# -*- coding: utf-8 -*-
"""Fuehrt alle Tests nacheinander aus und fasst das Ergebnis zusammen.

Aufruf:
    python tests\\alle_tests.py

Die Tests starten jeweils ein eigenes Fenster und benutzen eine eigene
Einstellungsdatei unter tests\\testcfg – deine echten Einstellungen bleiben
unberuehrt. Manche spielen kurz einen leisen Testton, damit die Pegelanzeige
etwas zu messen hat.
"""
import glob
import os
import subprocess
import sys
import time

TESTS = os.path.dirname(os.path.abspath(__file__))


def main():
    dateien = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    if not dateien:
        print("Keine Tests gefunden.")
        return 1

    breite = max(len(os.path.basename(d)) for d in dateien)
    ergebnisse = []
    start = time.perf_counter()

    for datei in dateien:
        name = os.path.basename(datei)
        print("{}  läuft …".format(name.ljust(breite)), end="", flush=True)
        t0 = time.perf_counter()
        lauf = subprocess.run([sys.executable, datei],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        dauer = time.perf_counter() - t0
        ok = lauf.returncode == 0
        ergebnisse.append((name, ok, lauf.stdout or "", lauf.stderr or ""))
        print("\r{}  {}  ({:.1f} s)".format(
            name.ljust(breite), "OK  " if ok else "FEHLER", dauer))

    print("\n" + "=" * 60)
    fehler = [e for e in ergebnisse if not e[1]]
    if fehler:
        for name, _, ausgabe, fehlertext in fehler:
            print("\n--- {} ---".format(name))
            for zeile in ausgabe.splitlines():
                if "FEHL" in zeile:
                    print("  " + zeile.strip())
            if fehlertext.strip():
                print("  " + fehlertext.strip().splitlines()[-1])
        print("\n{} von {} Testreihen fehlgeschlagen.".format(
            len(fehler), len(ergebnisse)))
    else:
        print("Alle {} Testreihen grün  ({:.0f} s gesamt).".format(
            len(ergebnisse), time.perf_counter() - start))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
