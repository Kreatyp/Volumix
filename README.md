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

## Lautstärke angleichen

Der **Knopf mit den zwei Pfeilen** in jeder Zeile, zwischen Name und
Lautsprecher. Gedacht für Sprache: In Discord ist einer laut, der nächste
flüstert — Volumix hebt das Leise an und zieht das Laute herunter. Ist es an,
leuchtet der Knopf in der Akzentfarbe.

An einem gestellten Gespräch mit drei verschieden lauten Sprechern gemessen:
Der Unterschied zwischen ihnen ging von **18,0 dB auf 7,3 dB** zurück,
während die Betonungen *innerhalb* eines Sprechers erhalten blieben (4,8 →
5,6 dB). Genau diese Trennung ist der Punkt — eine Regelung, die auch den
Silben hinterherläuft, bügelt Sprache platt.

> **Der Regler ist die Mitte, um die herum geregelt wird** — nicht die
> Obergrenze. Er bleibt im Fenster stehen, wo er steht: Was läuft, ist eine
> Regelung und keine Verstellung.
>
> Nach oben ist bei **100 %** Schluss, mehr lässt Windows für eine App nicht
> zu. Steht der Regler schon ganz oben, kann Volumix nur noch dämpfen und
> sagt das beim Einschalten auch. Ein Stück Luft nach oben lohnt sich:
> Bei halb aufgedrehtem Regler kam die Schwankung im selben Versuch auf
> 7,3 dB herunter, ohne diese Luft nur auf 12,5 dB.

Für **Musik ist es nichts**: Dort sind leise Stellen Absicht. Deshalb gilt
die Einstellung je App und nicht für alles. Bei *Gesamtlautstärke* und
*Systemklängen* gibt es den Knopf gar nicht erst.

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

Die Einstellungen liegen in drei Bereichen, die oben umschaltbar sind:
**Allgemein · Steuerung · Anzeige**. Jeder passt ohne Scrollen ins Fenster,
und das Fenster fährt beim Wechsel auf die passende Höhe.

### Allgemein

**Design** steht oben: **Dunkel/Hell** und **Farbe** (12 Akzentfarben) sind
frei kombinierbar und wirken sofort. Schneller geht der Modus über das
**Mond/Sonne-Symbol**.

Darunter **Sprache** (Deutsch oder English – die Oberfläche baut sich beim
Wechsel neu auf und ist sofort umgestellt), **Mit Windows starten**, das
einen Autostart-Eintrag anlegt, und **Anzeige an Spiele weitergeben** –
siehe unten.

### Steuerung

- **Steuerung aktiv** – schaltet die Funktion an/aus (auch per Tray-Menü).
- **Regeln mit** – **Daumenrad** oder die **Lautstärke-Tasten** der Tastatur.
- **Richtung umkehren** – falls „vorne = leiser" intuitiver ist. Gilt für
  Daumenrad **und** Lautstärke-Tasten.
- **Geschwindigkeit** (10–100 %) – wie weit eine Rastung regelt. Ein Wert
  genügt für Gesamt und Apps, weil beide auf derselben Kurve liegen.
- **Titel per Mehrfachdruck wechseln** – siehe unten.

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

## Im Vollbild: Anzeige an Spiele weitergeben

Im Vollbild liegt die Einblendung **hinter** dem Spiel. Das ist keine
Einstellung, die man umlegen könnte, sondern die Art, wie Windows Vollbild
zeichnet: Dort gehört der Bildschirm dem Spiel, und ein fremdes Fenster
kommt nicht davor – auch keines, das sich „immer im Vordergrund" nennt.

Wer die Anzeige dort trotzdem sehen will, braucht ein Spiel, das sie selbst
zeichnet. Dafür gibt es unter *Einstellungen → Allgemein* den Schalter
**Anzeige an Spiele weitergeben**. Volumix hält dann einen Anschluss auf
`127.0.0.1:48765` bereit und schickt bei jeder Änderung eine Zeile:

```json
{"typ": "lautstaerke", "app": "discord.exe", "name": "Discord",
 "prozent": 57, "stumm": false, "farbe": "#7C5CFF"}
```

Beim ersten Mal je App liegt zusätzlich ihr Symbol als PNG bei. Danach
nicht mehr – es ist einige Kilobyte groß, und bei jeder Rastung am Rad wäre
das ein Vielfaches der eigentlichen Nachricht.

> **Es wird nur gesendet, nie empfangen.** Über diesen Weg kann niemand die
> Lautstärke verstellen; was nichts entgegennimmt, kann auch nichts
> Falsches entgegennehmen. Der Anschluss hängt ausdrücklich an der
> Loopback-Adresse und ist nur von diesem Rechner aus erreichbar. Ab Werk
> ist die Sache **aus** – was einen Lauscher aufmacht, soll man einschalten
> müssen.

### Minecraft

Für Minecraft 1.21.1 gibt es die passende Mod, in zwei Fassungen: eine für
**Forge**, eine für **NeoForge**. Sie hört zu und zeichnet die Anzeige ins
Spielbild. Beide liegen dem Release bei.

Größe, Ort und Standzeit stehen in `config/volumix-client.toml`; bei
NeoForge kommt man im Spiel unter *Mods → Volumix → Konfigurieren* daran.

| | |
|---|---|
| `groesse` | 0,5 bis 3,0 – kommt zur Oberflächen-Skalierung hinzu |
| `x` | 0–100 % der Bildbreite, 50 ist die Mitte |
| `y` | 0–100 % der Bildhöhe, ab Werk 78 |
| `stehen_ms` | wie lange sie steht, danach blendet sie aus |
| `im_menue` | auch bei offenem Inventar oder Pausenmenü zeigen |

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
- **Ton bei voller Lautstärke** – ein kurzer Anschlag (90 ms), sobald der
  Regler oben ankommt. Er kommt beim *Ankommen*, nicht beim Weiterdrehen: Wer
  schon auf 100 % steht und weiterdreht, hört nichts mehr. Wer am Anschlag
  hin und her wackelt, ebenfalls nicht – dazwischen liegt eine Sperre.

  > Sobald der Ton einmal gespielt hat, legt Windows für Volumix eine eigene
  > Audiositzung an. Die App taucht dann selbst im Mixer auf; über *Apps
  > wählen* lässt sie sich ausblenden.

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
| `volumix\klang.py` | der Ton am Anschlag |
| `volumix\toene\` | die Klangdatei dazu |

Einstellungen liegen in `%APPDATA%\Volumix\config.json`,
der Autostart-Eintrag unter `HKCU\...\CurrentVersion\Run\Volumix`.

**Benötigt** (bereits installiert): Python 3.13 mit `PySide6`, `pycaw`,
`comtypes`, `pynput`, `Pillow`.

## Beenden

Rechtsklick auf das Tray-Symbol → **Beenden**.
(Das Schließen des Fensters minimiert nur in den Infobereich.)
