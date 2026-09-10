# -*- coding: utf-8 -*-
"""Netzwerk-Lautsprecher auf einen festen Wert bringen (Teufel Raumfeld).

Gedacht fuer Boxen, die per Cinch am Rechner haengen: Sie starten mit ihrem
eigenen Wert – bei der Raumfeld Stereo M rund 50 – und merken sich nur, was
zuletzt ueber ihre eigene App lief. Wer den Ton vom PC-Ausgang nimmt, stellt
deshalb jedes Mal von Hand nach. Dieses Modul nimmt das ab.

Gesprochen wird UPnP, wie es die Boxen ohnehin koennen: `RenderingControl`
mit `GetVolume` und `SetVolume`, Werte von 0 bis 100. Daneben laeuft auf der
Box ein kleiner Webdienst auf Port 47365, der `listDevices` und `getZones`
liefert – ueber `getZones` sieht man, ob sie ueberhaupt an ist.

Laeuft wie die Audio-Schicht in einem eigenen Thread und meldet sich ueber
einen Rueckruf. Das ist kein Luxus: Eine Box, die nicht antwortet, laesst
einen Aufruf in die Zeitgrenze laufen, und im Oberflaechen-Thread waere das
ein stehendes Fenster.

Drei Messwerte, die den Aufbau erklaeren (Stereo M, LAN, Median):

* `GetVolume` kostet 5,6 ms – Lesen ist praktisch umsonst.
* `SetVolume` auf denselben Wert kostet 17 ms, die Box tut dabei nichts.
* `SetVolume` auf einen anderen Wert kostet 86 ms, und zwar unabhaengig von
  der Sprungweite: zehn Schritte kosten so viel wie einer.

Deshalb wird vor jedem Schreiben gelesen. Steht der Wert schon richtig, ist
der Durchgang nach 5 ms vorbei statt nach 86.

An- und Ausschalten laeuft ueber `AVTransport`: `LeaveStandby` und
`EnterManualStandby`, beide in unter 50 ms beantwortet. Der Zustandswechsel
steht rund zwei Sekunden spaeter im `powerState`. Im Standby bleibt die Box
im Netz erreichbar – sonst liesse sie sich von hier aus nicht mehr wecken.

Wichtig fuer die Reihenfolge: Nach dem Aufwachen steht die Lautstaerke
wieder auf dem Startwert der Box (gemessen: 49). Erst wecken, dann setzen.
"""
import ctypes
import queue
import socket
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

PORT = 47365                    # Webdienst des Raumfeld-Hosts
UPNP_RC = "urn:schemas-upnp-org:service:RenderingControl:1"
UPNP_AV = "urn:schemas-upnp-org:service:AVTransport:1"

TAKT = 2.0                      # Sekunden zwischen zwei Abfragen
FRIST = 4.0                     # Zeitgrenze je Netzaufruf

# Wie lange der Rechner unberuehrt sein muss, damit ein Tastendruck als
# "wieder da" zaehlt. Zu kurz gewaehlt griffe es bei jeder Kaffeepause und
# wuerde eine von Hand gedrehte Lautstaerke ueberfahren; zu lang gewaehlt
# greift es nach der Mittagspause nicht mehr. Fuenf Minuten sind der
# Kompromiss – wer es anders will, aendert diese Zahl.
RUHE = 300.0

# Nach dem Einschalten zieht die Box ihren eigenen Startwert erst kurz nach
# dem Hochfahren. Ein einziger Schreibvorgang direkt beim Aufwachen wuerde
# davon ueberschrieben, also wird eine Weile nachkontrolliert.
NACHFASSEN = 20.0

# Ab wann die Boxen von selbst ausgehen duerfen. Zaehlt ab der letzten
# Eingabe – die Raumfeld-App hat dafuer eine eigene Zeit, diese hier ist
# unabhaengig davon, es gilt schlicht, was zuerst kommt.
AUS_NACH = 15 * 60.0

# Ausgeschaltet wird nur, wenn zusaetzlich so lange am Stueck kein Ton lief.
# Eingabe-Leerlauf allein genuegt nicht: Wer einen Film schaut, fasst eine
# Viertelstunde lang nichts an und moechte trotzdem nicht mittendrin die
# Boxen verlieren.
STILL = 60.0

# Findet sich gar nichts, wird hoechstens so oft neu gesucht. Ein Durchgang
# klopft an 254 Adressen – das gehoert nicht in jeden Zweisekundentakt, und
# nach jedem Fehlschlag wird der Abstand verdoppelt. Wer gar keine solche
# Box hat, soll von der Suche nichts merken.
SUCHTAKT = 60.0
SUCHTAKT_MAX = 600.0

