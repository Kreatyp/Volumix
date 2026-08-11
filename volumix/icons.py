# -*- coding: utf-8 -*-
"""Symbole als Vektoren und Programm-Icons aus den .exe-Dateien.

Die Symbole sind SVG-Pfade: Qt zeichnet sie in jeder Groesse scharf, ohne
dass wir – wie in der Tk-Fassung – Bilder in allen Groessen vorhalten muessen.
"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# SVG-Pfade in einem 24x24-Raster
PFADE = {
    # Zahnrad als Kontur – ein gefuellter Pfad mit Loch wird bei diesen
    # Groessen schnell zum Klecks.
    "gear": ("M19.1 12.9a7.4 7.4 0 000-1.8l2-1.5-1.9-3.2-2.3.9a7.4 7.4 0 00-1.6-.9"
             "L14.9 4h-3.8l-.4 2.4a7.4 7.4 0 00-1.6.9l-2.3-.9L4.9 9.6l2 1.5a7.4 "
             "7.4 0 000 1.8l-2 1.5 1.9 3.2 2.3-.9a7.4 7.4 0 001.6.9l.4 2.4h3.8"
             "l.4-2.4a7.4 7.4 0 001.6-.9l2.3.9 1.9-3.2z"),
    "gear_kreis": "M12 15.1a3.1 3.1 0 100-6.2 3.1 3.1 0 000 6.2z",
    "back": "M15.5 4.5L8 12l7.5 7.5",
    "vor": "M8.5 4.5L16 12l-7.5 7.5",
    "trash": ("M4 6.6h16 M9.6 6.6V4.4h4.8v2.2 M6.6 6.6l.9 13h9l.9-13"
              " M10.4 10.2v6 M13.6 10.2v6"),
    "moon": "M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z",
    "sun": ("M12 7.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9z M12 1.5v3 M12 19.5v3 "
            "M1.5 12h3 M19.5 12h3 M4.2 4.2l2.1 2.1 M17.7 17.7l2.1 2.1 "
            "M19.8 4.2l-2.1 2.1 M6.3 17.7l-2.1 2.1"),
    "help": "M12 2a10 10 0 100 20 10 10 0 000-20z",
    "search": "M10.5 3a7.5 7.5 0 105.3 12.8L21 21 M10.5 3a7.5 7.5 0 000 15",
    "check": "M4.5 12.5l5 5 10-11",
    "plus": "M12 5v14 M5 12h14",
    "trash": ("M4 7h16 M9 7V4.5h6V7 M6.5 7l1 13h9l1-13 "
              "M10 10.5v6.5 M14 10.5v6.5"),
    "save": ("M5 4h11l3 3v13H5z M8 4v6h7V4 M8 20v-6h8v6"),
    # Lautstaerke angleichen: zwei Pfeile, die aufeinander zu laufen –
    # zusammengebracht wird, was auseinanderliegt.
    #
    # Vorher stand hier eine abfallende Wellenform. Nebeneinander gerendert
    # in 20, 32 und 64 px war sie die einzige Fassung, die man in Knopfgroesse
    # ueberhaupt nicht mehr deuten konnte – sie sah aus wie ein Trennzeichen.
    # Balken („alle gleich hoch“) und Wellen mit Deckelstrich waren bei 20 px
    # ebenfalls nur noch Gekrissel.
    "angleichen": ("M12 3v7 M8.5 7l3.5 3.5L15.5 7"
                   " M12 21v-7 M8.5 17l3.5-3.5L15.5 17"),
}

# Lautsprecher: Kegel plus bis zu drei Wellen
_SPK_KEGEL = "M4 9.5h3.5L12 5.5v13L7.5 14.5H4z"
_SPK_WELLEN = [
    "M14.6 9.6a3.4 3.4 0 010 4.8",
    "M17 7.2a6.8 6.8 0 010 9.6",
    "M19.4 4.8a10.2 10.2 0 010 14.4",
]
# Kreuz rechts vom Kegel – der uebliche „stumm“-Hinweis
_SPK_KREUZ = [
    "M15.2 9.4l5.6 5.6",
    "M20.8 9.4l-5.6 5.6",
]

_svg_cache = {}


def _svg(pfade, farbe, breite=1.9, gefuellt=None):
    teile = []
    for p in pfade:
        if gefuellt and p in gefuellt:
            teile.append('<path d="{}" fill="{}"/>'.format(p, farbe))
        else:
            teile.append(
                '<path d="{}" fill="none" stroke="{}" stroke-width="{}"'
                ' stroke-linecap="round" stroke-linejoin="round"/>'.format(
                    p, farbe, breite))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            + "".join(teile) + "</svg>")


def pixmap(name, groesse, farbe, dpr=1.0):
    """Symbol als Pixmap – scharf fuer die uebergebene Bildschirmdichte."""
    schluessel = (name, groesse, farbe, round(dpr, 2))
    fertig = _svg_cache.get(schluessel)
    if fertig is not None:
        return fertig
    if name == "help":
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
               '<circle cx="12" cy="12" r="9.6" fill="none" stroke="{c}"'
               ' stroke-width="1.7"/>'
               '<text x="12" y="16.6" font-family="Segoe UI" font-size="13"'
               ' font-weight="600" fill="{c}" text-anchor="middle">?</text>'
               '</svg>').format(c=farbe)
    elif name == "gear":
        svg = _svg([PFADE["gear"], PFADE["gear_kreis"]], farbe, breite=1.7)
    elif name == "moon":
        svg = _svg([PFADE["moon"]], farbe, gefuellt=[PFADE["moon"]])
    else:
        svg = _svg([PFADE[name]], farbe)
    pm = _render(svg, groesse, dpr)
    _svg_cache[schluessel] = pm
    return pm


def speaker_pixmap(groesse, pegel, farbe, dpr=1.0, stumm=False):
    """Lautsprecher, dessen Wellen mit dem Pegel wachsen (wie in Windows).

    Bei `stumm` stehen statt der Wellen zwei gekreuzte Striche – so ist der
    Zustand auch ohne Farbe erkennbar.
    """
    stufe = 0 if pegel <= 0.001 else (1 if pegel < 0.34 else (2 if pegel < 0.67 else 3))
    schluessel = ("spk", groesse, stufe, farbe, round(dpr, 2), stumm)
    fertig = _svg_cache.get(schluessel)
    if fertig is not None:
        return fertig
    teile = ['<path d="{}" fill="{}"/>'.format(_SPK_KEGEL, farbe)]
    if stumm:
        for strich in _SPK_KREUZ:
            teile.append(
                '<path d="{}" fill="none" stroke="{}" stroke-width="2.1"'
                ' stroke-linecap="round"/>'.format(strich, farbe))
    else:
        for i, w in enumerate(_SPK_WELLEN):
            # Nicht aktive Wellen bleiben schwach sichtbar – so springt das
            # Symbol beim Regeln nicht in der Groesse.
            deckkraft = 1.0 if i < stufe else 0.18
            teile.append(
                '<path d="{}" fill="none" stroke="{}" stroke-width="1.9"'
                ' stroke-linecap="round" opacity="{}"/>'.format(
                    w, farbe, deckkraft))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           + "".join(teile) + "</svg>")
    pm = _render(svg, groesse, dpr)
    _svg_cache[schluessel] = pm
    return pm


def _render(svg, groesse, dpr):
    r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(int(groesse * dpr), int(groesse * dpr))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    r.render(p, QRectF(0, 0, groesse * dpr, groesse * dpr))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def app_logo(groesse, farbe, dpr=1.0):
    """Programmsymbol: ein runder Knopf mit zwei Regelwegen.

    Zwei Bahnen mit Knoepfen an verschiedenen Stellen – genau das, was das
    Programm macht: mehrere Lautstaerken, unabhaengig voneinander. Die runde
    Grundform ist Absicht; in der Taskleiste steht sonst ein abgerundetes
    Quadrat neben zwanzig anderen abgerundeten Quadraten.

    Bewusst grob gehalten: bei 16 px zerfaellt jedes feinere Motiv.
    """
    schluessel = ("logo", groesse, farbe, round(dpr, 2))
    fertig = _svg_cache.get(schluessel)
    if fertig is not None:
        return fertig
    heller = QColor(farbe).lighter(122).name()
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="{h}"/><stop offset="1" stop-color="{f}"/>'
           '</linearGradient></defs>'
           '<circle cx="24" cy="24" r="23" fill="url(#g)"/>'
           '<rect x="9" y="14" width="30" height="6" rx="3"'
           ' fill="#FFFFFF" opacity="0.3"/>'
           '<circle cx="17" cy="17" r="6.5" fill="#FFFFFF" opacity="0.55"/>'
           '<rect x="9" y="28" width="30" height="6" rx="3"'
           ' fill="#FFFFFF" opacity="0.3"/>'
           '<circle cx="31" cy="31" r="6.5" fill="#FFFFFF"/>'
           '</svg>').format(h=heller, f=farbe)
    pm = _render(svg, groesse, dpr)
    _svg_cache[schluessel] = pm
    return pm


def cache_leeren():
    _svg_cache.clear()


# ---------------------------------------------------------------------------
# Programm-Icons aus der .exe holen (Win32 – Qt kann das nicht)
# ---------------------------------------------------------------------------
class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HBITMAP),
                ("hbmColor", wintypes.HBITMAP)]


# 64-bit-sichere Signaturen (Handles sind zeigergross)
_user32.GetDC.restype = ctypes.c_void_p
_user32.GetDC.argtypes = [wintypes.HWND]
_user32.ReleaseDC.argtypes = [wintypes.HWND, ctypes.c_void_p]
_user32.GetIconInfo.restype = wintypes.BOOL
_user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ICONINFO)]
_user32.DestroyIcon.argtypes = [ctypes.c_void_p]
_user32.PrivateExtractIconsW.restype = ctypes.c_uint
_user32.PrivateExtractIconsW.argtypes = [
    wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT),
    wintypes.UINT, wintypes.DWORD]
_gdi32.GetDIBits.restype = ctypes.c_int
_gdi32.GetDIBits.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.POINTER(_BITMAPINFOHEADER), wintypes.UINT]
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]

_ICON_CACHE = {}          # (exe, groesse) -> QPixmap oder None
_BASIS = 64               # einmal gross holen, dann herunterskalieren


def _dib(hbm, groesse):
    bmi = _BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(bmi)
    bmi.biWidth = groesse
    bmi.biHeight = -groesse
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0
    puffer = (ctypes.c_ubyte * (groesse * groesse * 4))()
    hdc = _user32.GetDC(0)
    try:
        ok = _gdi32.GetDIBits(hdc, hbm, 0, groesse, puffer, ctypes.byref(bmi), 0)
    finally:
        _user32.ReleaseDC(0, hdc)
    return bytes(puffer) if ok else None


def _hicon_zu_image(hicon, groesse):
    ii = _ICONINFO()
    if not _user32.GetIconInfo(hicon, ctypes.byref(ii)):
        return None
    try:
        farbe = _dib(ii.hbmColor, groesse)
        if farbe is None:
            return None
        img = QImage(farbe, groesse, groesse, QImage.Format_ARGB32)
        return img.copy()          # Puffer gehoert uns nicht dauerhaft
    finally:
        if ii.hbmColor:
            _gdi32.DeleteObject(ii.hbmColor)
        if ii.hbmMask:
            _gdi32.DeleteObject(ii.hbmMask)


def exe_icon(pfad, groesse, dpr=1.0):
    """Programmsymbol als Pixmap, oder None."""
    if not pfad:
        return None
    ziel = int(groesse * dpr)
    schluessel = (pfad, ziel)
    if schluessel in _ICON_CACHE:
        pm = _ICON_CACHE[schluessel]
        if pm is not None:
            pm = QPixmap(pm)
            pm.setDevicePixelRatio(dpr)
        return pm
    pm = None
    try:
        hicon = wintypes.HICON()
        iconid = wintypes.UINT()
        n = _user32.PrivateExtractIconsW(ctypes.c_wchar_p(pfad), 0, _BASIS,
                                         _BASIS, ctypes.byref(hicon),
                                         ctypes.byref(iconid), 1, 0)
        if n >= 1 and hicon.value:
            try:
                img = _hicon_zu_image(hicon.value, _BASIS)
                if img is not None and not img.isNull():
                    pm = QPixmap.fromImage(img).scaled(
                        ziel, ziel, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            finally:
                _user32.DestroyIcon(hicon)
    except Exception:
        pm = None
    _ICON_CACHE[schluessel] = pm
    if pm is not None:
        pm = QPixmap(pm)
        pm.setDevicePixelRatio(dpr)
    return pm


def buchstaben_pixmap(buchstabe, groesse, hintergrund, vordergrund, dpr=1.0):
    """Ersatzkachel, wenn kein Programmsymbol zu holen ist."""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
           '<rect x="0" y="0" width="48" height="48" rx="13" fill="{bg}"/>'
           '<text x="24" y="33" font-family="Segoe UI" font-size="24"'
           ' font-weight="600" fill="{fg}" text-anchor="middle">{b}</text>'
           '</svg>').format(bg=hintergrund, fg=vordergrund,
                            b=buchstabe.upper()[:1])
    return _render(svg, groesse, dpr)
