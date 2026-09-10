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
    "tt_minimieren": ("Minimieren", "Minimise"),
    "tt_schliessen": ("Schließen — läuft im Infobereich weiter",
                      "Close — keeps running in the notification area"),

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
    "groesse_app": ("GRÖSSE", "SIZE"),
    "groesse_hilfe": (
        "Zieht die ganze Oberfläche größer oder kleiner — Schrift, Regler, "
        "Abstände, alles im selben Verhältnis.\n\n"
        "Das ist keine Zoomstufe, die nachträglich vergrößert: Qt rechnet "
        "damit von vornherein, die Schrift bleibt also gestochen.\n\n"
        "Der Wert muss feststehen, bevor Qt hochfährt — deshalb greift er "
        "erst beim nächsten Start.",
        "Scales the whole interface up or down — text, sliders, spacing, all "
        "in the same proportion.\n\n"
        "This is not a zoom applied afterwards: Qt works with it from the "
        "start, so text stays crisp.\n\n"
        "The value has to be settled before Qt starts up, so it takes effect "
        "the next time Volumix runs."),
    "skala_offen": ("Wirkt beim nächsten Start", "Takes effect on next start"),
    "jetzt_neu_starten": ("Jetzt neu starten", "Restart now"),

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
    "melder": ("Anzeige an Spiele weitergeben",
               "Pass the display on to games"),
    "melder_hilfe": (
        "Im Vollbild liegt die Einblendung von Volumix hinter dem Spiel — "
        "egal, wie weit oben ihr Fenster steht. Das ist keine Einstellung, "
        "die man umlegen kann, sondern die Art, wie Windows Vollbild "
        "zeichnet.\n\n"
        "Mit dieser Option meldet Volumix jede Änderung an Programme auf "
        "diesem Rechner, die zuhören — etwa die Minecraft-Mod. Das Spiel "
        "zeichnet die Anzeige dann selbst und sie ist auch im Vollbild da."
        "\n\n"
        "Es wird nur gesendet, nie empfangen: Über diesen Weg kann niemand "
        "deine Lautstärke verstellen. Erreichbar ist der Anschluss nur von "
        "diesem Rechner aus.",
        "In fullscreen the Volumix overlay sits behind the game — no matter "
        "how far on top its window is. That is not a setting, it is how "
        "Windows draws fullscreen.\n\n"
        "With this option Volumix reports every change to programs on this "
        "machine that listen — such as the Minecraft mod. The game then "
        "draws the display itself and it is there in fullscreen too.\n\n"
        "It only sends, never receives: nobody can change your volume this "
        "way. The port is reachable from this machine only."),
    "melder_belegt": ("Anschluss belegt — läuft Volumix schon einmal?",
                      "Port in use — is Volumix already running?"),

    # ---- Boxen im Netz ----
    "boxen": ("Boxen", "Speakers"),
    "boxen_titel": ("BOXEN IM NETZ", "NETWORK SPEAKERS"),
    "boxen_nachziehen": ("Lautstärke selbst nachziehen",
                         "Restore the volume automatically"),
    "boxen_hilfe": (
        "Für Lautsprecher, die per Kabel am Rechner hängen und trotzdem im "
        "Netz stehen — Teufel Raumfeld. Sie starten mit ihrem eigenen Wert "
        "und merken sich nur, was zuletzt über ihre eigene App lief.\n\n"
        "Trag die Lautstärke ein und drück Enter: Sie wird sofort gesetzt. "
        "Ist der Schalter an, wird sie danach von allein wiederhergestellt "
        "— wenn die Box angeht und wenn du nach längerer Pause an den "
        "Rechner zurückkommst.\n\n"
        "Enter setzt immer, auch bei ausgeschaltetem Schalter — und beim "
        "Anschalten kommt die Lautstärke ebenfalls immer mit, sonst wachte "
        "die Box auf ihrem eigenen Wert auf.",
        "For speakers wired to the computer that are on the network anyway "
        "— Teufel Raumfeld. They start at their own value and only remember "
        "what last played through their own app.\n\n"
        "Type the volume and press Enter: it is applied right away. With "
        "the switch on it is then restored by itself — when the speaker "
        "comes on, and when you return to the computer after a longer "
        "break.\n\n"
        "Enter always applies, even with the switch off — and switching on "
        "always brings the volume with it, otherwise the speaker would wake "
        "up at its own value."),
    "boxen_schalter": ("Boxen an", "Speakers on"),
    "boxen_mit_pc": ("Mit dem Rechner an- und ausschalten",
                     "Switch on and off with the computer"),
    "boxen_pc_hilfe": (
        "An, sobald du nach längerer Pause wieder an den Rechner kommst — "
        "und mit dem Anschalten gleich auf die eingetragene Lautstärke, "
        "denn die Box wacht auf ihrem eigenen Startwert auf.\n\n"
        "Aus nach 15 Minuten ohne Eingabe, aber nur, wenn dabei eine Minute "
        "lang kein Ton lief. Sonst gingen die Boxen mitten im Film aus — da "
        "fasst man eine Viertelstunde lang nichts an.\n\n"
        "Was du selbst schaltest, bleibt so: Von allein geht es erst wieder "
        "an, wenn du nach einer Pause zurückkommst.",
        "On as soon as you come back to the computer after a longer break — "
        "and straight to the volume you entered, because the speaker wakes "
        "up at its own starting value.\n\n"
        "Off after 15 minutes without input, but only if no sound played "
        "for a minute. Otherwise the speakers would go off in the middle of "
        "a film — you do not touch anything for a quarter of an hour "
        "there.\n\n"
        "What you switch yourself stays that way: it only comes back on by "
        "itself when you return after a break."),
    "boxen_laut": ("{wert} % ist ziemlich laut — noch einmal Enter",
                  "{wert}% is quite loud — press Enter again"),
    "boxen_suche": ("Suche …", "Searching …"),
    "boxen_weg": ("Keine Box gefunden", "No speaker found"),
    "boxen_an": ("Box ist an", "Speaker is on"),
    "boxen_aus": ("Box ist aus", "Speaker is off"),
    "tray_boxen": ("Boxen an/aus", "Speakers on/off"),
    "tt_boxen": ("Boxen an- und ausschalten — die Zahl anklicken und mit "
                 "Enter bestätigen setzt ihre Lautstärke",
                 "Switch the speakers on and off — click the number and "
                 "press Enter to set their volume"),
    "boxen_gesetzt": ("{name} auf {wert} % gesetzt",
                      "{name} set to {wert}%"),
    "boxen_steht": ("{name} steht auf {wert} %", "{name} is at {wert}%"),
    "beim_wechsel": ("BEIM WECHSEL GESAMT ↔ APP",
                     "WHEN SWITCHING MASTER ↔ APP"),
    "wechsel_frage": ("Was mit den Pegeln geschieht",
                      "What happens to the levels"),
    "eingabe": ("EINGABE", "INPUT"),
    "medientasten": ("MEDIENTASTEN", "MEDIA KEYS"),
    "im_fenster": ("IM FENSTER", "IN THE WINDOW"),
    "einblendung": ("EINBLENDUNG", "ON-SCREEN DISPLAY"),
    "system": ("SYSTEM", "SYSTEM"),
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
    "cover_bg": ("Coverbild als Hintergrund", "Cover art as background"),
    "cover_hilfe": (
        "Nimmt das Coverbild des laufenden Titels, zeichnet es weich und "
        "legt es hinter das Fenster — die Farben folgen damit der Musik.\n\n"
        "Damit alles lesbar bleibt, wird unter jeder Karte verdunkelt und "
        "unter der Kopfzeile ebenso. Zu sehen ist das Bild dort, wo kein "
        "Text steht — und es schimmert durch das Glas der Karten.\n\n"
        "Der Titel kommt von Windows selbst: Alles, was in der Titelanzeige "
        "der Lautstärketasten erscheint, taugt als Quelle.\n\n"
        "Kostet fast nichts. Gemessen: einmal je Titel 1 ms fürs "
        "Weichzeichnen, 5 ms fürs Holen des Bildes — und 0,06 ms je "
        "gezeichnetem Bild, bei 16,7 ms Spielraum.",
        "Takes the cover art of the current track, blurs it and puts it "
        "behind the window — the colours then follow the music.\n\n"
        "To keep everything readable, the area under each card is darkened, "
        "and under the header as well. The image shows where no text sits — "
        "and shimmers through the glass of the cards.\n\n"
        "The track comes from Windows itself: anything that appears in the "
        "volume-key track display works as a source.\n\n"
        "Costs almost nothing. Measured: 1 ms to blur and 5 ms to fetch the "
        "image, once per track — and 0.06 ms per frame drawn, out of 16.7 ms "
        "available."),
    "live_pegel": ("Live-Pegel neben den Reglern",
                   "Live meters next to the sliders"),
    "osd_anzeigen": ("Lautstärke-Einblendung anzeigen", "Show volume overlay"),
    "groesse": ("Größe", "Size"),
    "position_waagerecht": ("Position waagerecht", "Position horizontal"),
    "position_senkrecht": ("Position senkrecht", "Position vertical"),
    "transparenz": ("Transparenz", "Transparency"),

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
