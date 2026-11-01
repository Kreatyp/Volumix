# -*- coding: utf-8 -*-
"""Was gerade spielt – Titel, Interpret und Coverbild.

Windows fuehrt Buch darueber, welche Programme gerade Medien wiedergeben;
dieselbe Liste fuettert die Titelanzeige, die beim Druecken der
Lautstaerketasten erscheint. Spotify, Browser, Player melden sich dort an.

Gemessen auf diesem Rechner:

* Die Module einmal laden kostet **86 ms**. Deshalb geschieht das im
  Arbeitsthread und nicht beim Start – sonst stuende das Fenster laenger.
* Eigenschaften abfragen kostet **3,7 ms**, mit Coverbild **5,4 ms**.

Deshalb wird im Takt nur nach Titel und Interpret gefragt und das Bild erst
geholt, wenn sich etwas geaendert hat. Ein Titel dauert Minuten, das Bild
also hoechstens alle paar Minuten.

Meldet sich niemand an – kein Player offen, oder die Schnittstelle fehlt –,
kommt einmal eine leere Meldung und danach Ruhe. Das Modul ist damit auch
auf Rechnern harmlos, auf denen es nichts zu holen gibt.
"""
import threading
import time

TAKT = 1.5          # Sekunden zwischen zwei Abfragen

# Antwortet die Schnittstelle nicht, wird der Abstand groesser. Gemessen
# haengt ein Aufruf in dem Fall **10 Sekunden**, bis COM ihn abbricht – im
# 1,5-Sekunden-Takt liefe der Thread dann dauerhaft in dieses Loch und
# klopfte an eine Tuer, hinter der niemand ist.
FEHLERTAKT = [5.0, 15.0, 30.0, 60.0]


def beste_sitzung(kandidaten):
    """Welche Wiedergabe angezeigt wird, wenn mehrere laufen.

    Windows fuehrt eine „aktuelle" Sitzung, und das ist meist die zuletzt
    gestartete. Laeuft ein Stream im Browser, waehrend daneben Musik
    spielt, zeigte Volumix deshalb den Stream – samt Browserlogo als Cover.

    Die Reihenfolge ist deshalb, in dieser Rangfolge:

    1. Was gerade spielt, vor allem Pausierten.
    2. Was eine Laenge hat, vor einem Stream ohne Ende. Ein Titel mit
       Anfang und Ende ist das, wozu Cover, Zeit und Balken ueberhaupt
       passen – ein Stream hat davon nichts.
    3. Bei Gleichstand das, was Windows fuer das aktuelle haelt.

    `kandidaten` sind Vierergruppen `(sitzung, laeuft, dauer, ist_aktuell)`.
    """
    beste, bester_rang = None, None
    for sitzung, laeuft, dauer, ist_aktuell in kandidaten:
        rang = (1 if laeuft else 0,
                1 if dauer and dauer > 0 else 0,
                1 if ist_aktuell else 0)
        if bester_rang is None or rang > bester_rang:
            beste, bester_rang = sitzung, rang
    return beste


