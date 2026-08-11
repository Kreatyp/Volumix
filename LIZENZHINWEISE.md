# Lizenzhinweise

Volumix benutzt fremde Bausteine. Hier steht, welche das sind und unter
welchen Bedingungen sie stecken.

## Mitgeliefert im Programmpaket

| Baustein | Fassung | Lizenz |
|---|---|---|
| [Qt](https://www.qt.io) über [PySide6](https://doc.qt.io/qtforpython/) | 6.11.1 | LGPL v3 |
| [pynput](https://github.com/moses-palmer/pynput) | 1.8.2 | LGPL v3 |
| [pycaw](https://github.com/AndreMiras/pycaw) | 20251023 | MIT |
| [comtypes](https://github.com/enthought/comtypes) | 1.4.16 | MIT |
| [psutil](https://github.com/giampaolo/psutil) | 7.2.2 | BSD 3-Clause |

**Zur LGPL:** Qt und pynput liegen im Ordner `_internal` als einzelne Dateien,
nicht fest eingebaut. Wer will, kann sie durch eigene Fassungen derselben
Bibliotheken ersetzen — genau das verlangt die LGPL. Die vollständigen
Lizenztexte stehen unter
[gnu.org/licenses/lgpl-3.0](https://www.gnu.org/licenses/lgpl-3.0.html).

## Schrift der Oberfläche

Die gesamte Oberfläche ist in **Inter** gesetzt
([rsms](https://github.com/rsms/inter)). Sie steht unter der **SIL Open Font
License 1.1** — Weitergabe im Programmpaket ist ausdrücklich erlaubt, auch bei
kommerzieller Nutzung.

Die Schriftdatei liegt unter `volumix/fonts/Inter.ttf`, der vollständige
Lizenztext direkt daneben in `Inter-OFL.txt`.

> Die OFL verlangt lediglich, dass die Schrift nicht unter ihrem eigenen Namen
> verkauft wird und der Lizenztext mitwandert. Beides ist erfüllt.

## Klang

Der Ton am Anschlag (`volumix/toene/anschlag.wav`) ist gerechnet, nicht
aufgenommen: ein Sinus bei 880 Hz mit exponentiellem Abfall. Es steckt also
kein fremdes Material darin.

## Programmsymbole

Die Symbole von Chrome, Discord, Spotify und anderen Programmen holt Volumix
zur Laufzeit aus den jeweiligen Programmdateien auf deinem Rechner. Sie gehören
ihren Herstellern und werden nur zur Wiedererkennung angezeigt.