# Wie viele vergebliche Versuche an der bekannten Adresse hingenommen
# werden, bevor ueberhaupt das Netz abgesucht wird. Eine Box, die gerade
# nicht antwortet, ist meist dieselbe Box an derselben Adresse.
GEDULD = 5

# Nach dem Aufwachen braucht die Netzwerkkarte einen Moment. So lange wird
# kurz und oft nachgefasst, statt einmal zu scheitern und dann zu schweigen.
WACHFRIST = 30.0

# So lange dauert es gemessen, bis ein `LeaveStandby` im `powerState` steht.
WACHZEIT = 2.0

# Mindestabstand zwischen zwei echten Schaltvorgaengen. Wer auf dem Knopf
# herumdrueckt, aendert nur den Wunsch – ausgefuehrt wird der letzte, und
# hoechstens so oft. Ein Verstaerker, den man im Sekundentakt ein- und
# ausschaltet, dankt es nicht: Jedes Mal faehrt die Endstufe hoch, das
# Relais klackt, und die Box zieht ihren Startwert neu.
SCHALTSPERRE = 4.0


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def leerlauf():
    """Sekunden seit der letzten Maus- oder Tastatureingabe."""
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    # GetTickCount laeuft nach 49 Tagen ueber; dann kommt kurz eine negative
    # Differenz heraus. Die wird zu null – schlimmstenfalls faellt ein
    # einziges Wiederkommen aus.
    return max(0.0, (ctypes.windll.kernel32.GetTickCount()
                     - info.dwTime) / 1000.0)


def erreichbar(ip, frist=0.6):
    if not ip:
        return False
    try:
        with socket.create_connection((ip, PORT), timeout=frist):
            return True
    except OSError:
        return False


