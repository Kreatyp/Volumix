# -*- coding: utf-8 -*-
"""Hauptfenster: Mixer, Einstellungen, Profile, App-Auswahl."""
import ctypes
import functools

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QMenu, QPushButton, QScrollArea,
                               QSizePolicy, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

from . import config, icons
from .audio import AudioEngine, huebscher_name
from .config import MASTER_KEY
from .hooks import InputHook
from .osd import Osd
from . import sprache
from .sprache import SPRACHEN, T
from .theme import PALETTE, Theme
from .widgets import FadeScroll, MixerRow, Slider, ToggleSwitch

SWITCH_MODES = ["none", "carry", "apps100"]     # Beschriftung via T()


def durchsichtig(widget, name):
    """Macht genau dieses Widget durchsichtig – und nur dieses.

    Ohne ID-Selektor gilt ein Stylesheet in Qt auch fuer alle Kinder; die
    Karten darin waeren dann ebenfalls unsichtbar.
    """
    widget.setObjectName(name)
    widget.setStyleSheet("#{} {{ background: transparent; }}".format(name))


def rundknopf(symbol, theme, tooltip="", groesse=38):
    b = QPushButton()
    b.setObjectName("Rund")
    b.setCursor(Qt.PointingHandCursor)
    b.setToolTip(tooltip)
    b.setIcon(icons.pixmap(symbol, 19, theme.muted))
    b.setIconSize(QSize(19, 19))
    b._symbol = symbol
    return b


class _KlickZeile(QWidget):
    """Zeile, die als Ganzes anklickbar ist."""

    geklickt = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.geklickt.emit()


