# -*- coding: utf-8 -*-
"""Die Meldeschnittstelle nach aussen.

Geprueft wird vor allem, was sie NICHT darf: von aussen erreichbar sein,
Befehle entgegennehmen, das Symbol bei jeder Rastung erneut schicken, oder
die App aufhalten, wenn niemand zuhoert.
"""
import json
import os
import socket
import sys
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
_PROJEKT = os.path.dirname(_TESTS)
sys.path.insert(0, _PROJEKT)

from volumix.melder import Melder, FASSUNG                      # noqa: E402

fehler = 0


def pruefe(name, ist, soll=True, zusatz=""):
    global fehler
    ok = ist == soll
    fehler += 0 if ok else 1
    print("  {} {}{}".format("OK  " if ok else "FEHL", name,
                             "  " + zusatz if zusatz else ""))
    if not ok:
        print("       ist {}  soll {}".format(ist, soll))


def zeilen_lesen(sock, wieviele, frist=2.0):
    """`wieviele` JSON-Zeilen einsammeln."""
    sock.settimeout(frist)
    puffer, aus = b"", []
    ende = time.time() + frist
    while len(aus) < wieviele and time.time() < ende:
        try:
            teil = sock.recv(65536)
        except socket.timeout:
            break
        if not teil:
            break
        puffer += teil
        while b"\n" in puffer:
            zeile, puffer = puffer.split(b"\n", 1)
            if zeile.strip():
                aus.append(json.loads(zeile.decode("utf-8")))
    return aus


PORT = 48799          # eigener Port, damit ein laufendes Volumix nicht stoert

print("=== Ohne Zuhoerer laeuft alles weiter ===")
m = Melder(port=PORT)
pruefe("startet", m.starten())
start = time.perf_counter()
for i in range(200):
    m.melden("app.exe", "App", i % 100, symbol_png=b"x" * 4096)
dauer = time.perf_counter() - start
pruefe("200 Meldungen ins Leere kosten fast nichts", dauer < 0.25, True,
       "{:.0f} ms".format(dauer * 1000))

print("\n=== Zuhoerer bekommt Begruessung und Meldungen ===")
c = socket.create_connection(("127.0.0.1", PORT), timeout=2)
hallo = zeilen_lesen(c, 1)
pruefe("begruesst mit Fassungsnummer",
       bool(hallo) and hallo[0].get("fassung") == FASSUNG)
time.sleep(0.1)
m.melden("discord.exe", "Discord", 57, stumm=False, akzent="#7C5CFF")
daten = zeilen_lesen(c, 1)
pruefe("Meldung kommt an", bool(daten))
if daten:
    d = daten[0]
    pruefe("mit App, Name und Prozent",
           (d.get("app"), d.get("name"), d.get("prozent")),
           ("discord.exe", "Discord", 57))
    pruefe("Stummschaltung steht drin", d.get("stumm"), False)
    pruefe("Akzentfarbe steht drin", d.get("farbe"), "#7C5CFF")

print("\n=== Das Symbol geht nur einmal je App ===")
m.melden("spotify.exe", "Spotify", 40, symbol_png=b"PNGDATEN")
erste = zeilen_lesen(c, 1)
m.melden("spotify.exe", "Spotify", 41, symbol_png=b"PNGDATEN")
zweite = zeilen_lesen(c, 1)
pruefe("beim ersten Mal dabei", bool(erste) and "symbol" in erste[0])
pruefe("beim zweiten Mal nicht mehr",
       bool(zweite) and "symbol" in zweite[0], False)

print("\n=== Nimmt nichts entgegen ===")
# Wer hier etwas hineinschreibt, darf damit nichts bewirken – der Melder
# liest gar nicht erst.
c.sendall(b'{"typ":"setvol","app":"discord.exe","prozent":0}\n')
time.sleep(0.2)
m.melden("discord.exe", "Discord", 57)
nachher = zeilen_lesen(c, 1)
pruefe("laeuft unbeirrt weiter", bool(nachher))
pruefe("und meldet weiter den echten Wert",
       nachher[0].get("prozent") if nachher else None, 57)

print("\n=== Nur von diesem Rechner erreichbar ===")
# Der Lauscher haengt an 127.0.0.1. Ueber die Adresse des Rechners im Netz
# darf er nicht antworten.
eigene = socket.gethostbyname(socket.gethostname())
if eigene.startswith("127."):
    print("  --   kein Netzwerkzugang, Pruefung ausgelassen")
else:
    offen = True
    try:
        fremd = socket.create_connection((eigene, PORT), timeout=1.5)
        fremd.close()
    except OSError:
        offen = False
    pruefe("von aussen zu", offen, False, "getestet ueber {}".format(eigene))

print("\n=== Abgemeldeter Zuhoerer wird vergessen ===")
c.close()
time.sleep(0.2)
for _ in range(3):
    m.melden("app.exe", "App", 50)
    time.sleep(0.05)
pruefe("Liste wieder leer", m.zahl_zuhoerer(), 0)

print("\n=== Zweiter Melder auf demselben Anschluss ===")
zweiter = Melder(port=PORT)
pruefe("scheitert, ohne zu stuerzen", zweiter.starten(), False)

m.stoppen()
pruefe("nach dem Stoppen ist der Anschluss frei", Melder(port=PORT).starten())

print("\n{}".format("Alles gruen." if not fehler
                    else "{} Test(s) fehlgeschlagen!".format(fehler)))
sys.exit(1 if fehler else 0)
