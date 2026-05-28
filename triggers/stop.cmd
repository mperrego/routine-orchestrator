@echo off
REM Stop the running Routine Orchestrator (audio + Cast).
REM Paths resolve relative to this .cmd, so the same file works on any machine.
REM Output goes to logs\trigger.log so voice-fired failures are debuggable.
set "PROJ=%~dp0.."
if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"
echo. >> "%PROJ%\logs\trigger.log"
echo [%date% %time%] --- stop fired --- >> "%PROJ%\logs\trigger.log"
"%PROJ%\venv\Scripts\python.exe" "%PROJ%\Orchestrator_main_gui.py" --stop >> "%PROJ%\logs\trigger.log" 2>&1
