# -*- coding: utf-8 -*-
"""Hauptfenster: Mixer, Einstellungen, Profile, App-Auswahl."""
import ctypes
import functools

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QSize,
                            Qt, QTimer, Signal)
from PySide6.QtGui import QAction, QFontMetricsF, QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QPushButton, QScrollArea,
                               QSizePolicy, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

from . import config, icons, klang
from .audio import AudioEngine, huebscher_name
from .config import MASTER_KEY
from .hooks import InputHook
from .osd import Osd
from . import sprache
from .sprache import SPRACHEN, T
from .theme import PALETTE, Theme, basis_schrift, glaettung, mix
from .widgets import (FadeScroll, Flaeche, MixerRow, Slider,
                      ToggleSwitch)

SWITCH_MODES = ["none", "carry", "apps100"]     # Beschriftung via T()


def durchsichtig(widget, name):
    """Macht genau dieses Widget durchsichtig – und nur dieses.

    Ohne ID-Selektor gilt ein Stylesheet in Qt auch fuer alle Kinder; die
    Karten darin waeren dann ebenfalls unsichtbar.
    """
    widget.setObjectName(name)
    widget.setStyleSheet("#{} {{ background: transparent; }}".format(name))


# Groesse der Symbole in den runden Knoepfen der Kopfzeile. Steht hier, weil
# sie an zwei Stellen gebraucht wird – beim Bauen und beim Farbwechsel.
RUND_SYMBOL = 22


def rundknopf(symbol, theme, tooltip=""):
    b = QPushButton()
    b.setObjectName("Rund")
    b.setCursor(Qt.PointingHandCursor)
    b.setToolTip(tooltip)
    b.setIcon(icons.pixmap(symbol, RUND_SYMBOL, theme.muted))
    b.setIconSize(QSize(RUND_SYMBOL, RUND_SYMBOL))
    b._symbol = symbol
    return b


class _Profilname(QLineEdit):
    """Der Profilname – sieht aus wie Text, ist aber ein Eingabefeld.

    Ein Klick genuegt zum Umbenennen; einen eigenen Dialog braucht es dafuer
    nicht. Solange das Feld die Eingabe hat, taucht der Papierkorb daneben auf.
    """

    fokus_rein = Signal()
    fokus_raus = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Profilname")
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.selectAll()
        self.fokus_rein.emit()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.fokus_raus.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.fokus_raus.emit()      # Abbruch: alten Namen zurueckholen
            self.clearFocus()
            return
        super().keyPressEvent(e)


class _ProfilPunkte(QWidget):
    """Zeigt, das wievielte von wie vielen Profilen offen ist.

    Die Punkte stehen in einem festen Raster, die Markierung gleitet darueber
    hinweg. So bleibt die Reihe beim Blaettern stehen, statt sich jedes Mal
    neu zu ordnen – und man sieht in welche Richtung man gerade gegangen ist.
    """

    HOECHSTENS = 10        # darueber wird gezaehlt statt gezeichnet
    RASTER = 13.0
    PUNKT = 4.0
    MARKE = 12.0

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.anzahl = 0
        self.aktiv = 0
        self._stelle = 0.0
        self.setFixedHeight(9)
        self._gleiten = QPropertyAnimation(self, b"stelle", self)
        self._gleiten.setDuration(200)
        self._gleiten.setEasingCurve(QEasingCurve.OutCubic)

    def get_stelle(self):
        return self._stelle

    def set_stelle(self, wert):
        self._stelle = wert
        self.update()

    stelle = Property(float, get_stelle, set_stelle)

    def setzen(self, anzahl, aktiv):
        gewechselt = anzahl == self.anzahl and aktiv != self.aktiv
        self.anzahl, self.aktiv = anzahl, aktiv
        self._gleiten.stop()
        if gewechselt:
            self._gleiten.setStartValue(self._stelle)
            self._gleiten.setEndValue(float(aktiv))
            self._gleiten.start()
        else:
            # Kam ein Profil dazu oder faellt eines weg, verschiebt sich das
            # ganze Raster – dann waere eine Fahrt nur Zappeln.
            self._stelle = float(aktiv)
        self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QColor, QPainter
        from PySide6.QtCore import QRectF
        if self.anzahl < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        if self.anzahl > self.HOECHSTENS:
            p.setPen(QColor(self.theme.muted))
            f = p.font()
            f.setPixelSize(9)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter,
                       "{} / {}".format(self.aktiv + 1, self.anzahl))
            return
        h = 4.0
        breite = self.RASTER * (self.anzahl - 1) + self.PUNKT
        links = (self.width() - breite) / 2.0
        y = (self.height() - h) / 2.0
        p.setBrush(QColor(self.theme.muted))
        for i in range(self.anzahl):
            p.drawRoundedRect(
                QRectF(links + i * self.RASTER, y, self.PUNKT, h),
                h / 2.0, h / 2.0)
        mitte = links + self._stelle * self.RASTER + self.PUNKT / 2.0
        p.setBrush(QColor(self.theme.accent))
        p.drawRoundedRect(QRectF(mitte - self.MARKE / 2.0, y, self.MARKE, h),
                          h / 2.0, h / 2.0)


