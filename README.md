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

> **Wenn Volumix plötzlich verschwunden ist**, hat es meist der Virenscanner
> geholt — ein Fehlalarm, wie er bei mit PyInstaller gepackten Programmen
> häufig vorkommt. Was dagegen hilft und wie man die Datei zurückbekommt,
> steht in [`werkzeug\DEFENDER.md`](werkzeug/DEFENDER.md).

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

## Das Fenster hat keinen Rahmen

Es gibt keine Titelleiste mehr — nur **Minimieren** und **Schließen** oben
rechts. Der Balken ließ sich zwar über DWM einfärben, blieb aber ein Balken;
mit einem Coverbild dahinter fiel das erst recht auf.

Was Windows sonst um ein Fenster herum leistet, bleibt trotzdem erhalten. Es
muss nur einzeln bestellt werden, und das steht in `_titelleiste_faerben`:

| Was | Wie |
|---|---|
| Verschieben samt Anschnappen | `startSystemMove` auf dem Streifen ganz oben |
| Höhe ziehen | `startSystemResize` am unteren Saum (7 px, `SAUM`) |
| runde Ecken | `DWMWA_WINDOW_CORNER_PREFERENCE` |
| Schlagschatten | `DwmExtendFrameIntoClientArea` mit 1 px Rand |
| kein heller Strich außen | `DWMWA_BORDER_COLOR` auf `DWMWA_COLOR_NONE` |

Wichtig ist `startSystemMove`: Ein selbst nachgebautes Verschieben — Position
merken, bei jeder Mausbewegung setzen — verliert das Anschnappen an die
Bildschirmränder. Windows macht das selbst, wenn man es lässt.

Der Streifen mit den beiden Knöpfen liegt **außerhalb** der umschaltbaren
Seiten. Sonst wären sie in den Einstellungen weg, denn dort wird die
Kopfzeile ausgeblendet.

**Schließen beendet nicht** — das Fenster verschwindet, Volumix läuft im
Infobereich weiter. Beendet wird über dessen Menü. Das war schon vorher so,
steht jetzt aber im Hinweis am Knopf.

## Zurückhaltung als Entwurfsregel

Ein paar Elemente standen auf „wichtig", obwohl sie es nicht sind. Wenn alles
wichtig ist, führt nichts mehr das Auge. Fünf Stellen sind deshalb leiser
geworden:

- **Die Lautstärke-Pille** trug im Ruhezustand einen Akzentring *und* eine
  Akzentfüllung und war damit das lauteste Element im Fenster — für etwas,
  das man einmal einstellt. Der Ring bleibt jetzt dem Warnzustand vorbehalten;
  dass die Boxen an sind, sagt der Lautsprecher in Akzentfarbe ohnehin.
- **„Apps wählen"** war gefüllt und damit der kräftigste Knopf im Fenster.
  Jetzt ein Umriss (`#Leise`) — eine Nebensache, die auch so aussieht.
- **Die Fläche einer angehakten Zeile** war ein Vollton — die einzige flache
  Fläche im ganzen Fenster, während Karten, Leisten und Einblendung alle
  einen Verlauf und eine Lichtkante tragen. Genau daran lag es, dass sie wie
  aufgeklebt wirkte. Jetzt bekommt sie beides, die Kante schwächer als auf
  den Karten: Die Zeile liegt schon auf einer Scheibe, zwei gleich helle
  Kanten übereinander wären zu viel.
- **Die Überschrift LAUTSTÄRKE-MIXER** über der Mixerkarte ist weg. Sie
  stand wörtlich zwei Zeilen darüber im Untertitel des Fensters. Die Karte
  beginnt jetzt direkt mit der Abschnittsüberschrift *ALLES*, deren Linie
  die Gliederung ohnehin trägt.
- **Der Auswahlbalken** einer angehakten Zeile saß bündig bei x=0 und stieß
  damit gegen die Rundung der Zeile (Radius 12) — er sah aus wie
  abgeschnitten. Und er war die einzige flache Vollfarbe im Fenster, während
  alles andere Licht von oben bekommt. Jetzt sitzt er 5 px im Rand, ist 4
  statt 3 px breit (bei 150 % Bildschirmskalierung waren 3 px zu wenig) und
  trägt denselben Verlauf wie die Flächen.

