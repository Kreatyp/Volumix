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

## Schrift der Wortmarke

Der Schriftzug „VOLUMIX“ ist in **Ode to Idle Gaming** von
[Chequered Ink](https://chequered.ink) gesetzt. Deren Lizenz erlaubt die
Verwendung in Grafiken, nicht aber die Weitergabe der Schriftdatei selbst.

Deshalb liegt im Programm **nur ein fertiges Bild** (`volumix/fonts/wortmarke.png`),
keine Schriftdatei. Wer die Schrift selbst benutzen möchte, lädt sie bei
Chequered Ink herunter.

> Die Lizenz gilt ausdrücklich nur für **nicht-kommerzielle** Nutzung. Sollte
> Volumix jemals Geld kosten, muss die Wortmarke vorher auf eine andere
> Schrift wechseln oder eine kommerzielle Lizenz bekommen.

## Programmsymbole

Die Symbole von Chrome, Discord, Spotify und anderen Programmen holt Volumix
zur Laufzeit aus den jeweiligen Programmdateien auf deinem Rechner. Sie gehören
ihren Herstellern und werden nur zur Wiedererkennung angezeigt.
