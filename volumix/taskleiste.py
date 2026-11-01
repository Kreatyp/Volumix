# -*- coding: utf-8 -*-
"""Das angeheftete Taskleistensymbol in der Akzentfarbe.

Ist ein Programm an die Taskleiste angeheftet, zeigt Windows dort das Symbol
seiner Verknuepfung – auch waehrend es laeuft. Das Fenstersymbol, das Volumix
zur Laufzeit in der Akzentfarbe setzt, wird an dieser Stelle ignoriert. Die
Verknuepfung wiederum nimmt ab Werk das Symbol aus der .exe, und das ist beim
Bauen in der Voreinstellung Violett entstanden.

Nicht angeheftet faellt das nicht auf: Dann zeigt die Taskleiste das
Fenstersymbol, und die Farbe stimmt. Genau deshalb sah es auf einem Rechner
richtig aus und auf dem anderen nicht.

Abhilfe ist dieselbe, die Chrome fuer seine Profile nimmt: ein Symbol in der
passenden Farbe ablegen und in die Verknuepfung eintragen. Angefasst werden
nur Verknuepfungen, die auf genau diese .exe zeigen, und nur, wenn ihr
Symbol noch nicht stimmt – geschrieben wird also beim Farbwechsel, nicht bei
jedem Start.
"""
import ctypes
import os
import struct
import sys

# Die Taskleiste nimmt je nach Skalierung 24, 32, 40 oder 48 Pixel; 16 und 20
# braucht das Startmenue in der Liste, 256 der Explorer in grossen Ansichten.
GROESSEN = (16, 20, 24, 32, 40, 48, 64, 256)


def taskleisten_ordner():
    """Wo Windows die angehefteten Verknuepfungen ablegt."""
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                        "Internet Explorer", "Quick Launch", "User Pinned",
                        "TaskBar")


def _png(groesse, farbe):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from . import icons
    bild = icons.app_logo(groesse, farbe, 1.0).toImage()
    # Das Feld muss in einer Variablen liegen. `QBuffer(QByteArray())` gibt
    # es sofort wieder frei, waehrend der Puffer noch hineinschreibt – das
    # war schon einmal ein Absturz ohne jede Fehlermeldung.
    feld = QByteArray()
    puffer = QBuffer(feld)
    puffer.open(QIODevice.WriteOnly)
    bild.save(puffer, "PNG")
    puffer.close()
    return bytes(feld)


def ico_bytes(farbe):
    """Eine .ico mit allen Groessen, jede als PNG darin.

    Ohne Fremdpaket: Das Format ist ein Kopf, ein Verzeichnis und die Bilder
    dahinter. PNG-Eintraege versteht Windows seit Vista in jeder Groesse.
    """
    bilder = [(g, _png(g, farbe)) for g in GROESSEN]
    kopf = struct.pack("<HHH", 0, 1, len(bilder))
    verzeichnis = b""
    inhalt = b""
    versatz = 6 + 16 * len(bilder)
    for groesse, png in bilder:
        seite = 0 if groesse >= 256 else groesse     # 0 steht fuer 256
        verzeichnis += struct.pack("<BBBBHHII", seite, seite, 0, 0, 1, 32,
                                   len(png), versatz)
        inhalt += png
        versatz += len(png)
    return kopf + verzeichnis + inhalt


def symbol_datei(farbe, ordner):
    """Pfad zur .ico in dieser Farbe – angelegt, falls es sie noch nicht gibt.

    Je Farbe eine eigene Datei statt immer derselben: Windows haelt Symbole
    in einem Zwischenspeicher, der am Pfad haengt. Neuer Inhalt unter altem
    Namen bliebe dort oft stehen, bis der Explorer neu startet. Mehr als
    zwei Dutzend werden es nie – zwoelf Farben, je hell und dunkel.
    """
    os.makedirs(ordner, exist_ok=True)
    name = "volumix-{}.ico".format(farbe.lstrip("#").upper())
    pfad = os.path.join(ordner, name)
    if not os.path.exists(pfad):
        daten = ico_bytes(farbe)
        with open(pfad + ".neu", "wb") as f:
            f.write(daten)
        os.replace(pfad + ".neu", pfad)
    return pfad


def _gleich(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(
        os.path.abspath(b))


def verknuepfungen_faerben(farbe, symbolordner, exe=None, ordner=None):
    """Angeheftete Verknuepfungen auf diese .exe in der Farbe zeigen lassen.

    Gibt zurueck, wie viele tatsaechlich geaendert wurden.
    """
    exe = exe or sys.executable
    ordner = ordner or taskleisten_ordner()
    if not os.path.isdir(ordner):
        return 0
    import comtypes.client
    # `dynamic=True` ist Pflicht, sonst scheitert schon `Save()`.
    shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
    symbol = None
    geaendert = []
    for name in sorted(os.listdir(ordner)):
        if not name.lower().endswith(".lnk"):
            continue
        pfad = os.path.join(ordner, name)
        try:
            lnk = shell.CreateShortcut(pfad)
            ziel = lnk.TargetPath or ""
            if not ziel or not _gleich(ziel, exe):
                continue
            if symbol is None:
                symbol = symbol_datei(farbe, symbolordner)
            soll = symbol + ",0"
            if os.path.normcase(lnk.IconLocation or "") == os.path.normcase(soll):
                continue
            lnk.IconLocation = soll
            lnk.Save()
            geaendert.append(pfad)
        except Exception:
            continue
    if geaendert:
        _shell_benachrichtigen(geaendert)
    return len(geaendert)


def _shell_benachrichtigen(pfade):
    """Dem Explorer sagen, dass sich etwas geaendert hat.

    Die Meldung zur einzelnen Datei allein genuegt der Taskleiste oft nicht –
    sie liest ihre Symbole erst, wenn es heisst, dass sich Zuordnungen
    geaendert haben. Das laedt alle Symbole neu und ist deshalb nur hier, beim
    tatsaechlichen Farbwechsel, vertretbar.
    """
    try:
        shell32 = ctypes.windll.shell32
    except Exception:
        return
    SHCNE_UPDATEITEM = 0x00002000
    SHCNE_ASSOCCHANGED = 0x08000000
    SHCNF_IDLIST = 0x0000
    SHCNF_PATHW = 0x0005
    shell32.SHChangeNotify.argtypes = [ctypes.c_long, ctypes.c_uint,
                                       ctypes.c_void_p, ctypes.c_void_p]
    for pfad in pfade:
        puffer = ctypes.create_unicode_buffer(pfad)
        shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW,
                               ctypes.cast(puffer, ctypes.c_void_p), None)
    shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