Drei Versuche sind wieder zurückgedreht, weil sie im Betrieb nicht trugen.
Die **Profilleiste** war zweimal Gegenstand: ohne eigene Fläche wirkte sie
losgelöst, und in die Mixerkarte hineingezogen verschmolz sie mit etwas, das
sie nicht ist. Sie bleibt eine eigene Kachel mit 52 px. Und der **Fettdruck** in angehakten Zeilen ist zurück: Ohne
ihn war die angehakte Zeile im Vorbeischauen nicht mehr sofort zu finden,
auch wenn die Messung sagt, dass bei 14 px vor allem die Helligkeit trägt.
- **Um das ganze Fenster** liegt derselbe Lichtsaum, der die Karten wie Glas
  aussehen lässt: oben hell, nach unten auslaufend. Die Zeichnung dafür steht
  jetzt als `lichtkante()` für sich, damit Karten und Fenster dieselbe Geste
  benutzen und nicht zwei Kopien davon auseinanderlaufen.

Der Radius des Saums ist 8 px — der, mit dem Windows 11 rahmenlose Fenster
rundet. Ein anderer Wert und der Saum säße neben der Kante. Und seine Länge
ist ein fester Wert statt der 60 % der Höhe, mit denen die Karten arbeiten:
über ein ganzes Fenster gezogen wäre daraus ein heller Streifen bis zur Mitte.

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

Die Einstellungen liegen in vier Bereichen, die oben umschaltbar sind:
**Allgemein · Steuerung · Anzeige · Boxen**. Jeder passt ohne Scrollen
ins Fenster, und das Fenster fährt beim Wechsel auf die passende Höhe.

Der dritte hieß bis vor kurzem „Anzeige“ — er enthält aber auch den Ton am
Anschlag. Und die Boxen saßen unter Steuerung, wo der Reiter mit vier Karten
zu lang wurde; sie haben jetzt einen eigenen.

### Allgemein

**Design** steht oben: **Dunkel/Hell** und **Farbe** (12 Akzentfarben) sind
frei kombinierbar und wirken sofort. Schneller geht der Modus über das
**Mond/Sonne-Symbol**.

Die beiden Modi sind nicht dieselbe Oberfläche in anderen Farben. Im Dunkeln
sind die Flächen Milchglas über einem Grund, in dem farbiges Licht steht —
die Scheibe ist heller als der Grund, dazu ein Lichtsaum an der Oberkante.
Im Hellen trägt dieselbe Geste nichts: Weiße Milch auf hellem Grund ändert
die Helligkeit nicht, ein weißer Saum auf weißer Karte erst recht nicht.
Übrig blieb eine Karte, die man nur am Farbnebel des Fenstergrundes fand —
und der färbte sie gleich mit. Im hellen Modus ist die Karte deshalb ein
deckendes Blatt mit feiner Kante, und im Grund steht statt dreier Lichter
nur noch eines, weit gezogen und schwach: Zwei Farbtöne nebeneinander ergaben
dort keinen Verlauf, sondern einen Nebel, der von Violett nach Rosa drehte.

Gemessen an derselben Stelle, Karte gegen Grund: L\* 98,6 zu 91,7 im Hellen,
9,1 zu 3,0 im Dunkeln. Beide Modi haben damit denselben Abstand, nur
gegenläufig — und `tests/test_hell.py` prüft ihn, samt Kante und Textkontrast.

**Größe** zieht die ganze Oberfläche größer oder kleiner — 80 bis 130 %,
Schrift, Regler und Abstände im selben Verhältnis. Das ist keine Zoomstufe,
die ein fertiges Bild vergrößert: Der Wert geht als `QT_SCALE_FACTOR` in Qt,
das damit von vornherein rechnet, und die Schrift bleibt gestochen.
Nachgemessen an der Fensterbreite in echten Bildschirmpixeln: 840 bei 100 %,
966 bei 115 %.

Der Haken ist, dass der Wert feststehen muss, **bevor** Qt hochfährt — er
wird deshalb im Startpunkt `volumix.pyw` gesetzt und wirkt erst beim nächsten
Start. Sobald du ihn änderst, erscheint darunter ein Hinweis mit einem Knopf
*Jetzt neu starten*.

Der Neustart hat zwei Fallen, beide eingebaut und beide gemessen:

Die neue Instanz fährt hoch, während die alte noch läuft, und würde sich für
die überflüssige zweite halten und sofort beenden — aus dem Neustart würde
ein Beenden. Deshalb bekommt sie `--neustart` mit und wartet bis zu acht
Sekunden auf die Einzelinstanz-Sperre. Bewusst so herum: Die alte Instanz
müsste ihre Sperre sonst zuverlässig loslassen, und darauf ist in einer
gepackten App kein Verlass. Warten kann die neue immer.

