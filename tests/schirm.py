# -*- coding: utf-8 -*-
"""Testfenster auf den zweiten Bildschirm stellen.

Die Reihen machen echte Fenster auf und klicken darin herum. Auf dem
Hauptbildschirm springen sie dabei mitten in die Arbeit – nebenan stoeren
sie niemanden, und man kann ihnen sogar zusehen.

Gibt es nur einen Bildschirm, passiert nichts. Abschalten laesst es sich
mit `VOLUMIX_TEST_SCHIRM=0`, etwa wenn man die Fenster bewusst vorn haben
moechte.
"""
import os

from PySide6.QtWidgets import QApplication


def nebenan(fenster):
    """Verschiebt das Fenster auf den ersten Bildschirm, der nicht der
    Hauptbildschirm ist. Gibt zurueck, ob es geklappt hat.

    Muss *nach* `show()` gerufen werden: Vorher setzt Qt die Stelle beim
    Anzeigen noch einmal selbst.
    """
    if os.environ.get("VOLUMIX_TEST_SCHIRM") == "0":
        return False
    app = QApplication.instance()
    if app is None:
        return False
    andere = [s for s in app.screens() if s is not app.primaryScreen()]
    if not andere:
        return False
    flaeche = andere[0].availableGeometry()
    # Oben ansetzen statt mittig: Die Fenster wachsen nach unten, und ein
    # hochkant stehender Bildschirm hat oben mehr Luft als in der Mitte.
    fenster.move(flaeche.center().x() - fenster.width() // 2,
                 flaeche.top() + 40)
    return True
