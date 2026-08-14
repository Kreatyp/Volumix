# -*- coding: utf-8 -*-
"""Alle sichtbaren Texte an einer Stelle.

Aufruf ueber `T("schluessel")`. Fehlt eine Uebersetzung, wird der deutsche
Text genommen – die App bleibt dadurch immer bedienbar.
"""

SPRACHEN = [("de", "Deutsch"), ("en", "English")]

_AKTUELL = "de"

TEXTE = {
    # ---- Kopf und Grundgeruest ----
    # Ein Satz, kein Etikett: Gesperrte Versalien sind fuer kurze
    # Ordnungsworte da („ALLES“, „EINZELNE APPS“). Ueber einen ganzen Satz
    # gezogen lesen sie sich muehsam und geben dem Kopf ein Gewicht, das er
    # nicht braucht.
    "untertitel": ("Lautstärke-Mixer für einzelne Apps",
                   "Volume mixer for individual apps"),
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
    "angleichen": ("Lautstärke angleichen", "Even out volume"),
    "angleichen_an": ("Lautstärke wird angeglichen",
                      "Volume is being evened out"),
    "angleichen_hilfe": (
        "Hebt Leises an und zieht Lautes herunter, damit die Lautstärke "
        "gleichmäßig bleibt — gedacht für Sprache, wo einer laut und der "
        "nächste leise ist.\n\n"
        "Der Regler bleibt dabei stehen, wo du ihn hingestellt hast: Er ist "
        "die Mitte, um die herum geregelt wird.\n\n"
        "Für Musik ist es nichts — dort sind leise Stellen Absicht.",
        "Lifts quiet parts and pulls loud ones down so the volume stays "
        "even — meant for speech, where one person is loud and the next one "
        "quiet.\n\n"
        "The slider stays where you put it: it is the middle the control "
        "works around.\n\n"
        "Not for music — there the quiet parts are intended."),
    "angleichen_eng": (
        "Angleichen an — Regler etwas herunter, sonst fehlt Luft nach oben",
        "Evening out — turn the slider down a bit, no headroom otherwise"),

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
    "tt_modus": ("Hell / Dunkel", "Light / dark"),
    "tt_einstellungen": ("Einstellungen", "Settings"),
    "tt_zurueck": ("Zurück", "Back"),

    # ---- Profile ----
    "profil_loeschen": ("Profil löschen", "Delete profile"),
    "profil_neu": ("Neues Profil", "New profile"),
    "profil_zahl": ("Profil {n}", "Profile {n}"),
    "profil_geladen": ("Profil „{name}“", "Profile “{name}”"),
    "profil_geloescht": ("Profil „{name}“ gelöscht",
                         "Profile “{name}” deleted"),
    "profil_standard": ("Standard", "Default"),
    "profil_vor": ("Nächstes Profil", "Next profile"),
    "profil_zurueck": ("Vorheriges Profil", "Previous profile"),
    "profil_hilfe": (
        "Ein Profil merkt sich die Pegel aller Apps und welche davon am Rad "
        "bzw. an den Tasten hängen.\n\n"
        "Es gibt keinen Speichern-Knopf: Was du änderst, gehört ab sofort "
        "zum offenen Profil. Mit „+“ legst du sofort ein neues an — es "
        "startet als Kopie des aktuellen.\n\n"
        "Zum Umbenennen einfach hier hineinklicken und tippen. Solange das "
        "Feld offen ist, steht daneben der Papierkorb. Blättern geht auch "
        "mit den Pfeiltasten.\n\n"
        "Alles aus den Einstellungen — Farbe, Geschwindigkeit, Sprache — "
        "gilt für alle Profile gemeinsam.",
        "A profile remembers every app's level and which of them are on the "
        "wheel or the volume keys.\n\n"
        "There is no save button: whatever you change belongs to the open "
        "profile from now on. For a second version press “+” — it starts "
        "as a copy of the current one.\n\n"
        "To rename, click here and type. While the field is open the bin "
        "sits next to it. The arrow keys page through as well.\n\n"
        "Everything from the settings — colour, speed, language — applies "
        "to all profiles alike."),

    # ---- Einstellungen: Abschnitte ----
    # Die vier Reiter – gemischt geschrieben wie die Ueberschrift darueber.
    # Die Karten darin tragen die gesperrten Grossbuchstaben.
    "design": ("DESIGN", "APPEARANCE"),
    "steuerung": ("Steuerung", "Control"),
    "anzeige": ("Anzeige", "Display"),
    "allgemein": ("Allgemein", "General"),
    "sprache_abschnitt": ("SPRACHE", "LANGUAGE"),

    # ---- Einstellungen: Design ----
    "dunkel": ("Dunkel", "Dark"),
    "hell": ("Hell", "Light"),
    "farbe": ("FARBE", "COLOUR"),

    # ---- Einstellungen: Steuerung ----
    "geschwindigkeit": ("Geschwindigkeit", "Speed"),
    "tempo_hilfe": (
        "Wie weit ein Rasten am Rad oder ein Tastendruck die Lautstärke "
        "bewegt.\n\n"
        "Ein Wert genügt für alles: Volumix bringt die Regler einzelner "
        "Apps auf dieselbe Kurve wie die Windows-Gesamtlautstärke. Damit "
        "fühlt sich ein Schritt überall gleich an — und unten von selbst "
        "feiner als oben, so wie das Ohr es erwartet.",
        "How far one notch of the wheel or one key press moves the volume."
        "\n\n"
        "One value is enough: Volumix puts the sliders of individual apps "
        "on the same curve as the Windows master volume. A step then feels "
        "the same everywhere — and finer at the bottom than at the top, "
        "the way hearing expects it."),
    "steuerung_aktiv": ("Steuerung aktiv", "Control active"),
    "regeln_mit": ("Regeln mit", "Control with"),
    "daumenrad": ("Daumenrad", "Thumbwheel"),
    "lautstaerke_tasten": ("Lautstärke-Tasten", "Volume keys"),
    "richtung_umkehren": ("Richtung umkehren", "Reverse direction"),
    "titel_taste": ("Titel per Mehrfachdruck wechseln",
                    "Change track by pressing twice"),
    "titel_hilfe": (
        "Belegt die Wiedergabe-Taste doppelt, so wie es Kopfhörer tun:\n\n"
        "•  einmal drücken — Wiedergabe / Pause\n"
        "•  zweimal — nächster Titel\n"
        "•  dreimal — vorheriger Titel\n\n"
        "Der Haken: Volumix muss nach dem ersten Druck kurz abwarten, ob "
        "noch einer kommt. Solange das an ist, reagiert die Taste rund eine "
        "Drittelsekunde später. Aus bleibt sie so schnell wie immer.\n\n"
        "Wirkt überall, wo die Medientasten wirken — Spotify, YouTube und "
        "der Rest.",
        "Gives the play key a second and third meaning, the way earbuds do:"
        "\n\n"
        "•  press once — play / pause\n"
        "•  twice — next track\n"
        "•  three times — previous track\n\n"
        "The catch: after the first press Volumix has to wait and see "
        "whether another one follows. While this is on, the key responds "
        "about a third of a second later. Off, it stays as quick as ever."
        "\n\n"
        "Works wherever the media keys work — Spotify, YouTube and the "
        "rest."),
    "mit_windows_starten": ("Mit Windows starten", "Start with Windows"),
    "beim_wechsel": ("BEIM WECHSEL GESAMT ↔ APP",
                     "WHEN SWITCHING MASTER ↔ APP"),
    "wechsel_frage": ("Was mit den Pegeln geschieht",
                      "What happens to the levels"),
    "eingabe": ("EINGABE", "INPUT"),
    "medientasten": ("MEDIENTASTEN", "MEDIA KEYS"),
    "im_fenster": ("IM FENSTER", "IN THE WINDOW"),
    "einblendung": ("EINBLENDUNG", "ON-SCREEN DISPLAY"),
    "system": ("SYSTEM", "SYSTEM"),
    "ton": ("TON", "SOUND"),
    "ton_anschlag": ("Ton bei voller Lautstärke",
                     "Sound at full volume"),
    "ton_hilfe": (
        "Ein kurzer Ton, sobald der Regler oben ankommt — damit man auch "
        "ohne Hinsehen merkt, dass es nicht weiter geht.\n\n"
        "Er kommt beim Ankommen, nicht beim Weiterdrehen: Wer schon auf "
        "100 % steht und weiterdreht, hört nichts mehr.",
        "A short sound the moment the slider reaches the top — so you notice "
        "it will not go further without having to look.\n\n"
        "It plays on arrival, not while you keep turning: once you are at "
        "100 %, turning further stays silent."),
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
