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

from . import klang
from .config import GAMMA_STANDARD as GAMMA_STANDARD_CFG
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
        self.speed_step = 2.0          # Prozentpunkte je Rastung
        self.gamma = self.GAMMA_STANDARD
        self.switch_mode = "none"
        self.meters_an = True
        self.ton_am_anschlag = True

        # Lautstaerke angleichen: welche Apps, was der Nutzer wollte, und
        # wie weit gerade gedaempft wird
        self.angleichen = set()
        self._nutzer_amp = {}
        self._daempfung = {}

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
                    elif art == "angleichen":
                        self.angleichen_setzen(j[1], j[2])
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
                    if key in self.angleichen:
                        # Von Hand gestellt heisst: das ist ab jetzt die
                        # Obergrenze, von der aus gedaempft wird.
                        self._nutzer_amp[key] = self.amp_aus_pos(wert)
                    self.set_volume(key, wert)
                if refresh:
                    # Die Kurve haengt am Ausgabegeraet – beim Umstecken
                    # aendert sie sich, also regelmaessig nachlesen.
                    self._gamma_auffrischen()
                    self._apps_melden()
                if scroll:
                    self._scroll_anwenden(scroll)
                if self._ziel:
                    self._fahren()

                # Pegelanzeige: unabhaengig vom Rest, ~20 Bilder je Sekunde
                jetzt = time.perf_counter()
                if jetzt - letzte_messung >= 0.05:
                    letzte_messung = jetzt
                    # Die Regelung braucht denselben Takt wie die Anzeige,
                    # laeuft aber auch, wenn die Balken abgeschaltet sind.
                    try:
                        self._angleichen_regeln()
                    except Exception:
                        pass
                    if self.meters_an and self.on_meters:
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

    def _peaks(self, max_alter=2.0, roh=False):
        """Spitzenpegel je Programm (0..1).

        Ab Werk in Reglerskala – so passt der Ausschlag zur Fuellung des
        Reglers. Die Regelung braucht dagegen die rohe Amplitude, denn sie
        rechnet mit Faktoren.
        """
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
                wert = float(m.GetPeakValue())
                werte[key] = wert if roh else self.pos_aus_amp(wert)
            except Exception:
                pass
        return werte

    # ---- Lautstaerke angleichen -----------------------------------------
    # Zielpegel und Grenzen als Amplitude. Die Zahlen stammen aus einer
    # Probe mit drei verschieden lauten Sprechern: Die Schwankung ueber
    # Sekunden ging damit von 13,4 dB auf 7,3 dB zurueck, waehrend die
    # Dynamik innerhalb eines Sprechers erhalten blieb (12,5 -> 11,4 dB).
    ANGLEICH_ZIEL = 0.35
    ANGLEICH_TIEFSTENS = 0.25      # weiter wird nie gedaempft
    ANGLEICH_STILLE = 0.04         # darunter gilt es als Pause
    ANGLEICH_RUNTER = 0.30         # laut wird schnell weggenommen
    ANGLEICH_ZURUECK = 0.02        # zurueck geht es langsam, sonst pumpt es

    def angleichen_setzen(self, key, an):
        """Fuer eine App ein- oder ausschalten."""
        if an:
            self.angleichen.add(key)
            if key not in self._nutzer_amp:
                jetzt = self.amplitude(key)
                if jetzt is not None:
                    self._nutzer_amp[key] = jetzt
            self._daempfung[key] = 1.0
        else:
            self.angleichen.discard(key)
            self._daempfung.pop(key, None)
            # Zurueck auf das, was der Nutzer eingestellt hat
            nutzer = self._nutzer_amp.pop(key, None)
            if nutzer is not None:
                self._amp_setzen_alle(key, nutzer)

    def amplitude(self, key, by=None):
        """Aktuelle Amplitude einer App (0..1) oder None."""
        regler = (by if by is not None else self._by_key()).get(key, [])
        for v in regler:
            try:
                return float(v.GetMasterVolume())
            except Exception:
                continue
        return None

    def _amp_setzen_alle(self, key, amp):
        amp = max(0.0, min(1.0, float(amp)))
        for v in self._by_key().get(key, []):
            try:
                v.SetMasterVolume(amp, None)
            except Exception:
                pass

    def _angleichen_regeln(self):
        """Laute Stellen daempfen, damit die Lautstaerke gleichmaessig wirkt.

        Geregelt wird nur nach unten: Der vom Nutzer eingestellte Pegel ist
        die Obergrenze. Windows kennt fuer einzelne Apps keine Verstaerkung
        ueber 100 %, und heimlich leiser stellen, um Luft zu gewinnen, waere
        eine Ueberraschung beim naechsten Blick auf den Regler.
        """
        if not self.angleichen:
            return
        roh = self._peaks(roh=True)
        for key in list(self.angleichen):
            pegel = roh.get(key)
            if pegel is None:
                continue
            nutzer = self._nutzer_amp.get(key)
            if nutzer is None:
                nutzer = self.amplitude(key)
                if nutzer is None:
                    continue
                self._nutzer_amp[key] = nutzer
            d = self._daempfung.get(key, 1.0)
            if pegel > self.ANGLEICH_STILLE:
                # Der gemessene Pegel ist bereits gedaempft – der Faktor sagt
                # also direkt, wie weit nachzuregeln ist.
                gewuenscht = max(self.ANGLEICH_TIEFSTENS,
                                 min(1.0, d * self.ANGLEICH_ZIEL / pegel))
                tempo = (self.ANGLEICH_RUNTER if gewuenscht < d
                         else self.ANGLEICH_ZURUECK)
                d += (gewuenscht - d) * tempo
                self._daempfung[key] = d
                self._amp_setzen_alle(key, nutzer * d)

    # ---- Reglerweg und Amplitude ----------------------------------------
    #
    # Windows' Gesamtlautstaerke ist nicht linear: Der halbe Reglerweg daempft
    # auf rund 30 % Amplitude, nicht auf 50 %. Die Regler einzelner Apps sind
    # dagegen reine Amplitudenfaktoren – 50 % sind dort wirklich 50 %.
    #
    # Deshalb gibt es hier zwei Ebenen:
    #   Position   – was der Regler zeigt (0..1), fuer alle gleich
    #   Amplitude  – was tatsaechlich herauskommt (0..1)
    #
    # Umgerechnet wird mit Amplitude = Position^gamma. gamma stammt aus dem
    # laufenden System: Windows liefert zu jeder Reglerstellung auch den
    # dB-Wert, und aus beidem laesst sich der Exponent ablesen.
    GAMMA_STANDARD = GAMMA_STANDARD_CFG   # falls nichts abzulesen ist

    def _gamma_auffrischen(self):
        """Den Exponenten aus dem aktuellen Zustand der Gesamtlautstaerke lesen.

        Nur im mittleren Bereich sinnvoll: Nahe 0 und nahe 1 wird die Rechnung
        unzuverlaessig, weil der Logarithmus dort gegen null geht.
        """
        try:
            s = float(self._endpoint().GetMasterVolumeLevelScalar())
            db = float(self._endpoint().GetMasterVolumeLevel())
        except Exception:
            self._epv = None
            return
        if not (0.05 < s < 0.95) or db < -90.0:
            return
        amp = 10.0 ** (db / 20.0)
        if amp <= 0.0:
            return
        g = math.log(amp) / math.log(s)
        if 1.0 <= g <= 4.0:
            self.gamma = g

    def amp_aus_pos(self, pos):
        """Reglerposition -> tatsaechliche Amplitude."""
        pos = max(0.0, min(1.0, float(pos)))
        return pos ** self.gamma

    def pos_aus_amp(self, amp):
        """Amplitude -> Reglerposition."""
        amp = max(0.0, min(1.0, float(amp)))
        return amp ** (1.0 / self.gamma)

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
        """`wert` ist eine Reglerposition (0..1), keine Amplitude."""
        if key == MASTER_KEY:
            self.set_master_scalar(wert)      # Windows rechnet selbst um
            return
        self.set_app_amplitude(key, self.amp_aus_pos(wert))

    def prozent(self, key, by=None):
        """Reglerposition in Prozent – fuer Gesamt und Apps dieselbe Skala."""
        if key == MASTER_KEY:
            cur = self.master_scalar()
            return None if cur is None else cur * 100.0
        amp = self.app_amplitude(key, by)
        return None if amp is None else self.pos_aus_amp(amp) * 100.0

    # ---- die tatsaechliche Amplitude einer App ---------------------------
    def app_amplitude(self, key, by=None):
        regler = (by or self._by_key()).get(key, [])
        if not regler:
            return None
        try:
            return float(regler[0].GetMasterVolume())
        except Exception:
            return None

    def set_app_amplitude(self, key, amp):
        """Setzt die Amplitude und meldet, ob es angekommen ist.

        Der Sitzungsspeicher kann veraltet sein – dann zeigen die Objekte auf
        Sitzungen, die es nicht mehr gibt, und das Setzen verpufft still.
        Deshalb ein zweiter Versuch mit frisch geholter Liste.
        """
        amp = max(0.0, min(1.0, float(amp)))
        for versuch in (0, 1):
            regler = self._by_key(max_alter=2.0 if versuch == 0 else 0.0)
            regler = regler.get(key, [])
            if regler and all(self._amp_setzen(v, amp) for v in regler):
                return True
            self._cache_weg()
        return False

    @staticmethod
    def _amp_setzen(sav, amp):
        try:
            sav.SetMasterVolume(amp, None)
            return True
        except Exception:
            return False

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

        Ein Programm kann mehrere Sitzungen haben – Spotify und Discord tun
        das regelmaessig, meist gibt nur eine davon Ton aus. Deshalb werden
        alle gesammelt und der lauteste Ausschlag gilt fuer das Programm.
        Wird eine davon uebersehen, bleibt sie beim Wechsel auf voller
        Lautstaerke stehen – und genau das knallt.

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
            if sav is not None:
                regler.setdefault(key, []).append(sav)
            if m is not None:
                messer.setdefault(key, []).append(m)
        spitze = dict.fromkeys(regler, 0.0)
        for i in range(max(1, messungen)):
            if i:
                time.sleep(pause)
            for key, liste in messer.items():
                for m in liste:
                    try:
                        spitze[key] = max(spitze[key], float(m.GetPeakValue()))
                    except Exception:
                        pass
        return {k: v for k, v in regler.items() if spitze.get(k, 0.0) >= schwelle}

    @staticmethod
    def _flach(nach_key):
        """{key: [regler, ...]} zu einer einfachen Liste."""
        return [v for liste in nach_key.values() for v in liste]

    @staticmethod
    def _skalieren(regler, faktor):
        """Regler mit `faktor` multiplizieren, oder auf 100 % (faktor=None).

        Meldet zurueck, ob alle erreicht wurden – beim Angleichen haengt der
        Gehoerschutz daran.
        """
        alle = True
        for sav in regler:
            try:
                neu = 1.0 if faktor is None else float(sav.GetMasterVolume()) * faktor
                sav.SetMasterVolume(max(0.0, min(1.0, neu)), None)
            except Exception:
                alle = False
        return alle

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
        # Frisch holen: Hier haengt der Gehoerschutz dran, ein veralteter
        # Sitzungsspeicher liesse das Leiserstellen still ins Leere laufen.
        by = self._by_key(max_alter=0.0)
        # Hier geht es um tatsaechliche Lautheit, nicht um Reglerwege –
        # deshalb durchgehend mit Amplituden gerechnet.
        pegel = {k: a for k, a in ((k, self.app_amplitude(k, by)) for k in keys)
                 if a is not None}
        if not pegel:
            return
        # Apps, die gerade wirklich spielen, muessen mit – fuer sie aendert
        # sich die Gesamtdaempfung genauso. Stille Apps bleiben in Ruhe.
        mit = self._spielende(ausser=set(pegel))
        if richtung == "apps":
            leiser = all([self.set_app_amplitude(key, amp * gain)
                          for key, amp in pegel.items()])
            leiser = self._skalieren(self._flach(mit), gain) and leiser
            if not leiser:
                # Lieber gar nichts aendern als die Gesamtlautstaerke
                # aufreissen, waehrend die Apps noch laut stehen.
                return
            self._setzen_lassen()
            self.set_master_scalar(1.0)
        else:
            self.set_master_gain(min(pegel.values()) * gain)
            self._setzen_lassen()
            for key in pegel:
                self.set_app_amplitude(key, 1.0)
            self._skalieren(self._flach(mit), None)
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

    def _scroll_anwenden(self, delta):
        """Setzt nur das Ziel – gefahren wird in kleinen Schritten."""
        ziele = list(self.targets)
        if not ziele:
            return
        by = self._by_key()
        # Eine Schrittweite fuer alles: Gesamt und Apps liegen jetzt auf
        # derselben Skala, also fuehlt sich derselbe Schritt gleich an.
        aenderung = delta * self.speed_step
        angekommen = False
        for key in ziele:
            basis = self._ziel.get(key)
            if basis is None:
                basis = self.prozent(key, by)
                if basis is None:
                    continue
                self._jetzt[key] = basis
            ziel = max(0.0, min(100.0, basis + aenderung))
            # Der Ton kommt beim Ankommen, nicht beim Weiterdrehen: Wer oben
            # steht und noch dreht, hat schon 100 als Ausgangswert.
            if ziel >= 100.0 > basis:
                angekommen = True
            self._ziel[key] = ziel
            weg = abs(ziel - self._jetzt.get(key, ziel))
            self._schritt[key] = max(1, int(weg / 5.0 + 0.5))
        if angekommen and self.ton_am_anschlag:
            klang.anschlag()

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
                amp = float(sav.GetMasterVolume())
            except Exception:
                amp = 1.0
            # Bei geregelten Apps den Wunsch des Nutzers melden, nicht den
            # Ist-Wert: Sonst wandert der Schieber im Fenster staendig mit
            # der Regelung mit, und niemand koennte ihn noch anfassen.
            if key in self.angleichen and key in self._nutzer_amp:
                amp = self._nutzer_amp[key]
            # als Reglerposition melden, nicht als Amplitude
            vol = self.pos_aus_amp(amp)
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
