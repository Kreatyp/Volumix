# -*- coding: utf-8 -*-
"""
Baut aus volumix.pyw eine .exe (PyInstaller).

Aufruf:
    python build_exe.py            -> Ordner dist\\Volumix\\ (startet schnell)
    python build_exe.py --onefile  -> eine einzelne Datei (startet langsamer)

Qt bringt viel mit; als Einzeldatei muss das bei jedem Start entpackt werden.
Deshalb ist der Ordner die Voreinstellung – die Datei `Volumix.exe` darin
laesst sich ganz normal verknuepfen oder an die Taskleiste heften.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "volumix.pyw")
ICON = os.path.join(HIER, "icon.ico")


def icon_bauen(pfad):
    """Programmsymbol aus demselben Vektor wie in der App."""
    try:
        from PySide6.QtGui import QGuiApplication
        # Muss in einer Variablen liegen: ohne Verweis raeumt Python die
        # Anwendung wieder weg und das Zeichnen stuerzt ab.
        app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
        sys.path.insert(0, HIER)
        from PIL import Image
        from PySide6.QtGui import QImage
        from volumix import icons
        from volumix.theme import Theme
        farbe = Theme().accent
        rahmen = []
        for g in (16, 24, 32, 48, 64, 128, 256):
            img = icons.app_logo(g, farbe).toImage()
            img = img.convertToFormat(QImage.Format.Format_RGBA8888)
            rahmen.append(Image.frombuffer(
                "RGBA", (img.width(), img.height()),
                img.constBits().tobytes(), "raw", "RGBA", 0, 1))
        rahmen[-1].save(pfad, sizes=[(i.width, i.height) for i in rahmen])
        print("Symbol geschrieben:", pfad)
    except Exception as e:
        print("Symbol nicht neu gebaut ({}) – vorhandenes wird genutzt".format(e))


# Qt bringt viel mit, was ein Mixer nie anfasst. `--exclude-module` greift nur
# bei Python-Modulen – die DLLs sammelt PyInstaller ueber seinen Qt-Hook ein.
# Deshalb hier von Hand, nach dem Bau.
BALLAST = [
    "opengl32sw.dll",            # Software-3D, ~20 MB; Widgets brauchen es nicht
    "Qt6Quick.dll", "Qt6Qml.dll", "Qt6QmlModels.dll",
    "Qt6QmlWorkerScript.dll", "Qt6QuickControls2.dll",
    "Qt6QuickTemplates2.dll", "Qt6QuickWidgets.dll",
    "libcrypto-3-x64.dll", "libssl-3-x64.dll",
    "libcrypto-3.dll", "libssl-3.dll",
    "Qt6Network.dll", "Qt6Pdf.dll", "Qt6OpenGL.dll",
    "Qt6VirtualKeyboard.dll", "Qt6Charts.dll",
    "d3dcompiler_47.dll",
    # Die Netz-Anbindung fuer Python – ohne Qt6Network.dll ohnehin tot
    "QtNetwork.pyd",
    # Bildformate: gebraucht wird nur PNG, und das steckt in Qt6Gui
    "qjpeg.dll", "qwebp.dll", "qtiff.dll", "qgif.dll", "qicns.dll",
    "qtga.dll", "qwbmp.dll",
    # Zweiter Zeichenweg und Fenster ohne Bildschirm – beides ungenutzt
    "qdirect2d.dll", "qoffscreen.dll", "qminimal.dll",
    # Weitere Zusatzteile, die eine reine Widget-App nie anfasst
    "qpdf.dll", "qtvirtualkeyboardplugin.dll", "qtuiotouchplugin.dll",
    "qnetworklistmanager.dll",
]

# Ganze Ordner, egal wo sie liegen. Frueher standen hier feste Pfade wie
# "PySide6/translations" – die zeigten ins Leere, weil PyInstaller alles unter
# `_internal` ablegt. Das Entfernen lief damit jedes Mal ins Nichts, ohne
# sich zu beschweren. Deshalb jetzt ueber den Ordnernamen.
BALLAST_ORDNER = [
    "qml",             # QML-Laufzeit, die App ist reines Widget
    "translations",    # Qt-Uebersetzungen; Volumix bringt eigene Texte mit
    "tls",             # Verschluesselung fuer Netzverbindungen, die es nicht gibt
]


def ballast_entfernen(ordner):
    """Loescht Bestandteile, die Volumix nie benutzt."""
    weg = 0

    def groesse(pfad):
        return sum(os.path.getsize(os.path.join(w, f))
                   for w, _, fs in os.walk(pfad) for f in fs)

    for wurzel, ordner_liste, dateien in os.walk(ordner, topdown=True):
        for name in list(ordner_liste):
            if name in BALLAST_ORDNER:
                p = os.path.join(wurzel, name)
                try:
                    weg += groesse(p)
                    shutil.rmtree(p)
                    ordner_liste.remove(name)   # nicht hineinlaufen
                except OSError:
                    pass
        for d in dateien:
            if d in BALLAST:
                p = os.path.join(wurzel, d)
                try:
                    weg += os.path.getsize(p)
                    os.remove(p)
                except OSError:
                    pass
    if weg:
        print("Ballast entfernt: {:.1f} MB".format(weg / (1024 * 1024)))


def main():
    einzeldatei = "--onefile" in sys.argv
    icon_bauen(ICON)

    arbeit = os.path.join(tempfile.gettempdir(), "volumix_build")
    spec = os.path.join(tempfile.gettempdir(), "volumix_spec")
    ziel = os.path.join(HIER, "programm")

    argumente = [
        sys.executable, "-m", "PyInstaller", QUELLE,
        "--name", "Volumix",
        "--noconsole",
        "--icon", ICON,
        "--distpath", ziel,
        "--workpath", arbeit,
        "--specpath", spec,
        "--noconfirm",
        # Das Bild der Wortmarke muss mit ins Paket. Die Schrift selbst gehoert
        # NICHT hierher: ihre Lizenz verbietet die Weitergabe.
        "--add-data", os.path.join(HIER, "volumix", "fonts") + ";volumix/fonts",
        # Was PyInstaller nicht von allein findet
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "pynput.keyboard._win32",
        "--collect-submodules", "comtypes",
        "--collect-submodules", "pycaw",
        # Qt-Teile, die wir nicht brauchen – spart sehr viel Platz
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "PySide6.QtDataVisualization",
        "--exclude-module", "PySide6.QtPdf",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
    ]
    argumente.append("--onefile" if einzeldatei else "--onedir")

    print("Baue …", "(Einzeldatei)" if einzeldatei else "(Ordner)")
    r = subprocess.run(argumente, cwd=HIER)
    if r.returncode != 0:
        sys.exit(r.returncode)

    fertig = (os.path.join(ziel, "Volumix.exe") if einzeldatei
              else os.path.join(ziel, "Volumix", "Volumix.exe"))
    if not einzeldatei:
        ballast_entfernen(os.path.dirname(fertig))
        # Qt und pynput stehen unter der LGPL – der Hinweis darauf gehoert
        # mit ins Paket, nicht nur ins Repository.
        hinweise = os.path.join(HIER, "LIZENZHINWEISE.md")
        if os.path.exists(hinweise):
            shutil.copyfile(hinweise,
                            os.path.join(os.path.dirname(fertig),
                                         "LIZENZHINWEISE.md"))
    print("\nFertig ->", fertig)
    if os.path.exists(fertig):
        print("Startdatei: {:.1f} MB".format(
            os.path.getsize(fertig) / (1024 * 1024)))
        if not einzeldatei:
            gesamt = sum(
                os.path.getsize(os.path.join(w, f))
                for w, _, fs in os.walk(os.path.dirname(fertig)) for f in fs)
            print("Ordner gesamt: {:.1f} MB".format(gesamt / (1024 * 1024)))


if __name__ == "__main__":
    main()
