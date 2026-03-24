"""
Author: Michael
Project: Routine Orchestrator
File: audio_engine.py
Version: 7.0
Date: 2026-03-23
Description: Audio engine with Bluetooth device selection and WiFi Cast playback/volume control.
"""

import os
import random
import time
import socket
import threading
import http.server
import functools
import pygame
from pydub import AudioSegment
from gtts import gTTS

# --- INITIALIZATION ---
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Track which output device the mixer is currently using (None = system default)
_current_device = None

# Cast device cache (populated on first discovery to avoid repeated 5s scans)
_cast_cache = None

# Local HTTP server for serving audio files to Cast devices
_http_server = None
_http_thread = None

# Active Cast connection for stopping/checking playback
_active_cast = None
_active_browser = None

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
def get_output_devices(saved_speakers=None):
    """Returns Bluetooth/system devices + Cast devices in one list."""
    try:
        from pygame._sdl2.audio import get_audio_device_names
        devices = list(get_audio_device_names(False))
    except Exception as e:
        print(f"Device enumeration error: {e}")
        devices = []

    # Add Cast devices with [Cast] prefix
    cast_names = discover_cast_devices()
    for name in cast_names:
        cast_label = f"[Cast] {name}"
        if cast_label not in devices:
            devices.append(cast_label)

    # Merge saved Cast speakers that aren't already in the live list
    if saved_speakers:
        for speaker in saved_speakers:
            if speaker.startswith("[Cast]") and speaker not in devices:
                devices.append(speaker)

    return devices

# --- CAST FUNCTIONS ---

def discover_cast_devices(force_refresh=False):
    """Scans the network for Cast devices. Returns list of friendly names. Cached after first scan."""
    global _cast_cache
    if _cast_cache is not None and not force_refresh:
        return _cast_cache

    try:
        import pychromecast
        print("Scanning for Cast devices...")
        services, browser = pychromecast.discovery.discover_chromecasts(timeout=5)
        pychromecast.discovery.stop_discovery(browser)
        _cast_cache = [s.friendly_name for s in services]
        print(f"Found Cast devices: {_cast_cache}")
        return _cast_cache
    except Exception as e:
        print(f"Cast discovery error: {e}")
        _cast_cache = []
        return []

def set_cast_volume(cast_name, volume_percent):
    """Sets volume on a Cast device. volume_percent is 0-100."""
    try:
        import pychromecast
        casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[cast_name])
        if casts:
            cast = casts[0]
            cast.wait()
            cast.set_volume(volume_percent / 100.0)
            print(f"Cast volume set: {cast_name} → {volume_percent}%")
            cast.disconnect()
        else:
            print(f"Cast device not found: {cast_name}")
        pychromecast.discovery.stop_discovery(browser)
    except Exception as e:
        print(f"Cast volume error: {e}")

def _get_local_ip():
    """Gets this machine's WiFi IP address for Cast devices to reach."""
    try:
        # Use ifaddr (installed with pychromecast/zeroconf) to find the real WiFi adapter
        import ifaddr
        for adapter in ifaddr.get_adapters():
            for ip_info in adapter.ips:
                # Look for IPv4 addresses on common local network ranges
                if isinstance(ip_info.ip, str) and ip_info.ip.startswith(("192.168.", "10.0.")):
                    print(f"Using network IP: {ip_info.ip} ({adapter.nice_name})")
                    return ip_info.ip
    except Exception as e:
        print(f"ifaddr lookup failed: {e}")

    # Fallback to socket method
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def _start_http_server(directory, port=8089):
    """Starts a local HTTP server to serve audio files to Cast devices."""
    global _http_server, _http_thread

    # Stop existing server if running
    _stop_http_server()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    _http_server = http.server.HTTPServer(("", port), handler)
    _http_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
    _http_thread.start()
    print(f"HTTP server started on port {port} serving {directory}")

def _stop_http_server():
    """Stops the local HTTP server."""
    global _http_server, _http_thread
    if _http_server:
        _http_server.shutdown()
        _http_server = None
        _http_thread = None

