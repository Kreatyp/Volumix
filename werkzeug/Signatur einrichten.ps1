# Volumix signieren, damit Windows die Datei einem Herausgeber zuordnen kann.
#
# Warum ueberhaupt: Eine unsignierte, mit PyInstaller gepackte .exe hat kein
# Merkmal, an dem Windows sie wiedererkennt. Aendert sie sich bei jedem Bau,
# ist sie fuer den Virenscanner jedes Mal eine voellig neue, unbekannte
# Datei - und die Heuristik entscheidet neu. Mit einer Signatur bleibt der
# Herausgeber gleich, auch wenn sich der Inhalt aendert.
#
# Was dieses Skript NICHT kann: einem selbst ausgestellten Zertifikat das
# Vertrauen des Systems verschaffen. Dafuer muss es in den Speicher der
# vertrauenswuerdigen Stammzertifizierungsstellen - eine Entscheidung ueber
# die Sicherheit dieses Rechners, die niemand anderes fuer dich treffen
# sollte. Das Skript fragt dich an der Stelle.
#
# Aufruf (als Administrator):
#   powershell -ExecutionPolicy Bypass -File "werkzeug\Signatur einrichten.ps1"

$ErrorActionPreference = "Stop"
$Name = "Volumix (Luis Wuttig)"
$Exe = "F:\Dokumente\Claude\Volumix\programm\Volumix\Volumix.exe"

Write-Host "== Volumix signieren ==" -ForegroundColor Cyan

# 1) Zertifikat suchen oder anlegen
$zert = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq "CN=$Name" -and $_.NotAfter -gt (Get-Date) } |
        Select-Object -First 1

if ($zert) {
    Write-Host "Zertifikat vorhanden, gueltig bis $($zert.NotAfter.ToString('dd.MM.yyyy'))"
} else {
    Write-Host "Lege ein neues Zertifikat an (10 Jahre gueltig) ..."
    $zert = New-SelfSignedCertificate `
        -Subject "CN=$Name" `
        -Type CodeSigningCert `
        -KeyUsage DigitalSignature `
        -KeyLength 2048 `
        -KeyAlgorithm RSA `
        -HashAlgorithm SHA256 `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(10)
    Write-Host "angelegt: $($zert.Thumbprint)"
}

# 2) Vertrauen - nur auf Nachfrage
$vertraut = Get-ChildItem Cert:\CurrentUser\Root |
            Where-Object { $_.Thumbprint -eq $zert.Thumbprint }
if (-not $vertraut) {
    Write-Host ""
    Write-Host "Das Zertifikat ist selbst ausgestellt. Damit Windows der" -ForegroundColor Yellow
    Write-Host "Signatur glaubt, muss es unter deine vertrauenswuerdigen" -ForegroundColor Yellow
    Write-Host "Stammzertifizierungsstellen. Das heisst: Alles, was mit" -ForegroundColor Yellow
    Write-Host "diesem Zertifikat signiert ist, gilt dann als vertrauens-" -ForegroundColor Yellow
    Write-Host "wuerdig - achte also darauf, wo der private Schluessel liegt." -ForegroundColor Yellow
    Write-Host ""
    $antwort = Read-Host "Jetzt eintragen? (ja/nein)"
    if ($antwort -eq "ja") {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
        $store.Open("ReadWrite")
        $store.Add($zert)
        $store.Close()
        Write-Host "eingetragen." -ForegroundColor Green
    } else {
        Write-Host "uebersprungen - die Signatur bleibt vorhanden, gilt aber als nicht geprueft."
    }
} else {
    Write-Host "Zertifikat ist bereits als vertrauenswuerdig eingetragen."
}

# 3) Signieren
if (-not (Test-Path $Exe)) {
    Write-Host "Die .exe fehlt - erst bauen: python build_exe.py" -ForegroundColor Red
    exit 1
}
$ergebnis = Set-AuthenticodeSignature -FilePath $Exe -Certificate $zert `
            -HashAlgorithm SHA256 `
            -TimestampServer "http://timestamp.digicert.com"
Write-Host ""
Write-Host "Signatur: $($ergebnis.Status) - $($ergebnis.StatusMessage)"
Write-Host "Herausgeber: $($ergebnis.SignerCertificate.Subject)"
