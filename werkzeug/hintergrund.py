# -*- coding: utf-8 -*-
"""Erzeugt ein Hintergrundbild im Stil des Volumix-Fensters.

Dieselbe Rezeptur wie `MainWindow.paintEvent`: ein sehr dunkler Grund, in
dem weiches farbiges Licht steht. Dazu kommen unscharfe Formen – die
„Figuren" –, die dem Bild Tiefe geben, ohne erkennbar etwas darzustellen.

Aufruf:
    python werkzeug\\hintergrund.py                 -> 3840x2160
    python werkzeug\\hintergrund.py 2560 1440       -> eigene Groesse

Drei Dinge, die den Unterschied machen:

* **Rauschen.** Ein 4K-Verlauf ueber fast schwarzem Grund zeigt sonst
  Streifen: Zwischen zwei benachbarten Dunkeltoenen liegt oft nur eine
  Stufe, und die verlaeuft ueber hunderte Pixel. Ein Hauch Rauschen bricht
  die Kanten auf. Ohne das sieht ein solches Bild auf einem guten Monitor
  gebaendert aus, egal wie sauber gerechnet wurde.
* **Die Figuren werden weichgezeichnet, nicht transparent gemalt.** Eine
  Form mit 5 % Deckkraft bleibt eine Form mit erkennbaren Kanten; erst der
  Weichzeichner macht daraus Licht.
* **Randabdunklung.** Ohne sie wirkt der Bildrand offen und das Motiv
  laeuft aus dem Bild heraus.
"""
import random
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import (QApplication, QGraphicsBlurEffect,
                               QGraphicsPixmapItem, QGraphicsScene)

# Farben aus dem dunklen Modus von Volumix, Akzent Blau.
GRUND = "#05070C"
AKZENT = "#3B82F6"
ZWEIT = "#7C5CFF"          # Nachbar im Farbkreis – zwei Toene wirken wie
DRITT = "#14B8A6"          # Licht, ein einzelner wie ein Farbstich

RAUSCHEN = 0.016           # Deckkraft der Rauschkachel
RAND = 0.55                # wie stark die Ecken abgedunkelt werden


def licht(p, breite, hoehe, mx, my, weite, farbe, staerke):
    """Ein weiches rundes Licht im Grund."""
    r = max(breite, hoehe) * weite
    g = QRadialGradient(QPointF(breite * mx, hoehe * my), r)
    innen, aussen = QColor(farbe), QColor(farbe)
    innen.setAlphaF(staerke)
    aussen.setAlphaF(0.0)
    g.setColorAt(0.0, innen)
    g.setColorAt(1.0, aussen)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRect(0, 0, breite, hoehe)


def figuren(breite, hoehe):
    """Unscharfe Formen als eigene Ebene.

    Erst scharf gezeichnet, dann weichgezeichnet – nur so werden aus
    Rechtecken Lichtkoerper statt blasser Rechtecke. Die Anordnung nimmt
    die drei Balken der Wortmarke auf, ohne sie abzubilden.
    """
    ebene = QImage(breite, hoehe, QImage.Format_ARGB32_Premultiplied)
    ebene.fill(Qt.transparent)
    p = QPainter(ebene)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)

    # Weit auseinander und schlank: Eng beieinander verschmelzen sie unter
    # dem Weichzeichner zu einem Klumpen, und dann sieht man keine Figuren
    # mehr, sondern einen Fleck. Die Neigung ist bei allen gleich – das
    # haelt das Bild ruhig, obwohl die Formen ueber die ganze Flaeche
    # verteilt sind.
    formen = [
        # (x, y, breite, hoehe, Drehung, Farbe, Deckkraft)
        (0.13, 0.26, 0.055, 0.42, -16, AKZENT, 0.50),
        (0.25, 0.16, 0.055, 0.30, -16, ZWEIT, 0.38),
        (0.21, 0.62, 0.055, 0.26, -16, DRITT, 0.22),
        (0.47, 0.40, 0.050, 0.34, -16, ZWEIT, 0.26),
        (0.72, 0.24, 0.060, 0.30, -16, AKZENT, 0.34),
        (0.83, 0.55, 0.055, 0.44, -16, ZWEIT, 0.30),
        (0.63, 0.82, 0.050, 0.26, -16, AKZENT, 0.20),
        (0.94, 0.86, 0.050, 0.28, -16, DRITT, 0.16),
    ]
    for mx, my, bw, bh, dreh, farbe, deckung in formen:
        w, h = breite * bw, hoehe * bh
        p.save()
        p.translate(breite * mx, hoehe * my)
        p.rotate(dreh)
        f = QColor(farbe)
        f.setAlphaF(deckung)
        p.setBrush(f)
        p.drawRoundedRect(QRectF(-w / 2, -h / 2, w, h), w / 2, w / 2)
        p.restore()
    p.end()

    # Weichzeichnen ueber eine Szene – derselbe Weg wie beim Coverbild.
    szene = QGraphicsScene()
    stueck = QGraphicsPixmapItem(QPixmap.fromImage(ebene))
    effekt = QGraphicsBlurEffect()
    effekt.setBlurRadius(max(breite, hoehe) * 0.045)
    effekt.setBlurHints(QGraphicsBlurEffect.QualityHint)
    stueck.setGraphicsEffect(effekt)
    szene.addItem(stueck)

    weich = QImage(breite, hoehe, QImage.Format_ARGB32_Premultiplied)
    weich.fill(Qt.transparent)
    q = QPainter(weich)
    q.setRenderHint(QPainter.SmoothPixmapTransform, True)
    szene.render(q, QRectF(0, 0, breite, hoehe), QRectF(0, 0, breite, hoehe))
    q.end()
    return weich