Und sie **erbt die Umgebung der alten** — samt deren `QT_SCALE_FACTOR`.
Würde der Wert nur bei Abweichung von 100 gesetzt, käme man von 115 nie
wieder auf 100 zurück: Die neue Instanz fände den alten Faktor vor und
behielte ihn. Er wird deshalb immer gesetzt, auch bei 100 %.

Der Neustart startet **ohne** `--tray`: Der Knopf wurde im offenen Fenster
gedrückt, also gehört das Fenster danach wieder auf den Bildschirm.

Darunter **Sprache** (Deutsch oder English – die Oberfläche baut sich beim
Wechsel neu auf und ist sofort umgestellt), **Mit Windows starten**, das
einen Autostart-Eintrag anlegt, und **Anzeige an Spiele weitergeben**.

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

## Coverbild als Hintergrund

Unter **Einstellungen › Anzeige** liegt der Schalter *Coverbild als
Hintergrund*. Er nimmt das Cover des laufenden Titels, zeichnet es weich und
legt es hinter das Fenster — die Farben folgen damit der Musik.

Zu sehen ist das Bild im Rahmen um die Karten herum, und es schimmert durch
das Glas. Lesbar bleibt trotzdem alles, weil an vier Stellen verdunkelt wird:

| Stelle | Wieviel |
|---|---|
| über dem ganzen Bild | 18 % Fenstergrund (`COVER_SCHLEIER`) |
| unter jeder Karte | 78 % (`COVER_KARTEN`) |
| unter dem Kopf | 86 %, dann Verlauf auf 0 (`COVER_KOPF_DECKUNG`) |
| zu den Ecken hin | bis 35 % (`COVER_RAND`) |

Die Ecken sind kein Lesbarkeitsproblem, sondern eines der Wirkung: Ohne das
Ausblenden endet das Bild hart an der Fensterkante und sieht aufgeklebt aus.

Auch die **Titelleiste** zieht mit. Sie wird über DWM eingefärbt und stand
sonst in `theme.bg`, also fast schwarz — über einem farbigen Fenster ein
dunkler Balken. Ihre Farbe wird jetzt nicht berechnet, sondern am fertigen
Bild abgegriffen: die oberste Pixelzeile des Fensterinhalts, gemittelt.
Damit stimmt sie, egal wie Schleier, Randabdunklung und Kopfverlauf
eingestellt sind — gemessen eine Stufe Abweichung. Ohne Coverbild bleibt es
bei `theme.bg`.

Und der Fenstergrund leuchtet dann nicht mehr im Akzent, sondern im Farbton
des Covers — sonst stehen zwei Farbwelten übereinander. Regler, Haken und
Schalter behalten den Akzent: Bedienelemente sollen nicht mit jedem Titel
umfärben. Die Sättigung wird dabei nach oben *und* unten begrenzt, damit ein
flaues Cover trotzdem leuchtet und ein knallbuntes das Fenster nicht
einfärbt.

Die Karte ist der wichtigere Teil: Im dunklen Modus ist das Glas nur zu 7 %
deckend, ein Bild schiene sonst mitten durch die Schrift. Oben steht Text als
Einziger ohne Karte auf dem Grund — deshalb dort ein eigener Verlauf. Er
reicht so weit, wie dieser Text reicht: im Mixer 118 px unter die Oberkante,
in den Einstellungen bis unter die Reiterleiste, danach 36 px Auslauf. Eine
Kachel mit Kante sähe auf dem Bild aufgeklebt aus; so endet die Abdunklung,
ohne dass man merkt wo. Über einem hellen Cover stand der inaktive Reiter
vorher bei 1,4:1 und war nicht zu lesen — jetzt sind es 4,6 bis 5,7:1.

Beim Titelwechsel wird über 700 ms übergeblendet.

### Was es kostet

Die Frage war, ob das Leistung frisst. Gemessen auf diesem Rechner:

| Vorgang | Dauer | Wie oft |
|---|---|---|
| WinRT-Module laden | 86 ms | einmal, im Arbeitsthread |
| Titel abfragen | 3,7 ms | alle 1,5 s |
| Cover dazu holen | 5,4 ms | nur beim Titelwechsel |
| Weichzeichnen | 6,8 ms | nur beim Titelwechsel |
| Leuchtfarbe bestimmen | 0,24 ms | nur beim Titelwechsel |
| fertiges Bild zeichnen | 0,06 ms | je Bild, bei 16,7 ms Spielraum |

