# Selber anpassen

Eine Anleitung zum Schrauben an Volumix. Du brauchst nichts zu installieren,
Python 3.13 und PySide6 sind da.

---

## Die wichtigste Regel zuerst

Es gibt **zwei** Fassungen der App:

| | Was es ist |
|---|---|
| `volumix.pyw` + Ordner `volumix\` | Der **Quelltext**. Hier änderst du. |
| `programm\Volumix\Volumix.exe` | Das **fertige Paket**. Hier änderst du **nie**. |

Die `.exe` ist eine eingefrorene Kopie. Änderst du den Quelltext, merkt sie
davon nichts – bis du sie neu baust (siehe unten).

**Beim Ausprobieren startest du deshalb:**

```bash
"F:\Dokumente\Claude\Volumix\Volumix starten.bat"
```

Ändern → speichern → App beenden (Tray-Symbol → Beenden) → `.bat` nochmal
starten. Zwei Sekunden pro Runde.

> Es kann immer nur **eine** Instanz laufen. Läuft die `.exe` noch im
> Infobereich, musst du sie erst beenden.

---

## Wie der Quelltext aufgebaut ist

Anders als früher ist alles in Bausteine geteilt. Du musst also nicht mehr
4.000 Zeilen durchsuchen, sondern nur die passende Datei öffnen:

| Datei | Wofür |
|---|---|
| `volumix\theme.py` | **Farben und Aussehen** – hier fängst du an |
| `volumix\config.py` | Voreinstellungen, Autostart |
| `volumix\audio.py` | Windows-Audio: Pegel, Sitzungen, Spitzenwerte |
| `volumix\icons.py` | Symbole (als Vektoren) |
| `volumix\widgets.py` | Mixer-Zeile, Regler, Schalter, Pegelbalken |
| `volumix\window.py` | Hauptfenster, Einstellungen, Dialoge |
| `volumix\osd.py` | die Einblendung beim Regeln |
| `volumix\hooks.py` | Daumenrad und Lautstärke-Tasten |
| `volumix\sprache.py` | **alle sichtbaren Texte** – Deutsch und Englisch |

---

## Stufe 1: Aussehen – fast wie CSS

Das ganze Aussehen steckt in **einer** Funktion: `qss()` in
`volumix\theme.py`. Qt nennt das *Stylesheet*, die Schreibweise ist an CSS
angelehnt.

Beispiel – die Knöpfe runder und luftiger machen:

```css
QPushButton {
    background: {t.card2};
    border: none;
    border-radius: 9px;      /* größer = runder */
    padding: 7px 16px;       /* größer = mehr Luft */
    font-size: 12px;
}
```

Ein paar Dinge, die du dort direkt ändern kannst:

- **`border-radius`** – wie rund die Ecken sind (Karten: `#Karte`)
- **`font-size`** – Schriftgrößen, z. B. `#Prozent` für die Lautstärkezahl
- **`qlineargradient(...)`** – die Farbverläufe der Karten
- **`:hover`** – wie etwas aussieht, wenn der Zeiger darüber steht

**Eigene Akzentfarbe** hinzufügen: In `theme.py` steht oben die Liste
`PALETTE`. Eine Zeile ergänzen, fertig – der Punkt erscheint sofort in den
Einstellungen:

```python
("tuerkis", "Türkis", "#22D3EE", "#0891B2"),
#  Schlüssel, Anzeigename, für Dunkel, für Hell
```

Die neutralen Töne (Hintergrund, Karten, Text) stehen darunter in `DARK` und
`LIGHT`.

### Wenn du es plastisch magst

