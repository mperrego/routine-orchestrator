"""
Author: Michael
Project: Routine Orchestrator
File: Orchestrator_main_gui.py
Description: UI cleanup — dirty tracking, single editor limit, New Routine button.
Version: 9.2
Date: 2026-03-25
"""

import customtkinter as ctk
from tkinter import filedialog, simpledialog, messagebox
import audio_engine
import editors
import threading
import os
import sys
import pygame
import json
import tkinter as tk
import time

# -- Ecosystem sync ------------------------------------------------
try:
    ECOSYSTEM_CORE = os.environ.get('ECOSYSTEM_CORE_PATH', '')
    if ECOSYSTEM_CORE and ECOSYSTEM_CORE not in sys.path:
        sys.path.insert(0, ECOSYSTEM_CORE)
    from sync_core import manifest_reader
except ImportError:
    manifest_reader = None  # sync_core not available -- skip silently
# ------------------------------------------------------------------

class Action:
    def __init__(self, action_type, data, wait_on_completion=True):
        self.type = action_type
        self.data = data 
        self.wait_on_completion = wait_on_completion

class RoutineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. WINDOW SETUP
        self.title("Routine Orchestrator")
        self.geometry("1100x950")
        
        # 2. PATHS & PERSISTENCE (Must be defined before UI and load_settings)
        # Get the directory where Orchestrator_main_gui.py is located
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define specific sub-directories and settings file
        self.routines_dir = os.path.join(self.base_dir, "Routines")
        self.settings_file = os.path.join(self.base_dir, "settings.json")
        
        # Ensure the Routines folder exists immediately
        if not os.path.exists(self.routines_dir):
            os.makedirs(self.routines_dir)

        # 3. INITIALIZE TRACKERS (Load from file if possible, otherwise use base_dir)
        self.load_settings() 

        # SIGNAL FILES for CLI remote stop
        self.pid_file = os.path.join(self.base_dir, "orchestrator.pid")
        self.stop_signal_file = os.path.join(self.base_dir, "orchestrator.stop")

        # 4. APP STATE
        self.actions = []
        self.selected_index = ctk.IntVar(value=-1)
        self.is_running = False
        self.auto_close = False
        self.has_unsaved_changes = False
        self.current_routine_path = None
        self._audio_editor = None

        # Initialize the menu bar
        self.setup_menu()

        # 5. UI COMPONENTS - NEW ROUTINE BUTTON
        f_top = ctk.CTkFrame(self)
        f_top.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(f_top, text="New Routine", fg_color="#2b6cb0",
                       command=self.clear_routine).pack(side="left", padx=10, pady=5)

        # 6. UI COMPONENTS - MAIN LIST AREA
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 7. UI COMPONENTS - ACTIONS GROUP (Creation)
        f_actions_container = ctk.CTkFrame(self)
        f_actions_container.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_actions_container, text="Actions", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10)
        
        f_create = ctk.CTkFrame(f_actions_container, fg_color="transparent")
        f_create.pack(fill="x", padx=5, pady=(0, 5))
        # Button labels updated to be concise; the "add_action" logic handles the rest
        ctk.CTkButton(f_create, text="+ Add Audio", width=140, command=lambda: self.add_action("Audio")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Wait", width=100, command=lambda: self.add_action("Wait")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Script", width=100, command=lambda: self.add_action("Script")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Announcement", width=120, command=lambda: self.add_action("Announcement")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Routine", width=100, fg_color="#6a4c93", command=lambda: self.add_action("Routine")).pack(side="left", padx=5)

        # 8. UI COMPONENTS - EDIT ACTIONS GROUP (Management)
        f_edit_container = ctk.CTkFrame(self)
        f_edit_container.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_edit_container, text="Edit Actions", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10)

        f_mgmt = ctk.CTkFrame(f_edit_container, fg_color="transparent")
        f_mgmt.pack(fill="x", padx=5, pady=(0, 5))
        ctk.CTkButton(f_mgmt, text="Edit Selected", fg_color="#3a7ebf", command=self.edit_action).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Move Up", width=80, command=lambda: self.move_action(-1)).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Move Down", width=80, command=lambda: self.move_action(1)).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Delete Selection", fg_color="darkred", command=self.remove_action).pack(side="right", padx=5)

        # 9. UI COMPONENTS - PLAYBACK BAR
        f_run = ctk.CTkFrame(self)
        f_run.pack(fill="x", padx=20, pady=10)
        
        self.play_btn = ctk.CTkButton(f_run, text="RUN ROUTINE", fg_color="green", 
                                     font=("Arial", 14, "bold"), command=self.run_thread)
        self.play_btn.pack(side="left", fill="x", expand=True, padx=5)
        
        self.skip_btn = ctk.CTkButton(f_run, text="SKIP", fg_color="#cc8400", 
                                     state="disabled", width=80, command=self.skip_item)
        self.skip_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(f_run, text="STOP", fg_color="darkred", 
                                     state="disabled", width=80, command=self.stop_routine)
        self.stop_btn.pack(side="left", padx=5)

        self.exit_btn = ctk.CTkButton(f_run, text="EXIT", fg_color="#333333", 
                                     width=80, command=self.on_closing)
        self.exit_btn.pack(side="right", padx=5)

        # 10. UI COMPONENTS - STATUS BAR
        self.status = ctk.CTkLabel(self, text="Ready", anchor="w", text_color="#00d4ff", 
                                   font=("Arial", 12, "bold"))
        self.status.pack(side="bottom", fill="x", padx=20, pady=5)
        
        # Window Close Protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Pre-cache Cast devices in background so the editor opens instantly
        threading.Thread(target=audio_engine.discover_cast_devices, daemon=True).start()

        # After all UI is built, check for CLI arguments (skip --stop, handled in __main__)
        cli_args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if cli_args:
            self.auto_close = True
            self.after(100, lambda: self.load_and_run_from_cli(cli_args[0]))



    def load_and_run_from_cli(self, filename):
        """Loads a specific routine file and starts it immediately."""
        # Construct the full path
        path = os.path.join(self.routines_dir, filename)
        if not path.endswith(".json"):
            path += ".json"

        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            self.actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in data]
            self.update_display()
            self.safe_status_update(f"CLI Load: {filename}")
            
            # Start the routine automatically
            self.run_thread()
        else:
            print(f"Error: Routine '{filename}' not found in {self.routines_dir}")
        
    def setup_menu(self):
        """Initializes the top menu bar with File and Tools options."""
        # Create the main menu bar object
        # Note: We use the standard tkinter Menu (tk.Menu) for the top bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # --- FILE MENU ---
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Standard routine management options
        file_menu.add_command(label="New Routine", command=self.clear_routine)
        file_menu.add_command(label="Save Routine", command=self.save_routine)
        file_menu.add_command(label="Load Routine", command=self.load_routine)
        
        # Recent Files submenu
        recent_menu = tk.Menu(file_menu, tearoff=0)
        if hasattr(self, 'recent_files') and self.recent_files:
            for path in self.recent_files:
                name = os.path.basename(path)
                recent_menu.add_command(
                    label=name,
                    command=lambda p=path: self.load_specific_routine(p)
                )
        else:
            recent_menu.add_command(label="(No recent files)", state="disabled")
        file_menu.add_cascade(label="Open Recent", menu=recent_menu)

        file_menu.add_separator()

        # The CLI utility
        file_menu.add_command(
            label="Copy CLI Command to Clipboard",
            command=self.copy_cli_command
        )
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # --- TOOLS MENU (Optional - for future growth) ---
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Example tool: Opening the settings folder
        tools_menu.add_command(
            label="Open Routines Folder", 
            command=lambda: os.startfile(self.routines_dir)
        )
        
        # Example tool: Resetting the last used directory trackers
        tools_menu.add_command(
            label="Reset Saved Paths", 
            command=self.reset_settings
        )

    def _mark_dirty(self):
        """Flag that the routine has unsaved changes."""
        self.has_unsaved_changes = True

    def _prompt_save_if_dirty(self):
        """If there are unsaved changes, ask to save. Returns False if user cancels."""
        if not self.has_unsaved_changes or not self.actions:
            return True
        result = messagebox.askyesnocancel("Unsaved Changes",
                                            "You have unsaved changes. Save before continuing?")
        if result is None:  # Cancel
            return False
        if result:  # Yes
            self.save_routine()
        return True

    def clear_routine(self):
        """Prompts to save if dirty, then wipes the current actions list."""
        if not self._prompt_save_if_dirty():
            return
        self.actions = []
        self.has_unsaved_changes = False
        self.current_routine_path = None
        self.update_display()
        self.safe_status_update("New routine started.")

    def reset_settings(self):
        """Resets the directory trackers to the base directory."""
        self.last_audio_dir = self.base_dir
        self.last_script_dir = self.base_dir
        self.save_settings()
        messagebox.showinfo("Reset", "Directory trackers have been reset to the program folder.")
        
    def skip_item(self):
        """Interrupts current audio (pygame and Cast). The loop will then move to the next item."""
        audio_engine.stop_audio()
        audio_engine.stop_cast()
        self.safe_status_update("Skipping current item...") 

    def stop_routine(self):
        """Stops the entire routine, audio, and any active Cast."""
        self.is_running = False
        audio_engine.stop_audio()
        audio_engine.stop_cast()
        self.safe_status_update("Routine Stopped.")

    # --- Signal file methods for CLI remote stop ---

    def _write_pid_file(self):
        """Write current process ID so --stop knows we're running."""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            print(f"PID file warning: {e}")

    def _cleanup_signal_files(self):
        """Remove PID and stop signal files on exit."""
        for path in (self.pid_file, self.stop_signal_file):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def _should_stop(self):
        """Check both the internal flag and the external stop signal file."""
        if os.path.exists(self.stop_signal_file):
            print("Stop signal detected from external command.")
            self.is_running = False
            audio_engine.stop_audio()
            audio_engine.stop_cast()
        return not self.is_running

    def run_routine(self):
        """Sequentially executes actions and handles the Skip/Stop states."""
        self.is_running = True
        self._write_pid_file()
        # Clear any stale stop signal from a previous session
        if os.path.exists(self.stop_signal_file):
            os.remove(self.stop_signal_file)

        # UI State Management - Disable Play, Enable Stop/Skip
        self.after(0, lambda: self.play_btn.configure(state="disabled"))
        self.after(0, lambda: self.stop_btn.configure(state="normal"))
        self.after(0, lambda: self.skip_btn.configure(state="normal"))

        for a in self.actions:
            if self._should_stop():
                break

            if a.type == "Audio":
                self._run_audio_action(a)
            elif a.type == "Announcement":
                self._run_announcement_action(a)
            elif a.type == "Wait":
                self._run_wait_action(a)
            elif a.type == "Script":
                self._run_script_action(a)
            elif a.type == "Routine":
                self._run_routine_action(a)

        # --- ROUTINE COMPLETE ---
        self.is_running = False
        self._cleanup_signal_files()
        self.safe_status_update("Ready")

        # Reset UI Buttons
        self.after(0, lambda: self.play_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.after(0, lambda: self.skip_btn.configure(state="disabled"))

        # CLI AUTO-CLOSE LOGIC — schedule on main thread to avoid tkinter crashes
        if self.auto_close:
            print("CLI Routine complete. Auto-closing in 3 seconds...")
            self.after(3000, self.on_closing)

    def _run_audio_action(self, action):
        """Plays each audio item via Cast or Bluetooth, with volume, repeat, and duration."""
        for item in action.data:
            if self._should_stop(): break
            repeat_count = item.get('repeat', 1)
            duration_limit = int(item.get('duration', 0))
            device = item.get('device', None)
            volume = int(item.get('volume', 0))
            is_cast = device and device.startswith("[Cast] ")
            cast_name = device[7:] if is_cast else None  # Strip "[Cast] " prefix

            for i in range(repeat_count):
                if self._should_stop(): break

                full_path, display_name = audio_engine.get_next_filename(item)
                if full_path:
                    device_label = f" → {device}" if device else ""
                    vol_label = f" @ {volume}%" if volume > 0 else ""
                    self.safe_status_update(f"({i+1}/{repeat_count}) Playing: {display_name}{device_label}{vol_label}")

                    if is_cast:
                        # WiFi Cast playback (volume set on same connection)
                        success = audio_engine.play_audio_cast(full_path, cast_name, volume_percent=volume)
                        if success:
                            start_time = time.time()
                            while audio_engine.is_cast_playing() and not self._should_stop():
                                if duration_limit > 0 and (time.time() - start_time) >= duration_limit:
                                    audio_engine.stop_cast()
                                    break
                                time.sleep(0.5)
                            # Only stop between files if there are more to play
                            audio_engine.stop_cast()
                    else:
                        # Bluetooth / system device playback via pygame
                        audio_engine.play_audio(full_path, device=device)
                        start_time = time.time()
                        while audio_engine.is_playing() and not self._should_stop():
                            if duration_limit > 0 and (time.time() - start_time) >= duration_limit:
                                audio_engine.stop_audio()
                                break
                            time.sleep(0.1)

        # Restore default output device after this audio action completes
        audio_engine.reset_to_default_device()

    def _run_announcement_action(self, action):
        """Generates and plays a TTS announcement on the specified device."""
        # Handle both old format (string) and new format (dict)
        if isinstance(action.data, str):
            text, device, volume = action.data, None, 0
        else:
            text = action.data.get("text", "")
            device = action.data.get("device", None)
            volume = int(action.data.get("volume", 0))

        device_label = f" → {device}" if device else ""
        self.safe_status_update(f"Announcement: {text[:30]}...{device_label}")
        audio_engine.speak(text, device=device, volume=volume)
        # speak() blocks until done, so just reset device after
        audio_engine.reset_to_default_device()

    def _run_wait_action(self, action):
        """Counts down for the specified number of seconds."""
        for s in range(int(action.data)):
            if self._should_stop(): break
            self.safe_status_update(f"Wait: {int(action.data)-s}s remaining")
            time.sleep(1)

    def _run_script_action(self, action):
        """Runs an external Python script via subprocess."""
        script_name = os.path.basename(action.data)
        self.safe_status_update(f"Running Script: {script_name}...")

        success = audio_engine.run_external_script(action.data)

        if success:
            self.safe_status_update(f"SUCCESS: {script_name} finished")
        else:
            self.safe_status_update(f"ERROR: {script_name} failed")

        # Brief pause so the user can read the success/fail message
        time.sleep(2)

    def _run_routine_action(self, action, _depth=0):
        """Loads and executes a nested routine from a saved JSON file."""
        if _depth >= 10:
            self.safe_status_update("ERROR: Routine nesting too deep (max 10)")
            time.sleep(2)
            return

        routine_path = action.data
        routine_name = os.path.splitext(os.path.basename(routine_path))[0]

        if not os.path.exists(routine_path):
            self.safe_status_update(f"ERROR: Routine '{routine_name}' not found")
            time.sleep(2)
            return

        try:
            with open(routine_path, 'r') as f:
                data = json.load(f)
            nested_actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in data]
        except Exception as e:
            self.safe_status_update(f"ERROR loading routine: {e}")
            time.sleep(2)
            return

        self.safe_status_update(f"Running Routine: {routine_name}")

        for nested in nested_actions:
            if self._should_stop():
                break

            if nested.type == "Audio":
                self._run_audio_action(nested)
            elif nested.type == "Announcement":
                self._run_announcement_action(nested)
            elif nested.type == "Wait":
                self._run_wait_action(nested)
            elif nested.type == "Script":
                self._run_script_action(nested)
            elif nested.type == "Routine":
                self._run_routine_action(nested, _depth=_depth + 1)

        if self.is_running:
            self.safe_status_update(f"Routine '{routine_name}' complete")

    def safe_status_update(self, msg):
        """Ensures the status label is updated safely across threads."""
        try:
            self.after(0, lambda m=msg: self.status.configure(text=m))
        except Exception:
            pass

    def on_closing(self):
        """Safely shuts down the audio engine and closes the app."""
        if not self.auto_close and self.has_unsaved_changes and self.actions:
            result = messagebox.askyesnocancel("Unsaved Changes",
                                                "You have unsaved changes. Save before exiting?")
            if result is None:  # Cancel — don't close
                return
            if result:  # Yes — save first
                self.save_routine()
        self.is_running = False
        self._cleanup_signal_files()
        pygame.mixer.quit(); self.destroy(); sys.exit()


    def save_routine(self):
        """Saves the current list of actions to a JSON file and updates Recents."""
        # Open the save dialog, defaulting to your Routines folder
        filename = filedialog.asksaveasfilename(
            initialdir=self.routines_dir,
            title="Save Routine",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        
        if filename:
            try:
                # We change "wait" to "wait_on_completion" here
                data = [
                    {
                        "type": a.type, 
                        "data": a.data, 
                        "wait": a.wait_on_completion # <--- Matches your class
                    } 
                    for a in self.actions
                ]
                
                # Write to the file
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Update Recents list
                self.update_recent_files(filename)
                
                self.has_unsaved_changes = False
                self.current_routine_path = filename
                self.safe_status_update(f"Saved: {os.path.basename(filename)}")
                messagebox.showinfo("Success", "Routine saved successfully.")
            except Exception as e:
                messagebox.showerror("Save Error", f"An error occurred while saving: {e}")

    def load_routine(self):
        """Opens a file dialog to load a routine and updates the Recents list."""
        # Open the load dialog
        filename = filedialog.askopenfilename(
            initialdir=self.routines_dir,
            title="Load Routine",
            filetypes=[("JSON Files", "*.json")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # We map the JSON "wait" key back to "wait_on_completion"
                self.actions = [
                    Action(i['type'], i['data'], i.get('wait', True)) 
                    for i in data
                ]
                
                # Update the GUI display and directory tracker
                self.update_display()

                # Add this file to the 'Open Recent' menu
                self.update_recent_files(filename)
                
                self.has_unsaved_changes = False
                self.current_routine_path = filename
                self.safe_status_update(f"Loaded: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Load Error", f"An error occurred while loading: {e}")
                
            
    def add_action(self, atype):
        """Creates a new Action object and adds it to the routine."""
        # 1. AUDIO ACTION
        if atype == "Audio":
            new_action = Action("Audio", [], True)
            self.actions.append(new_action)
            self.update_display()
            self._mark_dirty()
            self.safe_status_update(f"Added {atype} action.")

            # Automatically open the editor for the newly created audio action
            self.selected_index.set(len(self.actions) - 1)
            self.edit_action()

        # 2. WAIT ACTION
        elif atype == "Wait":
            new_action = Action("Wait", 5, True)
            self.actions.append(new_action)
            self.update_display()
            self._mark_dirty()
            self.safe_status_update(f"Added {atype} action.")

        # 3. ANNOUNCEMENT ACTION
        elif atype == "Announcement":
            text = ctk.CTkInputDialog(text="Enter the announcement text:", title="New Announcement").get_input()
            if text:
                new_action = Action("Announcement", {"text": text, "device": None, "volume": 0}, True)
                self.actions.append(new_action)
                self.update_display()
                self._mark_dirty()
                self.safe_status_update(f"Added {atype} action.")
                # Open the announcement editor to pick speaker
                self.selected_index.set(len(self.actions) - 1)
                self.edit_action()

        # 4. SCRIPT ACTION
        elif atype == "Script":
            f = filedialog.askopenfilename(
                initialdir=self.last_script_dir,
                title="Select Python Script",
                filetypes=[("Python Files", "*.py")]
            )
            if f:
                self.last_script_dir = os.path.dirname(f)
                self.save_settings()
                new_action = Action("Script", f, True)
                self.actions.append(new_action)
                self.update_display()
                self._mark_dirty()
                self.safe_status_update(f"Added {atype} action.")

        # 5. ROUTINE ACTION (embed a saved routine inside this one)
        elif atype == "Routine":
            f = filedialog.askopenfilename(
                initialdir=self.routines_dir,
                title="Select Routine to Embed",
                filetypes=[("JSON Files", "*.json")]
            )
            if f:
                new_action = Action("Routine", f, True)
                self.actions.append(new_action)
                self.update_display()
                self._mark_dirty()
                self.safe_status_update(f"Added {atype} action.")

    def update_display(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        for i, a in enumerate(self.actions):
            row_frame = ctk.CTkFrame(self.list_frame)
            row_frame.pack(fill="x", pady=4, padx=5)
            
            label_text = f"{i+1}. {a.type.upper()}: {a.data}"
            if a.type == "Audio":
                label_text = f"{i+1}. PLAY AUDIO FILES"
            elif a.type == "Announcement":
                if isinstance(a.data, dict):
                    ann_text = a.data.get("text", "")[:40]
                    ann_device = a.data.get("device", None)
                    label_text = f"{i+1}. ANNOUNCE: {ann_text}"
                    if ann_device:
                        label_text += f" → {ann_device}"
                else:
                    label_text = f"{i+1}. ANNOUNCE: {a.data[:40]}"
            elif a.type == "Wait":
                label_text = f"{i+1}. WAIT: {a.data} Seconds"
            elif a.type == "Script":
                label_text = f"{i+1}. SCRIPT: {os.path.basename(a.data)}"
            elif a.type == "Routine":
                routine_name = os.path.splitext(os.path.basename(a.data))[0]
                label_text = f"{i+1}. ROUTINE: {routine_name}"

            rb = ctk.CTkRadioButton(row_frame, text=label_text, variable=self.selected_index, value=i, font=("Arial", 12, "bold"))
            rb.pack(side="left", padx=10, pady=5)
            
            def on_double_click(event, idx=i):
                self.selected_index.set(idx)
                self.edit_action()
            rb.bind("<Double-1>", on_double_click)

            # --- UPDATED NESTED AUDIO LIST ---
            if a.type == "Audio":
                sub_list = ctk.CTkFrame(self.list_frame, fg_color="transparent")
                sub_list.pack(fill="x", padx=45)
                for item in a.data:
                    name = os.path.basename(item['path'])
                    
                    # Create the base description
                    txt = f"↳ {name} ({item['mode']}) x{item['repeat']}"
                    
                    # Add duration, speaker, and volume info
                    duration = item.get('duration', 0)
                    if duration > 0:
                        txt += f" | playing for {duration} seconds"

                    device = item.get('device', None)
                    if device:
                        txt += f" | {device}"

                    volume = item.get('volume', 0)
                    if volume > 0:
                        txt += f" | Vol: {volume}%"

                    ctk.CTkLabel(sub_list, text=txt, font=("Arial", 11, "italic"), text_color="#3a7ebf").pack(anchor="w")

            if i > 0:
                cb = ctk.CTkCheckBox(row_frame, text="Wait", width=80, command=lambda idx=i: self.toggle_wait(idx))
                if a.wait_on_completion: cb.select()
                cb.pack(side="right", padx=10)


    def edit_action(self):
        """
        Unified editor for all action types. 
        Detects the selected action and opens the correct input dialog or window.
        """
        idx = self.selected_index.get()
        
        # 1. Validation: Ensure a valid index is selected
        if idx < 0 or idx >= len(self.actions): 
            return
            
        a = self.actions[idx]

        # 2. AUDIO: Open the specialized sequence editor (limit to one instance)
        if a.type == "Audio":
            if self._audio_editor and self._audio_editor.winfo_exists():
                self._audio_editor.focus()
                return
            self._audio_editor = editors.AudioSequenceEditor(self, a)

        # 3. ANNOUNCEMENT: Open editor with text + speaker selection
        elif a.type == "Announcement":
            editors.AnnouncementEditor(self, a)

        # 4. WAIT: Edit seconds using a dialog
        elif a.type == "Wait":
            dialog = ctk.CTkInputDialog(text="Enter wait time (seconds):", title="Edit Wait")
            v = dialog.get_input()
            
            if v and v.isdigit():
                a.data = int(v)
                self.update_display()
                self.safe_status_update(f"Wait updated to {v}s.")

        # 5. SCRIPT: Change the target Python file
        elif a.type == "Script":
            f = filedialog.askopenfilename(
                initialdir=os.path.dirname(a.data) if a.data else self.last_script_dir,
                title="Select New Python Script",
                filetypes=[("Python Files", "*.py")]
            )
            if f:
                a.data = f
                self.last_script_dir = os.path.dirname(f)
                self.save_settings()
                self.update_display()
                self.safe_status_update(f"Script updated to {os.path.basename(f)}")

        # 6. ROUTINE: Change which routine is embedded
        elif a.type == "Routine":
            f = filedialog.askopenfilename(
                initialdir=self.routines_dir,
                title="Select Different Routine",
                filetypes=[("JSON Files", "*.json")]
            )
            if f:
                a.data = f
                self.update_display()
                routine_name = os.path.splitext(os.path.basename(f))[0]
                self.safe_status_update(f"Routine updated to {routine_name}")

    def move_action(self, d):
        idx = self.selected_index.get()
        if 0 <= idx + d < len(self.actions):
            self.actions[idx], self.actions[idx+d] = self.actions[idx+d], self.actions[idx]
            self.selected_index.set(idx+d); self.update_display()
            self._mark_dirty()

    def remove_action(self):
        idx = self.selected_index.get()
        if 0 <= idx < len(self.actions):
            self.actions.pop(idx); self.selected_index.set(-1); self.update_display()
            self._mark_dirty()

    def toggle_wait(self, i):
        self.actions[i].wait_on_completion = not self.actions[i].wait_on_completion
        self._mark_dirty()

    def run_thread(self): 
        """Pre-enables buttons on the main thread, then starts the routine."""
        if self.actions:
            # Enable buttons here, BEFORE the thread starts
            self.play_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")
            
            threading.Thread(target=self.run_routine, daemon=True).start()

    def load_settings(self):
        """Load settings including recent files and saved speakers."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.last_audio_dir = settings.get("last_audio_dir", self.base_dir)
                    self.last_script_dir = settings.get("last_script_dir", self.base_dir)
                    self.recent_files = settings.get("recent_files", [])[:5]
                    self.saved_speakers = settings.get("saved_speakers", [])
            except Exception:
                self.last_audio_dir, self.last_script_dir = self.base_dir, self.base_dir
                self.recent_files = []
                self.saved_speakers = []
        else:
            self.last_audio_dir, self.last_script_dir = self.base_dir, self.base_dir
            self.recent_files = []
            self.saved_speakers = []


    def save_settings(self):
        """Save settings including recent files and saved speakers."""
        settings = {
            "last_audio_dir": self.last_audio_dir,
            "last_script_dir": self.last_script_dir,
            "recent_files": self.recent_files,
            "saved_speakers": self.saved_speakers
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=4)
    def copy_cli_command(self):
        """Generates a CLI command for the current script and routine, then copies to clipboard."""
        # Get the current script path
        script_path = os.path.abspath(__file__)
        
        # Ask the user which routine they want to create a command for
        f = filedialog.askopenfilename(
            initialdir=self.routines_dir,
            title="Select Routine for CLI Command",
            filetypes=[("JSON Files", "*.json")]
        )
        
        if f:
            # Extract just the filename without the .json extension
            routine_name = os.path.splitext(os.path.basename(f))[0]
            
            # Format the command (using quotes in case there are spaces in paths)
            cli_cmd = f'python "{script_path}" "{routine_name}"'
            
            # Copy to clipboard
            self.clipboard_clear()
            self.clipboard_append(cli_cmd)
            self.update() # Required for some systems to register the clipboard change
            
            # Show a message to the user
            messagebox.showinfo("CLI Command Copied", f"The following command is now on your clipboard:\n\n{cli_cmd}")
            self.safe_status_update("CLI command copied to clipboard.")

    def update_recent_files(self, file_path):
        """
        Manages the recent files list, ensures no duplicates, 
        limits to 5 items, and refreshes the menu.
        """
        # Ensure the path is absolute and clean
        file_path = os.path.abspath(file_path)
        
        # 1. Remove if already in list (to move it to the top)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # 2. Add to the front of the list
        self.recent_files.insert(0, file_path)
        
        # 3. Trim to keep only the 5 most recent
        self.recent_files = self.recent_files[:5]
        
        # 4. Save this new list to your settings.json on your hard drive
        self.save_settings()
        
        # 5. IMPORTANT: Re-run setup_menu so the 'Open Recent' list 
        # visually updates while the app is open
        self.setup_menu()

    def load_specific_routine(self, path):
        """
        Triggered when you click a filename in the 'Open Recent' menu.
        """
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct the actions from the JSON data
                self.actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in data]
                
                # Refresh the GUI list
                self.update_display()
                
                # Move this file to the top of the recents list
                self.update_recent_files(path)
                
                self.has_unsaved_changes = False
                self.current_routine_path = path
                self.safe_status_update(f"Loaded: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Could not load routine: {e}")
        else:
            messagebox.showwarning("File Not Found", "This routine file no longer exists.")
            # Optionally remove the dead path from recents
            if path in self.recent_files:
                self.recent_files.remove(path)
                self.save_settings()
                self.setup_menu()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pid_file = os.path.join(base_dir, "orchestrator.pid")
    stop_file = os.path.join(base_dir, "orchestrator.stop")

    # Handle --stop before launching the GUI (no window opens)
    if "--stop" in sys.argv:
        if os.path.exists(pid_file):
            with open(stop_file, 'w') as f:
                f.write("stop")
            print("Stop signal sent to running Orchestrator.")
        else:
            print("No running Orchestrator found (no PID file).")
        sys.exit(0)

    RoutineApp().mainloop()
