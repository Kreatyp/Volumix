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
    "bg": "#050609", "card": "#171A21", "card2": "#22262F",
    "senke": "#0E1016", "stroke": "#262B35", "fg": "#FFFFFF",
    "muted": "#868E9F", "knob": "#FFFFFF", "off": "#2B303A",
    "red": "#FF5C7C",
}
LIGHT = {
    "bg": "#E8EBF0", "card": "#FFFFFF", "card2": "#F1F3F7",
    "senke": "#DFE3EA", "stroke": "#D5DAE3", "fg": "#12151C",
    "muted": "#5A6272", "knob": "#FFFFFF", "off": "#C6CCD7",
    "red": "#DC2626",
}

# ---------------------------------------------------------------------------
# Glas
# ---------------------------------------------------------------------------
# Die Flaechen sind keine Volltoene mehr, sondern milchige Scheiben ueber
# einem Grund, in dem farbiges Licht steht. Ohne dieses Licht bringt Glas
# nichts: Auf gleichmaessigem Grau sieht Milchglas aus wie Grau.
#
#   schimmer  Deckkraft der Lichter im Grund
#   weite     ihr Radius, als Anteil der Fensterbreite. Der Wert entscheidet
#             ueber „dunkel“: Weit gezogen hellt das Licht die ganze Flaeche
#             auf, eng gezogen bleiben die Ecken wirklich dunkel.
#   deckung   wie dicht die Scheibe ist
#   licht     Lichtkante an ihrer Oberkante
#   schiene   wie tief die Reglerbahn im Glas liegt (Schwarzanteil)
#
# Gemessen am fertigen Bild, als Abstand Scheibe zu Grund in wahrgenommener
# Helligkeit: 4,1 bei der ersten Fassung, 7,9 mit diesen Werten.
# `schiene` ist der leere Teil der Reglerbahn – und im Dunkeln ist er ein
# HELLER Kanal, kein dunkler. Eine Vertiefung laesst sich nicht durch
# Dunkelheit darstellen, wenn der Boden schon fast schwarz ist: Gemessen in
# der Einblendung lag die schwarze Bahn 0,3 Punkte von ihrer Umgebung
# entfernt, war also schlicht nicht da. Als Weiss mit 12 % sind es 13,4.
#
# Im hellen Modus bleibt es umgekehrt: dort ist der Kanal dunkler als seine
# Umgebung, denn dort ist Platz nach unten.
# Am Fenstergrund zu drehen bringt fuer den Gesamteindruck fast nichts: Er
# ist nur ein schmaler Rahmen, die Scheiben fuellen die Flaeche. Der Grund
# ging ueber mehrere Runden von L* 10,4 auf 4,3 herunter – sichtbar war das
# kaum. Erst die Scheibe selbst aendert etwas:
#
#   Scheibe 17,5 %   Fenster im Mittel L* 24,0   Abstand zum Grund 11,5
#   Scheibe 13 %     Fenster im Mittel L* 22,0   Abstand  8,3
#   Scheibe 10 %     Fenster im Mittel L* 20,8   Abstand  5,8
#   Scheibe  7 %     Fenster im Mittel L* 19,8   Abstand  3,7
#
# Bei 7 % traegt nicht mehr die Flaeche die Abgrenzung, sondern die Kante –
# deshalb steht `licht` hoeher als vorher. Ohne das verschmelzen die Karten
# mit dem Grund.
#
# Auch das zeigt die Messung: Zwischen der hellsten und der dunkelsten
# Stufe liegen nur vier Punkte im Fenstermittel. Den Rest tragen weisser
# Text, bunte App-Symbole und die Regler – sie bestimmen den
# Helligkeitseindruck staerker als alle Flaechen zusammen.
GLAS_DUNKEL = {"schimmer": 0.15, "weite": 0.72, "deckung": 0.07,
               "licht": 0.58, "schiene": 0.12}
# Im Hellen traegt weisse Milch auf hellem Grund nichts. Dort ist die Karte
# deshalb ein deckendes Blatt mit feiner Kante (`deckung` 1,0, `licht` 0 –
# ein weisser Saum auf weisser Karte ist nichts), und das Licht im Grund ist
# nur noch ein Hauch: Bei 0,20 auf 0,85 Weite lag ein violett-rosa Nebel
# ueber dem halben Fenster, durch den jede Flaeche mitgefaerbt wurde. Weit
# gezogen und schwach bleibt davon eine Tonung, die man erst sucht, wenn man
# sie sucht.
GLAS_HELL = {"schimmer": 0.055, "weite": 1.3, "deckung": 1.0,
             "licht": 0.0, "schiene": 0.16}

