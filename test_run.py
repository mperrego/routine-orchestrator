import os
import sys

# --- THE PATH FIX ---
if sys.platform == 'win32':
    site_packages = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages")
    paths = [
        os.path.join(site_packages, "win32"),
        os.path.join(site_packages, "win32", "lib"),
        os.path.join(site_packages, "pywin32_system32")
    ]
    for p in paths:
        if p not in sys.path:
            sys.path.append(p)
    try:
        os.add_dll_directory(os.path.join(site_packages, "pywin32_system32"))
    except:
        pass

# --- THE ACTUAL TEST ---
import pyttsx3
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print("\n--- Available Voices ---")
    for index, voice in enumerate(voices):
        print(f"Index: {index} | Name: {voice.name}")
    print("------------------------\n")
except Exception as e:
    print(f"Still failing because: {e}")
