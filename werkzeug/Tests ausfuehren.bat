@echo off
rem Fuehrt alle Tests aus. Dauert etwa eine Minute.
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=python.exe"
"%PY%" "%~dp0..\tests\alle_tests.py"
echo.
pause
