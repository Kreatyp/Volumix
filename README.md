# Volumix

Ein **Lautstärke-Mixer** für Windows: die Windows-Gesamtlautstärke und jede
laufende Audio-App bekommen einen eigenen Schieberegler.

Der eigentliche Zweck: Du setzt pro Eintrag ein **Häkchen** – und deine
**Lautstärke-Tasten** regeln danach nur noch diese Apps. Während du spielst,
bleibt das Spiel laut, während du Discord leiser drehst.

Statt der Tasten geht auch das **seitliche Daumenrad** einer Logitech MX Master,
falls du so eine Maus hast. Das normale, senkrechte Scrollrad bleibt in beiden
Fällen **völlig unberührt**.

---

## Starten

Doppelklick auf **`programm\Volumix\Volumix.exe`**

Die App braucht **kein installiertes Python**. Beim ersten Start kann
Windows-SmartScreen einmal nachfragen („Weitere Informationen" → „Trotzdem
ausführen"), weil die Datei nicht signiert ist.

Volumix läuft dann im Hintergrund und legt ein **Lautsprecher-Symbol im
Infobereich** ab (unten rechts neben der Uhr, ggf. auf den Pfeil `^` klicken).

> Zum Ausprobieren von Änderungen am Quelltext: `Volumix starten.bat`.
> Neu bauen: `python build_exe.py`.

## Bedienen

1. Fenster öffnen (Klick aufs Tray-Symbol, oder die App erneut starten).
2. Im **Mixer** hat jede aktive Audio-App einen eigenen **Schieberegler**.
3. **Zeile anklicken** = diese App wird per Daumenrad gesteuert. Mehrere
   gleichzeitig gehen auch; angehakte Zeilen sind hervorgehoben.
4. Am **Daumenrad drehen** → die Lautstärke ändert sich, eine kleine
   Einblendung zeigt App und Prozent.

- **Live-Pegel:** Der helle Streifen im Schieberegler zeigt, was die App
  gerade wirklich ausgibt – mit einer Markierung, die kurz an der lautesten
  Stelle stehen bleibt. Abschaltbar unter *Einstellungen → Anzeige*.
- **Mausrad direkt über einem Schieberegler** regelt genau diese App – ohne
  sie anzuhaken. Daneben scrollt es die Liste.
- **Suchfeld:** Ab acht sichtbaren Apps erscheint über der Liste ein Suchfeld.
- **Stummschalten:** Klick auf das **Lautsprecher-Symbol** in der Zeile. Ein
  Regler auf **0 %** schaltet von allein stumm, Hochdrehen hebt es wieder auf.

## Profile

Unter der Kopfzeile steht der Name des offenen Profils, links und rechts davon
die Pfeile zum Wechseln. Das **+** legt ein neues an – es startet als Kopie des
aktuellen, du gibst nur einen Namen ein. Ein Klick auf den Namen öffnet die
Liste zum Springen, Umbenennen und Löschen.

**Einen Speichern-Knopf gibt es nicht.** Was du änderst, gehört ab sofort zum
offenen Profil. Dazu zählen:

- die Pegel aller Apps und der Gesamtlautstärke
- welche davon am Rad bzw. an den Tasten hängen
- Farbe und Hell/Dunkel
- die Geschwindigkeit

Sprache, Autostart, die Wahl zwischen Rad und Tasten, „Richtung umkehren",
Live-Pegel und die Einblendung gelten dagegen **für alle Profile** – die hängen
am Rechner, nicht an der Stimmung.
- **„Gesamtlautstärke" und einzelne Apps schließen sich aus** – sonst würde
  doppelt gedämpft: erst die App, dann nochmal global. Was dabei mit den Pegeln
  passiert, stellst du unter *Beim Wechsel Gesamt ↔ App* ein.
- **Fensterhöhe** lässt sich ziehen (höher als die Liste geht nicht), die
  Breite ist fest.
- Mehrere Monitore mit **verschiedener Skalierung** sind kein Problem: Volumix
  zeichnet sich auf jedem Bildschirm in dessen echter Auflösung.

## Einstellungen

Über das **Zahnrad oben rechts**, zurück über den **Pfeil oben links**.

### Design

**Modus** (Dunkel/Hell) und **Farbe** (12 Akzentfarben) sind frei kombinierbar
und wirken sofort. Schneller geht der Modus über das **Mond/Sonne-Symbol**.

### Sprache

**Deutsch** oder **English** – die Oberfläche baut sich beim Wechsel neu auf
und ist sofort umgestellt.

### Steuerung

- **Geschwindigkeit** (10–100 %) – wie weit eine Rastung regelt. Ein Wert
  genügt für Gesamt und Apps, weil beide auf derselben Kurve liegen.
- **Steuerung aktiv** – schaltet die Funktion an/aus (auch per Tray-Menü).
- **Horizontales Scrollen verwenden** – an: das Daumenrad steuert die
  Lautstärke. Aus: stattdessen die **Lautstärke-Tasten** der Tastatur.
- **Richtung umkehren** – falls „vorne = leiser" intuitiver ist. Gilt für
  Daumenrad **und** Lautstärke-Tasten.
- **Mit Windows starten** – legt einen Autostart-Eintrag an.

#### Beim Wechsel Gesamt ↔ App

Was du hörst, ist **App-Pegel × Dämpfung der Gesamtlautstärke**. Beim
Umschalten wandert die Steuerung vom einen Faktor auf den anderen – ohne
Ausgleich springt die Lautstärke. Drei Möglichkeiten (Erklärung auch im
Fragezeichen daneben):

| | |
|---|---|
| **Nichts ändern** | Ab Werk. Alle Pegel bleiben, wie sie sind. |
| **Pegel mitnehmen** | Die hörbare Lautstärke bleibt gleich – kein Sprung nach oben. |
| **Apps auf 100 %** | Beim Wechsel auf *Gesamtlautstärke* gehen alle Apps auf 100 %. |

Bei **Pegel mitnehmen** wird alles mitgezogen, was in dem Moment **hörbar Ton
ausgibt** – läuft Musik in Spotify, während du auf Chrome wechselst, wird
Spotify mit heruntergeregelt. Apps, die nur offen sind und schweigen (typisch:
Discord), bleiben unangetastet.

> Beim Umrechnen geht Volumix über Dezibel: Es klingt nach dem Wechsel
> **exakt gleich laut**, auch wenn die Zahl auf der anderen Seite anders
> steht. Kein Rundungsfehler.

## Alle Regler auf einer Kurve

Windows' Gesamtlautstärke dämpft nicht linear: Der halbe Reglerweg bedeutet
rund 30 % Amplitude, nicht 50 %. Die Regler einzelner Apps sind dagegen reine
Amplitudenfaktoren – dort sind 50 % wirklich 50 %.

Deshalb fühlten sich beide Regler unterschiedlich an: unten am App-Regler
sprang die Lautstärke, während der Windows-Regler dort fein blieb.

Volumix bringt die App-Regler auf dieselbe Kurve. Was ein Regler zeigt, ist
jetzt überall ein **Reglerweg**, keine rohe Amplitude:

| Reglerweg | tatsächliche Amplitude |
|---|---|
| 10 % | 2 % |
| 25 % | 10 % |
| 50 % | 31 % |
| 75 % | 61 % |

Den nötigen Exponenten liest Volumix im Betrieb vom Ausgabegerät ab – Windows
verrät zu jeder Reglerstellung auch den Dezibelwert, und daraus ergibt er sich.
Steckst du ein anderes Gerät an, passt sich die Kurve mit an. Bei einem Gerät
mit linearer Kurve ändert sich schlicht nichts.

Nebeneffekt: Unten wird von selbst feiner geregelt als oben, ohne dass es dafür
eine eigene Einstellung braucht.

### Anzeige

- **Live-Pegel neben den Reglern** – die Ausschlagbalken an/aus.
- **Lautstärke-Einblendung anzeigen**, dazu **Größe** und **Position**.
  Jede Änderung wird sofort als Vorschau eingeblendet.

### Sichtbare Apps

Windows legt für viele Programme eine Audiositzung an, die nie Ton ausgibt
(z. B. `msedgewebview2`, `ShellExperienceHost`). Diese sind ab Werk
ausgeblendet. Über **Apps wählen** in der unteren Leiste stellst du ein, was im
Mixer erscheint – mit Suchfeld, und die ganze Zeile ist anklickbar.

Gelistet sind nur Programme, die **gerade** eine Audiositzung haben. Deine
Haken merkt sich Volumix trotzdem dauerhaft: Schließt du eine App und startest
sie Tage später neu, ist sie wieder so eingestellt wie zuletzt.

---

## Falls das Daumenrad nichts bewirkt

1. Fenster öffnen und **Daumenrad bewegen**. Unten sollte „Daumenrad
   erkannt …" erscheinen.
   - **Erscheint das?** → Dann ist nur keine App angehakt bzw. „Steuerung
     aktiv" ist aus.
   - **Erscheint das nicht?** → In **Logi Options+** ist das Daumenrad
     vermutlich anders belegt. Dort auf **„Horizontales Scrollen"** stellen.
2. Die angehakte App muss gerade eine **aktive Audiositzung** haben.

---

## Dateien

| | |
|---|---|
| `programm\Volumix\Volumix.exe` | die fertige App (kein Python nötig) |
| `volumix.pyw` | Startpunkt des Quelltextes |
| `volumix\` | die einzelnen Bausteine (siehe unten) |
| `build_exe.py` | baut die App neu |
| `tests\` | Testreihen, `Tests ausfuehren.bat` startet alle |
| `Volumix starten.bat` | startet den Quelltext direkt |
| `archiv-tk\` | die alte Tkinter-Fassung, falls sie nochmal gebraucht wird |
| [`LIZENZHINWEISE.md`](LIZENZHINWEISE.md) | Lizenzen der mitgelieferten Bausteine |

Der Quelltext ist in Bausteine geteilt, statt in einer einzigen großen Datei:

| Datei | Inhalt |
|---|---|
| `volumix\config.py` | Einstellungen, Autostart, Ablageorte |
| `volumix\theme.py` | Farben und Stilvorlage |
| `volumix\audio.py` | Windows-Audio: Sitzungen, Pegel, Spitzenwerte |
| `volumix\icons.py` | Symbole (Vektoren) und Programm-Icons |
| `volumix\widgets.py` | Mixer-Zeile, Regler, Schalter, Pegelbalken |
| `volumix\osd.py` | die Lautstärke-Einblendung |
| `volumix\window.py` | Hauptfenster, Einstellungen, Dialoge |
| `volumix\hooks.py` | Daumenrad und Lautstärke-Tasten |
| `volumix\sprache.py` | alle sichtbaren Texte, Deutsch und Englisch |
| `volumix\fonts\` | die Wortmarke als Bild |

Einstellungen liegen in `%APPDATA%\Volumix\config.json`,
der Autostart-Eintrag unter `HKCU\...\CurrentVersion\Run\Volumix`.

**Benötigt** (bereits installiert): Python 3.13 mit `PySide6`, `pycaw`,
`comtypes`, `pynput`, `Pillow`.

## Beenden

Rechtsklick auf das Tray-Symbol → **Beenden**.
(Das Schließen des Fensters minimiert nur in den Infobereich.)