Der erste Anlauf rechnete das Cover auf 26×26 herunter und zog es wieder
hoch. Das kostete nur 1 ms, sah aber genau danach aus: kantige Blöcke und die
Rauten der Interpolation. Jetzt läuft Qts eigener Gaußfilter mit Radius 40
auf einer Fläche von 320 px — 6,8 ms statt 1, einmal je Titel, also ohne
Belang. Gerechnet wird mit einem Rand von der Breite des Radius, der
hinterher abgeschnitten wird: Der Filter zieht an der Bildkante Farbe aus dem
Nichts und hinterließe sonst einen hellen Saum.

Die Vorlage von Windows ist übrigens nur 300×300 groß — ein Miniaturbild.
Für einen Weichzeichner reicht das mühelos; die Streifen kamen nicht von der
Vorlage, sondern von den 26 Pixeln.

Im Takt wird nur nach Titel und Interpret gefragt; das Bild kommt erst, wenn
sich etwas geändert hat. Ein Titel dauert Minuten.

### Woher der Titel kommt

Von Windows selbst: `GlobalSystemMediaTransportControlsSession` — dieselbe
Liste, die die Titelanzeige der Lautstärketasten füttert. Alles, was dort
erscheint, taugt als Quelle: Spotify, Browser, Player.

Die Module sind native Erweiterungen; `build_exe.py` nimmt sie über
`--collect-all winrt` mit (rund 2,9 MB). Ob es geklappt hat, steht beim Start
in `%APPDATA%\Volumix\fehler.log` — „Titelwacht laeuft" oder der Grund,
warum nicht. Ohne die Module bleibt der Hintergrund schlicht leer.

## Boxen im Netz

Für Lautsprecher, die per Cinch am Rechner hängen und trotzdem im Netz
stehen — Teufel Raumfeld. Sie starten mit ihrem eigenen Wert (bei der
Stereo M rund 50, gemessen 49) und merken sich nur, was zuletzt über ihre
eigene App lief. Wer den Ton vom PC-Ausgang nimmt, zieht deshalb jedes Mal
von Hand nach.

### In der Kopfzeile

Was man im Vorbeigehen braucht, steht oben neben Mond und Zahnrad: eine
Pille mit Lautsprecher und Zahl.

- **Ein Klick auf den Lautsprecher** schaltet die Boxen an und aus. Beim
  Anschalten kommt die gezeigte Lautstärke gleich mit — die Box wacht sonst
  auf ihren eigenen 49 auf, während daneben 65 steht. Das gilt unabhängig
  von den Schaltern in den Einstellungen; die regeln nur, was *von selbst*
  geschieht.
- **Auf dem Knopf herumzudrücken schadet nichts.** Zwanzig Klicks in einer
  Sekunde ergeben einen einzigen Befehl an die Box: Geklickt wird nur der
  Wunsch, ausgeführt wird der letzte, und zwischen zwei echten
  Schaltvorgängen liegen mindestens vier Sekunden (`SCHALTSPERRE`). Steht
  die Box am Ende ohnehin schon so, passiert gar nichts. Ein Verstärker,
  den man im Sekundentakt ein- und ausschaltet, dankt es nicht.
- **Der Zustand hängt an zwei Merkmalen, nicht an einem.** An trägt die
  Pille den Akzentton und der Lautsprecher seine Wellen; aus ist er
  durchgestrichen und alles gedämpft. Wer Farben schlecht auseinanderhält,
  sieht es trotzdem.
- **Die Zahl ist ein Eingabefeld.** Hineinklicken, tippen, Enter. Beim
  Hineinklicken steht sie markiert da — man will sie ersetzen, nicht hinter
  ihr weitertippen. Ein Kasten mit Rahmen neben der Wortmarke wäre ein
  Fremdkörper, deshalb sieht das Feld erst beim Tippen nach einem aus.
- **Escape oder ein Klick daneben verwirft.** Übernommen wird nur mit Enter.
  Stillschweigend zu setzen wäre hier heikler als anderswo: Am Ende der
  Kette hängt ein Verstärker.
- **Ab 70 % wird nachgefragt.** Das erste Enter setzt noch nicht, sondern
  färbt Zahl und Rand warnend und schreibt einen Hinweis in die Statusleiste;
  erst das zweite setzt. Ein Vertipper — 90 statt 9 — kostet an einer Anlage
  mehr als ein zusätzlicher Tastendruck. Die Schwelle steht als `LAUT` in
  `volumix\window.py`.