def rauschkachel(kante=256, saat=7):
    """Feines Graurauschen als kachelbares Bild."""
    zufall = random.Random(saat)
    kachel = QImage(kante, kante, QImage.Format_ARGB32_Premultiplied)
    for y in range(kante):
        for x in range(kante):
            g = zufall.randint(0, 255)
            kachel.setPixelColor(x, y, QColor(g, g, g))
    return kachel


def bauen(breite, hoehe):
    bild = QImage(breite, hoehe, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(bild)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Grund: von oben leicht aufgehellt, nach unten tiefer
    grund = QLinearGradient(0, 0, 0, hoehe)
    grund.setColorAt(0.0, QColor("#080B14"))
    grund.setColorAt(0.55, QColor(GRUND))
    grund.setColorAt(1.0, QColor("#04050A"))
    p.fillRect(0, 0, breite, hoehe, grund)

    # Weites Licht im Grund – gross und schwach, das traegt die Stimmung
    licht(p, breite, hoehe, 0.20, 0.12, 0.85, AKZENT, 0.20)
    licht(p, breite, hoehe, 0.88, 0.72, 0.70, ZWEIT, 0.15)
    licht(p, breite, hoehe, 0.52, 1.05, 0.75, AKZENT, 0.10)
    licht(p, breite, hoehe, 0.05, 0.90, 0.55, DRITT, 0.07)

    # Die unscharfen Figuren darueber
    p.setOpacity(0.85)
    p.drawImage(0, 0, figuren(breite, hoehe))
    p.setOpacity(1.0)

    # Zu den Ecken hin abdunkeln
    ecken = QRadialGradient(QPointF(breite * 0.5, hoehe * 0.45),
                            max(breite, hoehe) * 0.78)
    klar, dicht = QColor("#020306"), QColor("#020306")
    klar.setAlphaF(0.0)
    dicht.setAlphaF(RAND)
    ecken.setColorAt(0.30, klar)
    ecken.setColorAt(1.0, dicht)
    p.setPen(Qt.NoPen)
    p.setBrush(ecken)
    p.drawRect(0, 0, breite, hoehe)

    # Rauschen gegen die Streifenbildung
    p.setOpacity(RAUSCHEN)
    p.setCompositionMode(QPainter.CompositionMode_Overlay)
    kachel = rauschkachel()
    for y in range(0, hoehe, kachel.height()):
        for x in range(0, breite, kachel.width()):
            p.drawImage(x, y, kachel)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.setOpacity(1.0)
    p.end()
    return bild


def main():
    app = QApplication(sys.argv)          # noqa: F841 – Qt braucht sie
    breite = int(sys.argv[1]) if len(sys.argv) > 2 else 3840
    hoehe = int(sys.argv[2]) if len(sys.argv) > 2 else 2160
    ziel = sys.argv[3] if len(sys.argv) > 3 else "Volumix-Hintergrund.png"
    bild = bauen(breite, hoehe)
    # Rueckgabewert pruefen: `save` wirft nicht, es gibt False zurueck – ein
    # fehlender Ordner oder ein falscher Pfad ginge sonst als Erfolg durch.
    if not bild.save(ziel):
        print("Konnte nicht schreiben: %s" % ziel)
        raise SystemExit(1)
    print("%s  %dx%d" % (ziel, breite, hoehe))


if __name__ == "__main__":
    main()