# Die Einblendung bekommt dieselben Werte gedaempft. Auf ihrer kleinen
# Flaeche wirkt dieselbe Menge Licht kraeftiger als im ganzen Fenster, und
# sie steht mitten im Bild, waehrend man etwas anderes tut – dort stoert
# Helligkeit mehr, als sie nuetzt.
#
# Anders als das Fenster liegt sie ueber fremdem Bild. Sie bringt ihren
# Grund deshalb selbst mit, laesst ihn aber durchscheinen: Bei der
# Voreinstellung deckt die fertige Flaeche zu Alpha 189 von 255, und der
# weisse Text haelt ueber weissem Untergrund 8,3:1. Reines Glas ohne Grund
# war Alpha 13 und damit unsichtbar, deckend wirkte sie wie aufgeklebt.
#
# Der Schimmer traegt hier die Farbe: Im Fenster kommt sie vom Coverbild
# selbst, ueber dem Schreibtisch gibt es nur dieses eine Licht. Bei 0,48
# lagen Akzent und Coverfarbe nur 7 Punkte auseinander (kaum zu sehen), bei
# 0,80 sind es 13.
OSD_SCHIMMER = 0.80        # Anteil am Schimmer des Fensters
OSD_DECKUNG = 0.22         # Anteil an der Dichte der Scheibe
OSD_GRUND_REST = 0.44      # was auch beim vollen Regler stehen bleibt
# So viel vom Coverbild steht im Fenster unter einer Karte: erst der Schleier
# ueber dem ganzen Bild (18 %), dann die Verdunklung unter der Karte (78 %) –
# bleiben 0,82 * 0,22. Die Einblendung ist nichts anderes als eine Karte, die
# ueber dem Schreibtisch steht, und nimmt denselben Anteil.
OSD_COVER = 0.18


def osd_deckkraft(klar):
    """Prozent Durchsicht aus den Einstellungen -> Deckkraft des Grundes.

    Ganz durchsichtig gibt es nicht: Ohne eigenen Grund faellt die
    Einblendung ueber hellem Bild in sich zusammen (gemessen Alpha 13 von
    255). Der Regler oeffnet ihn deshalb nur bis auf einen Rest.

    Der Rest ist nicht frei gewaehlt: Bei 0,44 misst der Text am Anschlag
    ueber weissem Untergrund noch 3,15:1 – knapp ueber dem, was fuer grosse
    fette Schrift reicht. Die Voreinstellung 50 landet damit bei 0,72 und
    8,3:1.
    """
    anteil = max(0, min(100, int(klar))) / 100.0
    return 1.0 - anteil * (1.0 - OSD_GRUND_REST)


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
        self.glas = dict(GLAS_HELL if self.hell else GLAS_DUNKEL)
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
        # Warnfarbe, unabhaengig vom gewaehlten Akzent: Sie soll auch dann
        # auffallen, wenn jemand Bernstein als Akzent eingestellt hat, und
        # sie kommt aus derselben Palette wie alles andere.
        self.warnung = "#F59E0B" if not self.hell else "#B45309"
        # Wie stark unter jeder Karte verdunkelt wird. Null im Normalfall –
        # der Fenstergrund ist ohnehin dunkel. Liegt ein Coverbild dahinter,
        # bekommt jede Karte darunter eine eigene dunkle Scheibe, damit der
        # Text lesbar bleibt, waehrend das Bild ringsum sichtbar ist.
        self.grund_dunkeln = 0.0

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
        /* Der Fenstergrund wird gezeichnet, nicht gefuellt – MainWindow malt
           dort das farbige Licht, durch das die Scheiben schimmern. */
        #Fenster {{ background: transparent; }}

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
        /* Enger gesperrt als frueher (1.3px): Die Zeile ist lang, und rechts
           daneben sitzt jetzt die Boxen-Pille. Die Sperrung machte sie rund
           25 px breiter, ohne dass man sie deshalb besser laese. */
        #Untertitel {{
            color: {t.muted};
            font-family: {SCHRIFT_KLEIN};
            font-size: 11px;
            font-weight: 400;
            letter-spacing: 0.6px;
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
        /* Einmal auf 400 heruntergenommen, um die Auszeichnung zu
           entschlacken – ohne Fettdruck war die angehakte Zeile aber im
           Vorbeischauen nicht mehr sofort zu finden. Bleibt fett. */
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
        /* Nebensache: Umriss statt Flaeche. Gefuellt war dieser Knopf der
           kraeftigste im Fenster – fuer etwas, das man selten braucht, und
           damit lauter als die Regler, um die es geht. */
        QPushButton#Leise {{
            background: transparent;
            border: 1px solid {t.stroke};
            color: {t.muted};
            font-weight: 500;
        }}
        QPushButton#Leise:hover {{
            background: {t.card2};
            color: {t.fg};
        }}
        /* Fensterknoepfe: flacher und kleiner als die runden Knoepfe,
           damit sie sich nicht vordraengen. Der Schliessen-Knopf wird beim
           Darueberfahren rot – so wie ueberall unter Windows. */
