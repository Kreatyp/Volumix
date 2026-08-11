# -*- coding: utf-8 -*-
"""Lautstaerke-Einblendung.

In der Tk-Fassung war das ein Layered Window mit von Hand gebautem RGBA-Bild.
Qt kann rahmenlose, durchscheinende Fenster von sich aus – hier bleibt nur das
Zeichnen selbst.
"""
from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF,
                            Qt, QTimer, Property)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QLinearGradient,
                           QPainter)
from PySide6.QtWidgets import QWidget

from . import icons
from .theme import glaettung, schrift
from .widgets import flaeche_zeichnen


class Osd(QWidget):
    """Kleine Anzeige, die beim Regeln kurz erscheint."""

    MAX_SYMBOLE = 6

    def __init__(self, theme):
        super().__init__(None)
        self.theme = theme
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                            | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._quellen = []          # (key, exe-Pfad, Name)
        self._prozent = 0
        self._gezeigt = 0.0         # weich nachgefuehrter Balkenwert
        self._text = None
        self._groesse = 45
        self._x, self._y = 50, 88
        self._versatz = 0.0
        self._akzent = None

        self._weg = QTimer(self)
        self._weg.setSingleShot(True)
        self._weg.timeout.connect(self.ausblenden)

        self._anim = QPropertyAnimation(self, b"versatz", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._fertig)

        # Der Balken laeuft dem Wert weich hinterher, statt zu springen –
        # beim Drehen am Rad wirkt das deutlich ruhiger.
        self._balken = QPropertyAnimation(self, b"gezeigt", self)
        self._balken.setDuration(130)
        self._balken.setEasingCurve(QEasingCurve.OutCubic)

    def get_versatz(self):
        return self._versatz

    def set_versatz(self, wert):
        self._versatz = wert
        self.setWindowOpacity(max(0.0, 1.0 - wert))
        self._platzieren()

    versatz = Property(float, get_versatz, set_versatz)

    def get_gezeigt(self):
        return self._gezeigt

    def set_gezeigt(self, wert):
        self._gezeigt = wert
        self.update()

    gezeigt = Property(float, get_gezeigt, set_gezeigt)

    def einstellen(self, groesse, x, y, theme=None):
        if theme is not None:
            self.theme = theme
        self._groesse, self._x, self._y = groesse, x, y
        self._masse()
        if self.isVisible():
            self._platzieren()
            self.update()

    def _masse(self):
        f = 0.6 + (self._groesse / 100.0) * 1.4      # 60 % .. 200 %
        self.skala = f
        self.setFixedSize(int(340 * f), int(96 * f))

    def _platzieren(self):
        bs = QGuiApplication.screenAt(QPoint(0, 0)) or QGuiApplication.primaryScreen()
        bild = bs.availableGeometry()
        w, h = self.width(), self.height()
        x = bild.x() + int((bild.width() - w) * self._x / 100.0)
        y = bild.y() + int((bild.height() - h) * self._y / 100.0)
        self.move(x, y + int(self._versatz * h * 0.6))

    def zeigen(self, quellen, prozent, text=None, dauer=1100, akzent=None):
        # Erwartet (Schluessel, Pfad, Name). Alles andere wird verworfen statt
        # spaeter beim Zeichnen zu scheitern – ein Fehler im paintEvent reisst
        # sonst das ganze Programm mit.
        sauber = []
        for eintrag in quellen or []:
            try:
                key, exe, name = eintrag
            except (TypeError, ValueError):
                continue
            sauber.append((key, exe, str(name or "")))
        self._quellen = sauber[:self.MAX_SYMBOLE]
        neu = prozent if prozent is not None else 0
        self._text = text
        if akzent:
            self._akzent = akzent
        self._masse()
        self._anim.stop()
        self._versatz = 0.0
        self.setWindowOpacity(1.0)
        self._platzieren()
        war_sichtbar = self.isVisible()
        self._balken.stop()
        if war_sichtbar:
            self._balken.setStartValue(self._gezeigt)
            self._balken.setEndValue(float(neu))
            self._balken.start()
        else:
            self._gezeigt = float(neu)      # frisch eingeblendet: kein Nachlauf
        self._prozent = neu
        self.update()
        if not war_sichtbar:
            self.show()
        self._weg.start(dauer)

    def ausblenden(self):
        if not self.isVisible():
            return
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _fertig(self):
        if self._versatz >= 0.99:
            self.hide()
            self._versatz = 0.0
            self.setWindowOpacity(1.0)

    def paintEvent(self, e):
        t = self.theme
        f = self.skala
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rand = 10 * f
        karte = QRectF(rand, rand, self.width() - 2 * rand,
                       self.height() - 2 * rand)
        radius = 20 * f

        # weicher Schatten
        for i in range(int(6 * f), 0, -1):
            c = QColor(0, 0, 0, int(10 + i * 2))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(karte.adjusted(-i, -i + i * 0.4, i, i + i * 0.4),
                              radius + i, radius + i)

        flaeche_zeichnen(p, t, karte, radius)

        dpr = self.devicePixelRatioF()
        d = int(30 * f)
        x = karte.left() + 16 * f
        mitte = karte.center().y()
        akzent = QColor(self._akzent or t.accent)

        # Symbole der gesteuerten Programme – hier in genau der Groesse geholt,
        # in der sie gezeichnet werden. Fertige Pixmaps aus dem Mixer waeren
        # 32 px gross und muessten hochskaliert werden.
        for key, exe, name in self._quellen:
            pm = icons.exe_icon(exe, d, dpr)
            if pm is None:
                if key == "#master":
                    pm = icons.app_logo(d, akzent.name(), dpr)
                else:
                    pm = icons.buchstaben_pixmap(name[:1] or "?", d,
                                                 t.senke, t.muted, dpr)
            p.drawPixmap(int(x), int(mitte - d / 2), d, d, pm)
            x += d + 8 * f

        # Lautsprecher, dessen Wellen mit dem Pegel wachsen
        sg = int(26 * f)
        spk = icons.speaker_pixmap(sg, self._prozent / 100.0, t.fg, dpr,
                                   stumm=self._prozent <= 0)
        p.drawPixmap(int(x), int(mitte - sg / 2), sg, sg, spk)
        x += sg + 12 * f

        # Balken
        rechts = karte.right() - 16 * f
        text = self._text or "{} %".format(self._prozent)
        satz = glaettung(QFont(schrift()))
        satz.setPixelSize(int(19 * f))
        satz.setWeight(QFont.Bold)
        p.setFont(satz)
        breite_text = p.fontMetrics().horizontalAdvance(text) + 8
        balken_rechts = rechts - breite_text - 12 * f
        bh = 8 * f
        schiene = QRectF(x, mitte - bh / 2, max(20.0, balken_rechts - x), bh)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.senke))
        p.drawRoundedRect(schiene, bh / 2, bh / 2)
        if self._text is None and self._gezeigt > 0:
            voll = QRectF(schiene)
            voll.setWidth(schiene.width() * max(0.0, min(100.0, self._gezeigt))
                          / 100.0)
            if voll.width() > bh:
                g = QLinearGradient(voll.topLeft(), voll.topRight())
                g.setColorAt(0.0, akzent.lighter(130))
                g.setColorAt(1.0, akzent)
                p.setBrush(g)
                p.drawRoundedRect(voll, bh / 2, bh / 2)

        p.setPen(QColor(t.fg))
        p.drawText(QRectF(balken_rechts, karte.top(), rechts - balken_rechts,
                          karte.height()),
                   Qt.AlignRight | Qt.AlignVCenter, text)