def play_audio_cast(file_path, cast_name, volume_percent=0):
    """Casts an audio file to a Cast device via local HTTP server. Sets volume on same connection."""
    global _active_cast, _active_browser
    try:
        import pychromecast

        # Convert non-MP3/WAV files first
        ext = file_path.lower()
        if not (ext.endswith('.mp3') or ext.endswith('.wav')):
            audio = AudioSegment.from_file(file_path)
            temp_path = os.path.join(os.path.dirname(file_path), "temp_converted.mp3")
            audio.export(temp_path, format="mp3")
            file_path = temp_path

        # Start HTTP server in the file's directory
        file_dir = os.path.dirname(os.path.abspath(file_path))
        file_name = os.path.basename(file_path)
        _start_http_server(file_dir)

        # Build the URL the Cast device will fetch
        local_ip = _get_local_ip()
        # URL-encode spaces and special chars in filename
        from urllib.parse import quote
        url = f"http://{local_ip}:8089/{quote(file_name)}"

        # Connect to the Cast device
        casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[cast_name])
        if not casts:
            print(f"Cast device not found: {cast_name}")
            pychromecast.discovery.stop_discovery(browser)
            return False

        _active_cast = casts[0]
        _active_browser = browser
        _active_cast.wait()

        # Set volume on this connection before playing
        if volume_percent > 0:
            _active_cast.set_volume(volume_percent / 100.0)
            print(f"Cast volume set: {cast_name} → {volume_percent}%")
            time.sleep(0.5)  # Give device time to apply volume

        # Determine content type
        content_type = "audio/mpeg" if file_path.lower().endswith(".mp3") else "audio/wav"

        # Cast the audio
        mc = _active_cast.media_controller
        mc.play_media(url, content_type)
        mc.block_until_active(timeout=10)
        # Wait for playback to actually start so is_cast_playing() works
        time.sleep(2)
        print(f"Casting: {file_name} → {cast_name}")
        return True

    except Exception as e:
        print(f"Cast playback error: {e}")
        return False

def stop_cast():
    """Stops Cast playback and cleans up."""
    global _active_cast, _active_browser
    try:
        if _active_cast:
            _active_cast.media_controller.stop()
            time.sleep(1)  # Brief wait instead of blocking indefinitely
            _active_cast.disconnect(timeout=3)
    except Exception as e:
        print(f"Cast stop: {e}")
    try:
        if _active_browser:
            import pychromecast
            pychromecast.discovery.stop_discovery(_active_browser)
    except:
        pass
    _active_cast = None
    _active_browser = None
    _stop_http_server()

def is_cast_playing():
    """Checks if Cast media is currently playing or buffering."""
    try:
        if _active_cast:
            mc = _active_cast.media_controller
            mc.update_status()
            state = mc.status.player_state
            return state in ("PLAYING", "BUFFERING", "UNKNOWN")
    except:
        pass
    return False

def switch_output_device(device_name):
    """Quits the mixer and reinitializes it with the specified output device."""
    global _current_device
    if device_name == _current_device:
        return True  # Already on this device

    try:
        pygame.mixer.quit()
        if device_name:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512,
                              devicename=device_name)
        else:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        _current_device = device_name
        print(f"Audio output: {device_name or 'System Default'}")
        return True
    except Exception as e:
        print(f"Device switch error ({device_name}): {e}")
        # Fall back to system default
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            _current_device = None
            print("Fell back to system default audio device")
        except:
            pass
        return False

def reset_to_default_device():
    """Switches the mixer back to the system default output device."""
    switch_output_device(None)

def play_audio(file_path, device=None):
    """Plays audio via pygame. Handles conversion and optional device routing."""
    try:
        # Switch output device if needed
        if device != _current_device:
            switch_output_device(device)

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

def speak(text, device=None, volume=0):
    """Generates a Google TTS MP3 and plays it on the specified device."""
    if not text:
        return
    # Use absolute path so the HTTP server can find it
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_file = os.path.join(base_dir, "temp_announcement.mp3")

    try:
        tts = gTTS(text=text, lang='en')
        tts.save(temp_file)

        is_cast = device and device.startswith("[Cast] ")

        if is_cast:
            cast_name = device[7:]
            play_audio_cast(temp_file, cast_name, volume_percent=volume)
            while is_cast_playing():
                time.sleep(0.1)
            stop_cast()
        else:
            # Bluetooth or system device via pygame
            pygame.mixer.music.unload()
            play_audio(temp_file, device=device)
            while is_playing():
                time.sleep(0.1)

    except Exception as e:
        print(f"Speech Error: {e}")
    finally:
        try:
            if not (device and device.startswith("[Cast] ")):
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