class _Reiter(QWidget):
    """Bereichswahl in den Einstellungen.

    Keine Kaesten, keine Rahmen: nur die Beschriftungen, die gewaehlte
    hervorgehoben, darunter eine Linie, die zur neuen Stelle faehrt statt zu
    springen. Dieselbe Bewegung wie bei den Profilpunkten – so fuehlt sich
    beides nach demselben Programm an.
    """

    gewechselt = Signal(int)
    HOEHE = 42

    def __init__(self, namen, theme, parent=None):
        super().__init__(parent)
        self.namen = list(namen)
        self.theme = theme
        self.aktiv = 0
        self._stelle = 0.0
        self._hover = -1
        self.setFixedHeight(self.HOEHE)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._fahrt = QPropertyAnimation(self, b"stelle", self)
        self._fahrt.setDuration(220)
        self._fahrt.setEasingCurve(QEasingCurve.OutCubic)

    def get_stelle(self):
        return self._stelle

    def set_stelle(self, wert):
        self._stelle = wert
        self.update()

    stelle = Property(float, get_stelle, set_stelle)

    def waehlen(self, nr, melden=True):
        nr = max(0, min(len(self.namen) - 1, int(nr)))
        if nr == self.aktiv:
            return
        self.aktiv = nr
        self._fahrt.stop()
        self._fahrt.setStartValue(self._stelle)
        self._fahrt.setEndValue(float(nr))
        self._fahrt.start()
        if melden:
            self.gewechselt.emit(nr)

    def _feld(self, x):
        breite = self.width() / max(1, len(self.namen))
        return int(max(0, min(len(self.namen) - 1, x // breite)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.waehlen(self._feld(e.position().x()))

    def mouseMoveEvent(self, e):
        neu = self._feld(e.position().x())
        if neu != self._hover:
            self._hover = neu
            self.update()

    def leaveEvent(self, e):
        self._hover = -1
        self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QColor, QFont, QPainter
        from PySide6.QtCore import QRectF
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        breite = self.width() / max(1, len(self.namen))
        for i, name in enumerate(self.namen):
            f = QFont(self.font())
            f.setPixelSize(13)
            f.setWeight(QFont.Bold if i == self.aktiv else QFont.Medium)
            p.setFont(f)
            if i == self.aktiv:
                p.setPen(QColor(t.fg))
            elif i == self._hover:
                p.setPen(QColor(mix(t.muted, t.fg, 0.5)))
            else:
                p.setPen(QColor(t.muted))
            p.drawText(QRectF(i * breite, 0, breite, self.HOEHE - 6),
                       Qt.AlignCenter, name)
        # Die Linie ist so breit wie ihre Beschriftung, nicht wie das Feld –
        # sonst schwimmt sie bei kurzen Woertern in der Luft.
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setWeight(QFont.Bold)
        mass = QFontMetricsF(f)
        i = int(round(self._stelle))
        wort = mass.horizontalAdvance(self.namen[i]) + 10
        mitte = (self._stelle + 0.5) * breite
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.accent))
        p.drawRoundedRect(QRectF(mitte - wort / 2.0, self.HOEHE - 3.0,
                                 wort, 2.5), 1.25, 1.25)


class _KlickZeile(QWidget):
    """Zeile, die als Ganzes anklickbar ist."""

    geklickt = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.geklickt.emit()


class Karte(Flaeche):
    """Panel mit Verlauf, Lichtkante und runden Ecken.

    `zusatz` kommt neben die Ueberschrift – dort steht das Fragezeichen, statt
    eine eigene Zeile dafuer zu brauchen.
    """

    def __init__(self, theme, titel=None, zusatz=None, parent=None):
        super().__init__(theme, 16, parent)
        self.setObjectName("Karte")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 14, 18, 16)
        self.lay.setSpacing(10)
        if titel:
            kopf = QHBoxLayout()
            kopf.setSpacing(4)
            k = QLabel(titel)
            k.setObjectName("Ueberschrift")
            kopf.addWidget(k)
            if zusatz is not None:
                kopf.addWidget(zusatz)
            kopf.addStretch(1)
            self.lay.addLayout(kopf)


