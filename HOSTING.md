# Seite und Download bei GitHub

Alles liegt in **einem** Repository: `github.com/Kreatyp/Volumix`.

| Was | Wo |
|---|---|
| Quelltext | im Repository |
| Webseite | Ordner `docs\` → wird von GitHub Pages ausgeliefert |
| Programmpaket | als Datei an einem **Release** |

Das ZIP liegt bewusst **nicht** im Repository. Es entsteht aus dem Quelltext
neu, und 27 MB in der Versionsgeschichte wären Ballast, der nie wieder
verschwindet. Deshalb steht `/paket/` in der `.gitignore`.

---

## Eine neue Fassung veröffentlichen

```bash
python build_exe.py
```

Dann das Paket packen (PowerShell, im Projektordner):

```bash
Compress-Archive -Path programm\Volumix -DestinationPath paket\Volumix-JJJJ-MM-TT.zip -CompressionLevel Optimal
```

Danach auf GitHub unter **Releases** → *Draft a new release* das ZIP anhängen
und veröffentlichen. Zum Schluss in `docs\index.html` die Adresse hinter
`ADRESSE DER PROGRAMMDATEI` auf die neue Datei zeigen lassen, dazu die
Größenangabe darunter — und alles einchecken:

```bash
git add -A
git commit -m "Neue Fassung"
git push
```

Die Seite aktualisiert sich danach von allein, meist innerhalb einer Minute.

---

## Wenn sich das Aussehen ändert

Die Bilder in `docs\bilder\` zeigen den Mixer in zwölf Farben, hell und
dunkel — aufgenommen mit englischer Oberfläche. Ändert sich das Design, müssen
sie neu aufgenommen werden, sonst zeigt die Seite einen alten Stand.

---

## Falls die Seite doch zu Cloudflare soll

Der Ordner `docs\` ist eigenständig und lässt sich unverändert dorthin
hochladen ([dash.cloudflare.com](https://dash.cloudflare.com) → *Workers &
Pages* → *Create* → *Pages* → *Upload assets*). Nur das Programmpaket darf
nicht mit: Cloudflare Pages nimmt höchstens 25 MiB pro Datei, das ZIP hat 27.
Das bliebe also weiterhin bei den GitHub-Releases.
