"""
Author: Michael
Project: Routine Orchestrator
File: audio_engine.py
Version: 4.3
Date: 2026-03-14
"""

import os
import random
import time
import pygame
from pydub import AudioSegment

if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# --- THIS IS THE MISSING FUNCTION ---
def get_next_filename(item_data):
    """
    Predicts the next file to be played without playing it.
    Returns the (full_path, display_name).
    """
    path = item_data.get("path")
    if not os.path.exists(path):
        return None, "Path Not Found"

    if os.path.isfile(path):
        return path, os.path.basename(path)
    
    valid_exts = ('.mp3', '.wav', '.m4a')
    files = sorted([f for f in os.listdir(path) if f.lower().endswith(valid_exts)])
    if not files:
        return None, "No Files Found"

    tracker_path = os.path.join(path, ".last_played.txt")
    chosen_file = None
    
    if item_data.get("mode") == "Sequential":
        last_played = ""
        if os.path.exists(tracker_path):
            try:
                with open(tracker_path, 'r', encoding='utf-8') as f:
                    last_played = f.read().strip()
            except: pass
        
        if last_played in files:
            next_idx = (files.index(last_played) + 1) % len(files)
            chosen_file = files[next_idx]
        else:
            chosen_file = files[0]
            
        with open(tracker_path, 'w', encoding='utf-8') as f:
            f.write(chosen_file)
    else:
        chosen_file = random.choice(files)
        
    return os.path.join(path, chosen_file), chosen_file

def stop_audio():
    """Immediately halts the pygame mixer."""
    pygame.mixer.music.stop()

def play_audio(file_path):
    """Handles playback and monitors for interruptions."""
    try:
        # (Handling for non-standard formats...)
        ext = file_path.lower()
        if not (ext.endswith('.mp3') or ext.endswith('.wav')):
            audio = AudioSegment.from_file(file_path)
            temp_path = "temp_converted.mp3"
            audio.export(temp_path, format="mp3")
            file_path = temp_path
            
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Engine Error: {e}")

def run_external_script(script_path):
    try: os.system(f"python \"{script_path}\"")
    except Exception as e: print(f"Script Error: {e}")

def wait_action(seconds):
    time.sleep(seconds)

def is_playing():
    return pygame.mixer.music.get_busy()
