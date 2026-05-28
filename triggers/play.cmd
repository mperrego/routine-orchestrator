@echo off
REM Play a routine by name (matches a JSON file in Routines/, without the extension).
REM Usage:  play.cmd PlaySilvaMeditation
REM Routed through bootstrap.py so the venv self-heals on a new machine.
if "%~1"=="" (
    echo Usage: play.cmd ^<RoutineName^>
    exit /b 1
)
set "PROJ=%~dp0.."
"%PROJ%\venv\Scripts\python.exe" "%PROJ%\bootstrap.py" %1
