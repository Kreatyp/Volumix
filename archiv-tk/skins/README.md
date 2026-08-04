# Skins – eigene Farbe bauen

Ein Skin bestimmt die **Akzentfarbe** der App – alles Bunte: Regler, Häkchen,
Schalter, Lautstärkebalken, aktive Markierungen.

Die neutralen Töne (Hintergrund, Karten, Text) kommen **nicht** vom Skin,
sondern vom **Modus**: Dunkel oder Hell. Beides ist frei kombinierbar –
z. B. „Mint + Hell“ oder „Bernstein + Dunkel“.

Umschalten in der App:
- **Modus**: Sonne/Mond-Symbol oben rechts (oder Einstellungen → DESIGN)
- **Farbe**: Einstellungen → DESIGN → Farbe

Beides wirkt **sofort**, ohne Neustart und ohne dass sich das Fenster neu aufbaut.

---

## Eigenen Skin anlegen

Neuen Ordner hier drin anlegen mit einer `theme.json`. Das Minimum:

```json
{
  "name": "Türkis",

  "accent":       { "dark": "#22D3EE", "light": "#0891B2" },
  "accent_hover": { "dark": "#3EDCF5", "light": "#0E7490" }
}
```

Fertig – der Skin erscheint sofort in den Einstellungen unter seinem `name`.

| Schlüssel      | Bedeutung |
|----------------|-----------|
| `name`         | Anzeigename in der App |
| `accent`       | die Hauptfarbe |
| `accent_hover` | etwas hellere/dunklere Variante beim Drüberfahren |
| `red`          | Warnfarbe (optional) |

Jede Farbe kann entweder ein fester Wert (`"#22D3EE"`) sein oder je Modus
unterschiedlich: `{ "dark": "...", "light": "..." }`.

> Tipp: Im dunklen Modus wirken kräftige, leuchtende Farben gut; im hellen
> Modus brauchst du eine etwas dunklere Variante, damit weiße Schrift auf der
> Farbe lesbar bleibt.

Mitgeliefert: `default` (Violett), `nord` (Nordblau), `mint`, `amber`
(Bernstein), `rose`.

---

## Optional: Maße und Schrift

Ein Skin darf zusätzlich Größen und Schrift festlegen. Weggelassene Werte
behalten den Standard. Alle Angaben gelten bei 100 % Skalierung – die App
rechnet sie automatisch auf deine Bildschirm-DPI hoch.

```json
{
  "name": "Kompakt",
  "accent": { "dark": "#7C5CFF", "light": "#6C4CF5" },
  "metrics": { "window_h": 620, "card_radius": 10, "row_icon": 26 },
  "fonts":   { "size_scale": 0.95 }
}
```

| metrics          | Bedeutung |
|------------------|-----------|
| `window_w/h`     | Fenstergröße |
| `card_radius`    | Eckenradius der Panels |
| `button_radius`  | Eckenradius der Knöpfe |
| `toggle_w/h`     | Größe der Schalter (Einstellungen) |
| `check_size`     | Größe der Auswahl-Kästchen im Mixer |
| `slider_track`   | Dicke der Regler-Schiene |
| `slider_knob`    | Durchmesser des Regler-Knopfs |
| `row_icon`       | Größe der App-Symbole im Mixer |
| `row_radius`     | Eckenradius der hervorgehobenen Zeile |
| `osd_w/h`        | Größe der Einblendung |
| `osd_radius`     | Eckenradius der Einblendung |
| `osd_icon`       | Größe der Symbole in der Einblendung |
| `osd_font_name`  | Schriftgröße des App-Namens in der Einblendung |
| `osd_font_pct`   | Schriftgröße der Prozentzahl in der Einblendung |

> Die Einblendung wird zusätzlich mit dem **Größe**-Regler aus den
> Einstellungen skaliert – steht der auf 60 %, wirkt auch die Schrift kleiner.

| fonts         | Bedeutung |
|---------------|-----------|
| `family`      | Schriftart (muss in Windows installiert sein) |
| `family_semi` | halbfette Variante für Überschriften |
| `size_scale`  | Schriftgrößen-Faktor, z. B. `1.15` = 15 % größer |

### Neutrale Töne überschreiben (für Fortgeschrittene)

Wer wirklich die Graustufen ändern will, kann `colors` (dunkel) bzw.
`colors_light` (hell) setzen – erlaubt sind `bg`, `card`, `card2`, `stroke`,
`fg`, `muted`, `knob`, `off`. Nur einzelne Werte reichen:

```json
"colors": { "bg": "#000000", "card": "#0E0E12" }
```

---

## Optional: eigene Grafiken (images\)

Für Sonderfälle – Verläufe, Illustrationen – kannst du einzelne gezeichnete
Elemente durch **PNGs mit Transparenz** ersetzen:

```
skins\meinskin\images\check_on.png
```

| Datei              | Ersetzt | Empfohlene Größe (px) |
|--------------------|---------|------------------------|
| `check_on.png`     | Kästchen angehakt | 192×192 |
| `check_off.png`    | Kästchen leer | 192×192 |
| `toggle_on.png`    | Schalter „an“ | 192×108 |
| `toggle_off.png`   | Schalter „aus“ | 192×108 |
| `slider_knob.png`  | Knopf des Schiebereglers | 152×152 |
| `gear.png`         | Zahnrad | 256×256 |
| `back.png`         | Zurück-Pfeil | 256×256 |
| `sun.png`          | Sonne (heller Modus) | 256×256 |
| `moon.png`         | Mond (dunkler Modus) | 256×256 |
| `osd_bg.png`       | Hintergrund der Einblendung | 1360×384 |
| `icon_master.png`  | Symbol „Windows (gesamt)“ | 256×256 |
| `icon_system.png`  | Symbol „Systemklänge“ | 256×256 |

**Wichtig:** Liefere die PNGs **größer** als die Anzeigegröße (Richtwert: 4×).
Herunterskalieren bleibt scharf, Hochskalieren wird unscharf.

Fehlt eine Datei, zeichnet die App das Element wie gewohnt selbst – du kannst
also einzelne Teile ersetzen und den Rest so lassen.

---

## Tipps

- Nach dem Bearbeiten einer `theme.json` einmal auf eine andere Farbe und
  zurück klicken – die Änderung wird sofort übernommen.
- Tippfehler im JSON (fehlendes Komma) → die App fällt still auf `default`
  zurück. Datei dann in einem Editor prüfen.
