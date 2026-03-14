"""
Author: Michael
Project: Routine Orchestrator
File: audio_engine.py
Description: Core audio playback logic handling MP3/WAV/M4A files, 
             sequential tracking, and external script execution.
Version: 3.5
Date: 2026-03-14
"""

import os
import random
import time
import pygame
from pydub import AudioSegment

# Initialize the mixer with a locked frequency to prevent sample rate errors
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def play_audio(file_path):
    """
    Handles native playback for mp3/wav and auto-conversion for other formats.
    """
    try:
        ext = file_path.lower()
        # Non-standard formats are exported to a temporary MP3 for stability
        if not (ext.endswith('.mp3') or ext.endswith('.wav')):
            audio = AudioSegment.from_file(file_path)
            temp_path = "temp_converted.mp3"
            audio.export(temp_path, format="mp3")
            file_path = temp_path
            
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Keep the thread alive while audio is playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Engine Error: {e}")

def process_directory(path, mode="Random"):
    """
    Selects and plays a file from a directory based on the chosen mode.
    Maintains a .last_played.txt file for Sequential logic.
    """
    valid_exts = ('.mp3', '.wav', '.m4a')
    files = sorted([f for f in os.listdir(path) if f.lower().endswith(valid_exts)])
    
    if not files:
        return "No Files Found"
        
    tracker_path = os.path.join(path, ".last_played.txt")
    chosen_file = None
    
    if mode == "Sequential":
        last_played = ""
        if os.path.exists(tracker_path):
            try:
                with open(tracker_path, 'r', encoding='utf-8') as f:
                    last_played = f.read().strip()
            except:
                pass
        
        if last_played in files:
            next_idx = (files.index(last_played) + 1) % len(files)
            chosen_file = files[next_idx]
        else:
            chosen_file = files[0]
            
        with open(tracker_path, 'w', encoding='utf-8') as f:
            f.write(chosen_file)
    else:
        chosen_file = random.choice(files)
        
    play_audio(os.path.join(path, chosen_file))
    return chosen_file

def run_external_script(script_path):
    """Executes a secondary Python script as part of the routine."""
    try:
        os.system(f"python \"{script_path}\"")
    except Exception as e:
        print(f"Script Error: {e}")

def wait_action(seconds):
    """Pauses execution for a specified duration."""
    time.sleep(seconds)
