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

Doppelklick auf **`Volumix`** im Hauptordner – die Verknüpfung legt
`build_exe.py` bei jedem Bau neu an.

> Die `.exe` selbst liegt unter `programm\Volumix\`, und dort muss sie auch
> bleiben: Daneben steht ein Ordner `_internal` mit Qt und allem Übrigen, ohne
> den sie nicht startet.

Die App braucht **kein installiertes Python**. Beim ersten Start kann
Windows-SmartScreen einmal nachfragen („Weitere Informationen" → „Trotzdem
ausführen"), weil die Datei nicht signiert ist.

Volumix läuft dann im Hintergrund und legt sein **Symbol im Infobereich** ab
(unten rechts neben der Uhr, ggf. auf den Pfeil `^` klicken).

> Zum Ausprobieren von Änderungen am Quelltext: `werkzeug\Volumix starten.bat`.
> Neu bauen: `python build_exe.py`.

### Wenn sich die App wortlos schließt

Ein Programm im Infobereich verschwindet lautlos, und ohne Konsole geht jede
Meldung ins Nichts. Deshalb schreibt Volumix zwei Dateien nach
`%APPDATA%\Volumix\`:

| | |
|---|---|
| `fehler.log` | jeder Start, jedes Beenden, und jeder Fehler mit vollem Weg |
| `absturz.log` | für Abstürze unterhalb von Python |

Steht in `fehler.log` ein **„beendet"**, hat jemand die App über das Tray-Menü
geschlossen. Fehlt es, ist sie von selbst gegangen — dann steht der Grund
entweder darüber oder in `absturz.log`.

> In `absturz.log` steht bei jedem Start eine Ausnahme `0x8001010D`. Die ist
> normal: Windows wirft sie beim Anlegen eines Fensters, Qt fängt sie ab.
> Nachgemessen — schon ein leeres Qt-Fenster ohne eine Zeile Volumix erzeugt
> sie. Genau deshalb liegt sie in einer eigenen Datei und nicht in
> `fehler.log`.

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
- Ändert sich ein Wert **von außen** – Daumenrad, Profilwechsel, ein anderes
  Programm am Windows-Mixer –, gleitet der Regler dorthin, statt zu springen.
  Was du selbst anfasst, folgt sofort.
- **Mausrad direkt über einem Schieberegler** regelt genau diese App – ohne
  sie anzuhaken. Daneben scrollt es die Liste.
- **Suchfeld:** Ab acht sichtbaren Apps erscheint über der Liste ein Suchfeld.
- **Stummschalten:** Klick auf das **Lautsprecher-Symbol** in der Zeile. Ein
  Regler auf **0 %** schaltet von allein stumm, Hochdrehen hebt es wieder auf.

## Profile

Unter der Kopfzeile steht der Name des offenen Profils, links und rechts davon
die Pfeile zum Wechseln – die **Pfeiltasten** tun dasselbe. Die Punkte darunter
zeigen, wo du gerade stehst. Das **+** legt ein neues an; es startet als Kopie
des aktuellen und der Name steht gleich zum Tippen bereit.

Ein Klick auf den Namen schaltet ihn zum Ändern frei, daneben erscheint der
Papierkorb. Bestätigt wird mit Klick daneben oder Enter, verworfen mit Escape.
In den Einstellungen taucht die Leiste nicht auf – dort wechselt man keine
Profile.

**Einen Speichern-Knopf gibt es nicht.** Was du änderst, gehört ab sofort zum
offenen Profil. Dazu zählen:

- die Pegel aller Apps und der Gesamtlautstärke
- welche davon am Rad bzw. an den Tasten hängen

**Alles aus den Einstellungen gilt für alle Profile** – Farbe, Hell/Dunkel,
Geschwindigkeit, Sprache, Autostart. Ein Profil ist ein Arbeitsstand, kein
zweites Programm.
- **„Gesamtlautstärke" und einzelne Apps schließen sich aus** – sonst würde
  doppelt gedämpft: erst die App, dann nochmal global. Was dabei mit den Pegeln
  passiert, stellst du unter *Beim Wechsel Gesamt ↔ App* ein.
- **Fensterhöhe** lässt sich ziehen (höher als die Liste geht nicht), die
  Breite ist fest.
- Mehrere Monitore mit **verschiedener Skalierung** sind kein Problem: Volumix
  zeichnet sich auf jedem Bildschirm in dessen echter Auflösung.

## Einstellungen

Über das **Zahnrad oben rechts**, zurück über den **Pfeil oben links**.

Die Einstellungen liegen in vier Bereichen, die oben umschaltbar sind:
**Design · Steuerung · Anzeige · Allgemein**. Jeder passt ohne Scrollen ins
Fenster, und das Fenster fährt beim Wechsel auf die passende Höhe.

### Design

**Modus** (Dunkel/Hell) und **Farbe** (12 Akzentfarben) sind frei kombinierbar
und wirken sofort. Schneller geht der Modus über das **Mond/Sonne-Symbol**.

### Steuerung

- **Steuerung aktiv** – schaltet die Funktion an/aus (auch per Tray-Menü).
- **Regeln mit** – **Daumenrad** oder die **Lautstärke-Tasten** der Tastatur.
- **Richtung umkehren** – falls „vorne = leiser" intuitiver ist. Gilt für
  Daumenrad **und** Lautstärke-Tasten.
- **Geschwindigkeit** (10–100 %) – wie weit eine Rastung regelt. Ein Wert
  genügt für Gesamt und Apps, weil beide auf derselben Kurve liegen.
- **Titel per Mehrfachdruck wechseln** – siehe unten.

### Allgemein

**Sprache** (Deutsch oder English – die Oberfläche baut sich beim Wechsel neu
auf und ist sofort umgestellt) und **Mit Windows starten**, das einen
Autostart-Eintrag anlegt.

#### Titel per Mehrfachdruck wechseln

Gibt der **Wiedergabe-Taste** eine zweite und dritte Bedeutung, so wie es
Kopfhörer tun:

| | |
|---|---|
| einmal drücken | Wiedergabe / Pause |
| zweimal | nächster Titel |
| dreimal | vorheriger Titel |

Das wirkt überall, wo die Medientasten wirken – Spotify, YouTube und der Rest.
Auch dann, wenn keine App angehakt ist; mit der Lautstärkesteuerung hat es
nichts zu tun.

> **Der Haken:** Volumix muss nach dem ersten Druck rund eine Drittelsekunde
> abwarten, ob noch einer kommt. Solange die Funktion an ist, reagiert die
> Taste also verzögert. Deshalb ist sie ab Werk aus.

Eine auf „Wiedergabe/Pause" belegte **Maustaste** funktioniert genauso – auch
wenn Logi Options+ die Taste nur simuliert.

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
- **Lautstärke-Einblendung anzeigen**, dazu **Größe** und **Position**. Jede
  Änderung wird sofort als Vorschau eingeblendet. Ist die Einblendung aus,
  sind die drei Regler ausgegraut – sie hätten dann nichts zu tun.

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
| `Volumix` | Verknüpfung zur fertigen App – der übliche Weg zum Starten |
| `volumix.pyw` | Startpunkt des Quelltextes |
| `volumix\` | die einzelnen Bausteine (siehe unten) |
| `build_exe.py` | baut die App neu, samt Symbol und Verknüpfung |
| `tests\` | Testreihen, `werkzeug\Tests ausfuehren.bat` startet alle |
| `werkzeug\` | Startdateien und eigene Notizen |
| `docs\` | die Webseite (GitHub Pages) |
| `programm\` | die gebaute App – entsteht aus dem Quelltext |
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
| `volumix\fonts\` | die Schrift der Oberfläche samt Lizenztext |

Einstellungen liegen in `%APPDATA%\Volumix\config.json`,
der Autostart-Eintrag unter `HKCU\...\CurrentVersion\Run\Volumix`.

**Benötigt** (bereits installiert): Python 3.13 mit `PySide6`, `pycaw`,
`comtypes`, `pynput`, `Pillow`.

## Beenden

Rechtsklick auf das Tray-Symbol → **Beenden**.
(Das Schließen des Fensters minimiert nur in den Infobereich.)
