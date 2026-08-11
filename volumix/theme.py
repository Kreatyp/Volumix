# -*- coding: utf-8 -*-
"""Schrift, Farben und Stilvorlage.

Anders als in der Tk-Fassung wird hier nichts gerendert: Qt bekommt eine
Stilvorlage (QSS, an CSS angelehnt) und zeichnet Ecken, Verlaeufe und
Hover-Zustaende selbst auf der Grafikkarte.

Grundregel fuer die Flaechen: Was tiefer liegt, ist dunkler. Reglerschienen
und leere Kaestchen sind Vertiefungen (`senke`), Karten und Knoepfe liegen
darueber. Vorher war die Schiene heller als ihre Karte – sie sah dadurch
erhaben aus, obwohl etwas darin laeuft.
"""
import os

from . import config

# Die Oberflaechenschrift von Windows selbst – dieselbe, die Explorer, die
# Einstellungen und die meisten Programme benutzen.
#
# Vorher lag hier eine mitgelieferte Schrift, damit das Programm nicht wie
# jedes andere aussieht. Der Preis dafuer war zu hoch: Eine Schriftdatei ist
# nur eine Datei. Segoe UI Variable ist mehr – Windows liefert sie in drei
# optischen Groessen, jede fuer ihren Bereich gezeichnet, und rendert sie auf
# jedem Bildschirm gleich. Genau daran lag es, dass eine fremde Schrift bei
# 11 px krisselig wurde und auf zwei Rechnern verschieden aussah.
#
#   Small    fuer die kleinen, gesperrten Beschriftungen
#   Text     fuer alles Normale
#   Display  fuer Wortmarke und Ueberschriften
#
# Der zweite Name ist jeweils der Rueckfall fuer Windows 10, das die
# Variable-Fassung noch nicht hat.
SCHRIFT_KLEIN = '"Segoe UI Variable Small", "Segoe UI"'
SCHRIFT_TEXT = '"Segoe UI Variable Text", "Segoe UI"'
SCHRIFT_GROSS = '"Segoe UI Variable Display", "Segoe UI"'
SCHRIFT_ERSATZ = "Segoe UI"

# (Schluessel, Anzeigename, dunkel, hell)
PALETTE = [
    ("violet", "Violett", "#7C5CFF", "#6C4CF5"),
    ("blue", "Blau", "#3B82F6", "#2563EB"),
    ("teal", "Petrol", "#14B8A6", "#0D9488"),
    ("green", "Grün", "#22C55E", "#16A34A"),
    ("lime", "Oliv", "#84CC16", "#65A30D"),
    ("amber", "Bernstein", "#F59E0B", "#D97706"),
    ("orange", "Orange", "#F97316", "#EA580C"),
    ("red", "Rot", "#EF4444", "#DC2626"),
    ("pink", "Pink", "#EC4899", "#DB2777"),
    ("purple", "Magenta", "#A855F7", "#9333EA"),
    ("slate", "Schiefer", "#64748B", "#475569"),
    ("gray", "Grau", "#9CA3AF", "#6B7280"),
]

# Der Fensterhintergrund liegt bewusst deutlich unter der Karte – sonst
# verschwindet die Karte im Untergrund und hat keine Kante.
DARK = {
    "bg": "#0B0C10", "card": "#171A21", "card2": "#22262F",
    "senke": "#0E1016", "stroke": "#262B35", "fg": "#EDEFF5",
    "muted": "#868E9F", "knob": "#FFFFFF", "off": "#2B303A",
    "red": "#FF5C7C",
}
LIGHT = {
    "bg": "#E8EBF0", "card": "#FFFFFF", "card2": "#F1F3F7",
    "senke": "#DFE3EA", "stroke": "#D5DAE3", "fg": "#12151C",
    "muted": "#5A6272", "knob": "#FFFFFF", "off": "#C6CCD7",
    "red": "#DC2626",
}


def schrift():
    """Der Familienname fuer Fliesstext – fuer alles, was selbst zeichnet.

    Windows 11 bringt die Variable-Fassung mit; wo sie fehlt, greift die
    Rueckfallkette in der Stilvorlage, hier der einfache Name.
    """
    from PySide6.QtGui import QFont, QFontInfo, QGuiApplication
    if QGuiApplication.instance() is None:
        return SCHRIFT_ERSATZ
    probe = QFont("Segoe UI Variable Text")
    if QFontInfo(probe).family().startswith("Segoe UI Variable"):
        return "Segoe UI Variable Text"
    return SCHRIFT_ERSATZ


