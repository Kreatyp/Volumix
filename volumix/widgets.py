# -*- coding: utf-8 -*-
"""Bausteine der Oberflaeche.

Alles hier ist ein echtes Qt-Widget: Ecken, Verlaeufe und Hover kommen aus der
Stilvorlage, nicht aus gerenderten Bildern.
"""
import time

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF,
                            QSize, Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QWidget)

from . import icons
from .config import MASTER_KEY
from .sprache import T
from .theme import mix


def flaeche_zeichnen(p, theme, rechteck, radius):
    """Erhabene Flaeche: leichter Verlauf und eine feine Lichtkante oben.

    Die Lichtkante ist der Unterschied zwischen „Rechteck in einem anderen
    Grauton“ und einer Flaeche, die wirklich im Raum liegt. Ueber die
    Stilvorlage geht das nicht – Qt zieht einen Rahmen rundherum, hier soll
    er nach unten auslaufen, so wie Licht von oben faellt.
    """
    g = QLinearGradient(rechteck.left(), rechteck.top(),
                        rechteck.left(), rechteck.bottom())
    g.setColorAt(0.0, QColor(theme.card_top))
    g.setColorAt(1.0, QColor(theme.card_bottom))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(rechteck, radius, radius)

    licht = QColor(*theme.kante)
    aus = QColor(licht)
    aus.setAlpha(0)
    saum = QLinearGradient(rechteck.left(), rechteck.top(), rechteck.left(),
                           rechteck.top() + max(12.0, rechteck.height() * 0.55))
    saum.setColorAt(0.0, licht)
    saum.setColorAt(1.0, aus)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QBrush(saum), 1.0))
    p.drawRoundedRect(rechteck, radius, radius)


