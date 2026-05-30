"""
Entry point for Routine Orchestrator.

Checks whether the venv is valid for this machine. If not (e.g. venv was built on a
different machine and synced via Google Drive), rebuilds it and relaunches. Passes all
CLI arguments through so Alexa voice triggers (python bootstrap.py RoutineName) work
unchanged.
"""

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import os
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).parent
    venv_path = project_root / "venv"
    requirements_path = project_root / "requirements.txt"
    python_version_file = project_root / ".python-version"
    main_script = project_root / "Orchestrator_main_gui.py"

    ecosystem_core = os.environ.get("ECOSYSTEM_CORE_PATH", "")
    if ecosystem_core and ecosystem_core not in sys.path:
        sys.path.insert(0, ecosystem_core)

    try:
        from shared_utils.venv_bootstrap import (
            check_venv_valid,
            rebuild_with_status_window,
            relaunch_with_venv,
        )
    except ImportError as exc:
        print(f"ERROR: Could not import venv_bootstrap from ecosystem-core: {exc}")
        print("Make sure ECOSYSTEM_CORE_PATH environment variable is set correctly.")
        sys.exit(1)

    check_result = check_venv_valid(venv_path, python_version_file)

    if check_result["status"] == "error":
        print(f"ERROR checking venv: {check_result['error_message']}")
        sys.exit(1)

    if not check_result["data"]["valid"]:
        reason = check_result["data"]["reason"]
        print(f"Venv needs rebuild: {reason}")

        rebuild_result = rebuild_with_status_window(
            venv_path,
            requirements_path,
            "We need to update the venv/ directory because we are on a different "
            "machine ...please wait",
        )

        if rebuild_result["status"] != "success":
            print(f"ERROR: Venv rebuild failed: {rebuild_result['error_message']}")
            sys.exit(1)

    relaunch_result = relaunch_with_venv(main_script, venv_path, sys.argv[1:])

    # Only reached on failure (relaunch_with_venv exits on success)
    if relaunch_result:
        print(f"ERROR: Failed to relaunch: {relaunch_result['error_message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
