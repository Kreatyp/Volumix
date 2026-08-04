# -*- coding: utf-8 -*-
"""Windows-Audio: Sitzungen, Pegel, Spitzenwerte.

Laeuft komplett in einem eigenen Thread (COM verlangt das) und redet ueber
Rueckrufe mit der Oberflaeche. Die Rechenregeln stammen unveraendert aus der
Tk-Fassung – sie waren der aufwendigste Teil und haben sich bewaehrt.
"""
import math
import queue
import threading
import time

from comtypes import CoInitialize, CoUninitialize
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

from .config import MASTER_KEY, SYSTEM_KEY
from .sprache import T

# Programmnamen, die Windows anders schreibt als der Mensch
_NAMEN = {
    "chrome.exe": "Chrome", "msedge.exe": "Edge", "firefox.exe": "Firefox",
    "spotify.exe": "Spotify", "discord.exe": "Discord",
    "telegram.exe": "Telegram", "vlc.exe": "VLC", "steam.exe": "Steam",
    "msedgewebview2.exe": "Edge WebView", "explorer.exe": "Explorer",
    "shellexperiencehost.exe": "Windows-Oberfläche",
    "startmenuexperiencehost.exe": "Startmenü",
    "applicationframehost.exe": "App-Fenster",
    "textinputhost.exe": "Tastatureingabe", "searchhost.exe": "Windows-Suche",
}


def huebscher_name(pname):
    n = _NAMEN.get(pname.lower())
    if n:
        return n
    basis = pname[:-4] if pname.lower().endswith(".exe") else pname
    basis = basis.replace("_", " ").replace("-", " ").strip()
    return basis[:1].upper() + basis[1:] if basis else pname


