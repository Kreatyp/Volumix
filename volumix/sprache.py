# -*- coding: utf-8 -*-
"""Alle sichtbaren Texte an einer Stelle.

Aufruf ueber `T("schluessel")`. Fehlt eine Uebersetzung, wird der deutsche
Text genommen – die App bleibt dadurch immer bedienbar.
"""

SPRACHEN = [("de", "Deutsch"), ("en", "English")]

_AKTUELL = "de"

TEXTE = {
    # ---- Kopf und Grundgeruest ----
    "untertitel": ("LAUTSTÄRKE-MIXER FÜR EINZELNE APPS",
                   "VOLUME MIXER FOR INDIVIDUAL APPS"),
    "mixer": ("LAUTSTÄRKE-MIXER", "VOLUME MIXER"),
    "alles": ("ALLES", "EVERYTHING"),
    "einzelne_apps": ("EINZELNE APPS", "INDIVIDUAL APPS"),
    "gesamtlautstaerke": ("Gesamtlautstärke", "Master volume"),
    "systemklaenge": ("Systemklänge", "System sounds"),
    "einstellungen": ("Einstellungen", "Settings"),
    "app_suchen": ("App suchen …", "Search app …"),
    "suchen": ("Suchen …", "Search …"),
    "stumm": ("stumm", "muted"),
    "stumm_schalten": ("Stumm schalten", "Mute"),

    # ---- Statusleiste ----
    "apps_waehlen": ("Apps wählen", "Choose apps"),
    "keine_app_aktiv": ("Keine App aktiv", "No app active"),
    "x_von_y": ("{a} von {b} Apps sichtbar", "{a} of {b} apps shown"),
    "rad_aus": ("Daumenrad erkannt — Steuerung ist AUS",
                "Thumbwheel detected — control is OFF"),
    "rad_kein_ziel": ("Daumenrad erkannt — noch keine App angehakt",
                      "Thumbwheel detected — no app selected yet"),
    "rad_aktiv": ("Daumenrad aktiv", "Thumbwheel active"),
    "tasten_aktiv": ("Lautstärke-Tasten aktiv", "Volume keys active"),

    # ---- Knopf-Hinweise ----
    "tt_profile": ("Profile", "Profiles"),
    "tt_modus": ("Hell / Dunkel", "Light / dark"),
    "tt_einstellungen": ("Einstellungen", "Settings"),
    "tt_zurueck": ("Zurück", "Back"),

    # ---- Profile ----
    "profil_speichern_titel": ("Profil speichern", "Save profile"),
    "profil_name": ("Name des Profils:", "Profile name:"),
    "profil_speichern": ("Aktuelle Pegel speichern …",
                         "Save current levels …"),
    "profil_loeschen": ("Profil löschen", "Delete profile"),
    "profil_gespeichert": ("Profil „{name}“ gespeichert",
                           "Profile “{name}” saved"),
    "profil_geladen": ("Profil „{name}“ geladen", "Profile “{name}” loaded"),
    "profil_geloescht": ("Profil „{name}“ gelöscht",
                         "Profile “{name}” deleted"),

    # ---- Einstellungen: Abschnitte ----
    "design": ("DESIGN", "APPEARANCE"),
    "steuerung": ("STEUERUNG", "CONTROL"),
    "anzeige": ("ANZEIGE", "DISPLAY"),
    "sprache_abschnitt": ("SPRACHE", "LANGUAGE"),

    # ---- Einstellungen: Design ----
    "modus": ("Modus", "Mode"),
    "dunkel": ("Dunkel", "Dark"),
    "hell": ("Hell", "Light"),
    "farbe": ("Farbe", "Colour"),

    # ---- Einstellungen: Steuerung ----
    "geschwindigkeit": ("Geschwindigkeit", "Speed"),
    "steuerung_aktiv": ("Steuerung aktiv", "Control active"),
    "scrollen_verwenden": ("Horizontales Scrollen verwenden",
                           "Use horizontal scrolling"),
    "richtung_umkehren": ("Richtung umkehren", "Reverse direction"),
    "mit_windows_starten": ("Mit Windows starten", "Start with Windows"),
    "beim_wechsel": ("Beim Wechsel Gesamt ↔ App",
                     "When switching master ↔ app"),
    "wechsel_none": ("Nichts ändern", "Change nothing"),
    "wechsel_carry": ("Pegel mitnehmen", "Carry level over"),
    "wechsel_apps100": ("Apps auf 100 %", "Apps to 100%"),
    "wechsel_hilfe": (
        "Was du hörst, ist App-Pegel × Gesamtlautstärke. Beim Umschalten "
        "wandert die Steuerung von einem Regler auf den anderen.\n\n"
        "• Nichts ändern – alle Pegel bleiben, wie sie sind.\n"
        "• Pegel mitnehmen – es klingt nach dem Wechsel gleich laut, kein "
        "plötzlicher Sprung nach oben.\n"
        "• Apps auf 100 % – beim Wechsel auf die Gesamtlautstärke gehen alle "
        "Apps auf 100 %.",
        "What you hear is app level × master volume. When you switch, control "
        "moves from one slider to the other.\n\n"
        "• Change nothing – all levels stay as they are.\n"
        "• Carry level over – it sounds equally loud after the switch, no "
        "sudden jump upwards.\n"
        "• Apps to 100% – switching to master volume sets every app to 100%."),

    # ---- Einstellungen: Anzeige ----
    "live_pegel": ("Live-Pegel neben den Reglern",
                   "Live meters next to the sliders"),
    "osd_anzeigen": ("Lautstärke-Einblendung anzeigen", "Show volume overlay"),
    "groesse": ("Größe", "Size"),
    "position_waagerecht": ("Position waagerecht", "Position horizontal"),
    "position_senkrecht": ("Position senkrecht", "Position vertical"),

    # ---- Dialog „Sichtbare Apps“ ----
    "sichtbare_apps": ("SICHTBARE APPS", "VISIBLE APPS"),
    "dialog_hilfe": (
        "Gelistet sind Apps, die gerade Ton ausgeben können.\n"
        "Nur angehakte erscheinen im Mixer.\n"
        "Deine Auswahl bleibt gespeichert – auch wenn du eine App\n"
        "schließt und später neu startest.",
        "Listed are apps that can currently produce sound.\n"
        "Only ticked ones appear in the mixer.\n"
        "Your choice is remembered – even if you close an app\n"
        "and start it again later."),
    "keine_app_ton": ("Gerade gibt keine App Ton aus.",
                      "No app is producing sound right now."),
    "abbrechen": ("Abbrechen", "Cancel"),
    "anwenden": ("Anwenden", "Apply"),

    # ---- Tray ----
    "oeffnen": ("Öffnen", "Open"),
    "beenden": ("Beenden", "Quit"),
}


def setzen(kuerzel):
    global _AKTUELL
    _AKTUELL = kuerzel if kuerzel in dict(SPRACHEN) else "de"


def aktuell():
    return _AKTUELL


def T(schluessel, **werte):
    """Text in der eingestellten Sprache, mit optionalen Platzhaltern."""
    eintrag = TEXTE.get(schluessel)
    if eintrag is None:
        return schluessel
    text = eintrag[1] if _AKTUELL == "en" and len(eintrag) > 1 else eintrag[0]
    if not text:
        text = eintrag[0]
    return text.format(**werte) if werte else text