class Titelwacht:
    """Ruft `on_titel(titel, interpret, cover)` bei jedem Titelwechsel.

    `cover` sind die rohen Bilddaten (meist JPEG) oder None. Der Rueckruf
    kommt aus dem Arbeitsthread – die Oberflaeche muss ihn in ihren eigenen
    weiterreichen.

    `on_zeit(position, dauer, laeuft)` kommt bei *jedem* Durchgang, nicht nur
    beim Wechsel: Der Fortschritt aendert sich staendig. Die Sekunden
    dazwischen rechnet sich die Anzeige selbst aus – anderthalb Sekunden
    Takt waeren als Ruckeln zu sehen. Laeuft nichts, kommen Nullen.
    """

    def __init__(self, on_titel=None, on_zeit=None):
        self.on_titel = on_titel
        self.on_zeit = on_zeit
        self._stop = False
        self._thread = None
        self._letzter = None        # (Titel, Interpret)
        self._fehler = 0            # Fehlschlaege in Folge

    # ---- Aussenseite -----------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._lauf, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    def neu_melden(self):
        """Beim naechsten Durchgang wieder melden, auch ohne Wechsel."""
        self._letzter = None

    # ---- Arbeitsthread ---------------------------------------------------
    def _lauf(self):
        try:
            import asyncio

            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Manager)
            from winrt.windows.storage.streams import (Buffer,
                                                       InputStreamOptions)
        except Exception as e:
            # Kein WinRT vorhanden – einmal Bescheid geben, dann still sein.
            # Ins Protokoll, weil man es sonst nicht merkt: Der Hintergrund
            # bliebe schlicht leer, ohne dass irgendwo stuende, warum. In der
            # gebauten App ist genau das der wahrscheinliche Fehler, wenn
            # PyInstaller die nativen Module nicht mitgenommen hat.
            from . import config
            config.notiz("Titelwacht aus: {}".format(e))
            self._melden(None, None, None)
            return
        from . import config
        config.notiz("Titelwacht laeuft")

        # Der Sitzungsmanager wird **einmal** geholt und behalten.
        #
        # Vorher stand `request_async()` in jeder Abfrage – alle 1,5 Sekunden
        # ein neuer Manager, also rund 57 000 am Tag, jeder davon eine
        # Anmeldung bei der Vermittlungskomponente von Windows. Ob das der
        # Grund war, dass sie nach Tagen Dauerbetrieb nicht mehr antwortete,
        # ist nicht bewiesen – aber es ist in jedem Fall verschwenderisch und
        # falsch: Der Manager ist ein Zugang, kein Ergebnis.
        manager = [None]

        def zeiten(sitzung):
            """Position und Laenge in Sekunden, dazu ob es gerade laeuft.

            Ein Livestream meldet kein Ende – dort kommt ein unsinniger Wert
            heraus (gemessen minus ein Tag). Solche Laengen werden verworfen;
            eine Position ohne Laenge ist immer noch eine Angabe.
            """
            try:
                z = sitzung.get_timeline_properties()
                dauer = z.end_time.total_seconds() - z.start_time.total_seconds()
                stelle = z.position.total_seconds()
            except Exception:
                return (0.0, 0.0, False)
            if dauer <= 0 or dauer > 24 * 3600:
                dauer = 0.0
            try:
                laeuft = int(sitzung.get_playback_info().playback_status) == 4
            except Exception:
                laeuft = False
            return (max(0.0, stelle), max(0.0, dauer), laeuft)

        def waehlen():
            """Die Sitzung, die angezeigt wird – siehe `beste_sitzung`.

            Fuer die Auswahl genuegen Zustand und Zeitangaben, und beide
            kommen ohne `await` heraus. Die Eigenschaften mit Titel und Bild
            werden nur fuer die eine geholt, die gewonnen hat.
            """
            aktuell = manager[0].get_current_session()
            kennung = aktuell.source_app_user_model_id if aktuell else None
            kandidaten = []
            try:
                sitzungen = list(manager[0].get_sessions())
            except Exception:
                sitzungen = []
            for s in sitzungen:
                stelle, dauer, laeuft = zeiten(s)
                kandidaten.append(
                    (s, laeuft, dauer,
                     s.source_app_user_model_id == kennung))
            return beste_sitzung(kandidaten) or aktuell

        async def hole(mit_bild):
            if manager[0] is None:
                manager[0] = await Manager.request_async()
            sitzung = waehlen()
            if sitzung is None:
                return None
            eig = await sitzung.try_get_media_properties_async()
            daten = None
            if mit_bild and eig.thumbnail is not None:
                strom = await eig.thumbnail.open_read_async()
                puffer = Buffer(strom.size)
                await strom.read_async(puffer, strom.size,
                                       InputStreamOptions.READ_AHEAD)
                daten = bytes(puffer)
            return eig.title, eig.artist, daten, zeiten(sitzung)

        while not self._stop:
            kaputt = False
            try:
                # Erst ohne Bild fragen: Das kostet 3,7 statt 5,4 ms, und in
                # den allermeisten Durchgaengen laeuft derselbe Titel weiter.
                jetzt = asyncio.run(hole(False))
            except Exception as e:
                jetzt, kaputt = None, True
                # Zugang beim naechsten Mal neu holen – vielleicht ist er es,
                # der nicht mehr taugt.
                manager[0] = None
                if self._fehler == 0:
                    from . import config
                    config.notiz("Titelwacht: Medienschnittstelle "
                                 "antwortet nicht ({})".format(e))

            if kaputt:
                # Nichts melden. Ein Fehler heisst nicht, dass nichts laeuft –
                # er heisst, dass wir es gerade nicht wissen. Das zuletzt
                # gemeldete Bild stehen zu lassen ist die ehrlichere Anzeige,
                # als es wegzunehmen.
                self._fehler += 1
            elif jetzt is None:
                self._fehler = 0
                self._zeit_melden(0.0, 0.0, False)
                if self._letzter is not None:
                    self._letzter = None
                    self._melden(None, None, None)
            else:
                if self._fehler:
                    from . import config
                    config.notiz("Titelwacht: Medienschnittstelle wieder da")
                self._fehler = 0
                titel, interpret, _, zeit = jetzt
                self._zeit_melden(*zeit)
                if (titel, interpret) != self._letzter:
                    self._letzter = (titel, interpret)
                    try:
                        mit = asyncio.run(hole(True))
                    except Exception:
                        mit = None
                    if mit:
                        self._melden(*mit[:3])
                    else:
                        self._melden(titel, interpret, None)

            pause = TAKT
            if self._fehler:
                pause = FEHLERTAKT[min(self._fehler, len(FEHLERTAKT)) - 1]
            for _ in range(int(pause * 10)):
                if self._stop:
                    return
                time.sleep(0.1)

    def _melden(self, titel, interpret, cover):
        if self.on_titel:
            try:
                self.on_titel(titel, interpret, cover)
            except Exception:
                # Beim Beenden haengt der Rueckruf ins Leere.
                pass

    def _zeit_melden(self, position, dauer, laeuft):
        if self.on_zeit:
            try:
                self.on_zeit(position, dauer, laeuft)
            except Exception:
                pass
