# Wenn Defender Volumix wegnimmt

Zweimal passiert, beide Male derselbe Fund: `Trojan:Win32/Bearfoos.A!ml`.
Das `!ml` am Ende heißt, dass kein Signaturtreffer vorlag, sondern ein
Lernmodell die Datei für verdächtig hielt. Es ist ein **Fehlalarm** – und
einer der bekanntesten überhaupt bei Programmen, die mit PyInstaller gepackt
sind.

## Warum ausgerechnet Volumix

Vier Merkmale trafen zusammen, jedes für sich harmlos:

| | |
|---|---|
| unsigniert | kein Herausgeber, den Windows wiedererkennen könnte |
| gepackt | eine PyInstaller-Datei entpackt sich beim Start selbst |
| ohne Angaben | kein Produktname, keine Beschreibung, keine Version |
| Registry-Autostart | `HKCU\…\CurrentVersion\Run` ist der Weg, über den sich Schadsoftware verankert |

Beim zweiten Mal stand der Run-Schlüssel ausdrücklich in der Fundmeldung,
neben der `.exe` und der Taskleisten-Verknüpfung. Der Klick auf „Mit Windows
starten" war der Auslöser.

## Was im Programm geändert wurde

* **Versionsangaben** stecken jetzt in der `.exe` – Produktname, Beschreibung,
  Herausgeber, Version, Copyright. Sichtbar unter *Eigenschaften → Details*.
* **Keine Kompression** mehr (`--noupx`). Ein Programm, das sich selbst
  entpackt, verhält sich wie etwas, das seinen Inhalt verbirgt.
* **Autostart ohne Registry**: Volumix legt eine Verknüpfung unter
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` an. Das leistet
  dasselbe, ist sichtbar und lässt sich von Hand entfernen. Ein alter
  Run-Eintrag wird beim Umschalten mit gelöscht.

Das nimmt der Heuristik drei von vier Anhaltspunkten. Eine Garantie ist es
nicht: Die `.exe` ändert sich bei jedem Bau, und das Modell entscheidet jedes
Mal neu.

## Was nur du selbst tun kannst

### 1. Signieren (`werkzeug\Signatur einrichten.ps1`)

Legt ein selbst ausgestelltes Zertifikat an und signiert die `.exe` damit.
Danach hat sie einen Herausgeber, der über alle Bauten hinweg gleich bleibt.

Damit Windows der Signatur glaubt, muss das Zertifikat unter die
vertrauenswürdigen Stammzertifizierungsstellen. Das ist eine Entscheidung
über die Sicherheit dieses Rechners – das Skript fragt dich, statt es
stillschweigend zu tun.

> Ein selbst ausgestelltes Zertifikat hilft **auf diesem Rechner**. Für andere
> Rechner bräuchte es ein gekauftes Zertifikat einer anerkannten Stelle
> (mehrere hundert Euro im Jahr).

### 2. Ordner ausnehmen (PowerShell als Administrator)

    Add-MpPreference -ExclusionPath "F:\Dokumente\Claude\Volumix"

Sicher wirksam, aber ernst gemeint: Defender schaut in diesem Ordner dann
nicht mehr hin. Vertretbar, solange dort nur eigener Quelltext liegt.

Prüfen, ob sie steht:

    (Get-MpPreference).ExclusionPath

### 3. Den Fehlalarm bei Microsoft melden

Der einzige Weg, die Erkennung wirklich abzustellen – auch für alle anderen,
die je eine PyInstaller-Datei bauen:

<https://www.microsoft.com/en-us/wdsi/filesubmission>

* *Submission type*: **Software developer**
* Datei: `programm\Volumix\Volumix.exe`
* Erkennungsname: `Trojan:Win32/Bearfoos.A!ml`
* Begründung: eigenes, mit PyInstaller gepacktes Python-Programm, kein
  Schadcode; Quelltext einsehbar unter <https://github.com/Kreatyp/Volumix>

Antwort kommt meist binnen ein bis zwei Tagen. Wird der Fehlalarm bestätigt,
verschwindet die Erkennung mit dem nächsten Signaturupdate.

## Wenn es schon passiert ist

Die Datei liegt in der Quarantäne und ist nicht verloren:

*Windows-Sicherheit → Viren- & Bedrohungsschutz → Schutzverlauf →* den
Eintrag aufklappen *→ Aktionen → Wiederherstellen*

Oder als Administrator:

    Restore-MpThreat -ThreatID 2147731250

Erst die Ausnahme setzen, dann wiederherstellen – sonst greift Defender
sofort wieder zu.