/* Rund wie alles andere im Fenster – die runden Knoepfe daneben sind
           44 px, diese hier 28: dieselbe Form, kleiner, damit sie sich als
           Fenstersteuerung zurueckhalten. Ein abgerundetes Rechteck war die
           einzige eckige Form im ganzen Programm und fiel entsprechend auf. */
        QPushButton#Fensterknopf, QPushButton#Schliessen {{
            background: transparent;
            border: none;
            border-radius: 14px;
            padding: 0px;
            min-width: 28px; max-width: 28px;
            min-height: 28px; max-height: 28px;
        }}
        QPushButton#Fensterknopf:hover, QPushButton#Schliessen:hover {{
            background: {"rgba(255,255,255,0.10)" if not t.hell else t.card2};
        }}
        QPushButton#Schliessen:hover {{ background: {t.red}; }}

        QPushButton#Rund {{
            background: transparent;
            border-radius: 22px;
            padding: 0px;
            min-width: 44px; max-width: 44px;
            min-height: 44px; max-height: 44px;
        }}
        QPushButton#Rund:hover {{
            background: {"rgba(255,255,255,0.10)" if not t.hell else t.card2};
        }}
        QPushButton#Rund:pressed {{
            background: {"rgba(255,255,255,0.16)" if not t.hell
                         else mix(t.card2, t.fg, 0.10)};
        }}
        /* Nicht gewaehlte Chips sind Glas, keine schwarzen Bloecke: Auf
           einer durchscheinenden Karte stanzt ein Vollton ein Loch. */
        QPushButton#Chip {{
            background: {"rgba(255,255,255,0.08)" if not t.hell else t.senke};
            border-radius: 10px;
            padding: 8px 15px;
            font-weight: 600;
        }}
        QPushButton#Chip:hover {{
            background: {"rgba(255,255,255,0.15)" if not t.hell
                         else mix(t.senke, t.fg, 0.10)};
        }}
        QPushButton#Chip:checked {{ background: {t.accent}; color: #FFFFFF; }}
        QPushButton#Flach {{
            background: transparent;
            padding: 4px;
            border-radius: 9px;
        }}
        QPushButton#Flach:hover {{
            background: {"rgba(255,255,255,0.10)" if not t.hell
                         else mix(t.card, t.fg, 0.10)};
        }}

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

        /* Eingabefeld – ebenfalls Glas. Als Vertiefung sass hier ein
           schwarzes Loch mitten in der Scheibe. */
        QLineEdit {{
            background: {"rgba(255,255,255,0.09)" if not t.hell else t.senke};
            border: 1px solid {"rgba(255,255,255,0.16)" if not t.hell
                               else t.stroke};
            border-radius: 9px;
            padding: 6px 11px;
            font-size: 12px;
            selection-background-color: {t.accent};
        }}
        QLineEdit:focus {{ border-color: {rgba(t.accent, 0.55)}; }}

        /* Boxen-Pille in der Kopfzeile: Die Zahl ist ein Eingabefeld, soll
           aber wie Text aussehen. Der Rahmen kommt erst beim Tippen. */
        QLineEdit#BoxenWert {{
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
            font-size: 14px;
            font-weight: 600;
        }}
        QLineEdit#BoxenWert:focus {{
            background: {"rgba(255,255,255,0.10)" if not t.hell else t.senke};
            border-radius: 5px;
        }}
        #BoxenProzent {{ font-size: 11px; }}
        QPushButton#BoxenKnopf {{
            background: transparent; border: none; padding: 0px;
        }}

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