- **Die Zahl anzufassen schaltet nie.** Geschaltet wird allein über den
  Lautsprecher links; die ganze rechte Hälfte der Pille — Feld,
  Prozentzeichen, Rand — setzt nur die Eingabe hinein. Das Feld selbst ist
  25 px breit, danebengetroffen hätte man sonst die Boxen ausgeschaltet.

Die Pille erscheint erst, wenn überhaupt eine Box im Netz gefunden wurde.
Gesucht wird nicht von allein — ein Rechner ohne solche Boxen soll nicht im
Hintergrund das Netz absuchen —, sondern sobald du den Steuerungsbereich
der Einstellungen aufmachst. Danach ist die Adresse gemerkt und die Pille
von jedem Start an da.

Sie sitzt in der Kopfzeile, und die ist auf der Einstellungsseite
ausgeblendet. Dort steht ohnehin die vollständige Karte.

Denselben An/Aus-Schalter gibt es im Tray-Menü. Alle drei Stellen zeigen
dasselbe: Wer die Box an ihrem eigenen Knopf oder in der Teufel-App
schaltet, sieht das hier ebenso.

### In den Einstellungen

Der Rest steht im Reiter **Boxen**:

**Lautstärke selbst nachziehen** setzt den eingetragenen Wert bei zwei
Gelegenheiten: wenn die Box angeht (danach 20 Sekunden lang
nachkontrolliert, weil sie ihren Startwert erst kurz nach dem Hochfahren
zieht) und wenn du nach längerer Pause an den Rechner zurückkommst.

**Mit dem Rechner an- und ausschalten** macht daraus das Ganze:

- **Der Rechner geht schlafen → die Boxen gehen aus.** Windows schickt dafür
  `WM_POWERBROADCAST`, und Volumix schaltet noch im selben Atemzug ab —
  nicht über den Arbeitsthread, der gleich mit eingefroren wird, sondern
  sofort und mit kurzer Zeitgrenze. Eine Box, die nicht antwortet, darf das
  Einschlafen nicht aufhalten.
- **Der Rechner wacht auf → die Boxen gehen an**, samt eingetragener
  Lautstärke. Das hängt bewusst *nicht* am Leerlaufzähler: Wer den Rechner
  am Netzschalter weckt, drückt dabei keine Taste. Vorher wartet Volumix bis
  zu 30 Sekunden darauf, dass die Netzwerkkarte wieder eine Verbindung hat.
- **An, sobald du nach einer Pause zurückkommst** — fünf Minuten ohne
  Eingabe genügen, siehe `RUHE`.
- **Aus nach 15 Minuten ohne Eingabe**, aber nur, wenn dabei eine Minute
  lang kein Ton lief. Ohne diese zweite Bedingung gingen die Boxen mitten im
  Film aus, denn da fasst man eine Viertelstunde lang nichts an.

Was Volumix beim Schlafen und Wachen tut, steht in
`%APPDATA%\Volumix\fehler.log` — beim Einschlafen sieht niemand zu, und
danach ist der Bildschirm aus. Dass die Botschaft überhaupt ankommt, hängt
am Standby-Verfahren: Dieser Rechner kann **S3**, dort schickt Windows sie.
Auf Geräten mit „Modern Standby“ (S0) gibt es sie nicht.

Ein Zahlenfeld gibt es hier nicht mehr: Die Lautstärke steht in der
Kopfzeile, dort ist sie jederzeit sichtbar und anklickbar. Zweimal dasselbe
an zwei Stellen heißt nur, dass man beide gleich halten muss.

Dazwischen wird nichts angefasst. Wer die Box selbst verstellt oder
ausschaltet, behält das, bis einer der Anlässe eintritt. Die drei Zeiten
stehen oben in `volumix\boxen.py`: `RUHE` (5 min, ab wann ein Tastendruck als
Wiederkommen zählt), `AUS_NACH` (15 min) und `STILL` (60 s Ruhe im Ton).

### Wie das technisch läuft

Gesprochen wird UPnP, das die Boxen ohnehin können:

| Zweck | Aufruf |
|---|---|
| Lautstärke lesen und setzen | `RenderingControl`: `GetVolume` / `SetVolume`, 0–100 |
| An und aus | `AVTransport`: `LeaveStandby` / `EnterManualStandby` |
| Ist sie an? | Webdienst auf Port 47365: `getZones` → `powerState` |
| Wo sitzt sie? | Webdienst: `listDevices` |