class AudioEngine:
    """Kapselt alles, was mit dem Windows-Mischpult zu tun hat.

    Auftraege kommen ueber `job()` herein, Ergebnisse gehen ueber die
    Rueckrufe `on_apps` und `on_volume` hinaus. Beide werden aus dem
    Arbeitsthread gerufen – die Oberflaeche muss sie in ihren eigenen Thread
    weiterreichen.
    """

    def __init__(self, on_apps=None, on_volume=None, on_meters=None):
        self.on_apps = on_apps
        self.on_volume = on_volume
        self.on_meters = on_meters
        self.jobs = queue.Queue()
        self.targets = set()
        # Prozentpunkte je Rastung. Getrennt, weil eine einzelne App feiner
        # dosiert werden will als die Gesamtlautstaerke.
        self.speed_step = 2.0          # Gesamtlautstaerke
        self.speed_step_apps = 2.0     # einzelne Apps
        self.speed_curve = True        # kleinere Schritte bei leisen Pegeln
        self.switch_mode = "none"
        self.meters_an = True

        self._epv = None
        self._sess_cache = None        # (Zeitpunkt, {key: [SimpleAudioVolume]})
        self._meter_cache = None       # (Zeitpunkt, {key: IAudioMeterInformation})
        self._ziel = {}                # key -> Zielpegel in Prozent
        self._jetzt = {}               # key -> aktueller Pegel
        self._schritt = {}
        self._stop = False
        self._thread = None

    # ---- Aussenseite -----------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._lauf, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.jobs.put(("quit",))

    def job(self, *args):
        self.jobs.put(args)

    # ---- Arbeitsschleife -------------------------------------------------
    def _lauf(self):
        CoInitialize()
        letzte_messung = 0.0
        try:
            while not self._stop:
                # Laeuft eine Lautstaerke-Fahrt? Dann nur kurz warten, damit
                # die Schritte gleichmaessig weiterlaufen.
                wartezeit = 0.007 if self._ziel else 0.05
                try:
                    job = self.jobs.get(timeout=wartezeit)
                    jobs = [job]
                    while True:
                        try:
                            jobs.append(self.jobs.get_nowait())
                        except queue.Empty:
                            break
                except queue.Empty:
                    jobs = []

                scroll = 0
                refresh = False
                wechsel = None
                setzen = {}
                stumm = {}
                profil = None
                for j in jobs:
                    art = j[0]
                    if art == "scroll":
                        scroll += j[1]
                    elif art == "refresh":
                        refresh = True
                    elif art == "setvol":
                        setzen[j[1]] = j[2]
                    elif art == "mute":
                        stumm[j[1]] = j[2]
                    elif art == "switch":
                        wechsel = (j[1], j[2])
                    elif art == "profile":
                        profil = j[1]
                    elif art == "quit":
                        return

                if wechsel is not None:
                    self._pegel_angleichen(*wechsel)
                    refresh = True
                if profil is not None:
                    self._profil_anwenden(profil)
                    refresh = True
                if stumm:
                    for key, an in stumm.items():
                        self._set_mute(key, an)
                    refresh = True
                for key, wert in setzen.items():
                    self._ziel.pop(key, None)
                    self._jetzt[key] = wert * 100.0
                    self.set_volume(key, wert)
                if refresh:
                    self._apps_melden()
                if scroll:
                    self._scroll_anwenden(scroll)
                if self._ziel:
                    self._fahren()

                # Pegelanzeige: unabhaengig vom Rest, ~20 Bilder je Sekunde
                jetzt = time.perf_counter()
                if (self.meters_an and self.on_meters
                        and jetzt - letzte_messung >= 0.05):
                    letzte_messung = jetzt
                    try:
                        self._melden(self.on_meters, self._peaks())
                    except Exception:
                        pass
        finally:
            CoUninitialize()

    # ---- Sitzungen -------------------------------------------------------
    def _sessions(self):
        try:
            return AudioUtilities.GetAllSessions()
        except Exception:
            return []

    def _key_von(self, s):
        if s.Process is None:
            return SYSTEM_KEY
        try:
            return s.Process.name().lower()
        except Exception:
            return None

    def _by_key(self, max_alter=2.0):
        """Regler je Programm – kurz gecacht.

        `GetAllSessions()` fragt ueber COM alle Sitzungen des Systems ab und
        kostet rund 13 ms; aus dem Zwischenspeicher sind es 0,001 ms.
        """
        jetzt = time.perf_counter()
        if self._sess_cache and jetzt - self._sess_cache[0] < max_alter:
            return self._sess_cache[1]
        gefunden = {}
        for s in self._sessions():
            key = self._key_von(s)
            if not key:
                continue
            try:
                sav = s.SimpleAudioVolume
            except Exception:
                continue
            if sav is not None:
                gefunden.setdefault(key, []).append(sav)
        self._sess_cache = (jetzt, gefunden)
        return gefunden

    def _cache_weg(self):
        self._sess_cache = None
        self._meter_cache = None

    def _peaks(self, max_alter=2.0):
        """Spitzenpegel je Programm (0..1) – fuer die Live-Anzeige."""
        jetzt = time.perf_counter()
        if not self._meter_cache or jetzt - self._meter_cache[0] >= max_alter:
            messer = {}
            for s in self._sessions():
                key = self._key_von(s)
                if not key:
                    continue
                try:
                    messer[key] = s._ctl.QueryInterface(IAudioMeterInformation)
                except Exception:
                    continue
            self._meter_cache = (jetzt, messer)
        werte = {}
        for key, m in self._meter_cache[1].items():
            try:
                werte[key] = float(m.GetPeakValue())
            except Exception:
                pass
        return werte

    # ---- Gesamtlautstaerke ----------------------------------------------
    def _endpoint(self):
        if self._epv is None:
            self._epv = AudioUtilities.GetSpeakers().EndpointVolume
        return self._epv

    def master_scalar(self):
        try:
            return float(self._endpoint().GetMasterVolumeLevelScalar())
        except Exception:
            self._epv = None
            return None

    def set_master_scalar(self, wert):
        try:
            self._endpoint().SetMasterVolumeLevelScalar(float(wert), None)
        except Exception:
            self._epv = None

    def master_gain(self):
        """Was die Gesamtlautstaerke wirklich daempft, als linearer Faktor.

        Der Windows-Regler ist *nicht* linear: 40 % dort daempfen staerker als
        40 % bei einer App (App-Regler sind reine Amplitudenfaktoren). Nur
        ueber Dezibel lassen sich die beiden Skalen verrechnen.
        """
        try:
            return 10.0 ** (float(self._endpoint().GetMasterVolumeLevel()) / 20.0)
        except Exception:
            self._epv = None
            return None

    def set_master_gain(self, gain):
        try:
            ep = self._endpoint()
            lo, hi, _ = ep.GetVolumeRange()
            db = 20.0 * math.log10(max(1e-5, min(1.0, float(gain))))
            ep.SetMasterVolumeLevel(max(lo, min(hi, db)), None)
        except Exception:
            self._epv = None

    # ---- Pegel setzen und lesen -----------------------------------------
    def set_volume(self, key, wert):
        if key == MASTER_KEY:
            self.set_master_scalar(wert)
            return
        for v in self._by_key().get(key, []):
            try:
                v.SetMasterVolume(float(wert), None)
            except Exception:
                self._cache_weg()

    def prozent(self, key, by=None):
        if key == MASTER_KEY:
            cur = self.master_scalar()
            return None if cur is None else cur * 100.0
        regler = (by or self._by_key()).get(key, [])
        if not regler:
            return None
        try:
            return regler[0].GetMasterVolume() * 100.0
        except Exception:
            return None

    def get_mute(self, key):
        try:
            if key == MASTER_KEY:
                return bool(self._endpoint().GetMute())
            regler = self._by_key().get(key, [])
            return bool(regler[0].GetMute()) if regler else False
        except Exception:
            return False

    def _set_mute(self, key, an):
        try:
            if key == MASTER_KEY:
                self._endpoint().SetMute(bool(an), None)
                return
            for v in self._by_key().get(key, []):
                v.SetMute(bool(an), None)
        except Exception:
            self._cache_weg()

    # ---- Wechsel Gesamt <-> App -----------------------------------------
    def _spielende(self, ausser=(), schwelle=0.01, messungen=4, pause=0.02):
        """Regler aller Sitzungen, die gerade hoerbar Ton ausgeben.

        Mehrfach gemessen, weil ein einzelner Wert in die Pause zwischen zwei
        Toenen fallen kann.
        """
        regler, messer = {}, {}
        for s in self._sessions():
            key = self._key_von(s)
            if not key or key in ausser:
                continue
            try:
                sav = s.SimpleAudioVolume
                m = s._ctl.QueryInterface(IAudioMeterInformation)
            except Exception:
                continue
            if sav is not None and m is not None:
                regler[key], messer[key] = sav, m
        spitze = dict.fromkeys(messer, 0.0)
        for i in range(max(1, messungen)):
            if i:
                time.sleep(pause)
            for key, m in messer.items():
                try:
                    spitze[key] = max(spitze[key], float(m.GetPeakValue()))
                except Exception:
                    pass
        return {k: v for k, v in regler.items() if spitze.get(k, 0.0) >= schwelle}

    @staticmethod
    def _skalieren(regler, faktor):
        """Regler mit `faktor` multiplizieren, oder auf 100 % (faktor=None)."""
        for sav in regler:
            try:
                neu = 1.0 if faktor is None else float(sav.GetMasterVolume()) * faktor
                sav.SetMasterVolume(max(0.0, min(1.0, neu)), None)
            except Exception:
                pass

    @staticmethod
    def _setzen_lassen(sekunden=0.08):
        """Kurz warten, bis eine Aenderung in der Ausgabe angekommen ist.

        Sitzungs- und Geraetelautstaerke greifen an verschiedenen Stellen der
        Audiokette und nicht im selben Moment. Ohne diese Pause steht fuer ein,
        zwei Puffer beides hoch – das hoert man als kurzen Knall.
        """
        time.sleep(sekunden)

    def _pegel_angleichen(self, richtung, keys):
        """Pegel angleichen, wenn die Steuerung zwischen Gesamt und Apps wechselt.

        Reihenfolge ist entscheidend: immer erst leiser stellen, dann lauter.
        """
        if self.switch_mode == "none":
            return
        keys = list(keys or [])
        if self.switch_mode == "apps100":
            if richtung == "master":
                self._skalieren(
                    [v for s in self._by_key().values() for v in s], None)
            return
        if not keys:
            return
        gain = self.master_gain()
        if gain is None:
            return
        by = self._by_key()
        pegel = {k: p for k, p in ((k, self.prozent(k, by)) for k in keys)
                 if p is not None}
        if not pegel:
            return
        # Apps, die gerade wirklich spielen, muessen mit – fuer sie aendert
        # sich die Gesamtdaempfung genauso. Stille Apps bleiben in Ruhe.
        mit = self._spielende(ausser=set(pegel))
        if richtung == "apps":
            for key, prozent in pegel.items():
                self.set_volume(key, max(0.0, min(1.0, prozent / 100.0 * gain)))
            self._skalieren(mit.values(), gain)
            self._setzen_lassen()
            self.set_master_scalar(1.0)
        else:
            self.set_master_gain(min(pegel.values()) / 100.0 * gain)
            self._setzen_lassen()
            for key in pegel:
                self.set_volume(key, 1.0)
            self._skalieren(mit.values(), None)
        self._ziel.clear()
        self._jetzt.clear()
        self._schritt.clear()

    def _profil_anwenden(self, profil):
        """Gespeicherte Pegel wiederherstellen – erst leiser, dann lauter."""
        master = profil.get("master")
        apps = profil.get("apps") or {}
        by = self._by_key()
        aktuell = {k: self.prozent(k, by) for k in apps}
        # zuerst alles, was leiser wird
        for key, wert in apps.items():
            jetzt = aktuell.get(key)
            if jetzt is not None and wert * 100.0 < jetzt:
                self.set_volume(key, wert)
        if master is not None:
            jetzt_m = self.master_scalar()
            if jetzt_m is not None and master < jetzt_m:
                self.set_master_scalar(master)
                self._setzen_lassen(0.05)
        # danach alles, was lauter wird
        for key, wert in apps.items():
            jetzt = aktuell.get(key)
            if jetzt is None or wert * 100.0 >= jetzt:
                self.set_volume(key, wert)
        if master is not None:
            jetzt_m = self.master_scalar()
            if jetzt_m is None or master >= jetzt_m:
                self.set_master_scalar(master)
        self._ziel.clear()
        self._jetzt.clear()

    # ---- Daumenrad -------------------------------------------------------
    def _kruemmung(self, pegel):
        """Wie stark ein Schritt beim aktuellen Pegel ausfaellt.

        Bei 5 % Lautstaerke sind vier Prozentpunkte fast eine Verdopplung, bei
        80 % kaum zu hoeren. Ist die Anpassung an, wird der Schritt unten
        kleiner und oben groesser – in der Mitte bleibt er, wie eingestellt.
        """
        if not self.speed_curve:
            return 1.0
        p = max(0.0, min(100.0, pegel))
        return 0.28 + 1.44 * (p / 100.0)      # 0 % -> 0,28x, 50 % -> 1x, 100 % -> 1,72x

    def _scroll_anwenden(self, delta):
        """Setzt nur das Ziel – gefahren wird in kleinen Schritten."""
        ziele = list(self.targets)
        if not ziele:
            return
        by = self._by_key()
        # Gesamt und Apps schliessen sich aus – ein Blick auf die Ziele reicht,
        # um zu wissen, welche Schrittweite gilt.
        schritt = (self.speed_step if MASTER_KEY in ziele
                   else self.speed_step_apps)
        for key in ziele:
            basis = self._ziel.get(key)
            if basis is None:
                basis = self.prozent(key, by)
                if basis is None:
                    continue
                self._jetzt[key] = basis
            # Der Schritt haengt am aktuellen Pegel, nicht nur an der
            # Einstellung – deshalb hier drin und je Ziel einzeln.
            ziel = max(0.0, min(100.0,
                                basis + delta * schritt * self._kruemmung(basis)))
            self._ziel[key] = ziel
            weg = abs(ziel - self._jetzt.get(key, ziel))
            self._schritt[key] = max(1, int(weg / 5.0 + 0.5))

    def _fahren(self):
        fertig = []
        for key, ziel in list(self._ziel.items()):
            cur = self._jetzt.get(key)
            if cur is None:
                fertig.append(key)
                continue
            diff = ziel - cur
            if abs(diff) <= 1:
                neu = ziel
                fertig.append(key)
            else:
                s = self._schritt.get(key, 1)
                neu = cur + (s if diff > 0 else -s)
                if (diff > 0 and neu > ziel) or (diff < 0 and neu < ziel):
                    neu = ziel
                    fertig.append(key)
            self._jetzt[key] = neu
            self.set_volume(key, neu / 100.0)
            if self.on_volume:
                self._melden(self.on_volume, key, int(round(neu)))
        for key in fertig:
            self._ziel.pop(key, None)
            self._schritt.pop(key, None)

    # ---- Bestandsaufnahme ------------------------------------------------
    def _melden(self, rueckruf, *args):
        """Rueckruf ausfuehren, aber nie den Thread reissen lassen.

        Beim Beenden werden die Rueckrufe abgeklemmt, waehrend dieser Thread
        noch einen Durchgang laeuft – dann zeigt er sonst einen Fehler an ein
        Fenster, das es nicht mehr gibt.
        """
        if rueckruf is None or self._stop:
            return
        try:
            rueckruf(*args)
        except (RuntimeError, TypeError):
            pass          # Fenster ist weg

    def _apps_melden(self):
        if not self.on_apps:
            return
        gesehen = {}
        reihe = []
        for s in self._sessions():
            try:
                sav = s.SimpleAudioVolume
            except Exception:
                continue
            if sav is None:
                continue
            exe = None
            if s.Process is None:
                key, name = SYSTEM_KEY, T("systemklaenge")
            else:
                try:
                    pname = s.Process.name()
                except Exception:
                    continue
                key = pname.lower()
                name = huebscher_name(pname)
                try:
                    exe = s.Process.exe()
                except Exception:
                    exe = None
            if key in gesehen:
                continue
            try:
                vol = float(sav.GetMasterVolume())
            except Exception:
                vol = 1.0
            try:
                muted = bool(sav.GetMute())
            except Exception:
                muted = False
            gesehen[key] = True
            reihe.append({"key": key, "name": name, "volume": vol,
                          "exe": exe, "muted": muted})
        reihe.sort(key=lambda it: it["name"].lower())
        mv = self.master_scalar()
        master = {"key": MASTER_KEY, "name": T("gesamtlautstaerke"),
                  "volume": mv if mv is not None else 1.0, "exe": None,
                  "muted": self.get_mute(MASTER_KEY)}
        self._melden(self.on_apps, [master] + reihe)