class MainWindow(QWidget):
    # Reihenfolge der Reiter in den Einstellungen. Wer sie umstellt, aendert
    # nur diese Zeile – angesprochen werden die Bereiche ueber ihren Namen,
    # nicht ueber ihre Stelle.
    BEREICHE = ("allgemein", "design", "steuerung", "anzeige")

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
        self.angleichen = set(self.cfg["angleichen"] or [])
        self.known = dict.fromkeys(self.cfg["known"] or [], "")
        self.exes = dict(self.cfg["exes"] or {})
        self.profiles = dict(self.cfg["profiles"] or {})
        self.rows = {}
        self.live = set()
        self._meta = {}
        self._items = []
        self._filter = ""
        # Es gibt immer genau ein offenes Profil. Wer von frueher kommt, hat
        # Profile im alten Format (nur Pegel) – die bekommen die fehlenden
        # Teile aus den jetzigen Einstellungen.
        for name, profil in list(self.profiles.items()):
            for k in config.PROFIL_TEILE:
                profil.setdefault(k, self.cfg[k])
            profil.setdefault("targets", sorted(self.targets))
            self._profil_umrechnen(profil)
        self._profil_sicherstellen()
        for k in config.PROFIL_TEILE:
            self.cfg[k] = self.profiles[self.cfg["profil"]].get(k, self.cfg[k])
        self.theme.set(self.cfg["mode"], self.cfg["accent"])

        self.setObjectName("Fenster")
        self.setWindowTitle("Volumix")
        self.setWindowIcon(QIcon(icons.app_logo(64, self.theme.accent)))
        self._wunsch_hoehe = self.cfg.get("window_h", 720)
        self._erwartet = None
        self.resize(560, self._wunsch_hoehe)
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
        self.engine.ton_am_anschlag = self.cfg["ton_anschlag"]
        self.engine.angleichen = set(self.angleichen)
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
        self.hook.titel_taste = self.cfg["titel_taste"]
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
        self._hilfe_knoepfe = []      # beim Neuaufbau wieder von vorn
        self._flachknoepfe = []
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
        titel = QLabel("Volumix")
        titel.setObjectName("Wortmarke")
        unter = QLabel(T("untertitel"))
        unter.setObjectName("Untertitel")
        spalte.addWidget(titel)
        spalte.addWidget(unter)
        kopf.addLayout(spalte, 1)
        self.btn_modus = rundknopf("moon", self.theme, T("tt_modus"))
        self.btn_modus.clicked.connect(self._modus_wechseln)
        self.btn_einst = rundknopf("gear", self.theme, T("tt_einstellungen"))
        self.btn_einst.clicked.connect(lambda: self._seite(1))
        for b in (self.btn_modus, self.btn_einst):
            kopf.addWidget(b)
        aussen.addWidget(self.kopfzeile)
        self.profilleiste = self._profilleiste_bauen()
        aussen.addWidget(self.profilleiste)

        # Umschaltbarer Bereich: Mixer / Einstellungen
        self.mixer_seite = self._mixer_bauen()
        self.einst_seite = self._einstellungen_bauen()
        self.einst_seite.hide()
        aussen.addWidget(self.mixer_seite, 1)
        aussen.addWidget(self.einst_seite, 1)

        # Statusleiste
        self.leiste = Flaeche(self.theme, 12)
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

        self.karte = Karte(self.theme, T("mixer"))
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

        # Vier Bereiche statt einer langen Liste: Vorher standen sechzehn
        # Zeilen untereinander, alle im selben Muster. Da fuehrt nichts das
        # Auge, und man scrollt an dem vorbei, was man sucht.
        self.reiter = _Reiter([T(n) for n in self.BEREICHE], self.theme)
        self.reiter.gewechselt.connect(self._bereich_zeigen)
        lay.insertWidget(1, self.reiter)

        bauer = {"design": self._bereich_design,
                 "steuerung": self._bereich_steuerung,
                 "anzeige": self._bereich_anzeige,
                 "allgemein": self._bereich_allgemein}
        self._bereiche = [bauer[n]() for n in self.BEREICHE]
        for w in self._bereiche:
            ilay.addWidget(w)
        nr = getattr(self, "_einst_bereich", 0)
        self.reiter.aktiv = nr
        self.reiter.set_stelle(float(nr))
        for i, w in enumerate(self._bereiche):
            w.setVisible(i == nr)
        ilay.addStretch(1)
        return seite

    # ---- Die vier Bereiche ----------------------------------------------
    def _bereich(self, *karten):
        """Huelle um die Karten eines Bereichs."""
        w = QWidget()
        durchsichtig(w, "Bereich")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        for k in karten:
            lay.addWidget(k)
        return w

    def _chipreihe(self, karte, werte, gewaehlt, rueckruf):
        """Reihe sich gegenseitig ausschliessender Knoepfe."""
        gruppe = QButtonGroup(self)
        reihe = QHBoxLayout()
        reihe.setSpacing(8)
        for wert, name in werte:
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(wert == gewaehlt)
            b.clicked.connect(functools.partial(rueckruf, wert))
            gruppe.addButton(b)
            reihe.addWidget(b)
        reihe.addStretch(1)
        karte.lay.addLayout(reihe)
        return gruppe

    def _bereich_design(self):
        # Modus und Farbe in einer Karte: zwei Karten mit je einer Zeile sind
        # mehr Rahmen als Inhalt.
        k = Karte(self.theme, T("modus"))
        self.modus_gruppe = self._chipreihe(
            k, (("dark", T("dunkel")), ("light", T("hell"))),
            self.theme.mode, self._modus_setzen)

        titel = QLabel(T("farbe"))
        titel.setObjectName("Ueberschrift")
        k.lay.addSpacing(6)
        k.lay.addWidget(titel)
        self.farbknoepfe = {}
        for i in range(0, len(PALETTE), 6):
            r = QHBoxLayout()
            r.setSpacing(9)
            for key, name, dunkel, hell in PALETTE[i:i + 6]:
                b = _Farbpunkt(key, self.theme, name)
                b.clicked.connect(functools.partial(self._farbe_setzen, key))
                self.farbknoepfe[key] = b
                r.addWidget(b)
            r.addStretch(1)
            k.lay.addLayout(r)
        return self._bereich(k)

    def _bereich_steuerung(self):
        k = Karte(self.theme, T("eingabe"))
        self.sw_aktiv = self._schalter_zeile(
            k, T("steuerung_aktiv"), self.cfg["active"], self._aktiv_setzen)
        # Frueher war das ein Schalter „Horizontales Scrollen verwenden“ –
        # zwei Moeglichkeiten, von denen eine im Namen stand und die andere
        # gar nicht. Als Auswahl sieht man beide.
        k.lay.addWidget(QLabel(T("regeln_mit")))
        self.eingabe_gruppe = self._chipreihe(
            k, ((False, T("daumenrad")), (True, T("lautstaerke_tasten"))),
            self.cfg["media_keys"], self._eingabe_setzen)
        # Gilt fuer beide Eingabearten, deshalb nicht „Scrollrichtung“
        self._schalter_zeile(
            k, T("richtung_umkehren"), self.cfg["reverse"],
            self._reverse_setzen)

        tempo_kopf = QHBoxLayout()
        tempo_kopf.setSpacing(4)
        tempo_kopf.addWidget(QLabel(T("geschwindigkeit")))
        tempo_kopf.addWidget(self._fragezeichen(T("tempo_hilfe")))
        tempo_kopf.addStretch(1)
        k.lay.addLayout(tempo_kopf)
        self.tempo_wert = QLabel("{} %".format(self.cfg["speed"]))
        k.lay.addLayout(self._regler_zeile(
            "", self.cfg["speed"], 10, 100,
            self._tempo_setzen, self.tempo_wert, breite=0))

        m = Karte(self.theme, T("medientasten"))
        self._schalter_zeile(
            m, T("titel_taste"), self.cfg["titel_taste"],
            self._titel_taste_setzen, hilfe=T("titel_hilfe"))

        self.btn_hilfe = self._fragezeichen(T("wechsel_hilfe"))
        w = Karte(self.theme, T("beim_wechsel"), zusatz=self.btn_hilfe)
        self.wechsel_gruppe = self._chipreihe(
            w, [(v, T("wechsel_" + v)) for v in SWITCH_MODES],
            self.cfg["switch_mode"], self._wechsel_setzen)
        return self._bereich(k, m, w)

    def _bereich_anzeige(self):
        k = Karte(self.theme, T("im_fenster"))
        self._schalter_zeile(
            k, T("live_pegel"), self.cfg["meters"], self._meter_setzen)

        o = Karte(self.theme, T("einblendung"))
        self._schalter_zeile(
            o, T("osd_anzeigen"), self.cfg["osd_enabled"], self._osd_setzen)
        # Groesse und Ort gehoeren zur Einblendung. Ist sie aus, sind sie
        # ohne Wirkung – dann sollen sie auch danach aussehen.
        self.osd_teile = QWidget()
        durchsichtig(self.osd_teile, "OsdTeile")
        tlay = QVBoxLayout(self.osd_teile)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(0)
        self.osd_groesse_wert = QLabel("{} %".format(self.cfg["osd_size"]))
        tlay.addLayout(self._regler_zeile(
            T("groesse"), self.cfg["osd_size"], 10, 100, self._osd_groesse,
            self.osd_groesse_wert))
        # Die Mitte trifft man von Hand nie genau – dort rastet es ein.
        self.osd_x_wert = QLabel("{} %".format(self.cfg["osd_x"]))
        tlay.addLayout(self._regler_zeile(
            T("position_waagerecht"), self.cfg["osd_x"], 0, 100, self._osd_x,
            self.osd_x_wert, rastpunkte=(50,)))
        self.osd_y_wert = QLabel("{} %".format(self.cfg["osd_y"]))
        tlay.addLayout(self._regler_zeile(
            T("position_senkrecht"), self.cfg["osd_y"], 0, 100, self._osd_y,
            self.osd_y_wert, rastpunkte=(50,)))
        self.osd_teile.setEnabled(self.cfg["osd_enabled"])
        o.lay.addWidget(self.osd_teile)

        t = Karte(self.theme, T("ton"))
        self._schalter_zeile(
            t, T("ton_anschlag"), self.cfg["ton_anschlag"],
            self._ton_setzen, hilfe=T("ton_hilfe"))
        return self._bereich(k, o, t)

    def _bereich_allgemein(self):
        k = Karte(self.theme, T("sprache_abschnitt"))
        self.sprach_gruppe = self._chipreihe(
            k, SPRACHEN, self.cfg["sprache"], self._sprache_setzen)

        s = Karte(self.theme, T("system"))
        self._schalter_zeile(
            s, T("mit_windows_starten"), config.get_autostart(),
            lambda an: config.set_autostart(an))
        return self._bereich(k, s)

    def bereich_nr(self, name):
        """Stelle eines Bereichs – Aufrufer muessen die Reihenfolge nicht
        kennen, nur den Namen."""
        return self.BEREICHE.index(name)

    def _bereich_zeigen(self, nr):
        self._einst_bereich = nr
        for i, w in enumerate(self._bereiche):
            w.setVisible(i == nr)
        self._einblenden(self._bereiche[nr], 150)
        self._einst_roll.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, functools.partial(self._einst_hoehe, True))

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

    def _schalter_zeile(self, karte, text, wert, rueckruf, hilfe=None):
        """Schalterzeile – die ganze Zeile schaltet um, nicht nur der Knopf."""
        zeile = _KlickZeile()
        # Ohne das schrumpft die Zeile auf ihren Inhalt und der Schalter
        # rutscht nach links statt am rechten Rand zu bleiben.
        zeile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        z = QHBoxLayout(zeile)
        z.setContentsMargins(0, 3, 0, 3)
        if hilfe:
            z.setSpacing(4)
            z.addWidget(QLabel(text))
            # Der Knopf verschluckt den Klick, die Zeile schaltet dabei nicht um
            z.addWidget(self._fragezeichen(hilfe))
            z.addStretch(1)
        else:
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
        # Gesammelt, damit sie beim Farb- oder Moduswechsel mitgezogen werden
        self._hilfe_knoepfe.append(b)
        return b

    # ---- Aussehen --------------------------------------------------------
    def _vorlage_anwenden(self):
        # Auf die Anwendung, nicht aufs Fenster: Erklaerblasen sind eigene
        # Fenster und wuerden ein Widget-Stylesheet gar nicht sehen.
        app = QApplication.instance()
        if app is not None:
            app.setFont(basis_schrift())
            app.setStyleSheet(self.theme.qss())
            self._kanten_weich_machen()
        else:
            self.setStyleSheet(self.theme.qss())
        dpr = self.devicePixelRatioF()
        self.logo.setPixmap(icons.app_logo(40, self.theme.accent, dpr))
        self.setWindowIcon(QIcon(icons.app_logo(64, self.theme.accent, dpr)))
        for b in (self.btn_modus, self.btn_einst,
                  getattr(self, "btn_zurueck", None)):
            if b is not None:
                name = "sun" if (b is self.btn_modus and self.theme.hell) else b._symbol
                b.setIcon(icons.pixmap(name, RUND_SYMBOL, self.theme.muted, dpr))
                b.setIconSize(QSize(RUND_SYMBOL, RUND_SYMBOL))
        for b in getattr(self, "_flachknoepfe", []):
            b.setIcon(icons.pixmap(b._symbol, 17, self.theme.muted, dpr))
        for b in getattr(self, "_hilfe_knoepfe", []):
            b.setIcon(icons.pixmap("help", 16, self.theme.muted, dpr))
        for punkt in getattr(self, "farbknoepfe", {}).values():
            punkt.theme = self.theme
            punkt.update()
        # Die Flaechen zeichnen sich selbst und wissen von einem Farbwechsel
        # sonst nichts – ohne das bleiben Karten und Leisten stehen, wie sie
        # waren, waehrend alles darauf schon die neue Farbe hat.
        for flaeche in self.findChildren(Flaeche):
            flaeche.theme = self.theme
            flaeche.update()
        for row in self.rows.values():
            row.theme_wechseln(self.theme)
        self.fade.theme = self.theme
        self.osd.einstellen(self.cfg["osd_size"], self.cfg["osd_x"],
                            self.cfg["osd_y"], self.theme)
        if getattr(self, "tray", None):
            self.tray.setIcon(QIcon(icons.app_logo(64, self.theme.accent)))
        self._titelleiste_faerben()

    def _kanten_weich_machen(self):
        """Die Glaettungsvorgabe nachziehen.

        Die Stilvorlage baut fuer jede Schriftregel eine neue Schrift und
        laesst dabei alles fallen, was nicht im Blatt steht – auch die
        Vorgabe, Buchstaben nicht aufs Pixelraster zu zwingen. Deshalb hier
        hinterher ueber alles gehen, was schon steht.
        """
        for w in self.findChildren(QWidget):
            w.setFont(glaettung(w.font()))
        self.setFont(glaettung(self.font()))

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

    def _einblenden(self, widget, ms=160):
        """Weiches Aufblenden.

        Der Effekt wird hinterher wieder entfernt: dauerhaft gesetzt, kostet
        er bei jedem Neuzeichnen einen Zwischenpuffer – und der Mixer zeichnet
        sich mehrmals pro Sekunde neu.
        """
        effekt = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effekt)
        anim = QPropertyAnimation(effekt, b"opacity", widget)
        anim.setDuration(ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(
            lambda: QTimer.singleShot(0, lambda: widget.setGraphicsEffect(None)))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _seite(self, nr):
        self.view = nr
        if nr == 1 and self.mixer_seite.isVisible():
            self._mixer_hoehe = self.height()
        self.mixer_seite.setVisible(nr == 0)
        self.einst_seite.setVisible(nr == 1)
        self.leiste.setVisible(nr == 0)
        self.kopfzeile.setVisible(nr == 0)
        # Profile gehoeren zum Mixer. In den Einstellungen wechselt man keine
        # Profile – dort steht die Leiste nur im Weg.
        self.profilleiste.setVisible(nr == 0)
        if nr == 1:
            # So weit aufziehen, wie der Inhalt braucht – aber nie weiter.
            QTimer.singleShot(0, self._einst_hoehe)
            self._einblenden(self.einst_seite)
        else:
            zurueck = getattr(self, "_mixer_hoehe", None)
            if zurueck:
                self.resize(self.width(), zurueck)
            QTimer.singleShot(0, self._hoehe_anpassen)
            self._einblenden(self.mixer_seite)

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
                    it = dict(it, angleichen=it["key"] in self.angleichen)
                    row = MixerRow(it, it["key"] in self.targets, self.theme,
                                   self.cfg["meters"])
                    row.toggled.connect(self._ziel_umschalten)
                    row.volume_changed.connect(self._regler_bewegt)
                    row.mute_clicked.connect(self._stumm)
                    row.angleichen_clicked.connect(self._angleichen_setzen)
                    self.rows[it["key"]] = row
                    self.inhalt_lay.insertWidget(pos, row)
                    pos += 1
        else:
            for it in items:
                row = self.rows.get(it["key"])
                if row is not None:
                    row.aktualisieren(dict(
                        it, angleichen=it["key"] in self.angleichen))
                    row.set_gewaehlt(it["key"] in self.targets)
        # Frisch gebaute Zeilen kennen die Glaettungsvorgabe noch nicht
        self._kanten_weich_machen()
        QTimer.singleShot(0, self._fade)
        QTimer.singleShot(0, self._hoehe_anpassen)

    def get_fensterhoehe(self):
        return float(self.height())

    def set_fensterhoehe(self, wert):
        self.resize(self.width(), int(round(wert)))

    fensterhoehe = Property(float, get_fensterhoehe, set_fensterhoehe)

    def _einst_hoehe(self, fahren=False):
        """Einstellungen so hoch wie noetig – und nicht hoeher.

        Ohne Obergrenze liesse sich das Fenster ins Leere ziehen. Beim
        Wechsel des Bereichs (`fahren`) gleitet die Hoehe, statt zu springen:
        Die Bereiche sind unterschiedlich lang, und ein Fenster, das jedes
        Mal aufblitzt, wirkt hektisch.
        """
        if not self.einst_seite.isVisible():
            return
        inhalt = self._einst_inhalt.sizeHint().height()
        rest = self.height() - self._einst_roll.viewport().height()
        gewuenscht = inhalt + rest + 8
        platz = self.screen().availableGeometry().height() - 70
        # Untergrenze ist die Mindesthoehe des Fensters selbst – tiefer waere
        # sinnlos und liesse Deckel und Boden gegeneinander laufen. Seit die
        # Einstellungen in Bereiche geteilt sind, braucht „Design“ kaum Platz;
        # eine hoehere Grenze liesse darunter nur eine leere Flaeche stehen.
        hoechstens = max(self.minimumHeight(), min(platz, gewuenscht))
        self.setMaximumHeight(hoechstens)
        if fahren and abs(self.height() - hoechstens) > 4:
            anim = getattr(self, "_hoehe_anim", None)
            if anim is None:
                anim = QPropertyAnimation(self, b"fensterhoehe", self)
                anim.setDuration(190)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.finished.connect(functools.partial(
                    self._einst_roll.setVerticalScrollBarPolicy,
                    Qt.ScrollBarAsNeeded))
                self._hoehe_anim = anim
            # Waehrend das Fenster noch schrumpft, passt der Inhalt kurz nicht
            # hinein – die Bildlaufleiste blitzt auf und schiebt alles um ihre
            # Breite zur Seite. Deshalb ist sie fuer die Dauer der Fahrt weg.
            self._einst_roll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            anim.stop()
            anim.setStartValue(float(self.height()))
            anim.setEndValue(float(hoechstens))
            anim.start()
        else:
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

        Das Fenster kehrt immer zur gewuenschten Hoehe zurueck, sobald der
        Inhalt sie zulaesst. Frueher wurde nur verkleinert – nach einem
        Neuaufbau lief diese Pruefung, bevor die Zeilen da waren, deckelte
        auf die Mindesthoehe und das Fenster blieb dort stehen.
        """
        if not self.mixer_seite.isVisible():
            return
        if not self.rows:
            # Nach einem Neuaufbau laeuft das hier, bevor die Zeilen da sind.
            # Jetzt zu messen hiesse: „kaum Inhalt“ – und das Fenster faellt
            # auf die Mindesthoehe. Wenn die Zeilen kommen, ruft es sich
            # ohnehin selbst wieder auf.
            return
        inhalt = self.inhalt.sizeHint().height()
        rest = self.height() - self.rollbereich.viewport().height()
        gewuenscht = inhalt + rest + 6
        hoechstens = max(360, min(self.screen().availableGeometry().height() - 80,
                                  gewuenscht))
        self.setMaximumHeight(hoechstens)
        ziel = min(hoechstens, self._wunsch_hoehe)
        if abs(self.height() - ziel) > 2:
            self._selbst_hoehe(ziel)

    def _selbst_hoehe(self, hoehe):
        """Hoehe von sich aus setzen – klar getrennt vom Ziehen mit der Maus.

        Ohne die Markierung merkt sich das Fenster jede eigene Anpassung als
        Wunsch des Nutzers und kehrt nie zur alten Groesse zurueck.
        """
        self._erwartet = hoehe
        self.resize(self.width(), hoehe)
        # Falls die Meldung ausbleibt, nicht ewig warten
        QTimer.singleShot(300, functools.partial(setattr, self,
                                                 "_erwartet", None))

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

    def _angleichen_setzen(self, key, an):
        """Lautstaerke dieser App angleichen – oder eben nicht mehr."""
        if an:
            self.angleichen.add(key)
        else:
            self.angleichen.discard(key)
        self.cfg["angleichen"] = sorted(self.angleichen)
        self.engine.job("angleichen", key, an)
        row = self.rows.get(key)
        if row is not None:
            row.set_angleichen(an)
        self._melden(T("angleichen_an") if an else T("angleichen"))
        self._speichern()

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

    def keyPressEvent(self, e):
        """Pfeil links und rechts blaettern durch die Profile.

        Das Ereignis landet hier nur, wenn es niemand vorher gebraucht hat:
        Im Namensfeld bewegen die Pfeile den Schreibzeiger, auf einem Regler
        aendern sie den Wert. Beides bleibt, wie es war.
        """
        if e.key() in (Qt.Key_Left, Qt.Key_Right) and self.mixer_seite.isVisible():
            self._profil_blaettern(-1 if e.key() == Qt.Key_Left else 1)
            e.accept()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        """Klick irgendwo daneben beendet das Umbenennen.

        Die meisten Flaechen nehmen keine Eingabe an, deshalb behielte das
        Namensfeld sie sonst und man muesste eigens Enter druecken.
        """
        feld = getattr(self, "profil_name", None)
        if feld is not None and feld.hasFocus():
            feld.clearFocus()
        super().mousePressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.einst_seite.isVisible():
            QTimer.singleShot(0, self._einst_fade)
        else:
            QTimer.singleShot(0, self._fade)
            # Nur was von Hand gezogen wird, zaehlt als Wunschhoehe. Waehrend
            # eines Neuaufbaus faellt das Fenster kurz in sich zusammen –
            # das ist keine Absicht des Nutzers.
            if getattr(self, "_baut_um", False):
                return
            erwartet = getattr(self, "_erwartet", None)
            if erwartet is not None and abs(self.height() - erwartet) <= 2:
                self._erwartet = None
            elif self.height() < self.maximumHeight() - 2:
                # Eine eigene Begrenzung landet immer genau auf dem Deckel.
                # Darunter kann es nur jemand gezogen haben.
                self._wunsch_hoehe = self.height()
                self.cfg["window_h"] = self.height()

    # ---- Profile ---------------------------------------------------------
    def _profilleiste_bauen(self):
        """Schmaler Streifen: zurueck, Name, vor, plus."""
        leiste = Flaeche(self.theme, 12)
        leiste.setObjectName("Profilleiste")
        leiste.setFixedHeight(52)
        z = QHBoxLayout(leiste)
        z.setContentsMargins(6, 4, 6, 4)
        z.setSpacing(2)

        self.btn_prof_zurueck = self._flachknopf("back", T("profil_zurueck"))
        self.btn_prof_zurueck.clicked.connect(lambda: self._profil_blaettern(-1))
        z.addWidget(self.btn_prof_zurueck)

        self.profil_name = _Profilname()
        self.profil_name.setToolTip(T("profil_hilfe"))
        self.profil_name.fokus_rein.connect(self._profil_bearbeiten)
        self.profil_name.fokus_raus.connect(self._profil_name_uebernehmen)
        self.profil_name.editingFinished.connect(self.profil_name.clearFocus)
        self.profil_punkte = _ProfilPunkte(self.theme)
        mitte = QVBoxLayout()
        mitte.setContentsMargins(0, 0, 0, 0)
        mitte.setSpacing(0)
        mitte.addWidget(self.profil_name)
        mitte.addWidget(self.profil_punkte)
        z.addLayout(mitte, 1)

        # Kein Fokus: Sonst verliert das Namensfeld ihn beim Anklicken und der
        # Papierkorb waere weg, bevor der Klick ankommt.
        self.btn_prof_weg = self._flachknopf("trash", T("profil_loeschen"))
        self.btn_prof_weg.setFocusPolicy(Qt.NoFocus)
        self.btn_prof_weg.clicked.connect(self._profil_weg)
        self.btn_prof_weg.hide()
        z.addWidget(self.btn_prof_weg)

        self.btn_prof_vor = self._flachknopf("vor", T("profil_vor"))
        self.btn_prof_vor.clicked.connect(lambda: self._profil_blaettern(1))
        z.addWidget(self.btn_prof_vor)

        self.btn_prof_neu = self._flachknopf("plus", T("profil_neu"))
        self.btn_prof_neu.clicked.connect(self._profil_neu)
        z.addWidget(self.btn_prof_neu)

        self._profilleiste_auffrischen()
        return leiste

    def _flachknopf(self, symbol, tooltip):
        b = QPushButton()
        b.setObjectName("Flach")
        b.setFixedSize(30, 30)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tooltip)
        b.setIcon(icons.pixmap(symbol, 17, self.theme.muted))
        b.setIconSize(QSize(17, 17))
        b._symbol = symbol
        self._flachknoepfe.append(b)
        return b

    def _profilleiste_auffrischen(self):
        namen = self._profil_namen()
        mehrere = len(namen) > 1
        self.profil_name.setText(self.cfg["profil"] or "")
        self.btn_prof_zurueck.setEnabled(mehrere)
        self.btn_prof_vor.setEnabled(mehrere)
        self.btn_prof_weg.setEnabled(mehrere)
        stelle = namen.index(self.cfg["profil"]) if self.cfg["profil"] in namen else 0
        self.profil_punkte.setzen(len(namen), stelle)

    def _profil_bearbeiten(self):
        """Feld hat die Eingabe – Papierkorb dazu, Pfeile weg.

        Der Papierkorb erscheint immer, auch beim letzten Profil – dort nur
        ausgegraut. Ganz zu verschwinden wirkte wie ein Fehler.
        """
        self.btn_prof_weg.setEnabled(len(self.profiles) > 1)
        self.btn_prof_weg.show()
        self.btn_prof_zurueck.hide()
        self.btn_prof_vor.hide()

    def _profil_name_uebernehmen(self):
        """Feld verliert die Eingabe – Namen uebernehmen, Leiste zurueck.

        Waehrend eines Neuaufbaus verliert auch das alte Feld die Eingabe.
        Sein Text gehoert dann noch zum vorigen Profil und wuerde als
        Umbenennung durchgehen – deshalb hier aussteigen.
        """
        if getattr(self, "_baut_um", False):
            return
        self.btn_prof_weg.hide()
        self.btn_prof_zurueck.show()
        self.btn_prof_vor.show()
        alt = self.cfg["profil"]
        neu = self.profil_name.text().strip()
        if not neu or neu == alt or neu in self.profiles:
            self.profil_name.setText(alt)      # ungueltig: zurueck auf alt
            return
        self.profiles[neu] = self.profiles.pop(alt)
        self.cfg["profil"] = neu
        self._speichern()

    def _profil_weg(self):
        self._profil_loeschen(self.cfg["profil"])

    def _profil_namen(self):
        return sorted(self.profiles, key=lambda n: n.lower())

    def _profil_sicherstellen(self):
        """Es gibt immer genau ein offenes Profil – notfalls wird eins angelegt."""
        if not self.profiles:
            self.profiles[T("profil_standard")] = self._profil_abbild()
        if self.cfg["profil"] not in self.profiles:
            self.cfg["profil"] = self._profil_namen()[0]

    def _profil_umrechnen(self, profil):
        """Alte Profile speichern App-Pegel als rohe Amplitude.

        Seit die Regler aller Apps derselben Kurve folgen wie die
        Gesamtlautstaerke, stehen dort Reglerpositionen. Ohne Umrechnung
        waeren die alten Werte nach dem Laden zu leise.
        """
        if profil.get("fassung") == config.PROFIL_FASSUNG:
            return
        apps = profil.get("apps") or {}
        profil["apps"] = {k: config.pos_aus_amp(v) for k, v in apps.items()}
        profil["fassung"] = config.PROFIL_FASSUNG

    def _profil_abbild(self):
        """Der jetzige Zustand als Profil."""
        apps = {}
        master = None
        for it in self._items:
            if it["key"] == MASTER_KEY:
                master = it["volume"]
            else:
                apps[it["key"]] = it["volume"]
        profil = {"master": master, "apps": apps,
                  "targets": sorted(self.targets)}
        for k in config.PROFIL_TEILE:
            profil[k] = self.cfg[k]
        return profil

    def _profil_sichern(self):
        """Den jetzigen Zustand ins offene Profil schreiben.

        Es gibt bewusst keinen Speichern-Knopf: Was man aendert, gehoert ab
        sofort zum offenen Profil. Deshalb laeuft das bei jedem Sichern mit.
        """
        name = self.cfg.get("profil")
        if not name or name not in self.profiles:
            return
        alt = self.profiles[name]
        neu = self._profil_abbild()
        # Pegel nur uebernehmen, wenn wir welche kennen – direkt nach dem
        # Start ist die Liste noch leer und wuerde das Profil auswaschen.
        if not neu["apps"] and neu["master"] is None:
            neu["master"] = alt.get("master")
            neu["apps"] = alt.get("apps") or {}
        self.profiles[name] = neu

    def _profil_blaettern(self, richtung):
        namen = self._profil_namen()
        if len(namen) < 2:
            return
        i = namen.index(self.cfg["profil"]) if self.cfg["profil"] in namen else 0
        self._profil_oeffnen(namen[(i + richtung) % len(namen)])

    def _profil_oeffnen(self, name):
        """Ein anderes Profil aufschlagen.

        Frueher wurde dafuer das ganze Fenster verworfen und neu gebaut – zu
        der Zeit hing an einem Profil noch die halbe Einstellungsseite. Ein
        Profil haelt heute nur Pegel und Ziele; dafuer genuegt es, die
        vorhandenen Zeilen umzustellen. Nebenbei faellt das Fenster beim
        Blaettern nicht mehr kurz zusammen.
        """
        profil = self.profiles.get(name)
        if profil is None:
            return
        self._profil_sichern()          # das bisherige festhalten
        # Die Pegelliste gehoert noch zum alten Profil. Wuerde sie stehen
        # bleiben, schriebe das naechste Sichern die alten Werte ins neue
        # Profil – leer heisst „warte auf frische Meldung“.
        self._items = []
        self.cfg["profil"] = name
        ziele = profil.get("targets")
        if ziele is not None:
            self.targets = set(ziele)
            self.engine.targets = set(self.targets)
            for key, row in self.rows.items():
                row.set_gewaehlt(key in self.targets)
        self.engine.job("profile", profil)
        self._profilleiste_auffrischen()
        self._einblenden(self.profil_name, 200)
        self._status_setzen()
        self._speichern()
        self._melden(T("profil_geladen", name=name))

    def _profil_neu(self):
        """Sofort anlegen, ohne Nachfrage – der Name laesst sich gleich tippen."""
        self._profil_sichern()
        n = len(self.profiles) + 1
        while T("profil_zahl", n=n) in self.profiles:
            n += 1
        name = T("profil_zahl", n=n)
        self.profiles[name] = self._profil_abbild()      # Kopie des jetzigen
        self.cfg["profil"] = name
        self._profilleiste_auffrischen()
        self._speichern()
        # Gleich zum Umbenennen bereit: Name steht markiert im Feld
        self.profil_name.setFocus(Qt.OtherFocusReason)

    def _profil_loeschen(self, name):
        if len(self.profiles) < 2:      # das letzte bleibt stehen
            return
        if self.profiles.pop(name, None) is None:
            return
        self._melden(T("profil_geloescht", name=name))
        if self.cfg["profil"] == name:
            self.cfg["profil"] = self._profil_namen()[0]
            self._profil_oeffnen(self.cfg["profil"])
        else:
            self._profilleiste_auffrischen()
            self._speichern()


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
    # Langsamster und schnellster Schritt in Prozentpunkten je Rastung
    TEMPO_MIN = 0.2
    TEMPO_MAX = 4.2

    def _schrittweite(self, prozent):
        """Prozentwert vom Regler in Prozentpunkte je Rastung.

        Bewusst nicht linear: Zwischen 0,2 und 0,4 Punkten liegen Welten,
        zwischen 3,8 und 4,0 kaum etwas. Gleichmaessig verteilt waere der
        ganze feine Bereich auf den ersten Millimetern des Reglers.
        """
        s = max(10.0, min(100.0, float(prozent)))
        anteil = (s - 10.0) / 90.0
        return self.TEMPO_MIN * (self.TEMPO_MAX / self.TEMPO_MIN) ** anteil

    def _tempo_uebernehmen(self):
        self.engine.speed_step = self._schrittweite(self.cfg["speed"])

    def _tempo_setzen(self, wert):
        wert = int(wert)
        self.cfg["speed"] = wert
        self.tempo_wert.setText("{} %".format(wert))
        self._tempo_uebernehmen()
        self._speichern()

    def _aktiv_setzen(self, an):
        self.cfg["active"] = an
        self.hook.aktiv = an
        self._speichern()

    def _eingabe_setzen(self, tasten):
        """Womit geregelt wird – Daumenrad oder die Lautstaerke-Tasten."""
        self.cfg["media_keys"] = tasten
        self.hook.media_keys = tasten
        self.hook.start()
        self._melden(T("tasten_aktiv") if tasten else T("rad_aktiv"))
        self._speichern()

    def _titel_taste_setzen(self, an):
        self.cfg["titel_taste"] = an
        self.hook.titel_taste = an
        # Neu starten: Der Tastatur-Hook wird jetzt gebraucht (oder eben
        # nicht mehr), und das entscheidet sich erst beim Aufbauen.
        self.hook.start()
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
        """Fenster verwerfen und frisch aufbauen (Sprach- oder Profilwechsel)."""
        self._baut_um = True
        # Ohne Inhalt faellt das Fenster auf seine Mindesthoehe zusammen und
        # bleibt dort – die vorherige Hoehe muss von Hand zurueck.
        hoehe = self.height()
        try:
            self._neu_aufbauen_intern(seite)
        finally:
            self._baut_um = False
        # Sofort, nicht spaeter: Die Hoehenlogik rechnet mit der aktuellen
        # Fenstergroesse. Liefe sie zuerst, saehe sie das zusammengefallene
        # Fenster und setzte den Deckel entsprechend tief.
        self.setMaximumHeight(16777215)
        self._selbst_hoehe(hoehe)
        # Beim Abbau faellt das Fenster zusammen; diese Meldung kann verspaetet
        # eintreffen und wuerde als Wunsch durchgehen. Deshalb den Wert danach
        # noch einmal festnageln – jetzt und im naechsten Durchlauf.
        self._wunsch_hoehe = hoehe
        QTimer.singleShot(0, functools.partial(setattr, self,
                                               "_wunsch_hoehe", hoehe))

    def _neu_aufbauen_intern(self, seite):
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

    def _ton_setzen(self, an):
        self.cfg["ton_anschlag"] = an
        self.engine.ton_am_anschlag = an
        if an:
            klang.anschlag()          # einmal hoeren, was man da einschaltet
        self._speichern()

    def _osd_setzen(self, an):
        self.cfg["osd_enabled"] = an
        teile = getattr(self, "osd_teile", None)
        if teile is not None:
            teile.setEnabled(an)
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
        # Kein Speichern-Knopf: Der jetzige Zustand ist das offene Profil.
        self._profil_sichern()
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
        # Die Spur im Protokoll: Wer sie findet, weiss, dass jemand beendet
        # hat. Fehlt sie, ist die App von selbst verschwunden.
        config.notiz("beendet")
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
        karte = Flaeche(parent.theme, 16)
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
        self.roll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        durchsichtig(self.roll.viewport(), "DlgFlaeche")
        self.inhalt = QWidget()
        durchsichtig(self.inhalt, "DlgInhalt")
        self.ilay = QVBoxLayout(self.inhalt)
        self.ilay.setContentsMargins(0, 0, 6, 0)
        self.ilay.setSpacing(2)
        self.ilay.addStretch(1)
        self.roll.setWidget(self.inhalt)
        lay.addWidget(self.roll, 1)
        # Die Liste ist oft laenger als der Dialog. Ohne Abblendung sieht sie
        # unten einfach aufgehoert aus – man sucht nicht nach dem, was man
        # nicht vermutet. Hier laenger als im Mixer: die Liste geht oft ueber
        # das Doppelte des Sichtbaren, das darf man von weitem sehen.
        self.schleier = FadeScroll(parent.theme, hoehe=42, parent=self.roll)
        self.roll.verticalScrollBar().valueChanged.connect(self._fade)

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

    def _fade(self):
        leiste = self.roll.verticalScrollBar()
        sicht = self.roll.viewport()
        self.schleier.setGeometry(0, 0, sicht.width(), sicht.height())
        self.schleier.zeigen(leiste.value() > 4,
                             leiste.value() < leiste.maximum() - 4)
        self.schleier.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self._fade)

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
            QTimer.singleShot(0, self._fade)
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
        # Erst wenn die Zeilen stehen, weiss der Rollbereich, wie weit es geht
        QTimer.singleShot(0, self._fade)

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
        # Eigener Name: die Mixer-Zeile zeichnet ihren Hintergrund selbst,
        # diese hier holt ihn aus der Stilvorlage.
        self.setObjectName("DlgZeile")
        self.setAttribute(Qt.WA_StyledBackground, True)
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
