@echo off
REM Play a routine by name (matches a JSON file in Routines/, without the extension).
REM Usage:  play.cmd PlaySilvaMeditation
REM Routed through bootstrap.py so the venv self-heals on a new machine.
REM Output goes to logs\trigger.log so voice-fired failures are debuggable.
if "%~1"=="" (
    echo Usage: play.cmd ^<RoutineName^>
    exit /b 1
)
set "PROJ=%~dp0.."
if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"
echo. >> "%PROJ%\logs\trigger.log"
echo [%date% %time%] --- play fired: %1 --- >> "%PROJ%\logs\trigger.log"
"%PROJ%\venv\Scripts\python.exe" "%PROJ%\bootstrap.py" %1 >> "%PROJ%\logs\trigger.log" 2>&1
