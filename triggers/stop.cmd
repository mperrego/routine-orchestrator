@echo off
REM Stop the running Routine Orchestrator (audio + Cast).
REM Paths resolve relative to this .cmd, so the same file works on any machine.
set "PROJ=%~dp0.."
"%PROJ%\venv\Scripts\python.exe" "%PROJ%\Orchestrator_main_gui.py" --stop