def glaettung(f):
    """Buchstaben nicht aufs Pixelraster zwingen.

    Qt richtet Text unter Windows von sich aus an ganzen Pixeln aus. Das
    macht ihn gestochen, laesst aber die Rundungen eckig werden – man sieht
    es an den aeusseren Kanten. Browser und Electron-Programme verzichten
    darauf und lassen die Kanten weich auslaufen; deshalb wirkt Text dort
    „glatter“, obwohl er unschaerfer ist.

    Gemessen an denselben zwei Zeilen: 27 Grauabstufungen statt 13, und ein
    Drittel mehr Pixel im weichen Uebergangsbereich.
    """
    from PySide6.QtGui import QFont
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def basis_schrift():
    """Die Grundschrift der Anwendung – traegt die Glaettungsvorgabe.

    Wird ueber QApplication.setFont gesetzt. Die Familie steht trotzdem in
    der Stilvorlage: Ohne sie dort faellt Qt bei jedem abweichenden Gewicht
    auf eine fremde Familie zurueck (siehe test_schalter).
    """
    from PySide6.QtGui import QFont
    f = QFont(schrift())
    f.setPixelSize(13)
    return glaettung(f)


def _rgb(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def mix(c1, c2, t):
    """Farbe zwischen c1 und c2 (t = 0..1)."""
    a, b = _rgb(c1), _rgb(c2)
    return "#{:02X}{:02X}{:02X}".format(
        *(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)))


def shift(farbe, faktor):
    """Heller (>1) oder dunkler (<1) machen."""
    return "#{:02X}{:02X}{:02X}".format(
        *(max(0, min(255, int(round(k * faktor)))) for k in _rgb(farbe)))


def rgba(farbe, deckkraft):
    """Als rgba() fuer die Stilvorlage – Qt kennt kein #RRGGBBAA."""
    r, g, b = _rgb(farbe)
    return "rgba({}, {}, {}, {})".format(r, g, b, round(deckkraft, 3))


