"""
Author: Michael
Project: Routine Orchestrator
File: audio_engine.py
Version: 5.1
Date: 2026-03-14
Description: Stable build using gTTS for announcements and pygame for playback.
"""

import os
import random
import time
import pygame
from pydub import AudioSegment
from gtts import gTTS

# --- INITIALIZATION ---
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def get_next_filename(item_data):
    """Predicts the next file and updates the .last_played.txt bookmark for ALL audio actions."""
    path = item_data.get("path")
    if not path or not os.path.exists(path):
        return None, "Path Not Found"

    # --- 1. DEFINE DIRECTORY AND TRACKER ---
    if os.path.isfile(path):
        # If it's a file, the 'folder' is the directory it sits in
        folder_path = os.path.dirname(path)
        chosen_file = os.path.basename(path)
    else:
        # If it's a folder, the 'folder' is the path itself
        folder_path = path
        chosen_file = None

    tracker_path = os.path.join(folder_path, ".last_played.txt")
    valid_exts = ('.mp3', '.wav', '.m4a')
    
    # Get alphabetical list for the directory
    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts)])
    if not files:
        return None, "No Files Found"

    # --- 2. SELECTION LOGIC (Only for Folders) ---
    if not chosen_file:
        if item_data.get("mode") == "Sequential":
            last_played = ""
            if os.path.exists(tracker_path):
                try:
                    with open(tracker_path, 'r', encoding='utf-8') as f:
                        last_played = f.read().strip()
                except:
                    pass
            
            idx = (files.index(last_played) + 1) % len(files) if last_played in files else 0
            chosen_file = files[idx]
        else:
            # Random Mode
            import random
            chosen_file = random.choice(files)
        
    # --- 3. UNIVERSAL BOOKMARK UPDATE ---
    # This now runs for single files AND folders
    try:
        with open(tracker_path, 'w', encoding='utf-8') as f:
            f.write(chosen_file)
    except Exception as e:
        print(f"Error updating tracker in {folder_path}: {e}")
        
    return os.path.join(folder_path, chosen_file), chosen_file
def play_audio(file_path):
    """Plays audio via pygame. Handles conversion for non-standard formats."""
    try:
        ext = file_path.lower()
        if not (ext.endswith('.mp3') or ext.endswith('.wav')):
            audio = AudioSegment.from_file(file_path)
            temp_path = "temp_converted.mp3"
            audio.export(temp_path, format="mp3")
            file_path = temp_path
            
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Playback Error: {e}")

def stop_audio():
    """Immediately stops all audio playback."""
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

def speak(text):
    """Generates a Google TTS MP3 and plays it through the audio mixer."""
    if not text:
        return
    temp_file = "temp_announcement.mp3"
    try:
        # Clear the mixer and generate speech
        pygame.mixer.music.unload() 
        tts = gTTS(text=text, lang='en')
        tts.save(temp_file)
        
        # Play the speech
        play_audio(temp_file)
        
        # Block until speaking is done
        while is_playing():
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Speech Error: {e}")
    finally:
        # Give a moment to release the file, then try to remove the temp file
        try:
            pygame.mixer.music.unload()
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass

def is_playing():
    """Checks if the pygame mixer is currently busy."""
    return pygame.mixer.music.get_busy()

def wait_action(seconds):
    """A standard blocking pause."""
    time.sleep(seconds)

def run_external_script(script_path):
    """Executes external Python scripts and returns True if successful."""
    import subprocess
    import sys
    
    script_dir = os.path.dirname(os.path.abspath(script_path))
    
    try:
        # sys.executable is the key—it points to the python.exe currently running
        subprocess.run(
            [sys.executable, script_path], 
            cwd=script_dir, 
            check=True, 
            capture_output=True, 
            text=True
        )
        return True
    except Exception as e:
        print(f"Script Error: {e}")
        return False