def eigenes_netz():
    """Praefix des eigenen /24-Netzes, z. B. 192.168.178."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0].rsplit(".", 1)[0]
    except OSError:
        return None
    finally:
        s.close()


def suchen(bekannt=None):
    """Bekannte Adresse pruefen, sonst das eigene Netz absuchen."""
    if erreichbar(bekannt):
        return bekannt
    praefix = eigenes_netz()
    if not praefix:
        return None
    adressen = ["{}.{}".format(praefix, i) for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=128) as ex:
        treffer = ex.map(lambda a: erreichbar(a, 0.7), adressen)
        for ip, ok in zip(adressen, treffer):
            if ok:
                return ip
    return None


def _holen(url, frist=FRIST):
    with urllib.request.urlopen(url, timeout=frist) as r:
        return r.read()


def renderer(host):
    """[(Name, Lautstaerke-URL, Standby-URL)] je Lautsprecher der Anlage.

    Der Port des Renderers wechselt beim Neustart der Box, deshalb wird die
    Adresse jedes Mal ueber `listDevices` aufgeloest statt gemerkt.
    """
    aus = []
    liste = _holen("http://{}:{}/listDevices".format(host, PORT))
    for dev in ET.fromstring(liste):
        if dev.get("type") != "urn:schemas-upnp-org:device:MediaRenderer:1":
            continue
        ort = dev.get("location")
        basis = ort[:ort.index("/", ort.index("//") + 2)]
        adressen = {}
        for dienst in ET.fromstring(_holen(ort)).findall(".//{*}service"):
            art = dienst.findtext("{*}serviceType")
            if art in (UPNP_RC, UPNP_AV):
                adressen[art] = basis + dienst.findtext("{*}controlURL")
        if UPNP_RC in adressen:
            aus.append((dev.text or "Renderer", adressen[UPNP_RC],
                        adressen.get(UPNP_AV)))
    return aus


def _soap(url, aktion, ns=UPNP_RC, frist=None, **args):
    felder = "".join("<{0}>{1}</{0}>".format(k, v) for k, v in args.items())
    rumpf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
        ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        '<s:Body><u:{0} xmlns:u="{1}">{2}</u:{0}></s:Body></s:Envelope>'
    ).format(aktion, ns, felder).encode("utf-8")
    anfrage = urllib.request.Request(url, data=rumpf, headers={
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPACTION": '"{}#{}"'.format(ns, aktion)})
    with urllib.request.urlopen(anfrage, timeout=frist or FRIST) as r:
        return r.read().decode("utf-8", "replace")


def lesen(url):
    antwort = _soap(url, "GetVolume", InstanceID=0, Channel="Master")
    anfang = antwort.find("<CurrentVolume>")
    if anfang < 0:
        return None
    ende = antwort.index("</CurrentVolume>", anfang)
    return int(antwort[anfang + len("<CurrentVolume>"):ende])


def schreiben(url, wert):
    _soap(url, "SetVolume", InstanceID=0, Channel="Master",
          DesiredVolume=int(wert))


def wecken(url, frist=None):
    """Aus dem Standby holen. Der Zustand steht rund 2 s spaeter im Netz."""
    _soap(url, "LeaveStandby", ns=UPNP_AV, frist=frist, InstanceID=0)


def standby(url, frist=None):
    """In den Standby schicken."""
    _soap(url, "EnterManualStandby", ns=UPNP_AV, frist=frist, InstanceID=0)


def an(host):
    """Ist mindestens ein Raum wach?"""
    xml = _holen("http://{}:{}/getZones".format(host, PORT))
    return any(r.get("powerState") == "ACTIVE"
               for r in ET.fromstring(xml).iter("room"))


_messer = [None]


def ton_laeuft(schwelle=0.004):
    """Kommt gerade Ton aus dem Standard-Ausgang von Windows?

    Gemessen wird am Geraet, nicht an den einzelnen Sitzungen – das ist ein
    Aufruf statt einer Runde durch alle Programme, und es geht hier nur um
    „irgendetwas oder nichts“.

    Im Zweifel „ja“: Wer die Frage nicht beantworten kann, soll die Boxen
    nicht mitten im Film abschalten. Der Aufrufer muss in seinem Thread
    vorher `CoInitialize()` gerufen haben.
    """
    try:
        from comtypes import CLSCTX_ALL, POINTER, cast
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        if _messer[0] is None:
            geraet = AudioUtilities.GetSpeakers()
            schnitt = geraet.Activate(IAudioMeterInformation._iid_,
                                      CLSCTX_ALL, None)
            _messer[0] = cast(schnitt, POINTER(IAudioMeterInformation))
        return _messer[0].GetPeakValue() > schwelle
    except Exception:
        # Auch das Standardgeraet kann wechseln – dann beim naechsten Mal neu
        _messer[0] = None
        return True


NETZFEHLER = (urllib.error.URLError, socket.timeout, OSError, ET.ParseError,
              ValueError)


class Boxen:
    """Haelt die Lautsprecher auf `ziel` und schaltet sie bei Bedarf.

    Zwei Schalter, die unabhaengig voneinander sind:

    `aktiv`    zieht die Lautstaerke nach – wenn die Box angeht, wenn man
               nach laengerer Pause an den Rechner zurueckkommt, und wenn im
               Eingabefeld eine Zahl bestaetigt wird.
    `schalten` schaltet die Boxen mit dem Rechner an und aus.

    Gesetzt wird nur zu diesen Anlaessen, nicht dauernd: Wer die Box
    zwischendurch selbst verstellt, behaelt seinen Wert.

    Alles laeuft im Arbeitsthread. `on_status` wird von dort gerufen und
    bekommt einen Schluessel und die Zusatzangaben – die Uebersetzung in
    lesbaren Text macht die Oberflaeche, sonst haette dieses Modul einen
    Sprachstand zu verwalten.
    """

    def __init__(self, on_status=None):
        self.on_status = on_status
        self.ziel = 65
        self.aktiv = False
        self.schalten = False
        self.host = ""
        self.jobs = queue.Queue()
        self._stop = False
        self._thread = None
        self._renderer = []
        self._war_da = False
        self._war_weg = True         # laenger als RUHE unberuehrt
        self._still_ab = None        # seit wann kein Ton mehr laeuft
        self._letzter = None         # zuletzt gemeldeter An/Aus-Zustand
        self._naechste_suche = 0.0
        self._wunsch = None          # gewuenschter An/Aus-Zustand, noch offen
        self._zuletzt_geschaltet = 0.0
        self._fehlschlaege = 0       # vergebliche Versuche in Folge

    # ---- Aussenseite -----------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._lauf, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.jobs.put(("quit",))

    def jetzt_setzen(self):
        """Sofort anwenden – der Enter-Druck im Eingabefeld."""
        self.jobs.put(("setzen",))

    def neu_suchen(self):
        """Nur nachsehen, ob eine Box da ist – ohne etwas an ihr zu aendern."""
        self.jobs.put(("suchen",))

    def wieder_melden(self):
        """Den naechsten Durchgang wieder melden lassen, auch ohne Wechsel.

        Der Zweisekundentakt meldet sonst nur Aenderungen – sonst
        ueberschriebe er dauernd die Zeile mit der Lautstaerke. Wer die
        Oberflaeche neu aufbaut, hat aber Bedienelemente, die noch nichts
        wissen.
        """
        self._letzter = None

    def an_schalten(self):
        self._wunsch = True
        self.jobs.put(("wunsch",))

    def aus_schalten(self):
        self._wunsch = False
        self.jobs.put(("wunsch",))

    # ---- Arbeitsthread ---------------------------------------------------
    def _lauf(self):
        # Die Tonmessung geht ueber COM; das verlangt eine Anmeldung je
        # Thread. Scheitert sie, laeuft alles andere trotzdem – dann wird
        # nur nicht von selbst ausgeschaltet.
        try:
            from comtypes import CoInitialize, CoUninitialize
            CoInitialize()
        except Exception:
            CoUninitialize = None
        try:
            while not self._stop:
                try:
                    job = self.jobs.get(timeout=TAKT)
                except queue.Empty:
                    job = None
                if job:
                    if job[0] == "quit":
                        break
                    # Ein Auftrag von Hand wartet nicht auf den Suchtakt
                    self._naechste_suche = 0.0
                    if job[0] == "suchen":
                        # Nur nachsehen. Wer die Einstellungen aufmacht, will
                        # wissen, ob eine Box da ist – und nicht, dass ihm
                        # dabei die Lautstaerke verstellt wird.
                        self._renderer = []
                        self.host = ""
                        self._melden("suche")
                        self._zustand_melden()
                        continue
                    if job[0] == "wach":
                        self._nach_dem_schlaf()
                        continue
                    if job[0] == "setzen":
                        self._anwenden(nachfassen=False)
                        continue
                    if job[0] == "wunsch":
                        self._wunsch_umsetzen()
                        continue
                # Auch ohne eingeschaltete Selbsttaetigkeit wird der Zustand
                # abgefragt: Die Anzeige in der Kopfzeile soll stimmen, auch
                # wenn die Box am Geraet oder in der Teufel-App geschaltet
                # wird. Kostet eine Abfrage von rund 5 ms.
                if self.aktiv or self.schalten or self.host or self._renderer:
                    self._pruefen()
        finally:
            if CoUninitialize:
                try:
                    CoUninitialize()
                except Exception:
                    pass

    def _melden(self, schluessel, name="", wert=0):
        # Jede Meldung sagt nebenbei etwas ueber An/Aus. An einer Stelle
        # festgehalten, damit `_pruefen` nur noch Wechsel meldet.
        if schluessel in ("an", "aus", "weg"):
            self._letzter = schluessel
        elif schluessel in ("steht", "gesetzt"):
            self._letzter = "an"
        if self.on_status:
            try:
                self.on_status(schluessel, name, wert)
            except Exception:
                # Beim Beenden haengt der Rueckruf schon ins Leere. Das darf
                # diesen Thread nicht reissen.
                pass

    def _verbinden(self):
        """Adresse und Lautsprecher besorgen, notfalls durch Suchen.

        Das Absuchen des Netzes kostet ein bis zwei Sekunden und klopft an
        254 Adressen. Deshalb zwei Bremsen davor: Solange eine Adresse
        bekannt ist, wird sie erst `GEDULD` Mal einzeln versucht – eine Box,
        die gerade nicht antwortet, ist meist dieselbe Box an derselben
        Stelle. Und schlaegt auch das Suchen fehl, verdoppelt sich der
        Abstand bis zum naechsten Versuch.
        """
        if self._renderer and erreichbar(self.host):
            return True
        if time.time() < self._naechste_suche:
            return False

        if self.host and erreichbar(self.host, 0.8):
            gefunden = self.host
        elif self.host and self._fehlschlaege < GEDULD:
            self._fehlschlaege += 1
            self._naechste_suche = time.time() + TAKT
            return False
        else:
            gefunden = suchen(self.host)

        if not gefunden:
            self._fehlschlaege += 1
            self.host, self._renderer = "", []
            self._naechste_suche = time.time() + min(
                SUCHTAKT * 2 ** max(0, self._fehlschlaege - GEDULD),
                SUCHTAKT_MAX)
            return False

        self._fehlschlaege = 0
        self._naechste_suche = 0.0
        self.host = gefunden
        try:
            self._renderer = renderer(gefunden)
        except NETZFEHLER:
            self._renderer = []
        return bool(self._renderer)

    def _anwenden(self, nachfassen=True):
        """Auf `ziel` bringen. Gibt zurueck, ob die Box erreicht wurde."""
        if not self._verbinden():
            self._melden("weg")
            return False
        ende = time.time() + (NACHFASSEN if nachfassen else 0)
        while True:
            try:
                for name, url, _av in self._renderer:
                    ist = lesen(url)
                    # Lesen ist billig, Schreiben nicht – siehe Modulkopf.
                    if ist == self.ziel:
                        self._melden("steht", name, self.ziel)
                    else:
                        schreiben(url, self.ziel)
                        self._melden("gesetzt", name, self.ziel)
            except NETZFEHLER:
                self._melden("weg")
                self._renderer = []
                return False
            # Ein wartender Auftrag geht vor: Wer waehrend des Nachfassens
            # eine neue Zahl bestaetigt, soll nicht zwanzig Sekunden auf
            # seine Box warten.
            if time.time() >= ende or self._stop or not self.jobs.empty():
                return True
            time.sleep(2.0)

    def schlafen(self):
        """Der Rechner geht schlafen – jetzt sofort ausschalten.

        Laeuft ausnahmsweise im Thread des Aufrufers und nicht ueber die
        Warteschlange: Der Arbeitsthread wird gleich mit eingefroren, sein
        naechster Durchgang kaeme erst nach dem Aufwachen. Windows wartet
        beim Einschlafen nicht lange, deshalb kurze Zeitgrenzen – eine Box,
        die nicht antwortet, darf das Einschlafen nicht aufhalten.
        """
        if not self.schalten or not self._renderer:
            return False
        try:
            for _name, _rc, av in self._renderer:
                if av:
                    standby(av, frist=1.5)
        except NETZFEHLER:
            return False
        self._war_da = False
        self._wunsch = None
        self._still_ab = None
        self._zuletzt_geschaltet = time.time()
        self._melden("aus")
        return True

    def aufwachen(self):
        """Zurueck aus dem Schlaf: alles neu feststellen.

        Der Rechner war weg – das zaehlt als Wiederkommen, ganz gleich, wie
        kurz die letzte Eingabe her ist. Ohne das griffe die Leerlauf-Regel
        gerade dann nicht, wenn man sie braucht: Wer den Rechner per
        Kurzbefehl schlafen legt, hat eine Sekunde vorher noch die Maus
        bewegt, und nach dem Aufwachen steht der Zaehler wieder bei null.
        """
        self._war_weg = True
        self._wunsch = None
        self._zuletzt_geschaltet = 0.0
        self._naechste_suche = 0.0
        self._fehlschlaege = 0
        self._renderer = []          # Adresse frisch aufloesen
        self._letzter = None         # naechste Meldung geht auf jeden Fall raus
        self.jobs.put(("wach",))

    def _nach_dem_schlaf(self):
        """Warten, bis das Netz wieder da ist, und dann Bescheid geben.

        Direkt nach dem Aufwachen hat die Netzwerkkarte noch keine
        Verbindung. Einmal zu scheitern und dann bis zum naechsten Suchtakt
        zu schweigen hiesse, dass die Anzeige in der Kopfzeile eine Minute
        lang etwas Falsches zeigt.
        """
        self._melden("suche")
        ende = time.time() + WACHFRIST
        while self.host and time.time() < ende and not self._stop:
            if erreichbar(self.host, 0.5):
                break
            time.sleep(1.0)
        if not self._verbinden():
            self._melden("weg")
            return
        try:
            da = an(self.host)
        except NETZFEHLER:
            self._melden("weg")
            return
        self._war_da = da
        self._war_weg = False
        # Das Aufwachen selbst ist das Zeichen, dass jemand da ist – nicht
        # der Leerlaufzaehler. Wer den Rechner am Netzschalter oder per
        # Fernstart weckt, hat dabei keine Taste gedrueckt, und die
        # Leerlauf-Regel griffe erst beim naechsten Mausklick.
        if self.schalten and not da:
            self._schalten_jetzt(True)
        elif self.aktiv and da:
            self._anwenden()
        else:
            self._melden("an" if da else "aus")

    def _zustand_melden(self):
        """Suchen und melden, ohne etwas an der Box zu aendern."""
        if not self._verbinden():
            self._melden("weg")
            return
        try:
            self._war_da = an(self.host)
        except NETZFEHLER:
            self._melden("weg")
            return
        self._melden("an" if self._war_da else "aus")

    def _wunsch_umsetzen(self):
        """Einen offenen Schaltwunsch ausfuehren – hoechstens einen.

        Zehn Klicks auf den Knopf sind zehnmal derselbe Wunsch, nicht zehn
        Befehle. Steht die Box am Ende ohnehin schon so, passiert gar
        nichts; sonst wird einmal geschaltet, fruehestens SCHALTSPERRE nach
        dem letzten Mal. Was dazwischen liegt, verfaellt.
        """
        if self._wunsch is None:
            return
        if self._renderer and self._wunsch == self._war_da:
            # Das Hin und Her war ein Nullsummenspiel – nichts zu tun.
            self._wunsch = None
            self._melden("an" if self._war_da else "aus")
            return
        if time.time() - self._zuletzt_geschaltet < SCHALTSPERRE:
            return          # bleibt offen, der naechste Durchgang nimmt ihn
        ein = self._wunsch
        self._wunsch = None
        self._zuletzt_geschaltet = time.time()
        self._schalten_jetzt(ein)

    def _schalten_jetzt(self, ein):
        """An- oder ausschalten und den Zustand danach geradeziehen."""
        if not self._verbinden():
            self._melden("weg")
            return
        try:
            for _name, _rc, av in self._renderer:
                if av:
                    (wecken if ein else standby)(av)
        except NETZFEHLER:
            self._melden("weg")
            self._renderer = []
            return
        self._still_ab = None
        if ein:
            # Der Zustandswechsel steht rund zwei Sekunden spaeter im Netz,
            # und die Box wacht auf ihrem eigenen Startwert auf – erst
            # wecken, dann setzen, und dabei nachfassen.
            time.sleep(WACHZEIT)
            self._war_da = True
            # Immer, auch ohne eingeschaltetes Nachziehen: Die Box wacht auf
            # ihrem eigenen Wert auf (gemessen 49), und in der Kopfzeile
            # steht die gewuenschte Zahl direkt neben dem Schalter. Sie dort
            # zu zeigen und beim Anschalten zu ignorieren waere schwer zu
            # erklaeren. `aktiv` regelt die beiden *anderen* Gelegenheiten.
            self._anwenden()
        else:
            self._war_da = False
            self._melden("aus")

    def _pruefen(self):
        """Ein Durchgang: Ist die Box neu da? Ist der Mensch neu da?"""
        if self._wunsch is not None:
            # Ein Wunsch, der noch in der Sperrzeit haengt, geht vor.
            self._wunsch_umsetzen()
            if self._wunsch is not None:
                return      # weiterhin offen – nichts melden, sonst
                            # spraenge die Anzeige zwischendurch zurueck
        da = False
        if not self._renderer:
            self._verbinden()        # haelt selbst den Suchtakt ein
        if self._renderer:
            try:
                da = an(self.host)
            except NETZFEHLER:
                da = False

        ruhig = leerlauf()
        if ruhig >= RUHE:
            self._war_weg = True
        zurueck = self._war_weg and ruhig < 5.0

        # ---- Anschalten, sobald wieder jemand am Rechner sitzt
        if self.schalten and zurueck and not da and self._renderer:
            self._war_weg = False
            self._schalten_jetzt(True)
            return

        # ---- Lautstaerke nachziehen
        anlass = None
        if self.aktiv and da and not self._war_da:
            anlass = "box"
        elif self.aktiv and da and zurueck:
            anlass = "mensch"
        self._war_da = da
        if anlass:
            self._war_weg = False
            # Beim Einschalten nachfassen, beim Zurueckkommen nicht: da
            # laeuft die Box schon und haelt ihren Wert.
            self._anwenden(nachfassen=(anlass == "box"))
            return
        if zurueck:
            self._war_weg = False

        # ---- Ausschalten, wenn lange niemand da war und nichts mehr laeuft
        if self.schalten and da and ruhig >= AUS_NACH:
            if ton_laeuft():
                self._still_ab = None
            elif self._still_ab is None:
                self._still_ab = time.time()
            elif time.time() - self._still_ab >= STILL:
                self._schalten_jetzt(False)
                return
        else:
            self._still_ab = None

        # Nur bei Wechsel melden, sonst ueberschriebe der Zweisekundentakt
        # dauernd die Zeile mit der Lautstaerke.
        zustand = "an" if da else ("aus" if self._renderer else "weg")
        if zustand != self._letzter:
            self._letzter = zustand
            self._melden(zustand)