class Flaeche(QFrame):
    """Karte, Leiste, Profilleiste – alle mit demselben Aufbau."""

    def __init__(self, theme, radius=16, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.radius = radius

    def paintEvent(self, e):
        if self.theme is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        flaeche_zeichnen(p, self.theme,
                         QRectF(0.5, 0.5, self.width() - 1.0,
                                self.height() - 1.0),
                         self.radius)


def _verblassen(pm, deckkraft):
    """Kopie des Bildes mit verringerter Deckkraft."""
    from PySide6.QtGui import QPixmap
    blass = QPixmap(pm.size())
    blass.setDevicePixelRatio(pm.devicePixelRatio())
    blass.fill(Qt.transparent)
    p = QPainter(blass)
    p.setOpacity(deckkraft)
    p.drawPixmap(0, 0, pm)
    p.end()
    return blass


class ToggleSwitch(QWidget):
    """Schiebeschalter mit weicher Bewegung."""

    toggled = Signal(bool)

    def __init__(self, an=False, theme=None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._an = bool(an)
        self._weg = 1.0 if self._an else 0.0
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)
        # Die Eigenschaft MUSS anders heissen als `pos`: das ist bei Qt bereits
        # die Fensterposition. Sonst schiebt die Animation das ganze Widget
        # nach links, statt den Knopf darin zu bewegen.
        self._anim = QPropertyAnimation(self, b"schieber", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_schieber(self):
        return self._weg

    def set_schieber(self, wert):
        self._weg = wert
        self.update()

    schieber = Property(float, get_schieber, set_schieber)

    def isChecked(self):
        return self._an

    def setChecked(self, an, melden=False):
        an = bool(an)
        if an == self._an:
            return
        self._an = an
        self._anim.stop()
        self._anim.setStartValue(self._weg)
        self._anim.setEndValue(1.0 if an else 0.0)
        self._anim.start()
        if melden:
            self.toggled.emit(an)

    def mousePressEvent(self, e):
        self.setChecked(not self._an, melden=True)
        # MUSS angenommen werden: sonst reicht Qt den Klick an die Zeile
        # darunter weiter, die ebenfalls umschaltet – und der Schalter steht
        # danach wieder da, wo er war.
        e.accept()

    def paintEvent(self, e):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        aus, an = QColor(t.off), QColor(t.accent)
        farbe = QColor(
            int(aus.red() + (an.red() - aus.red()) * self._weg),
            int(aus.green() + (an.green() - aus.green()) * self._weg),
            int(aus.blue() + (an.blue() - aus.blue()) * self._weg))
        p.setPen(Qt.NoPen)
        p.setBrush(farbe)
        p.drawRoundedRect(self.rect(), 13, 13)
        d = 20
        x = 3 + self._weg * (self.width() - d - 6)
        p.setBrush(QColor(t.knob))
        p.drawEllipse(QRectF(x, 3, d, d))


class Slider(QSlider):
    """Waagerechter Regler, der auch auf Klick in die Schiene reagiert.

    Mit `rastpunkte` schnappt er in der Naehe bestimmter Werte ein – praktisch
    fuer die Mitte, die man sonst nie genau trifft.
    """

    def __init__(self, parent=None, rastpunkte=(), rastweite=4):
        super().__init__(Qt.Horizontal, parent)
        self.setRange(0, 100)
        self.setCursor(Qt.PointingHandCursor)
        self.rastpunkte = tuple(rastpunkte)
        self.rastweite = rastweite

    def _rasten(self, wert):
        for punkt in self.rastpunkte:
            if abs(wert - punkt) <= self.rastweite:
                return punkt
        return wert

    def _aus_maus(self, e):
        anteil = e.position().x() / max(1, self.width())
        wert = int(round(max(0.0, min(1.0, anteil)) * 100))
        return self._rasten(wert)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._anfassen()
            self.setValue(self._aus_maus(e))
            self.sliderMoved.emit(self.value())
            e.accept()
            self.setSliderDown(True)
            return
        super().mousePressEvent(e)

    def _anfassen(self):
        """Haken fuer Unterklassen – eine laufende Bewegung endet hier."""

    def mouseMoveEvent(self, e):
        if self.isSliderDown():
            self.setValue(self._aus_maus(e))
            self.sliderMoved.emit(self.value())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.isSliderDown():
            self.setSliderDown(False)
            self.sliderReleased.emit()
            e.accept()
            self._losgelassen_aussehen(e)
            return
        super().mouseReleaseEvent(e)

    def _losgelassen_aussehen(self, e):
        """Haken fuer Unterklassen – der Lautstaerkeregler laesst hier den
        Knopf wieder schrumpfen, wenn der Zeiger beim Loslassen woanders ist.
        """

    def wheelEvent(self, e):
        """Das Mausrad hier NICHT verarbeiten, sondern weiterreichen.

        Qt wuerde den Wert stillschweigend aendern, ohne dass jemand davon
        erfaehrt. In den Einstellungen soll das Rad die Seite scrollen – ein
        versehentlich verstellter Regler beim Scrollen waere aergerlich.
        """
        e.ignore()


class VolumeSlider(Slider):
    """Lautstaerkeregler mit eingebauter Pegelanzeige.

    Der Ausschlag liegt waagerecht *in* der Schiene – wie bei einem Mischpult,
    wo Regelweg und Aussteuerung dieselbe Bahn teilen. Deshalb wird hier alles
    selbst gezeichnet statt ueber die Stilvorlage.
    """

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.muted = False
        self.meter_an = True
        self._pegel = 0.0
        self._halten = 0.0
        self._spitze = 0.0     # Markierung, die kurz stehen bleibt
        self._griff = 0.0      # 0 = ruhend, 1 = angefasst
        self.setFixedHeight(24)
        self.setAttribute(Qt.WA_Hover, True)
        self._wachsen = QPropertyAnimation(self, b"griff", self)
        self._wachsen.setDuration(140)
        self._wachsen.setEasingCurve(QEasingCurve.OutCubic)
        self._gleiten = QPropertyAnimation(self, b"value", self)
        self._gleiten.setDuration(self.GLEITEN_MS)
        self._gleiten.setEasingCurve(QEasingCurve.OutCubic)

    SCHRITT = 4          # Prozentpunkte je Rastung
    GLEITEN_MS = 130     # kurz genug, dass es nicht traege wirkt

    def weich_setzen(self, wert):
        """Werte von aussen gleiten lassen, statt sie springen zu lassen.

        Gemeint sind Aenderungen, die woanders herkommen: Daumenrad,
        Profilwechsel, der Abgleich im Takt, ein anderes Programm am
        Windows-Mixer. Was der Nutzer hier selbst anfasst – ziehen, Rad ueber
        dem Regler – muss dagegen sofort folgen, sonst haengt es am Gummiband.
        """
        wert = max(0, min(100, int(wert)))
        self._gleiten.stop()
        if abs(wert - self.value()) <= 1:
            self.setValue(wert)         # ein Punkt sieht niemand fliegen
            return
        self._gleiten.setStartValue(self.value())
        self._gleiten.setEndValue(wert)
        self._gleiten.start()

    def sofort_setzen(self, wert):
        self._gleiten.stop()
        self.setValue(int(wert))

    # Der Knopf waechst unter dem Zeiger. Kostet nichts und sagt vor dem
    # ersten Klick, dass man ihn anfassen kann.
    def get_griff(self):
        return self._griff

    def set_griff(self, wert):
        self._griff = wert
        self.update()

    griff = Property(float, get_griff, set_griff)

    def _greifen(self, an):
        self._wachsen.stop()
        self._wachsen.setStartValue(self._griff)
        self._wachsen.setEndValue(1.0 if an else 0.0)
        self._wachsen.start()

    def enterEvent(self, e):
        self._greifen(True)

    def leaveEvent(self, e):
        if not self.isSliderDown():
            self._greifen(False)

    def _losgelassen_aussehen(self, e):
        if not self.rect().contains(e.position().toPoint()):
            self._greifen(False)

    def _anfassen(self):
        self._gleiten.stop()

    def wheelEvent(self, e):
        """Rad ueber dem Regler regelt diese App.

        Bewusst hier und nicht nur in der Zeile: Der Regler liegt oben und
        bekommt das Ereignis zuerst. Gemeldet wird ueber dieselben Signale wie
        beim Ziehen – sonst wuerde die Lautstaerke nie wirklich gesetzt und
        der Regler beim naechsten Abgleich zurueckspringen.
        """
        e.accept()
        rastungen = e.angleDelta().y() / 120.0
        if not rastungen:
            return
        # Auch bei stumm drehen lassen: sonst kaeme man aus dem Zustand
        # „0 % und stumm“ per Rad nicht mehr heraus.
        neu = max(0, min(100, self.value() + int(round(rastungen * self.SCHRITT))))
        if neu != self.value():
            self.sofort_setzen(neu)     # eigene Eingabe: ohne Nachlauf
            self.sliderMoved.emit(neu)
            self.sliderReleased.emit()

    def set_pegel(self, wert):
        # Kommt bereits in Reglerskala herein – die Audio-Schicht rechnet den
        # Spitzenwert um. Hier nichts mehr stauchen, sonst zweimal.
        wert = max(0.0, min(1.0, wert))
        self._pegel = wert
        # langsamer Rueckgang, damit Spitzen stehen bleiben statt zu zappeln
        neu = max(wert, self._halten - 0.06)
        # Die Spitzenmarkierung faellt noch traeger – wie am Mischpult
        spitze = max(wert, self._spitze - 0.018)
        if (abs(neu - self._halten) > 0.004
                or abs(spitze - self._spitze) > 0.004
                or (self._halten and wert <= 0.001)):
            self._halten = max(0.0, neu)
            self._spitze = max(0.0, spitze)
            self.update()

    def paintEvent(self, e):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        h = 8              # etwas dicker: der Pegelstreifen braucht Flaeche
        knopf = 14.0 + 2.0 * self._griff
        y = (self.height() - h) / 2.0
        weg = self.width() - knopf                    # Laufweg des Knopfs
        anteil = self.value() / 100.0
        fuell_breite = knopf / 2.0 + weg * anteil

        # Schiene – eine Vertiefung, deshalb dunkler als die Karte und mit
        # einem angedeuteten Schatten an der oberen Innenkante.
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.senke))
        p.drawRoundedRect(QRectF(0, y, self.width(), h), h / 2.0, h / 2.0)
        schatten = QColor(0, 0, 0, 46 if not t.hell else 26)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(schatten, 1.0))
        p.drawRoundedRect(QRectF(0.5, y + 0.5, self.width() - 1.0, h - 1.0),
                          (h - 1.0) / 2.0, (h - 1.0) / 2.0)
        p.setPen(Qt.NoPen)

        # Fuellung bis zum eingestellten Wert
        if fuell_breite > h:
            if self.muted:
                p.setBrush(QColor(t.off))
            else:
                # Einfarbig, nicht als Verlauf. Ein Farbverlauf ueber die
                # Fuellung ist das Erkennungszeichen eines Fortschrittsbalkens
                # aus einer Vorlagensammlung – und er macht denselben Pegel je
                # nach Position verschieden hell.
                p.setBrush(QColor(t.accent))
            p.drawRoundedRect(QRectF(0, y, fuell_breite, h), h / 2.0, h / 2.0)

        # Pegel: LED-Segmente INNERHALB der Fuellung, dazu eine Spitzen-
        # markierung, die traeger zurueckfaellt. Der Ausschlag kann nie lauter
        # sein als eingestellt – so bleibt die Anzeige ehrlich.
        if self.meter_an and not self.muted and self._halten > 0.008:
            self._pegel_zeichnen(p, y, h, fuell_breite)

        # Knopf. Der Schatten darunter ist aus drei Ringen mit fallender
        # Deckkraft gebaut – QPainter kann nicht weichzeichnen, und ein
        # harter Rand sieht aufgeklebt aus.
        kx = weg * anteil
        mitte = QRectF(kx, (self.height() - knopf) / 2.0, knopf, knopf)
        for i, deckung in enumerate((10, 18, 30) if not t.hell else (14, 22, 34)):
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(0, 0, 0, deckung), 1.0))
            weite = 2.4 - i * 0.8
            p.drawEllipse(mitte.adjusted(-weite, -weite + 0.4,
                                         weite, weite + 0.8))
        p.setBrush(QColor(t.knob))
        # Im hellen Modus liegt ein weisser Knopf auf hellem Grund – ohne
        # Kante verschwindet er, sobald er ueber die leere Schiene faehrt.
        p.setPen(QPen(QColor(mix(t.stroke, t.fg, 0.3)), 1.0) if t.hell
                 else Qt.NoPen)
        p.drawEllipse(mitte.adjusted(0.5, 0.5, -0.5, -0.5) if t.hell else mitte)

    def _pegel_zeichnen(self, p, y, h, fuell_breite):
        """Aussteuerung als heller Streifen in der Reglerbahn.

        Er sitzt innerhalb der Fuellung – lauter als eingestellt kann eine App
        nicht sein, und das soll man auch sehen. Nach rechts wird er kraeftiger,
        damit hohe Ausschlaege ins Auge fallen.
        """
        breite = fuell_breite * self._halten
        if breite <= 3:
            return
        innen_y = y + 1.0
        innen_h = h - 2.0
        # Im hellen Modus liegt der Streifen auf farbiger Fuellung – dort
        # traegt Weiss ebenfalls, muss aber dichter sein.
        anfang = 130 if not self.theme.hell else 170
        ende = 255
        g = QLinearGradient(0, 0, breite, 0)
        g.setColorAt(0.0, QColor(255, 255, 255, anfang))
        g.setColorAt(1.0, QColor(255, 255, 255, ende))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(1.0, innen_y, breite - 2.0, innen_h),
                          innen_h / 2.0, innen_h / 2.0)

        # Spitzenmarkierung: bleibt kurz stehen und faellt traeger zurueck
        if self._spitze > self._halten + 0.03:
            sx = fuell_breite * self._spitze
            if sx < fuell_breite - 2:
                p.setBrush(QColor(255, 255, 255, 210))
                p.drawRoundedRect(QRectF(sx - 2.0, innen_y, 2.5, innen_h),
                                  1.2, 1.2)