Die Adresse der Box wird gemerkt (`boxen_host`). Antwortet sie nicht, wird
sie erst fünfmal einzeln erneut versucht (`GEDULD`) — eine Box, die gerade
schweigt, ist meist dieselbe Box an derselben Stelle. Erst danach wird das
eigene /24-Netz abgesucht, und schlägt auch das fehl, verdoppelt sich der
Abstand bis zum nächsten Versuch bis auf zehn Minuten. Ein Durchgang klopft
an 254 Adressen; das soll niemand merken, der gar keine solche Box hat —
und schon gar nicht im Minutentakt nach jedem Aufwachen.

Der Port des Renderers wechselt beim Neustart der Box, deshalb wird er jedes
Mal über `listDevices` aufgelöst.

Drei Messwerte erklären den Aufbau (Stereo M über LAN, Median):

| Vorgang | Dauer |
|---|---|
| `GetVolume` | 5,6 ms |
| `SetVolume` auf denselben Wert | 17 ms |
| `SetVolume` auf einen anderen Wert | 86 ms |

Die 86 ms sind unabhängig von der Sprungweite — zehn Schritte kosten so
viel wie einer. Deshalb wird **vor jedem Schreiben gelesen**: Steht der Wert
schon richtig, ist der Durchgang nach 5 ms vorbei statt nach 86.
`EnterManualStandby` und `LeaveStandby` werden in unter 50 ms beantwortet,
der neue `powerState` steht rund zwei Sekunden später im Netz. Im Standby
bleibt die Box erreichbar — sonst ließe sie sich von hier aus nicht wecken.

Ob gerade Ton läuft, wird am Standardgerät von Windows gemessen
(`IAudioMeterInformation`), nicht an den einzelnen Sitzungen: ein Aufruf
statt einer Runde durch alle Programme. Lässt sich die Frage nicht
beantworten, gilt „es läuft etwas" — im Zweifel gehen die Boxen lieber
nicht aus.

Das Ganze läuft in einem eigenen Thread. Eine Box, die nicht antwortet,
lässt einen Aufruf in die Zeitgrenze laufen — im Oberflächen-Thread wäre das
ein stehendes Fenster.

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
- **Lautstärke-Einblendung anzeigen**, dazu **Größe**, **Position** und
  **Transparenz**. Jede Änderung wird sofort als Vorschau eingeblendet. Ist
  die Einblendung aus, sind die vier Regler ausgegraut – sie hätten dann
  nichts zu tun.
- **Transparenz** öffnet den eigenen Grund der Einblendung, durch den der
  Bildschirm dahinter scheint. Ganz durchsichtig gibt es nicht: Ohne Grund
  fällt sie über hellem Bild in sich zusammen (gemessen Alpha 13 von 255),
  deshalb bleibt am Anschlag ein Rest von 44 % stehen — dort misst der Text
  über weißem Untergrund noch 3,15:1. Ab Werk steht der Regler auf 50 %,
  das ergibt Alpha 189 von 255 und 8,3:1.

  Das Coverbild trägt die Einblendung unabhängig davon mit: Es liegt in
  ihrem Grund, mit demselben Anteil wie unter einer Karte im Fenster
  (0,82 × 0,22 = 18 %, `OSD_COVER`). Auf 0 % Transparenz sieht sie damit aus
  wie ein Stück der App. Mit der Transparenz wird es blasser — wer die
  Einblendung durchsichtig stellt, will den Bildschirm dahinter sehen und
  nicht ein zweites Bild darüber.
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
| `tests\schirm.py` | schiebt die Testfenster auf den zweiten Bildschirm |
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
| `volumix\boxen.py` | Lautsprecher im Netz (Raumfeld) |
| `volumix\energie.py` | Schlafen und Aufwachen des Rechners |
| `volumix\titel.py` | laufender Titel und sein Coverbild |

Einstellungen liegen in `%APPDATA%\Volumix\config.json`,
der Autostart-Eintrag unter `HKCU\...\CurrentVersion\Run\Volumix`.

**Benötigt** (bereits installiert): Python 3.13 mit `PySide6`, `pycaw`,
`comtypes`, `pynput`, `Pillow` — und für das Coverbild `winrt-Windows.Media.Control`,
`winrt-Windows.Storage.Streams`, `winrt-Windows.Foundation`,
`winrt-Windows.Foundation.Collections`, `winrt-Windows.System`.

## Beenden

Rechtsklick auf das Tray-Symbol → **Beenden**.
(Das Schließen des Fensters minimiert nur in den Infobereich.)