class Karte(QFrame):
    """Panel mit Verlauf und runden Ecken – eine Zeile Stilvorlage."""

    def __init__(self, titel=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Karte")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 14, 18, 16)
        self.lay.setSpacing(10)
        if titel:
            k = QLabel(titel)
            k.setObjectName("Ueberschrift")
            self.lay.addWidget(k)


class MainWindow(QWidget):
    apps_bereit = Signal(list)
    volume_bereit = Signal(str, int)
    meters_bereit = Signal(dict)
    scroll_bereit = Signal(float)
    mute_bereit = Signal()
    rad_gesehen = Signal()

    def __init__(self):
        super().__init__()
        config.migrate()
        config.autostart_pruefen()
        self.cfg = config.load()
        sprache.setzen(self.cfg["sprache"])
        self.theme = Theme(self.cfg["mode"], self.cfg["accent"])
        self.targets = set(self.cfg["targets"])
        self.hidden = set(self.cfg["hidden"] or [])
        self.known = dict.fromkeys(self.cfg["known"] or [], "")
        self.exes = dict(self.cfg["exes"] or {})
        self.profiles = dict(self.cfg["profiles"] or {})
        self.rows = {}
        self.live = set()
        self._meta = {}
        self._items = []
        self._filter = ""

        self.setObjectName("Fenster")
        self.setWindowTitle("Volumix")
        self.setWindowIcon(QIcon(icons.app_logo(64, self.theme.accent)))
        self.resize(560, self.cfg.get("window_h", 720))
        self.setMinimumWidth(560)
        self.setMaximumWidth(560)
        self.setMinimumHeight(360)

        self.osd = Osd(self.theme)
        self.osd.einstellen(self.cfg["osd_size"], self.cfg["osd_x"],
                            self.cfg["osd_y"])

        self.engine = AudioEngine(
            on_apps=lambda items: self.apps_bereit.emit(items),
            on_volume=lambda k, p: self.volume_bereit.emit(k, p),
            on_meters=lambda d: self.meters_bereit.emit(d))
        self.engine.targets = set(self.targets)
        self.engine.switch_mode = self.cfg["switch_mode"]
        self.engine.meters_an = self.cfg["meters"]
        self._tempo_uebernehmen()

        self.apps_bereit.connect(self._apps_uebernehmen)
        self.volume_bereit.connect(self._volume_uebernehmen)
        self.meters_bereit.connect(self._meter_uebernehmen)
        self.scroll_bereit.connect(self._scroll)
        self.mute_bereit.connect(self._mute_umschalten)
        self.rad_gesehen.connect(self._rad_melden)

        self.hook = InputHook(
            on_scroll=lambda r: self.scroll_bereit.emit(r),
            on_mute=lambda: self.mute_bereit.emit(),
            on_gesehen=lambda: self.rad_gesehen.emit())
        self.hook.aktiv = self.cfg["active"]
        self.hook.reverse = self.cfg["reverse"]
        self.hook.media_keys = self.cfg["media_keys"]
        self.hook.hat_ziele = lambda: bool(self.targets)

        self._aufbauen()
        self._vorlage_anwenden()
        self.engine.start()
        self.hook.start()
        self._tray()

        self._takt = QTimer(self)
        self._takt.timeout.connect(lambda: self.engine.job("refresh"))
        self._takt.start(1500)
        self.engine.job("refresh")

    # ---- Aufbau ----------------------------------------------------------
    def _aufbauen(self):
        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(18, 16, 18, 14)
        aussen.setSpacing(10)

        # Kopfzeile – in den Einstellungen ausgeblendet, dort gibt es eine
        # eigene mit Zurueck-Pfeil; die Knoepfe waeren doppelt.
        self.kopfzeile = QWidget()
        kopf = QHBoxLayout(self.kopfzeile)
        kopf.setContentsMargins(0, 0, 0, 0)
        kopf.setSpacing(12)
        self.logo = QLabel()
        self.logo.setFixedSize(40, 40)
        kopf.addWidget(self.logo)
        spalte = QVBoxLayout()
        spalte.setSpacing(2)
        titel = QLabel()
        titel.setObjectName("Wortmarke")
        self.wortmarke = titel
        unter = QLabel(T("untertitel"))
        unter.setObjectName("Untertitel")
        spalte.addWidget(titel)
        spalte.addWidget(unter)
        kopf.addLayout(spalte, 1)
        self.btn_profile = rundknopf("save", self.theme, T("tt_profile"))
        self.btn_profile.clicked.connect(self._profil_menue)
        self.btn_modus = rundknopf("moon", self.theme, T("tt_modus"))
        self.btn_modus.clicked.connect(self._modus_wechseln)
        self.btn_einst = rundknopf("gear", self.theme, T("tt_einstellungen"))
        self.btn_einst.clicked.connect(lambda: self._seite(1))
        for b in (self.btn_profile, self.btn_modus, self.btn_einst):
            kopf.addWidget(b)
        aussen.addWidget(self.kopfzeile)

        # Umschaltbarer Bereich: Mixer / Einstellungen
        self.mixer_seite = self._mixer_bauen()
        self.einst_seite = self._einstellungen_bauen()
        self.einst_seite.hide()
        aussen.addWidget(self.mixer_seite, 1)
        aussen.addWidget(self.einst_seite, 1)

        # Statusleiste
        self.leiste = QFrame()
        self.leiste.setObjectName("Leiste")
        self.leiste.setFixedHeight(46)
        ll = QHBoxLayout(self.leiste)
        ll.setContentsMargins(14, 0, 12, 0)
        self.status = QLabel("")
        self.status.setObjectName("Hinweis")
        ll.addWidget(self.status, 1)
        self.btn_apps = QPushButton(T("apps_waehlen"))
        self.btn_apps.setCursor(Qt.PointingHandCursor)
        self.btn_apps.clicked.connect(self._apps_dialog)
        ll.addWidget(self.btn_apps)
        aussen.addWidget(self.leiste)

    def _mixer_bauen(self):
        seite = QWidget()
        lay = QVBoxLayout(seite)
        lay.setContentsMargins(0, 0, 0, 0)

        self.karte = Karte(T("mixer"))
        lay.addWidget(self.karte, 1)

        # Suchfeld – erscheint erst ab genug Apps
        self.suche = QLineEdit()
        self.suche.setPlaceholderText(T("app_suchen"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(self._suchen)
        self.suche.hide()
        self.karte.lay.addWidget(self.suche)

        self.rollbereich = QScrollArea()
        self.rollbereich.setWidgetResizable(True)
        self.rollbereich.setFrameShape(QFrame.NoFrame)
        self.rollbereich.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Durchsichtig, damit der Verlauf der Karte durchscheint. Der Selektor
        # MUSS auf die ID eingeschraenkt sein – ein Stylesheet ohne Selektor
        # schlaegt in Qt auf alle Kinder durch und macht sie ebenfalls leer.
        durchsichtig(self.rollbereich.viewport(), "MixerFlaeche")
        self.inhalt = QWidget()
        durchsichtig(self.inhalt, "MixerInhalt")
        self.inhalt_lay = QVBoxLayout(self.inhalt)
        self.inhalt_lay.setContentsMargins(0, 0, 4, 0)
        self.inhalt_lay.setSpacing(3)
        self.inhalt_lay.addStretch(1)
        self.rollbereich.setWidget(self.inhalt)
        self.karte.lay.addWidget(self.rollbereich, 1)

        self.fade = FadeScroll(self.theme, parent=self.rollbereich)
        self.rollbereich.verticalScrollBar().valueChanged.connect(self._fade)
        return seite

    def _abschnitt(self, text):
        huelle = QWidget()
        durchsichtig(huelle, "Abschnitt")
        huelle.setFixedHeight(30)
        z = QHBoxLayout(huelle)
        z.setContentsMargins(14, 8, 14, 2)
        z.setSpacing(12)
        k = QLabel(text)
        k.setObjectName("Ueberschrift")
        z.addWidget(k)
        # Farbe kommt aus der Stilvorlage, nicht aus einem eigenen Stylesheet:
        # ein hier fest gesetzter Wert bliebe beim Moduswechsel stehen und die
        # Linie waere im hellen Modus noch die dunkle von vorher.
        linie = QFrame()
        linie.setObjectName("Trennlinie")
        linie.setFrameShape(QFrame.NoFrame)
        linie.setFixedHeight(1)
        z.addWidget(linie, 1)
        return huelle

    # ---- Einstellungen ---------------------------------------------------
    def _einstellungen_bauen(self):
        seite = QWidget()
        lay = QVBoxLayout(seite)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        kopf = QHBoxLayout()
        zurueck = rundknopf("back", self.theme, T("tt_zurueck"))
        zurueck.clicked.connect(lambda: self._seite(0))
        self.btn_zurueck = zurueck
        kopf.addWidget(zurueck)
        t = QLabel(T("einstellungen"))
        t.setObjectName("Titel")
        kopf.addWidget(t, 1)
        lay.addLayout(kopf)

        roll = QScrollArea()
        roll.setWidgetResizable(True)
        roll.setFrameShape(QFrame.NoFrame)
        roll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Sonst liegt hier ein schwarzer Kasten hinter den Karten
        durchsichtig(roll.viewport(), "EinstFlaeche")
        innen = QWidget()
        durchsichtig(innen, "EinstInhalt")
        ilay = QVBoxLayout(innen)
        ilay.setContentsMargins(0, 0, 6, 0)
        ilay.setSpacing(12)
        roll.setWidget(innen)
        lay.addWidget(roll, 1)
        self._einst_roll = roll
        self._einst_inhalt = innen
        # Abblendung nach oben und unten, sobald es etwas zu scrollen gibt
        self._einst_schleier = FadeScroll(self.theme, parent=roll,
                                          auf_karte=False)
        roll.verticalScrollBar().valueChanged.connect(self._einst_fade)

        # --- Design ---
        k = Karte(T("design"))
        zeile = QHBoxLayout()
        zeile.setAlignment(Qt.AlignTop)
        links = QVBoxLayout()
        links.setSpacing(6)
        links.setAlignment(Qt.AlignTop)
        links.addWidget(QLabel(T("modus")))
        modus = QHBoxLayout()
        self.modus_gruppe = QButtonGroup(self)
        for wert, name in (("dark", T("dunkel")), ("light", T("hell"))):
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(self.theme.mode == wert)
            b.clicked.connect(functools.partial(self._modus_setzen, wert))
            self.modus_gruppe.addButton(b)
            modus.addWidget(b)
        modus.addStretch(1)
        links.addLayout(modus)
        zeile.addLayout(links)
        zeile.addStretch(1)

        rechts = QVBoxLayout()
        rechts.setSpacing(6)
        rechts.setAlignment(Qt.AlignTop)
        rechts.addWidget(QLabel(T("farbe")))
        raster = QVBoxLayout()
        raster.setSpacing(6)
        self.farbknoepfe = {}
        for i in range(0, len(PALETTE), 6):
            r = QHBoxLayout()
            r.setSpacing(7)
            for key, name, dunkel, hell in PALETTE[i:i + 6]:
                b = _Farbpunkt(key, self.theme, name)
                b.clicked.connect(functools.partial(self._farbe_setzen, key))
                self.farbknoepfe[key] = b
                r.addWidget(b)
            r.addStretch(1)
            raster.addLayout(r)
        rechts.addLayout(raster)
        zeile.addLayout(rechts)
        k.lay.addLayout(zeile)
        ilay.addWidget(k)

        # --- Steuerung ---
        k = Karte(T("steuerung"))
        tempo_kopf = QHBoxLayout()
        tempo_kopf.setSpacing(4)
        tempo_kopf.addWidget(QLabel(T("geschwindigkeit")))
        self.btn_tempo_hilfe = self._fragezeichen(T("tempo_hilfe"))
        tempo_kopf.addWidget(self.btn_tempo_hilfe)
        tempo_kopf.addStretch(1)
        k.lay.addLayout(tempo_kopf)
        self.tempo_wert = QLabel("{} %".format(self.cfg["speed"]))
        k.lay.addLayout(self._regler_zeile(
            T("tempo_gesamt"), self.cfg["speed"], 10, 100,
            self._tempo_setzen, self.tempo_wert, breite=76))
        self.tempo_apps_wert = QLabel("{} %".format(self.cfg["speed_apps"]))
        k.lay.addLayout(self._regler_zeile(
            T("tempo_apps"), self.cfg["speed_apps"], 10, 100,
            self._tempo_apps_setzen, self.tempo_apps_wert, breite=76))
        self.sw_aktiv = self._schalter_zeile(
            k, T("steuerung_aktiv"), self.cfg["active"], self._aktiv_setzen)
        self._schalter_zeile(
            k, T("scrollen_verwenden"), not self.cfg["media_keys"],
            self._eingabe_setzen)
        # Gilt fuer beide Eingabearten, deshalb nicht „Scrollrichtung“
        self._schalter_zeile(
            k, T("richtung_umkehren"), self.cfg["reverse"],
            self._reverse_setzen)
        self._schalter_zeile(
            k, T("mit_windows_starten"), config.get_autostart(),
            lambda an: config.set_autostart(an))

        wechsel = QHBoxLayout()
        wechsel.addWidget(QLabel(T("beim_wechsel")))
        self.btn_hilfe = self._fragezeichen(T("wechsel_hilfe"))
        wechsel.addWidget(self.btn_hilfe)
        wechsel.addStretch(1)
        k.lay.addLayout(wechsel)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.wechsel_gruppe = QButtonGroup(self)
        for wert in SWITCH_MODES:
            b = QPushButton(T("wechsel_" + wert))
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(self.cfg["switch_mode"] == wert)
            b.clicked.connect(functools.partial(self._wechsel_setzen, wert))
            self.wechsel_gruppe.addButton(b)
            chips.addWidget(b)
        chips.addStretch(1)
        k.lay.addLayout(chips)
        ilay.addWidget(k)

        # --- Anzeige ---
        k = Karte(T("anzeige"))
        self._schalter_zeile(
            k, T("live_pegel"), self.cfg["meters"],
            self._meter_setzen)
        self._schalter_zeile(
            k, T("osd_anzeigen"), self.cfg["osd_enabled"],
            self._osd_setzen)
        self.osd_groesse_wert = QLabel("{} %".format(self.cfg["osd_size"]))
        k.lay.addLayout(self._regler_zeile(
            T("groesse"), self.cfg["osd_size"], 10, 100, self._osd_groesse,
            self.osd_groesse_wert))
        # Die Mitte trifft man von Hand nie genau – dort rastet es ein.
        self.osd_x_wert = QLabel("{} %".format(self.cfg["osd_x"]))
        k.lay.addLayout(self._regler_zeile(
            T("position_waagerecht"), self.cfg["osd_x"], 0, 100, self._osd_x,
            self.osd_x_wert, rastpunkte=(50,)))
        self.osd_y_wert = QLabel("{} %".format(self.cfg["osd_y"]))
        k.lay.addLayout(self._regler_zeile(
            T("position_senkrecht"), self.cfg["osd_y"], 0, 100, self._osd_y,
            self.osd_y_wert, rastpunkte=(50,)))
        ilay.addWidget(k)

        # --- Sprache ---
        k = Karte(T("sprache_abschnitt"))
        sp = QHBoxLayout()
        sp.setSpacing(8)
        self.sprach_gruppe = QButtonGroup(self)
        for kuerzel, name in SPRACHEN:
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(self.cfg["sprache"] == kuerzel)
            b.clicked.connect(functools.partial(self._sprache_setzen, kuerzel))
            self.sprach_gruppe.addButton(b)
            sp.addWidget(b)
        sp.addStretch(1)
        k.lay.addLayout(sp)
        ilay.addWidget(k)

        ilay.addStretch(1)
        return seite

    def _regler_zeile(self, text, wert, lo, hi, rueckruf, anzeige,
                      rastpunkte=(), breite=160):
        z = QHBoxLayout()
        z.setContentsMargins(0, 5, 0, 5)      # Luft nach oben und unten
        z.setSpacing(14)
        lbl = QLabel(text)
        lbl.setFixedWidth(breite)
        z.addWidget(lbl)
        s = Slider(rastpunkte=rastpunkte)
        s.setRange(lo, hi)
        s.setValue(wert)
        s.valueChanged.connect(rueckruf)
        z.addWidget(s, 1)
        anzeige.setFixedWidth(46)
        anzeige.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        z.addWidget(anzeige)
        return z

    def _schalter_zeile(self, karte, text, wert, rueckruf):
        """Schalterzeile – die ganze Zeile schaltet um, nicht nur der Knopf."""
        zeile = _KlickZeile()
        # Ohne das schrumpft die Zeile auf ihren Inhalt und der Schalter
        # rutscht nach links statt am rechten Rand zu bleiben.
        zeile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        z = QHBoxLayout(zeile)
        z.setContentsMargins(0, 3, 0, 3)
        z.addWidget(QLabel(text), 1)
        sw = ToggleSwitch(wert, self.theme)
        sw.toggled.connect(rueckruf)
        z.addWidget(sw)
        zeile.geklickt.connect(lambda: sw.setChecked(not sw.isChecked(),
                                                     melden=True))
        karte.lay.addWidget(zeile)
        return sw

    def _fragezeichen(self, text):
        """Kleines Fragezeichen, das beim Zeigen den Text erklaert."""
        b = QPushButton()
        b.setObjectName("Flach")
        b.setFixedSize(24, 24)
        b.setCursor(Qt.WhatsThisCursor)
        b.setIcon(icons.pixmap("help", 16, self.theme.muted))
        b.setIconSize(QSize(16, 16))
        b.setToolTip(text)
        return b

    # ---- Aussehen --------------------------------------------------------
    def _vorlage_anwenden(self):
        # Auf die Anwendung, nicht aufs Fenster: Erklaerblasen sind eigene
        # Fenster und wuerden ein Widget-Stylesheet gar nicht sehen.
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(self.theme.qss())
        else:
            self.setStyleSheet(self.theme.qss())
        dpr = self.devicePixelRatioF()
        self.logo.setPixmap(icons.app_logo(40, self.theme.accent, dpr))
        if getattr(self, "wortmarke", None) is not None:
            self.wortmarke.setPixmap(icons.wortmarke(27, self.theme.fg, dpr))
        self.setWindowIcon(QIcon(icons.app_logo(64, self.theme.accent, dpr)))
        for b in (self.btn_profile, self.btn_modus, self.btn_einst,
                  getattr(self, "btn_zurueck", None)):
            if b is not None:
                name = "sun" if (b is self.btn_modus and self.theme.hell) else b._symbol
                b.setIcon(icons.pixmap(name, 19, self.theme.muted, dpr))
        for name in ("btn_hilfe", "btn_tempo_hilfe"):
            b = getattr(self, name, None)
            if b is not None:
                b.setIcon(icons.pixmap("help", 16, self.theme.muted, dpr))
        for punkt in getattr(self, "farbknoepfe", {}).values():
            punkt.theme = self.theme
            punkt.update()
        for row in self.rows.values():
            row.theme_wechseln(self.theme)
        self.fade.theme = self.theme
        self.osd.einstellen(self.cfg["osd_size"], self.cfg["osd_x"],
                            self.cfg["osd_y"], self.theme)
        if getattr(self, "tray", None):
            self.tray.setIcon(QIcon(icons.app_logo(64, self.theme.accent)))
        self._titelleiste_faerben()

    def _titelleiste_faerben(self):
        """Titelleiste und Fensterrahmen in die App-Farbe bringen.

        Windows 11 laesst das ueber DWM zu – so muss die Leiste nicht
        nachgebaut werden und Verschieben, Minimieren und Schliessen
        verhalten sich weiter wie gewohnt.
        """
        try:
            dwm = ctypes.windll.dwmapi
            hwnd = int(self.winId())

            def colorref(hexfarbe):
                c = hexfarbe.lstrip("#")
                r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
                return ctypes.c_int(b << 16 | g << 8 | r)   # 0x00BBGGRR

            dunkel = ctypes.c_int(0 if self.theme.hell else 1)
            for attr in (20, 19):                    # heller/dunkler Modus
                dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), attr,
                                          ctypes.byref(dunkel),
                                          ctypes.sizeof(dunkel))
            for attr, wert in ((35, colorref(self.theme.bg)),      # Leiste
                               (36, colorref(self.theme.fg)),      # Schrift
                               (34, colorref(self.theme.bg))):     # Rahmen
                dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), attr,
                                          ctypes.byref(wert),
                                          ctypes.sizeof(wert))
        except Exception:
            pass

    def _seite(self, nr):
        self.view = nr
        if nr == 1 and self.mixer_seite.isVisible():
            self._mixer_hoehe = self.height()
        self.mixer_seite.setVisible(nr == 0)
        self.einst_seite.setVisible(nr == 1)
        self.leiste.setVisible(nr == 0)
        self.kopfzeile.setVisible(nr == 0)
        if nr == 1:
            # So weit aufziehen, wie der Inhalt braucht – aber nie weiter.
            QTimer.singleShot(0, self._einst_hoehe)
        else:
            zurueck = getattr(self, "_mixer_hoehe", None)
            if zurueck:
                self.resize(self.width(), zurueck)
            QTimer.singleShot(0, self._hoehe_anpassen)

    def _modus_wechseln(self):
        self._modus_setzen("dark" if self.theme.hell else "light")

    def _modus_setzen(self, modus):
        self.cfg["mode"] = modus
        self.theme.set(modus, self.theme.accent_key)
        icons.cache_leeren()
        self._vorlage_anwenden()
        # ueber T() vergleichen, sonst greift der Abgleich nur auf Deutsch
        soll = T("hell") if modus == "light" else T("dunkel")
        for b in self.modus_gruppe.buttons():
            b.setChecked(b.text() == soll)
        self._speichern()

    def _farbe_setzen(self, key):
        self.cfg["accent"] = key
        self.theme.set(self.theme.mode, key)
        icons.cache_leeren()
        self._vorlage_anwenden()
        self._speichern()

    # ---- Mixer -----------------------------------------------------------
    def _apps_uebernehmen(self, items):
        neu = False
        for it in items:
            if it["key"] == MASTER_KEY:
                continue
            if it["key"] not in self.known:
                self.known[it["key"]] = it["name"]
                neu = True
            if it.get("exe") and self.exes.get(it["key"]) != it["exe"]:
                self.exes[it["key"]] = it["exe"]
                neu = True
            self._meta[it["key"]] = it["name"]
        self.live = {it["key"] for it in items if it["key"] != MASTER_KEY}
        if neu:
            self._speichern()

        sichtbar = [it for it in items
                    if it["key"] == MASTER_KEY or it["key"] not in self.hidden]
        if self._filter:
            sichtbar = [it for it in sichtbar
                        if self._filter in it["name"].lower()
                        or it["key"] == MASTER_KEY]
        self._items = sichtbar
        self._zeilen_setzen(sichtbar)
        self._status_setzen()
        # Suchfeld erst zeigen, wenn es sich lohnt
        self.suche.setVisible(len([i for i in items
                                   if i["key"] not in self.hidden]) > 7
                              or bool(self._filter))
        if getattr(self, "_dialog", None) is not None:
            self._dialog.liste_fuellen()

    def _zeilen_setzen(self, items):
        keys = [it["key"] for it in items]
        if set(keys) != set(self.rows.keys()):
            for row in self.rows.values():
                row.setParent(None)
                row.deleteLater()
            self.rows.clear()
            while self.inhalt_lay.count() > 1:
                w = self.inhalt_lay.takeAt(0)
                if w.widget():
                    w.widget().setParent(None)
            master = [it for it in items if it["key"] == MASTER_KEY]
            apps = [it for it in items if it["key"] != MASTER_KEY]
            pos = 0
            for titel, gruppe in ((T("alles"), master),
                                  (T("einzelne_apps"), apps)):
                if not gruppe:
                    continue
                self.inhalt_lay.insertWidget(pos, self._abschnitt(titel))
                pos += 1
                for it in gruppe:
                    row = MixerRow(it, it["key"] in self.targets, self.theme,
                                   self.cfg["meters"])
                    row.toggled.connect(self._ziel_umschalten)
                    row.volume_changed.connect(self._regler_bewegt)
                    row.mute_clicked.connect(self._stumm)
                    self.rows[it["key"]] = row
                    self.inhalt_lay.insertWidget(pos, row)
                    pos += 1
        else:
            for it in items:
                row = self.rows.get(it["key"])
                if row is not None:
                    row.aktualisieren(it)
                    row.set_gewaehlt(it["key"] in self.targets)
        QTimer.singleShot(0, self._fade)
        QTimer.singleShot(0, self._hoehe_anpassen)

    def _einst_hoehe(self):
        """Einstellungen so hoch wie noetig – und nicht hoeher.

        Ohne Obergrenze liesse sich das Fenster ins Leere ziehen.
        """
        if not self.einst_seite.isVisible():
            return
        inhalt = self._einst_inhalt.sizeHint().height()
        rest = self.height() - self._einst_roll.viewport().height()
        gewuenscht = inhalt + rest + 8
        platz = self.screen().availableGeometry().height() - 70
        hoechstens = max(400, min(platz, gewuenscht))
        self.setMaximumHeight(hoechstens)
        self.resize(self.width(), hoechstens)
        QTimer.singleShot(0, self._einst_fade)

    def _einst_fade(self):
        leiste = self._einst_roll.verticalScrollBar()
        sicht = self._einst_roll.viewport()
        self._einst_schleier.setGeometry(0, 0, sicht.width(), sicht.height())
        self._einst_schleier.zeigen(leiste.value() > 4,
                                    leiste.value() < leiste.maximum() - 4)
        self._einst_schleier.raise_()

    def _hoehe_anpassen(self):
        """Fenster nicht hoeher machen, als die Liste braucht.

        Der Nutzer darf kleiner ziehen; groesser als noetig ist nur leerer
        Raum. Beim ersten Aufbau wird die passende Hoehe gesetzt.
        """
        if not self.mixer_seite.isVisible():
            return
        inhalt = self.inhalt.sizeHint().height()
        rest = self.height() - self.rollbereich.viewport().height()
        gewuenscht = inhalt + rest + 6
        hoechstens = max(360, min(self.screen().availableGeometry().height() - 80,
                                  gewuenscht))
        self.setMaximumHeight(hoechstens)
        if not getattr(self, "_hoehe_gesetzt", False):
            self._hoehe_gesetzt = True
            self.resize(self.width(), min(hoechstens,
                                          self.cfg.get("window_h", 720)))
        elif self.height() > hoechstens:
            self.resize(self.width(), hoechstens)

    def _volume_uebernehmen(self, key, prozent):
        row = self.rows.get(key)
        if row is not None:
            row.set_volume(prozent / 100.0)
            # gilt auch fuers Daumenrad: ganz runtergedreht heisst stumm
            self._stumm_abgleichen(key, prozent / 100.0)

    def _meter_uebernehmen(self, werte):
        if not self.cfg["meters"]:
            return
        for key, row in self.rows.items():
            if key == MASTER_KEY:
                # Gesamt zeigt den lautesten Ausschlag aller Apps
                row.set_pegel(max(werte.values()) if werte else 0.0)
            else:
                row.set_pegel(werte.get(key, 0.0))

    def _ziel_umschalten(self, key, an):
        if an:
            if key == MASTER_KEY:
                vorher = [k for k in self.targets if k != MASTER_KEY]
                self.targets = {MASTER_KEY}
                if vorher:
                    self.engine.job("switch", "master", vorher)
            else:
                vom_master = MASTER_KEY in self.targets
                self.targets.discard(MASTER_KEY)
                self.targets.add(key)
                if vom_master:
                    self.engine.job("switch", "apps", [key])
        else:
            self.targets.discard(key)
        self.engine.targets = set(self.targets)
        for k, row in self.rows.items():
            row.set_gewaehlt(k in self.targets)
        self._speichern()
        self.engine.job("refresh")

    def _regler_bewegt(self, key, wert, endgueltig):
        self.engine.job("setvol", key, wert)
        if endgueltig:
            self._stumm_abgleichen(key, wert)

    def _stumm_abgleichen(self, key, wert):
        """0 % schaltet stumm, alles darueber hebt die Stummschaltung auf.

        Sonst haette man zwei Zustaende fuer dieselbe Sache: Regler ganz
        unten, aber laut Windows nicht stumm.
        """
        row = self.rows.get(key)
        if row is None:
            return
        soll = wert <= 0.005
        if soll != row.muted:
            self._stumm(key, soll)

    def _stumm(self, key, an):
        row = self.rows.get(key)
        if row is not None:
            row.set_muted(an)
        self.engine.job("mute", key, an)

    def _scroll(self, rastungen):
        if not self.targets:
            return
        self.engine.job("scroll", rastungen)
        QTimer.singleShot(120, self._osd_zeigen)

    def _mute_umschalten(self):
        for key in list(self.targets):
            self._stumm(key, not self.engine.get_mute(key))

    def _rad_melden(self):
        if not self.hook.aktiv:
            self._melden(T("rad_aus"))
        elif not self.targets:
            self._melden(T("rad_kein_ziel"))

    def _osd_zeigen(self):
        if not self.cfg["osd_enabled"] or not self.targets:
            return
        # Nicht die fertigen Zeilen-Symbole weiterreichen: die sind 32 px gross
        # und wuerden in der Einblendung hochskaliert – das sieht matschig aus.
        # Stattdessen Pfad und Name geben, die Einblendung rendert selbst
        # in der Groesse, die sie gerade braucht.
        quellen, werte = [], []
        for key in sorted(self.targets):
            row = self.rows.get(key)
            name = self._meta.get(key) or huebscher_name(key)
            quellen.append((key, self.exes.get(key), name))
            if row is not None:
                werte.append(row.regler.value())
        if not werte:
            return
        schnitt = int(round(sum(werte) / len(werte)))
        self.osd.zeigen(quellen, schnitt, akzent=self.theme.accent)

    def _suchen(self, text):
        self._filter = text.strip().lower()
        self.engine.job("refresh")

    def _fade(self):
        leiste = self.rollbereich.verticalScrollBar()
        self.fade.setGeometry(0, 0, self.rollbereich.viewport().width(),
                              self.rollbereich.viewport().height())
        self.fade.zeigen(leiste.value() > 4,
                         leiste.value() < leiste.maximum() - 4)
        self.fade.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.einst_seite.isVisible():
            QTimer.singleShot(0, self._einst_fade)
        else:
            QTimer.singleShot(0, self._fade)
            self.cfg["window_h"] = self.height()

    # ---- Profile ---------------------------------------------------------
    def _profil_menue(self):
        m = QMenu(self)
        m.setStyleSheet(self.theme.qss())
        if self.profiles:
            for name in sorted(self.profiles):
                a = m.addAction(name)
                a.triggered.connect(functools.partial(self._profil_laden, name))
            m.addSeparator()
            entfernen = m.addMenu(T("profil_loeschen"))
            for name in sorted(self.profiles):
                a = entfernen.addAction(name)
                a.triggered.connect(functools.partial(self._profil_loeschen, name))
            m.addSeparator()
        a = m.addAction(T("profil_speichern"))
        a.triggered.connect(self._profil_speichern)
        m.exec(self.btn_profile.mapToGlobal(self.btn_profile.rect().bottomLeft()))

    def _profil_speichern(self):
        name, ok = QInputDialog.getText(self, T("profil_speichern_titel"),
                                        T("profil_name"))
        if not ok or not name.strip():
            return
        name = name.strip()
        apps = {}
        master = None
        for it in self._items:
            if it["key"] == MASTER_KEY:
                master = it["volume"]
            else:
                apps[it["key"]] = it["volume"]
        self.profiles[name] = {"master": master, "apps": apps}
        self._speichern()
        self._melden(T("profil_gespeichert", name=name))

    def _profil_laden(self, name):
        profil = self.profiles.get(name)
        if profil:
            self.engine.job("profile", profil)
            self._melden(T("profil_geladen", name=name))

    def _profil_loeschen(self, name):
        if self.profiles.pop(name, None) is not None:
            self._speichern()
            self._melden(T("profil_geloescht", name=name))

    # ---- Statusleiste ----------------------------------------------------
    def _status_setzen(self):
        sichtbar = [k for k in self.live if k not in self.hidden]
        if not self.live:
            self.status.setText(T("keine_app_aktiv"))
        else:
            self.status.setText(T("x_von_y", a=len(sichtbar), b=len(self.live)))

    def _melden(self, text, ms=1800):
        self.status.setText(text)
        QTimer.singleShot(ms, self._status_setzen)

    # ---- Einstellungs-Rueckrufe ------------------------------------------
    def _schrittweite(self, prozent):
        s = max(10.0, min(100.0, float(prozent)))
        return 0.8 + (s - 10.0) / 90.0 * 3.4        # 0,8 .. 4,2 Punkte

    def _tempo_uebernehmen(self):
        """Beide Schrittweiten an die Audio-Schicht durchreichen."""
        self.engine.speed_step = self._schrittweite(self.cfg["speed"])
        self.engine.speed_step_apps = self._schrittweite(
            self.cfg["speed_apps"])

    def _tempo_setzen(self, wert):
        wert = int(round(wert / 10.0) * 10)
        self.cfg["speed"] = wert
        self.tempo_wert.setText("{} %".format(wert))
        self._tempo_uebernehmen()
        self._speichern()

    def _tempo_apps_setzen(self, wert):
        wert = int(round(wert / 10.0) * 10)
        self.cfg["speed_apps"] = wert
        self.tempo_apps_wert.setText("{} %".format(wert))
        self._tempo_uebernehmen()
        self._speichern()

    def _aktiv_setzen(self, an):
        self.cfg["active"] = an
        self.hook.aktiv = an
        self._speichern()

    def _eingabe_setzen(self, scrollen):
        self.cfg["media_keys"] = not scrollen
        self.hook.media_keys = not scrollen
        self.hook.start()
        self._melden(T("rad_aktiv") if scrollen else T("tasten_aktiv"))
        self._speichern()

    def _reverse_setzen(self, an):
        self.cfg["reverse"] = an
        self.hook.reverse = an
        self._speichern()

    def _wechsel_setzen(self, wert):
        self.cfg["switch_mode"] = wert
        self.engine.switch_mode = wert
        for b in self.wechsel_gruppe.buttons():
            b.setChecked(b.text() == T("wechsel_" + wert))
        self._speichern()

    def _sprache_setzen(self, kuerzel):
        """Sprache wechseln – die Oberflaeche wird dafuer neu aufgebaut.

        Die Beschriftungen stecken in den Widgets; einzeln nachziehen waere
        fehleranfaellig. Der Neuaufbau dauert Millisekunden und ist derselbe
        Weg wie beim Wechsel der Bildschirm-Skalierung.
        """
        if kuerzel == self.cfg["sprache"]:
            return
        self.cfg["sprache"] = kuerzel
        sprache.setzen(kuerzel)
        self._speichern()
        merker = self.view if hasattr(self, "view") else 1
        self._neu_aufbauen(merker)

    def _neu_aufbauen(self, seite=0):
        """Fenster verwerfen und frisch aufbauen (Sprachwechsel)."""
        alt = self.layout()
        if alt is not None:
            while alt.count():
                eintrag = alt.takeAt(0)
                w = eintrag.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            QWidget().setLayout(alt)      # altes Layout freigeben
        self.rows.clear()
        self._aufbauen()
        self._vorlage_anwenden()
        self._seite(seite)
        self.engine.job("refresh")

    def _meter_setzen(self, an):
        self.cfg["meters"] = an
        self.engine.meters_an = an
        for row in self.rows.values():
            row.set_meter_sichtbar(an)
        self._speichern()

    def _osd_setzen(self, an):
        self.cfg["osd_enabled"] = an
        self._speichern()

    def _osd_groesse(self, wert):
        self.cfg["osd_size"] = wert
        self.osd_groesse_wert.setText("{} %".format(wert))
        self._osd_vorschau()

    def _osd_x(self, wert):
        self.cfg["osd_x"] = wert
        self.osd_x_wert.setText("{} %".format(wert))
        self._osd_vorschau()

    def _osd_y(self, wert):
        self.cfg["osd_y"] = wert
        self.osd_y_wert.setText("{} %".format(wert))
        self._osd_vorschau()

    def _osd_vorschau(self):
        self.osd.einstellen(self.cfg["osd_size"], self.cfg["osd_x"],
                            self.cfg["osd_y"])
        # Dieselbe Form wie im Betrieb: (Schluessel, Pfad, Name). Die
        # Einblendung rendert das Symbol selbst in der passenden Groesse.
        self.osd.zeigen([(MASTER_KEY, None, "Volumix")], 60,
                        akzent=self.theme.accent)
        self._speichern()

    # ---- App-Auswahl -----------------------------------------------------
    def _apps_dialog(self):
        # Hauptfenster abdunkeln, damit der Dialog im Vordergrund steht
        schleier = QWidget(self)
        schleier.setObjectName("Abdunklung")
        schleier.setGeometry(self.rect())
        schleier.show()
        schleier.raise_()
        d = AppsDialog(self)
        self._dialog = d
        d.move(self.mapToGlobal(self.rect().center())
               - d.rect().center())
        try:
            d.exec()
        finally:
            self._dialog = None
            schleier.deleteLater()

    # ---- Ablage / Tray ---------------------------------------------------
    def _speichern(self):
        self.cfg.update({
            "targets": sorted(self.targets),
            "hidden": sorted(self.hidden),
            "known": sorted(self.known.keys()),
            "exes": self.exes,
            "profiles": self.profiles,
        })
        config.save(self.cfg)

    def _tray(self):
        self.tray = QSystemTrayIcon(QIcon(icons.app_logo(64, self.theme.accent)),
                                    self)
        self.tray.setToolTip("Volumix")
        m = QMenu()
        a_open = QAction(T("oeffnen"), self)
        a_open.triggered.connect(self._nach_vorn)
        m.addAction(a_open)
        self.a_aktiv = QAction(T("steuerung_aktiv"), self, checkable=True)
        self.a_aktiv.setChecked(self.cfg["active"])
        self.a_aktiv.triggered.connect(self._tray_aktiv)
        m.addAction(self.a_aktiv)
        m.addSeparator()
        a_end = QAction(T("beenden"), self)
        a_end.triggered.connect(self._beenden)
        m.addAction(a_end)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(
            lambda grund: self._nach_vorn()
            if grund == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _tray_aktiv(self, an):
        self.cfg["active"] = an
        self.hook.aktiv = an
        self.sw_aktiv.setChecked(an)
        self._speichern()

    def _nach_vorn(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        """Schliessen minimiert nur – beendet wird ueber das Tray-Menue."""
        e.ignore()
        self.hide()

    def _beenden(self):
        self._speichern()
        self.hook.stop()
        # Erst abklemmen, dann stoppen: der Audio-Thread laeuft noch einen
        # Durchgang weiter und wuerde sonst an ein totes Fenster melden.
        self.engine.on_apps = None
        self.engine.on_volume = None
        self.engine.on_meters = None
        self.engine.stop()
        self.tray.hide()
        QApplication.quit()


class _Farbpunkt(QPushButton):
    """Runder Farbknopf mit Ring, wenn gewaehlt."""

    def __init__(self, key, theme, name, parent=None):
        super().__init__(parent)
        self.key = key
        self.theme = theme
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(name)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, e):
        from PySide6.QtGui import QColor, QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        farbe = QColor(self.theme.accent_of(self.key))
        gewaehlt = self.theme.accent_key == self.key
        d = 22
        x = (self.width() - d) / 2
        y = (self.height() - d) / 2
        if gewaehlt:
            stift = QPen(QColor(self.theme.fg), 2)
            p.setPen(stift)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(Qt.NoPen)
        p.setBrush(farbe)
        p.drawEllipse(int(x), int(y), d, d)


class AppsDialog(QDialog):
    """Welche Apps im Mixer erscheinen.

    Rahmenlos und ueber dem abgedunkelten Hauptfenster – ein Fenster mit
    Windows-Titelleiste wirkt hier wie ein Fremdkoerper.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.haupt = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.vorgemerkt = set(parent.hidden)

        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(0, 0, 0, 0)
        karte = QFrame()
        karte.setObjectName("Karte")
        aussen.addWidget(karte)
        self.setStyleSheet(parent.theme.qss())
        self.resize(parent.width() - 60, min(parent.height() - 70, 520))

        lay = QVBoxLayout(karte)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)

        kopf = QHBoxLayout()
        t = QLabel(T("sichtbare_apps"))
        t.setObjectName("DialogTitel")
        kopf.addWidget(t, 1)
        hilfe = QPushButton()
        hilfe.setObjectName("Flach")
        hilfe.setFixedSize(26, 26)
        hilfe.setIcon(icons.pixmap("help", 17, parent.theme.muted))
        hilfe.setIconSize(QSize(17, 17))
        hilfe.setToolTip(T("dialog_hilfe"))
        kopf.addWidget(hilfe)
        lay.addLayout(kopf)

        self.suche = QLineEdit()
        self.suche.setPlaceholderText(T("suchen"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(self.liste_fuellen)
        lay.addWidget(self.suche)

        self.roll = QScrollArea()
        self.roll.setWidgetResizable(True)
        self.roll.setFrameShape(QFrame.NoFrame)
        durchsichtig(self.roll.viewport(), "DlgFlaeche")
        self.inhalt = QWidget()
        durchsichtig(self.inhalt, "DlgInhalt")
        self.ilay = QVBoxLayout(self.inhalt)
        self.ilay.setContentsMargins(0, 0, 6, 0)
        self.ilay.setSpacing(2)
        self.ilay.addStretch(1)
        self.roll.setWidget(self.inhalt)
        lay.addWidget(self.roll, 1)

        knoepfe = QHBoxLayout()
        knoepfe.addStretch(1)
        ab = QPushButton(T("abbrechen"))
        ab.clicked.connect(self.reject)
        knoepfe.addWidget(ab)
        ok = QPushButton(T("anwenden"))
        ok.setObjectName("Betont")
        ok.clicked.connect(self._anwenden)
        knoepfe.addWidget(ok)
        lay.addLayout(knoepfe)

        self.liste_fuellen()

    def liste_fuellen(self):
        while self.ilay.count() > 1:
            w = self.ilay.takeAt(0)
            if w.widget():
                w.widget().setParent(None)
        filter_text = self.suche.text().strip().lower()
        live = sorted(self.haupt.live,
                      key=lambda k: self.haupt._meta.get(k, k).lower())
        if not live:
            leer = QLabel(T("keine_app_ton"))
            leer.setObjectName("Hinweis")
            self.ilay.insertWidget(0, leer)
            return
        pos = 0
        for key in live:
            name = self.haupt._meta.get(key) or huebscher_name(key)
            if filter_text and filter_text not in name.lower():
                continue
            self.ilay.insertWidget(pos, _AppZeile(
                key, name, key not in self.vorgemerkt, self.haupt,
                self._umschalten))
            pos += 1

    def _umschalten(self, key, sichtbar):
        if sichtbar:
            self.vorgemerkt.discard(key)
        else:
            self.vorgemerkt.add(key)

    def _anwenden(self):
        self.haupt.hidden = set(self.vorgemerkt)
        # Ausgeblendete Apps koennen nicht laenger Ziel sein
        self.haupt.targets -= self.haupt.hidden
        self.haupt.engine.targets = set(self.haupt.targets)
        self.haupt._speichern()
        self.haupt.engine.job("refresh")
        self.accept()


class _AppZeile(QWidget):
    """Eine Zeile im Auswahldialog – die ganze Zeile schaltet um."""

    def __init__(self, key, name, an, haupt, rueckruf, parent=None):
        super().__init__(parent)
        from .widgets import _Kaestchen
        self.key = key
        self.rueckruf = rueckruf
        self.theme = haupt.theme
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("Zeile")
        self.setProperty("hover", False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 10, 0)
        lay.setSpacing(11)
        self.box = _Kaestchen(haupt.theme, 22)
        self.box.setChecked(an)
        self.box.clicked.connect(self._umschalten)
        lay.addWidget(self.box)
        symbol = QLabel()
        pm = icons.exe_icon(haupt.exes.get(key), 24, self.devicePixelRatioF())
        if pm is None:
            pm = icons.buchstaben_pixmap(name[:1] or "?", 24,
                                         haupt.theme.card2, haupt.theme.muted,
                                         self.devicePixelRatioF())
        symbol.setPixmap(pm)
        symbol.setFixedSize(24, 24)
        lay.addWidget(symbol)
        lay.addWidget(QLabel(name), 1)

    def _umschalten(self):
        self.box.setChecked(not self.box.isChecked())
        self.rueckruf(self.key, self.box.isChecked())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._umschalten()

    def enterEvent(self, e):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)

    def leaveEvent(self, e):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