class Prozent(QWidget):
    """Die Zahl rechts in der Mixer-Zeile.

    Jede Ziffer bekommt eine feste Zelle. Ohne das wandert die Zahl beim
    Regeln hin und her, weil die 1 schmaler ist als die 8 – bei einem Wert,
    der sich staendig aendert, faellt genau das auf. Das Zeichen dahinter ist
    kleiner und leiser: es aendert sich nie und muss nicht mitschreien.
    """

    LUFT = 3.0

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._wert = 0
        self._text = ""            # gesetzt = statt der Zahl anzeigen
        self.setFixedWidth(52)

    def set_wert(self, wert):
        wert = int(wert)
        if wert != self._wert or self._text:
            self._wert, self._text = wert, ""
            self.update()

    def set_text(self, text):
        if text != self._text:
            self._text = text
            self.update()

    def text(self):
        """Was gerade zu lesen ist."""
        return self._text or "{} %".format(self._wert)

    def _schriften(self):
        familie = self.font().family()
        zahl = QFont(familie)
        zahl.setPixelSize(16)
        zahl.setWeight(QFont.Bold)
        zeichen = QFont(familie)
        zeichen.setPixelSize(11)
        zeichen.setWeight(QFont.DemiBold)
        return zahl, zeichen

    def paintEvent(self, e):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        zahl_f, zeichen_f = self._schriften()
        if self._text:
            p.setFont(zeichen_f)
            p.setPen(QColor(t.muted))
            p.drawText(self.rect(), Qt.AlignRight | Qt.AlignVCenter, self._text)
            return
        ziffern = str(max(0, self._wert))
        p.setFont(zahl_f)
        mass = p.fontMetrics()
        zelle = max(mass.horizontalAdvance(str(d)) for d in range(10))
        p.setFont(zeichen_f)
        zeichen_breite = p.fontMetrics().horizontalAdvance("%")
        x = self.width() - (len(ziffern) * zelle + self.LUFT + zeichen_breite)
        # Beide auf derselben Grundlinie: sonst schwebt das kleinere Zeichen
        # neben der Zahl, statt mit ihr auf einer Linie zu stehen.
        basis = (self.height() + mass.ascent() - mass.descent()) / 2.0

        p.setFont(zahl_f)
        p.setPen(QColor(t.fg))
        for ziffer in ziffern:
            versatz = (zelle - mass.horizontalAdvance(ziffer)) / 2.0
            p.drawText(QRectF(x + versatz, basis - mass.ascent(),
                              zelle, mass.height()),
                       Qt.AlignLeft | Qt.AlignTop, ziffer)
            x += zelle
        p.setFont(zeichen_f)
        klein = p.fontMetrics()
        p.setPen(QColor(t.muted))
        p.drawText(QRectF(x + self.LUFT, basis - klein.ascent(),
                          zeichen_breite, klein.height()),
                   Qt.AlignLeft | Qt.AlignTop, "%")