Im Nachbarordner `..\Volumix-Relief\` liegt ein Abzweig, bei dem die Oberfläche
Tiefe hat: vertiefte Reglerbahnen, gewölbte Knöpfe, Zeilen als erhabene
Kacheln. Dort ist das eine Einstellung unter *Design → Stil*. Falls du so etwas
hier einbauen willst, steht in jenem Ordner unter derselben Überschrift, aus
welchen Stellen es besteht.

---

## Stufe 2: Kleine Änderungen

### Wie schnell das Daumenrad regelt

`volumix\window.py`, suche nach `_schrittweite`:

```python
return 0.8 + (s - 10.0) / 90.0 * 3.4     # 0,8 .. 4,2 Punkte
```

Die `3.4` größer machen = bei 100 % wird es schneller.

### Höhe einer Mixer-Zeile

`volumix\widgets.py`, suche `setFixedHeight(54)` in `MixerRow`.

### Wie lange die Einblendung stehen bleibt

`volumix\osd.py`, suche `dauer=1100` – Millisekunden.

### Wann das Suchfeld erscheint

`volumix\window.py`, suche `> 7` – ab wie vielen sichtbaren Apps.

### Welche Programme ab Werk ausgeblendet sind

`volumix\config.py`, `DEFAULT_HIDDEN` – eine schlichte Liste.

### Eine Beschriftung ändern

Alle sichtbaren Texte stehen in `volumix\sprache.py`, je Eintrag ein Paar aus
Deutsch und Englisch:

```python
"apps_waehlen": ("Apps wählen", "Choose apps"),
```

Im Code steht dann nur noch `T("apps_waehlen")`. Eine weitere Sprache wäre ein
dritter Eintrag je Zeile plus ein Kürzel in `SPRACHEN`.

### Wie schnell das Mausrad über einer Zeile regelt

`volumix\widgets.py`, in `MixerRow.wheelEvent`: `rastungen * 4` – die `4` sind
Prozentpunkte pro Rastung.

---

## Tests

Nach einer Änderung:

```bash
"F:\Dokumente\Claude\Volumix\Tests ausfuehren.bat"
```

Acht Testreihen, etwa 15 Sekunden. Sie prüfen die Pegel-Umrechnung, die
Schalter, die Einblendung, die Richtungsumkehr, den Sprachwechsel und das
Mausrad. Dabei starten kurz Fenster und es erklingt ein leiser Testton – das
gehört dazu. Deine echten Einstellungen werden nicht angefasst; die Tests
benutzen eine eigene Ablage unter `tests\testcfg`.

### Ein neues Symbol

`volumix\icons.py`, das Wörterbuch `PFADE`. Die Symbole sind SVG-Pfade in
einem 24×24-Raster – dieselbe Sprache, die auch Webseiten benutzen. Fertige
Pfade findest du z. B. bei Lucide oder Feather Icons.

---

## Fallen, in die ich schon getappt bin

- **Die Fensterbreite** wird über `setMinimumWidth` + `setMaximumWidth` fest
  gehalten, nicht über eine Sperre. Andere Wege beißen sich auf Monitoren mit
  abweichender Skalierung.
- **Der Windows-Gesamtregler ist nicht linear**, App-Regler schon. 40 % sind
  nicht gleich 40 %. Verrechnen geht nur über Dezibel (`master_gain` in
  `audio.py`).
- **Erst leiser stellen, dann lauter** – sonst knallt es kurz. Deshalb das
  `_setzen_lassen()` zwischen den Schritten.
- **Audio läuft in einem eigenen Thread.** Von dort darf man Qt-Widgets
  *nicht* direkt anfassen – die Rückmeldungen gehen über Signale
  (`apps_bereit` und Geschwister in `window.py`) in den Oberflächen-Thread.
- **Rollbereiche brauchen `background: transparent`**, sonst liegt ein grauer
  Kasten über dem Kartenverlauf.

---

## Wenn du etwas kaputt machst

Die App startet dann nicht mehr. Um den Fehler zu **sehen**, starte sie
ausnahmsweise mit Konsolenfenster:

```bash
"C:\Users\Luis\AppData\Local\Programs\Python\Python313\python.exe" "F:\Dokumente\Claude\Volumix\volumix.pyw"
```

Nur prüfen, ob alle Dateien fehlerfrei sind:

```bash
"C:\Users\Luis\AppData\Local\Programs\Python\Python313\python.exe" -c "import py_compile,glob,os; os.chdir(r'F:\Dokumente\Claude\Volumix'); [py_compile.compile(f, doraise=True) for f in ['volumix.pyw']+glob.glob('volumix/*.py')]; print('OK')"
```

**Python ist einrückungsempfindlich.** Eingerückte Zeilen gehören zusammen –
verrutscht die Einrückung, ändert sich die Bedeutung. Immer Leerzeichen, keine
Tabs (VS Code macht das von allein richtig).

---

## Zurück auf Anfang

Bevor du etwas Größeres umbaust: **Kopie ziehen.**

```bash
xcopy /E /I /Y "F:\Dokumente\Claude\Volumix\volumix" "F:\Dokumente\Claude\Volumix\volumix.SICHERUNG"
```

Geht schief? Ordner zurückkopieren, fertig.

> Für richtiges Rückgängigmachen gibt es **Git** – ist auf dem Rechner schon
> installiert. Sag Bescheid, dann richte ich es ein.

Im Ordner `archiv-tk\` liegt außerdem die alte Tkinter-Fassung, komplett
lauffähig, falls du je vergleichen willst.

---

## Neue `.exe` bauen

1. App beenden (Tray-Symbol → **Beenden**).
2. Bauen:

```bash
"C:\Users\Luis\AppData\Local\Programs\Python\Python313\python.exe" "F:\Dokumente\Claude\Volumix\build_exe.py"
```

Dauert etwa eine Minute. Ergebnis: `programm\Volumix\Volumix.exe`.

> Es entsteht ein **Ordner**, keine Einzeldatei – Qt bringt viel mit, und als
> Einzeldatei müsste das bei jedem Start entpackt werden. Willst du trotzdem
> eine einzelne Datei: `python build_exe.py --onefile`.

---

## Und wenn du nicht weiterkommst

Beschreib mir, was du vorhast – ich zeig dir die Stelle. Auch „ich hab das
probiert und es kam dieser Fehler" ist völlig in Ordnung; die Fehlermeldung
mitschicken hilft am meisten.
