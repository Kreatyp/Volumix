# -*- coding: utf-8 -*-
"""Farben und Stilvorlage.

Anders als in der Tk-Fassung wird hier nichts gerendert: Qt bekommt eine
Stilvorlage (QSS, an CSS angelehnt) und zeichnet Ecken, Verlaeufe und
Hover-Zustaende selbst auf der Grafikkarte.
"""

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
# verschwindet der Verlauf im Untergrund und die Karte hat keine Kante.
DARK = {
    "bg": "#0D0E12", "card": "#1E212A", "card2": "#2A2E39",
    "stroke": "#383D4A", "fg": "#F2F4F8", "muted": "#8B93A7",
    "knob": "#FFFFFF", "off": "#3A3F4B", "red": "#FF5C7C",
}
LIGHT = {
    "bg": "#E4E7ED", "card": "#FFFFFF", "card2": "#E7EAF0",
    "stroke": "#CBD1DC", "fg": "#12151C", "muted": "#5A6272",
    "knob": "#FFFFFF", "off": "#BFC6D2", "red": "#DC2626",
}


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
        # Karten bekommen einen sichtbaren Verlauf. Im hellen Modus faellt ein
        # Farbstich sofort auf – dort deshalb sparsam und mit neutralem Grau
        # statt Blau abdunkeln, sonst wirkt die Flaeche schmutzig.
        if self.hell:
            self.card_top = "#FFFFFF"
            self.card_bottom = mix(self.card, "#9AA3B2", 0.13)
        else:
            self.card_top = mix(self.card, self.accent, 0.08)
            self.card_bottom = mix(self.card, "#000000", 0.30)
        self.row_sel_top = mix(self.card2, self.accent, 0.20 if not self.hell else 0.14)
        self.row_sel_bottom = mix(self.card2, self.accent, 0.05)
        self.row_sel_hover = mix(self.card2, self.accent, 0.28 if not self.hell else 0.20)
        self.row_hover_top = mix(self.card2, self.fg, 0.10 if not self.hell else 0.05)
        self.row_hover_bottom = mix(self.card2, self.fg, 0.02)

    def accent_of(self, key):
        farbe = next((p for p in PALETTE if p[0] == key), PALETTE[0])
        return farbe[3] if self.hell else farbe[2]

    # ---- Stilvorlage -----------------------------------------------------
    def qss(self):
        t = self
        return f"""
        QWidget {{
            color: {t.fg};
            font-family: "Segoe UI";
            font-size: 13px;
        }}
        #Fenster {{ background: {t.bg}; }}

        /* Karten: Verlauf und runde Ecken – in Tk waren das gerenderte Bilder */
        #Karte {{
            border-radius: 16px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {t.card_top}, stop:1 {t.card_bottom});
        }}
        #Leiste {{
            border-radius: 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {t.card_top}, stop:1 {t.card_bottom});
        }}
        #Ueberschrift {{
            color: {t.muted};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
        }}
        /* Die Wortmarke ist ein Bild – siehe icons.wortmarke() */
        #Titel {{ font-size: 20px; font-weight: 600; }}
        #DialogTitel {{
            font-family: "Segoe UI Variable Display", "Segoe UI Semibold",
                         "Segoe UI";
            font-size: 17px;
            font-weight: 600;
            letter-spacing: 2.2px;
        }}
        #Abdunklung {{ background: rgba(0, 0, 0, 110); }}
        #Untertitel {{
            color: {t.muted};
            font-size: 11px;
            letter-spacing: 1.4px;
        }}
        #Hinweis {{ color: {t.muted}; font-size: 12px; }}
        #Trennlinie {{ background: {t.stroke}; border: none; }}

        /* Mixer-Zeile – Hover und Auswahl bekommen je einen eigenen Verlauf */
        #Zeile {{ border-radius: 12px; background: transparent; }}
        #Zeile[hover="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {t.row_hover_top}, stop:1 {t.row_hover_bottom});
        }}
        #Zeile[gewaehlt="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {t.row_sel_top}, stop:1 {t.row_sel_bottom});
        }}
        #Zeile[gewaehlt="true"][hover="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {t.row_sel_hover}, stop:1 {t.row_sel_bottom});
        }}
        #Name {{ font-size: 14px; }}
        #Prozent {{ font-size: 15px; font-weight: 600; }}
        #ProzentStumm {{ color: {t.muted}; font-size: 12px; }}

        /* Knoepfe */
        QPushButton {{
            background: {t.card2};
            border: none;
            border-radius: 9px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {t.stroke}; }}
        QPushButton:pressed {{ background: {mix(t.card2, t.fg, 0.18)}; }}
        QPushButton#Betont {{ background: {t.accent}; color: #FFFFFF; }}
        QPushButton#Betont:hover {{ background: {t.accent_hover}; }}
        QPushButton#Rund {{
            background: {t.card};
            border-radius: 19px;
            padding: 0px;
            min-width: 38px; max-width: 38px;
            min-height: 38px; max-height: 38px;
        }}
        QPushButton#Rund:hover {{ background: {t.card2}; }}
        QPushButton#Chip {{
            background: {t.card2};
            border-radius: 9px;
            padding: 7px 14px;
            font-weight: 500;
        }}
        QPushButton#Chip:hover {{ background: {t.stroke}; }}
        QPushButton#Chip:checked {{ background: {t.accent}; color: #FFFFFF; }}
        QPushButton#Flach {{
            background: transparent;
            padding: 4px;
            border-radius: 8px;
        }}
        QPushButton#Flach:hover {{ background: {mix(t.card2, t.fg, 0.14)}; }}

        /* Schieberegler */
        QSlider::groove:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: {t.card2};
        }}
        QSlider::sub-page:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {mix(t.accent, '#FFFFFF', 0.3)}, stop:1 {t.accent});
        }}
        QSlider::handle:horizontal {{
            width: 15px; height: 15px;
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
            background: {t.card2};
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 7px 12px;
            selection-background-color: {t.accent};
        }}
        QLineEdit:focus {{ border-color: {t.accent}; }}

        /* Bildlaufleiste */
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {mix(t.card2, t.fg, 0.16 if t.hell else 0.28)};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {mix(t.card2, t.fg, 0.30 if t.hell else 0.42)};
        }}
        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none; border: none; height: 0px;
        }}

        QToolTip {{
            background: {mix(t.card2, t.fg, 0.06)};
            color: {t.fg};
            border: 1px solid {t.stroke};
            border-radius: 8px;
            padding: 9px 12px;
            font-size: 12px;
        }}
        """

