# -*- coding: utf-8 -*-
"""Meldet Lautstaerkeaenderungen an andere Programme auf demselben Rechner.

Gebaut fuer Spiele im Vollbild: Dort liegt ein fremdes Fenster wie die
Einblendung von Volumix hinter dem Spiel, egal wie weit oben es steht. Das
Spiel muss die Anzeige also selbst zeichnen – und dafuer erfahren, was
gerade passiert ist.

Aufbau: Volumix haelt einen Lauscher auf 127.0.0.1, wer will, verbindet
sich und bekommt je Aenderung eine Zeile JSON. Kein Empfang in die andere
Richtung – niemand soll ueber diesen Weg die Lautstaerke stellen koennen,
und was nichts entgegennimmt, kann auch nichts Falsches entgegennehmen.

Nur die Loopback-Adresse, nie 0.0.0.0: Das Ding gehoert diesem Rechner und
hat im Netz nichts verloren.
"""
import base64
import json
import socket
import threading

PORT = 48765
ADRESSE = "127.0.0.1"

# Fassung des Formats. Wer mitliest, kann daran erkennen, ob er die Zeilen
# noch versteht – ohne das muesste jede Aenderung hier alles brechen, was
# jemals angebunden wurde.
FASSUNG = 1


class Melder:
    """Lauscher plus Verteiler. Ohne Zuhoerer kostet er nichts."""

    def __init__(self, port=PORT):
        self.port = port
        self._lauscher = None
        self._faden = None
        self._stop = threading.Event()
        self._schloss = threading.Lock()
        self._zuhoerer = []          # [(socket, {keys mit gesendetem Symbol})]
        self.laeuft = False

    # ---- an und aus ------------------------------------------------------
    def starten(self):
        if self.laeuft:
            return True
        self._stop.clear()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # NICHT SO_REUSEADDR: Unter Windows heisst das etwas anderes als
            # unter Linux – dort duerfen sich mehrere Sockets denselben
            # Anschluss teilen. Eine zweite Volumix-Instanz haette sich
            # klaglos danebengesetzt und die Meldungen waeren zufaellig mal
            # hier, mal dort gelandet. SO_EXCLUSIVEADDRUSE macht daraus das,
            # was man erwartet: Der Zweite scheitert.
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind((ADRESSE, self.port))
            s.listen(4)
            s.settimeout(0.5)
        except OSError:
            # Port belegt – etwa eine zweite Volumix-Instanz. Kein Grund,
            # deshalb die ganze App scheitern zu lassen.
            return False
        self._lauscher = s
        self._faden = threading.Thread(target=self._annehmen, daemon=True)
        self._faden.start()
        self.laeuft = True
        return True

    def stoppen(self):
        self._stop.set()
        with self._schloss:
            zuhoerer = [z for z, _ in self._zuhoerer]
            self._zuhoerer = []
        for z in zuhoerer:
            try:
                z.close()
            except OSError:
                pass
        if self._lauscher is not None:
            try:
                self._lauscher.close()
            except OSError:
                pass
            self._lauscher = None
        self.laeuft = False

    # ---- Betrieb ---------------------------------------------------------
    def _annehmen(self):
        while not self._stop.is_set():
            try:
                verbindung, _ = self._lauscher.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            verbindung.settimeout(1.0)
            with self._schloss:
                self._zuhoerer.append((verbindung, set()))
            self._zeile_senden(verbindung, {"typ": "hallo",
                                            "fassung": FASSUNG,
                                            "programm": "Volumix"})

    def _zeile_senden(self, verbindung, daten):
        try:
            roh = (json.dumps(daten, ensure_ascii=False) + "\n").encode("utf-8")
            verbindung.sendall(roh)
            return True
        except OSError:
            return False

    def zahl_zuhoerer(self):
        with self._schloss:
            return len(self._zuhoerer)

    def melden(self, key, name, prozent, stumm=False, symbol_png=None,
               akzent=None):
        """Eine Aenderung an alle Zuhoerer.

        `symbol_png` sind rohe PNG-Bytes. Sie gehen nur beim ersten Mal je
        Zuhoerer und App mit: Ein Symbol ist einige Kilobyte gross, und bei
        jeder Rastung am Rad waere das ein Vielfaches der eigentlichen
        Nachricht.
        """
        if not self.laeuft:
            return
        grund = {"typ": "lautstaerke", "app": key, "name": name,
                 "prozent": int(prozent), "stumm": bool(stumm)}
        if akzent:
            grund["farbe"] = akzent
        with self._schloss:
            zuhoerer = list(self._zuhoerer)
        tot = []
        for verbindung, gesehen in zuhoerer:
            daten = dict(grund)
            if symbol_png and key not in gesehen:
                daten["symbol"] = base64.b64encode(symbol_png).decode("ascii")
            if self._zeile_senden(verbindung, daten):
                if symbol_png:
                    gesehen.add(key)
            else:
                tot.append(verbindung)
        if tot:
            with self._schloss:
                self._zuhoerer = [(z, g) for z, g in self._zuhoerer
                                  if z not in tot]
            for z in tot:
                try:
                    z.close()
                except OSError:
                    pass
