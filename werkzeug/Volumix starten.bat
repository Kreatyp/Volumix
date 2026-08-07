@echo off
rem Startet Volumix aus dem Quelltext - zum Ausprobieren von Aenderungen.
rem Die fertige App startet die Verknuepfung im Hauptordner.
set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"
start "" "%PYW%" "%~dp0..\volumix.pyw"