class Theme:
    """Aktuelle Farbwelt – Modus plus Akzentfarbe."""

    def __init__(self, mode="dark", accent="violet"):
        self.set(mode, accent)

    def set(self, mode, accent):
        self.mode = "light" if mode == "light" else "dark"
        self.hell = self.mode == "light"
        self.accent_key = accent
        basis = LIGHT if self.hell else DARK
        for k, v in basis.items():
            setattr(self, k, v)
        farbe = next((p for p in PALETTE if p[0] == accent), PALETTE[0])
        self.accent = farbe[3] if self.hell else farbe[2]
        self.accent_hover = shift(self.accent, 0.88 if self.hell else 1.14)
        # Gedaempfter Akzent fuer grosse Flaechen: die volle Farbe ist als
        # Hintergrund zu laut, sie gehoert auf Regler und Haken.
        self.accent_leise = mix(self.card, self.accent, 0.18 if not self.hell
                                else 0.13)
        # Karten bekommen einen ganz leichten Verlauf plus eine helle Kante an
        # der Oberkante – gezeichnet wird beides in widgets.Flaeche.
        if self.hell:
            self.card_top = "#FFFFFF"
            self.card_bottom = mix(self.card, "#9AA3B2", 0.09)
            self.kante = (255, 255, 255, 235)
        else:
            self.card_top = mix(self.card, self.accent, 0.05)
            self.card_bottom = mix(self.card, "#000000", 0.13)
            self.kante = (255, 255, 255, 18)
        # Zeilen: die Auswahl traegt einen Akzentbalken am linken Rand, die
        # Flaeche selbst hebt sich nur leicht ab. Frueher war sie kraeftig
        # eingefaerbt – bei mehreren gewaehlten Apps wurde die Liste bunt.
        self.row_hover = mix(self.card, self.fg, 0.055 if not self.hell else 0.05)
        self.row_sel = mix(self.card, self.accent, 0.11 if not self.hell else 0.09)
        self.row_sel_hover = mix(self.card, self.accent,
                                 0.16 if not self.hell else 0.14)

    def accent_of(self, key):
        farbe = next((p for p in PALETTE if p[0] == key), PALETTE[0])
        return farbe[3] if self.hell else farbe[2]

    # ---- Stilvorlage -----------------------------------------------------
    def qss(self):
        t = self
        return f"""
        /* Fliesstext. Segoe UI Variable kennt nur 400 und 700 – die feinen
           Zwischenstufen einer Webschrift gibt es hier nicht, dafuer sitzt
           jede Stufe auf dem Pixelraster. */
        QWidget {{
            color: {t.fg};
            font-family: {SCHRIFT_TEXT};
            font-size: 13px;
            font-weight: 400;
        }}
        #Fenster {{ background: {t.bg}; }}

        /* Karte, Leiste und Profilleiste zeichnen sich selbst –
           siehe widgets.Flaeche. Hier stehen nur die Schriften. */
        /* Die kleinen gesperrten Beschriftungen: dafuer gibt es in
           Windows eine eigene optische Groesse. */
        #Ueberschrift {{
            color: {mix(t.muted, t.bg, 0.15)};
            font-family: {SCHRIFT_KLEIN};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.3px;
        }}
        #Titel {{
            font-family: {SCHRIFT_GROSS};
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.2px;
        }}
        /* Grosse Groessen bekommen die Display-Fassung – dort sitzen die
           Buchstaben enger und die Formen sind feiner gezeichnet. */
        #Wortmarke {{
            font-family: {SCHRIFT_GROSS};
            font-size: 27px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }}
        #DialogTitel {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.6px;
        }}
        #Abdunklung {{ background: rgba(0, 0, 0, 120); }}
        #Untertitel {{
            color: {t.muted};
            font-family: {SCHRIFT_KLEIN};
            font-size: 11px;
            font-weight: 400;
            letter-spacing: 1.3px;
        }}
        #Hinweis {{ color: {t.muted}; font-size: 12px; }}
        #Trennlinie {{ background: {mix(t.card, t.fg, 0.10)}; border: none; }}

        /* Profilleiste: Der Name ist ein Eingabefeld, sieht aber aus wie Text.
           Erst beim Anklicken zeigt sich, dass man darin schreiben kann. */
        QLineEdit#Profilname {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 4px 10px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: -0.1px;
            color: {t.fg};
            selection-background-color: {t.accent};
        }}
        QLineEdit#Profilname:hover {{ background: {t.card2}; }}
        QLineEdit#Profilname:focus {{
            background: {t.senke};
            border-color: {rgba(t.accent, 0.55)};
        }}

        /* Mixer-Zeile: Hintergrund und Auswahlbalken zeichnet MixerRow
           selbst, damit der Balken einfahren kann. */
        /* Der Unterschied liegt nicht nur im Gewicht: 500 gegen 700 sieht man
           bei 14 px kaum. Erst zusammen mit der Helligkeit tritt die
           angehakte Zeile wirklich hervor. */
        #Name {{
            font-size: 14px;
            font-weight: 400;
            color: {mix(t.fg, t.muted, 0.30)};
        }}
        #NameGewaehlt {{
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -0.1px;
            color: {t.fg};
        }}
        /* Zeile im App-Auswahldialog */
        #DlgZeile {{ border-radius: 10px; background: transparent; }}
        #DlgZeile[hover="true"] {{ background: {t.row_hover}; }}

        /* Knoepfe */
        QPushButton {{
            background: {t.card2};
            border: none;
            border-radius: 10px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {mix(t.card2, t.fg, 0.10)}; }}
        QPushButton:pressed {{ background: {mix(t.card2, t.fg, 0.18)}; }}
        QPushButton#Betont {{ background: {t.accent}; color: #FFFFFF; }}
        QPushButton#Betont:hover {{ background: {t.accent_hover}; }}
        QPushButton#Rund {{
            background: transparent;
            border-radius: 22px;
            padding: 0px;
            min-width: 44px; max-width: 44px;
            min-height: 44px; max-height: 44px;
        }}
        QPushButton#Rund:hover {{ background: {t.card2}; }}
        QPushButton#Rund:pressed {{ background: {mix(t.card2, t.fg, 0.10)}; }}
        QPushButton#Chip {{
            background: {t.senke};
            border-radius: 10px;
            padding: 8px 15px;
            font-weight: 600;
        }}
        QPushButton#Chip:hover {{ background: {mix(t.senke, t.fg, 0.10)}; }}
        QPushButton#Chip:checked {{ background: {t.accent}; color: #FFFFFF; }}
        QPushButton#Flach {{
            background: transparent;
            padding: 4px;
            border-radius: 9px;
        }}
        QPushButton#Flach:hover {{ background: {mix(t.card, t.fg, 0.10)}; }}

        /* Schieberegler (in den Einstellungen; der Lautstaerkeregler
           zeichnet sich selbst) */
        QSlider::groove:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: {t.senke};
        }}
        QSlider::sub-page:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {mix(t.accent, '#FFFFFF', 0.22)}, stop:1 {t.accent});
        }}
        QSlider::handle:horizontal {{
            width: 14px; height: 14px;
            margin: -5px 0;
            border-radius: 8px;
            background: {t.knob};
            border: 1px solid {mix(t.stroke, t.fg, 0.45) if t.hell else t.stroke};
        }}
        QSlider::handle:horizontal:hover {{ background: {mix(t.knob, t.accent, 0.2)}; }}
        QSlider#Stumm::sub-page:horizontal {{ background: {t.off}; }}

        /* Kaestchen */
        QCheckBox::indicator {{
            width: 22px; height: 22px;
            border-radius: 7px;
            background: {t.off};
        }}
        QCheckBox::indicator:hover {{ background: {mix(t.off, t.fg, 0.15)}; }}
        QCheckBox::indicator:checked {{
            background: {t.accent};
            image: url(haken);
        }}

        /* Schalter (in ToggleSwitch selbst gezeichnet) */

        /* Eingabefeld */
        QLineEdit {{
            background: {t.senke};
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 6px 11px;
            font-size: 12px;
            selection-background-color: {t.accent};
        }}
        QLineEdit:focus {{ border-color: {rgba(t.accent, 0.55)}; }}

        /* Bildlaufleiste */
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {mix(t.card, t.fg, 0.20 if t.hell else 0.24)};
            border-radius: 3px;
            min-height: 34px;
            margin: 0px 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {mix(t.card, t.fg, 0.34 if t.hell else 0.40)};
        }}
        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none; border: none; height: 0px;
        }}

        QToolTip {{
            background: {mix(t.card, t.fg, 0.07)};
            color: {t.fg};
            border: 1px solid {t.stroke};
            border-radius: 9px;
            padding: 9px 12px;
            font-size: 12px;
        }}
        """