class _ElidedLabel(QLabel):
    """Beschriftung, die bei Platzmangel mit „…“ endet statt abzubrechen."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._voll = text

    def setText(self, text):
        self._voll = text
        self._neu_setzen()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._neu_setzen()

    def _neu_setzen(self):
        gekuerzt = self.fontMetrics().elidedText(
            self._voll, Qt.ElideRight, max(10, self.width()))
        QLabel.setText(self, gekuerzt)
        self.setToolTip(self._voll if gekuerzt != self._voll else "")


class MixerRow(QWidget):
    """Eine Zeile im Mixer: Haken, Symbol, Name, Pegel, Regler, Prozent."""

    toggled = Signal(str, bool)          # key, gewaehlt
    volume_changed = Signal(str, float, bool)   # key, 0..1, endgueltig
    mute_clicked = Signal(str, bool)
    angleichen_clicked = Signal(str, bool)

    def __init__(self, item, gewaehlt, theme, meter_an=True, parent=None):
        super().__init__(parent)
        self.key = item["key"]
        self.theme = theme
        self.muted = bool(item.get("muted"))
        self._gewaehlt = bool(gewaehlt)
        self._hover = False
        self._selbst_gestellt = 0.0   # Zeitpunkt eigener Eingabe
        self.setObjectName("Zeile")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedHeight(56)
        # Der Balken am linken Rand faehrt ein, statt zu erscheinen – das
        # zeigt beilaeufig, welche Zeile gerade dazugekommen ist.
        self._balken = 1.0 if self._gewaehlt else 0.0
        self._fahrt = QPropertyAnimation(self, b"balken", self)
        self._fahrt.setDuration(180)
        self._fahrt.setEasingCurve(QEasingCurve.OutCubic)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        self.box = _Kaestchen(theme)
        # Wird die Zeile neu gebaut, waehrend die App schon angehakt ist,
        # muss das Kaestchen das von Anfang an zeigen – sonst leuchtet die
        # Zeile als gewaehlt, das Haekchen daneben bleibt aber leer.
        self.box.setChecked(self._gewaehlt)
        self.box.clicked.connect(lambda: self.toggled.emit(self.key,
                                                           not self._gewaehlt))
        lay.addWidget(self.box)
        lay.addSpacing(12)

        self.symbol = QLabel()
        self.symbol.setFixedSize(32, 32)
        lay.addWidget(self.symbol)
        lay.addSpacing(12)

        self.name = _ElidedLabel(item["name"])
        self.name.setObjectName("NameGewaehlt" if self._gewaehlt else "Name")
        self.name.setMinimumWidth(50)
        lay.addWidget(self.name, 1)

        # Knopf fuer „Lautstaerke angleichen“. Er steht auch im ausgeschalteten
        # Zustand da – blass, aber sichtbar. Vorher lag die Sache in einem
        # Rechtsklick-Menue und war damit praktisch nicht auffindbar.
        self.angleich_knopf = QPushButton()
        self.angleich_knopf.setObjectName("Flach")
        self.angleich_knopf.setFixedSize(32, 32)
        self.angleich_knopf.setCursor(Qt.PointingHandCursor)
        self.angleich_knopf.clicked.connect(
            lambda: self.angleichen_clicked.emit(self.key,
                                                 not self._angleichen))
        # Nicht bei Gesamtlautstaerke und Systemklaengen: Die Gesamtlautstaerke
        # hat keinen eigenen Pegel, an dem sich etwas angleichen liesse, und
        # ein Knopf, der nichts tut, ist schlimmer als keiner.
        if self.key.startswith("#"):
            self.angleich_knopf.hide()
        lay.addWidget(self.angleich_knopf)
        lay.addSpacing(4)

        self.lautsprecher = QPushButton()
        self.lautsprecher.setObjectName("Flach")
        self.lautsprecher.setFixedSize(32, 32)
        self.lautsprecher.setCursor(Qt.PointingHandCursor)
        self.lautsprecher.setToolTip(T("stumm_schalten"))
        self.lautsprecher.clicked.connect(
            lambda: self.mute_clicked.emit(self.key, not self.muted))
        lay.addWidget(self.lautsprecher)
        lay.addSpacing(12)

        self.regler = VolumeSlider(theme)
        self.regler.setFixedWidth(128)
        self.regler.meter_an = meter_an
        self.regler.setValue(int(round(item["volume"] * 100)))
        self.regler.sliderMoved.connect(self._geschoben)
        self.regler.sliderReleased.connect(self._losgelassen)
        # Zahl und Lautsprecher haengen am Regler selbst, nicht am Zielwert –
        # sonst stuenden sie schon auf dem neuen Wert, waehrend der Regler
        # noch unterwegs ist.
        self.regler.valueChanged.connect(self._wert_anzeigen)
        lay.addWidget(self.regler)
        lay.addSpacing(10)

        self.prozent = Prozent(theme)
        lay.addWidget(self.prozent)

        self._exe = item.get("exe")
        self._name_text = item["name"]
        self._angleichen = bool(item.get("angleichen"))
        self.symbol_setzen()
        self._beschriften()
        self._angleich_zeichnen()

    # ---- Aussehen --------------------------------------------------------
    def get_balken(self):
        return self._balken

    def set_balken(self, wert):
        self._balken = wert
        self.update()

    balken = Property(float, get_balken, set_balken)

    def paintEvent(self, e):
        """Hintergrund und Auswahlbalken.

        Frueher kam beides aus der Stilvorlage. Die gewaehlte Zeile war dabei
        kraeftig eingefaerbt – bei mehreren angehakten Apps wurde die Liste
        bunt. Jetzt traegt ein schmaler Balken am linken Rand die Aussage, die
        Flaeche hebt sich nur noch leicht ab.
        """
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self._gewaehlt:
            grund = t.row_sel_hover if self._hover else t.row_sel
        elif self._hover:
            grund = t.row_hover
        else:
            grund = None
        p.setPen(Qt.NoPen)
        if grund:
            p.setBrush(QColor(grund))
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 12, 12)
        if self._balken > 0.01:
            hoch = (self.height() - 20) * self._balken
            p.setBrush(QColor(t.accent))
            p.drawRoundedRect(
                QRectF(0, (self.height() - hoch) / 2.0, 3.0, hoch), 1.5, 1.5)

    def symbol_setzen(self):
        dpr = self.devicePixelRatioF()
        pm = icons.exe_icon(self._exe, 32, dpr)
        if pm is None:
            if self.key == MASTER_KEY:
                pm = icons.app_logo(32, self.theme.accent, dpr)
            else:
                pm = icons.buchstaben_pixmap(
                    self._name_text[:1] or "?", 32,
                    self.theme.card2, self.theme.muted, dpr)
        # Stumm = blasses Symbol. `opacity` aus der Stilvorlage wirkt bei
        # Qt-Widgets nicht – die Deckkraft muss ins Bild selbst.
        if self.muted:
            pm = _verblassen(pm, 0.35)
        self.symbol.setPixmap(pm)
        self._lautsprecher_zeichnen()

    def _lautsprecher_zeichnen(self):
        t = self.theme
        farbe = t.accent if self.muted else t.fg
        wert = 0.0 if self.muted else max(0.05, self.regler.value() / 100.0)
        self.lautsprecher.setIcon(
            icons.speaker_pixmap(20, wert, farbe, self.devicePixelRatioF(),
                                 stumm=self.muted))
        self.lautsprecher.setIconSize(QSize(20, 20))

    def _angleich_zeichnen(self):
        """Eingeschaltet in der Akzentfarbe, sonst blass.

        Ein Knopf, der nur im eingeschalteten Zustand zu sehen waere, laesst
        sich nicht einschalten – deshalb ist er immer da, aber zurueckhaltend.
        """
        t = self.theme
        farbe = t.accent if self._angleichen else t.fg
        pm = icons.pixmap("angleichen", 22, farbe, self.devicePixelRatioF())
        if not self._angleichen:
            pm = _verblassen(pm, 0.45)
        self.angleich_knopf.setIcon(pm)
        self.angleich_knopf.setIconSize(QSize(22, 22))
        self.angleich_knopf.setToolTip(T("angleichen_an") if self._angleichen
                                       else T("angleichen_hilfe"))

    def set_angleichen(self, an):
        an = bool(an)
        if an == self._angleichen:
            return
        self._angleichen = an
        self._angleich_zeichnen()

    def _wert_anzeigen(self, wert):
        if not self.muted:
            self.prozent.set_wert(wert)
        self._lautsprecher_zeichnen()

    def _beschriften(self):
        if self.muted:
            self.prozent.set_text(T("stumm"))
        else:
            self.prozent.set_wert(self.regler.value())

    def theme_wechseln(self, theme):
        self.theme = theme
        self.box.theme = theme
        self.regler.theme = theme
        self.prozent.theme = theme
        self.regler.update()
        self.prozent.update()
        self.update()
        self.symbol_setzen()
        self._angleich_zeichnen()

    # ---- Zustand ---------------------------------------------------------
    def set_gewaehlt(self, an):
        an = bool(an)
        if an == self._gewaehlt:
            return
        self._gewaehlt = an
        self.box.setChecked(an)
        self.name.setObjectName("NameGewaehlt" if an else "Name")
        self.name.style().unpolish(self.name)
        self.name.style().polish(self.name)
        self._fahrt.stop()
        self._fahrt.setStartValue(self._balken)
        self._fahrt.setEndValue(1.0 if an else 0.0)
        self._fahrt.start()
        self.update()

    def set_volume(self, wert):
        """Wert von aussen uebernehmen (Refresh, Daumenrad).

        Kurz nach einer eigenen Eingabe wird das ignoriert: Die App liest die
        echten Pegel im Takt, und ein Durchlauf, der schon unterwegs war,
        wuerde sonst den gerade gestellten Wert zurueckschreiben.
        """
        if self.regler.isSliderDown():
            return
        if time.monotonic() - self._selbst_gestellt < 0.7:
            return
        neu = int(round(wert * 100))
        if neu == self.regler.value():
            return
        self.regler.weich_setzen(neu)

    def set_muted(self, an):
        an = bool(an)
        if an == self.muted:
            return
        self.muted = an
        self.regler.muted = an
        self.regler.update()
        self.symbol_setzen()
        self._beschriften()

    def set_pegel(self, wert):
        self.regler.set_pegel(wert)

    def set_meter_sichtbar(self, an):
        self.regler.meter_an = an
        self.regler.update()

    def aktualisieren(self, item):
        if item["name"] != self._name_text:
            self._name_text = item["name"]
            self.name.setText(item["name"])
        if item.get("exe") and item["exe"] != self._exe:
            self._exe = item["exe"]
            self.symbol_setzen()
        self.set_muted(bool(item.get("muted")))
        self.set_angleichen(item.get("angleichen"))
        self.set_volume(item["volume"])

    # ---- Maus ------------------------------------------------------------
    def _geschoben(self, wert):
        self._selbst_gestellt = time.monotonic()
        self.volume_changed.emit(self.key, wert / 100.0, False)

    def _losgelassen(self):
        self._selbst_gestellt = time.monotonic()
        self.volume_changed.emit(self.key, self.regler.value() / 100.0, True)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.toggled.emit(self.key, not self._gewaehlt)

    # Kein wheelEvent: Das Rad ueber der Zeile soll die Liste scrollen. Nur
    # genau ueber dem Regler verstellt es die Lautstaerke – das erledigt
    # VolumeSlider selbst. Vorher schluckte die ganze Zeile das Rad, dadurch
    # liess sich die Liste kaum noch bewegen, ohne etwas zu verstellen.


class _Kaestchen(QWidget):
    """Auswahl-Kaestchen mit weichem Haken."""

    clicked = Signal()

    def __init__(self, theme, groesse=24, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._an = False
        self._hover = False
        self.setFixedSize(groesse, groesse)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

    def setChecked(self, an):
        self._an = bool(an)
        self.update()

    def isChecked(self):
        return self._an

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
            e.accept()

    def paintEvent(self, e):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self._an:
            grund = QColor(t.accent)
            if self._hover:
                grund = QColor(t.accent_hover)
            p.setPen(Qt.NoPen)
            p.setBrush(grund)
        else:
            # Leer heisst leer: ein Rahmen, keine Fuellung. Der gefuellte
            # graue Block sah aus wie ein abgeschalteter Knopf – man haelt
            # ihn fuer gesperrt statt fuer anklickbar.
            rand = QColor(mix(t.stroke, t.fg, 0.22 if self._hover else 0.0))
            p.setPen(QPen(rand, 1.6))
            p.setBrush(QColor(t.senke) if self._hover else Qt.NoBrush)
            r = r.adjusted(0.3, 0.3, -0.3, -0.3)
        p.drawRoundedRect(r, 7, 7)
        if self._an:
            pfad = QPainterPath()
            w, h = self.width(), self.height()
            pfad.moveTo(w * 0.27, h * 0.52)
            pfad.lineTo(w * 0.43, h * 0.68)
            pfad.lineTo(w * 0.74, h * 0.34)
            stift = QPen(QColor("#FFFFFF"), max(2.0, w * 0.11))
            stift.setCapStyle(Qt.RoundCap)
            stift.setJoinStyle(Qt.RoundJoin)
            p.setPen(stift)
            p.drawPath(pfad)


class FadeScroll(QWidget):
    """Blendet den Inhalt darunter weich aus.

    Liegt als durchsichtiges Widget ueber dem Rollbereich – in Tk brauchte es
    dafuer noch einen Trick mit der angeschnittenen Zeile.
    """

    def __init__(self, theme, hoehe=28, parent=None, auf_karte=True):
        super().__init__(parent)
        self.theme = theme
        self.hoehe = hoehe
        self.oben = False
        self.unten = False
        # In den Einstellungen liegt der Rollbereich auf dem Fensterhinter-
        # grund, im Mixer auf der Karte – die Blende muss dazu passen.
        self.auf_karte = auf_karte
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def zeigen(self, oben, unten):
        if (oben, unten) != (self.oben, self.unten):
            self.oben, self.unten = oben, unten
            self.update()

    def paintEvent(self, e):
        if not (self.oben or self.unten):
            return
        p = QPainter(self)
        oben_farbe = (self.theme.card_top if self.auf_karte else self.theme.bg)
        farbe = QColor(self.theme.card_bottom if self.auf_karte
                       else self.theme.bg)
        w, h = self.width(), self.height()
        if self.oben:
            g = QLinearGradient(0, 0, 0, self.hoehe)
            c = QColor(oben_farbe)
            c.setAlpha(255)
            g.setColorAt(0.0, c)
            c2 = QColor(c)
            c2.setAlpha(0)
            g.setColorAt(1.0, c2)
            p.fillRect(0, 0, w, self.hoehe, g)
        if self.unten:
            g = QLinearGradient(0, h - self.hoehe, 0, h)
            c = QColor(farbe)
            c.setAlpha(0)
            g.setColorAt(0.0, c)
            c2 = QColor(farbe)
            c2.setAlpha(255)
            g.setColorAt(1.0, c2)
            p.fillRect(0, h - self.hoehe, w, self.hoehe, g)
