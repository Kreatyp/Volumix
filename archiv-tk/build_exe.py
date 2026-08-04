# -*- coding: utf-8 -*-
"""
Baut aus volumix.pyw eine einzelne .exe (PyInstaller, --onefile).
Erzeugt vorher ein passendes icon.ico.

Aufruf:
    python build_exe.py
Ergebnis:
    Volumix.exe  (im selben Ordner)
"""
import os
import sys
import importlib.util
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "icon.ico")
SRC = os.path.join(HERE, "volumix.pyw")


def make_icon(path):
    """Nutzt dasselbe Logo wie die App (make_icon_image aus dem Hauptmodul)."""
    spec = importlib.util.spec_from_file_location("twv_icon", SRC)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        # Das Modul beendet sich, wenn bereits eine Instanz laeuft
        print("Hinweis: laufende Instanz beenden, sonst bleibt das alte Icon.")
        return
    img = mod.make_icon_image(256, "#7C5CFF")
    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                          (64, 64), (128, 128), (256, 256)])


def main():
    make_icon(ICON)
    work = os.path.join(tempfile.gettempdir(), "tw_build_work")
    spec = os.path.join(tempfile.gettempdir(), "tw_build_spec")
    import PyInstaller.__main__ as pim
    pim.run([
        SRC,
        "--onefile",
        "--noconsole",
        "--name", "Volumix",
        "--icon", ICON,
        "--collect-submodules", "pynput",
        "--collect-submodules", "pystray",
        "--collect-submodules", "comtypes",
        "--collect-submodules", "pycaw",
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pystray._win32",
        "--distpath", HERE,
        "--workpath", work,
        "--specpath", spec,
        "--noconfirm",
    ])
    print("\nFertig -> " + os.path.join(HERE, "Volumix.exe"))


if __name__ == "__main__":
    main()
