"""
Audio Engine Backend
--------------------
Author: Michael
Version: 3.5

Supported Formats: .mp3, .wav, .m4a
Features: 
- Native playback for .mp3 and .wav
- Auto-conversion for .m4a
- Sequential tracking via .last_played.txt
"""

import os
import random
import time
import pygame
from pydub import AudioSegment

# Initialize mixer with standard frequency to reduce .wav playback errors
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def play_audio(file_path):
    """
    Handles native playback for mp3/wav and conversion for others.
    """
    try:
        ext = file_path.lower()
        
        # If it's not a standard format pygame likes, convert it
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
        print(f"Engine Error playing {os.path.basename(file_path)}: {e}")

def process_directory(path, mode="Random"):
    """
    Finds the next file in the folder based on mode and plays it.
    """
    valid_exts = ('.mp3', '.wav', '.m4a')
    files = sorted([f for f in os.listdir(path) if f.lower().endswith(valid_exts)])
    
    if not files:
        print(f"No audio files found in: {path}")
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
            
        # Update the tracker for next time
        with open(tracker_path, 'w', encoding='utf-8') as f:
            f.write(chosen_file)
    else:
        # Random mode
        chosen_file = random.choice(files)
    
    full_path = os.path.join(path, chosen_file)
    play_audio(full_path)
    return chosen_file

def run_external_script(script_path):
    try:
        # Simple execution for your automation scripts
        os.system(f"python \"{script_path}\"")
    except Exception as e:
        print(f"Script Error: {e}")

def wait_action(seconds):
    time.sleep(seconds)
