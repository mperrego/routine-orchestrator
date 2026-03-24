"""
Author: Michael
Project: Routine Orchestrator
File: Orchestrator_main_gui.py
Description: Added SKIP button and renamed folder addition button.
Version: 8.5
Date: 2026-03-14
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

        # 4. APP STATE
        self.actions = []
        self.selected_index = ctk.IntVar(value=-1)
        self.is_running = False
        self.auto_close = False  
        
        # Initialize the menu bar
        self.setup_menu()

        # 5. UI COMPONENTS - TOP MENU (Save/Load)
        f_io = ctk.CTkFrame(self)
        f_io.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(f_io, text="Save Routine", command=self.save_routine).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(f_io, text="Load Routine", command=self.load_routine).pack(side="left", padx=10, pady=5)

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

        import sys # Add to imports

        # Pre-cache Cast devices in background so the editor opens instantly
        threading.Thread(target=audio_engine.discover_cast_devices, daemon=True).start()

        # After all UI is built, check for CLI arguments
        if len(sys.argv) > 1:
            self.auto_close = True # <--- ADD THIS: Mark for automatic shutdown
            # We use after() to wait 100ms for the GUI to fully render 
            # before starting the heavy lifting
            self.after(100, lambda: self.load_and_run_from_cli(sys.argv[1]))



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
        
        file_menu.add_separator()
        
        # The new CLI utility
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

    def clear_routine(self):
        """Wipes the current actions list to start fresh."""
        if messagebox.askyesno("Confirm", "Clear all actions and start a new routine?"):
            self.actions = []
            self.update_display()
            self.safe_status_update("New routine started.")

    def reset_settings(self):
        """Resets the directory trackers to the base directory."""
        self.last_audio_dir = self.base_dir
        self.last_script_dir = self.base_dir
        self.save_settings()
        messagebox.showinfo("Reset", "Directory trackers have been reset to the program folder.")
        
    def skip_item(self):
        """Interrupts current audio. The loop will then move to the next item."""
        audio_engine.stop_audio()
        self.safe_status_update("Skipping current item...") 

    def stop_routine(self):
        """Stops the entire routine, audio, and any active Cast."""
        self.is_running = False
        audio_engine.stop_audio()
        audio_engine.stop_cast()
        self.safe_status_update("Routine Stopped.")


    def run_routine(self):
        """Sequentially executes actions and handles the Skip/Stop states."""
        self.is_running = True

        # UI State Management - Disable Play, Enable Stop/Skip
        self.after(0, lambda: self.play_btn.configure(state="disabled"))
        self.after(0, lambda: self.stop_btn.configure(state="normal"))
        self.after(0, lambda: self.skip_btn.configure(state="normal"))

        for a in self.actions:
            if not self.is_running:
                break

            if a.type == "Audio":
                self._run_audio_action(a)
            elif a.type == "Announcement":
                self._run_announcement_action(a)
            elif a.type == "Wait":
                self._run_wait_action(a)
            elif a.type == "Script":
                self._run_script_action(a)

        # --- ROUTINE COMPLETE ---
        self.is_running = False
        self.safe_status_update("Ready")

        # Reset UI Buttons
        self.after(0, lambda: self.play_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.after(0, lambda: self.skip_btn.configure(state="disabled"))

        # CLI AUTO-CLOSE LOGIC
        if self.auto_close:
            print("CLI Routine complete. Auto-closing in 3 seconds...")
            time.sleep(3)
            self.on_closing()

    def _run_audio_action(self, action):
        """Plays each audio item via Cast or Bluetooth, with volume, repeat, and duration."""
        for item in action.data:
            if not self.is_running: break
            repeat_count = item.get('repeat', 1)
            duration_limit = int(item.get('duration', 0))
            device = item.get('device', None)
            volume = int(item.get('volume', 0))
            is_cast = device and device.startswith("[Cast] ")
            cast_name = device[7:] if is_cast else None  # Strip "[Cast] " prefix

            for i in range(repeat_count):
                if not self.is_running: break

                full_path, display_name = audio_engine.get_next_filename(item)
                if full_path:
                    device_label = f" → {device}" if device else ""
                    vol_label = f" @ {volume}%" if volume > 0 else ""
                    self.safe_status_update(f"({i+1}/{repeat_count}) Playing: {display_name}{device_label}{vol_label}")
                    self.update()

                    if is_cast:
                        # WiFi Cast playback (volume set on same connection)
                        success = audio_engine.play_audio_cast(full_path, cast_name, volume_percent=volume)
                        if success:
                            start_time = time.time()
                            while audio_engine.is_cast_playing() and self.is_running:
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
                        while audio_engine.is_playing() and self.is_running:
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
        self.update()
        audio_engine.speak(text, device=device, volume=volume)
        # speak() blocks until done, so just reset device after
        audio_engine.reset_to_default_device()

    def _run_wait_action(self, action):
        """Counts down for the specified number of seconds."""
        for s in range(int(action.data)):
            if not self.is_running: break
            self.safe_status_update(f"Wait: {int(action.data)-s}s remaining")
            self.update()
            time.sleep(1)

    def _run_script_action(self, action):
        """Runs an external Python script via subprocess."""
        script_name = os.path.basename(action.data)
        self.safe_status_update(f"Running Script: {script_name}...")
        self.update()

        success = audio_engine.run_external_script(action.data)

        if success:
            self.safe_status_update(f"SUCCESS: {script_name} finished")
        else:
            self.safe_status_update(f"ERROR: {script_name} failed")

        # Brief pause so the user can read the success/fail message
        time.sleep(2)


    def safe_status_update(self, msg):
        """Ensures the status label is updated safely across threads."""
        try: self.status.configure(text=msg)
        except: pass

    def on_closing(self):
        """Safely shuts down the audio engine and closes the app."""
        self.is_running = False
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
                
                # Update our directory tracker and Recents list
                self.last_used_dir = os.path.dirname(filename)
                self.update_recent_files(filename)
                
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
                self.last_used_dir = os.path.dirname(filename)
                
                # Add this file to the 'Open Recent' menu
                self.update_recent_files(filename)
                
                self.safe_status_update(f"Loaded: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Load Error", f"An error occurred while loading: {e}")
                
            
    def add_action(self, atype):
        """Creates a new Action object and adds it to the routine."""
        # 1. AUDIO ACTION
        if atype == "Audio":
            # Initialize with an empty list for audio data and 'wait' set to True
            new_action = Action("Audio", [], True)
            self.actions.append(new_action)
            self.update_display()
            
            # Automatically open the editor for the newly created audio action
            self.selected_index.set(len(self.actions) - 1)
            self.edit_action()

        # 2. WAIT ACTION
        elif atype == "Wait":
            # Default to a 5-second wait if not specified
            new_action = Action("Wait", 5, True)
            self.actions.append(new_action)
            self.update_display()

        # 3. SCRIPT ACTION

        elif atype == "Announcement":
            # Ask the user what they want the AI to say
            text = ctk.CTkInputDialog(text="Enter the announcement text:", title="New Announcement").get_input()
            if text:
                new_action = Action("Announcement", {"text": text, "device": None, "volume": 0}, True)
                self.actions.append(new_action)
                self.update_display()
                # Open the announcement editor to pick speaker
                self.selected_index.set(len(self.actions) - 1)
                self.edit_action()


        # 4. SCRIPT ACTION
        elif atype == "Script":
            # Open file dialog using the last used script directory
            f = filedialog.askopenfilename(
                initialdir=self.last_script_dir,
                title="Select Python Script",
                filetypes=[("Python Files", "*.py")]
            )
            
            if f:
                # Update the directory tracker for scripts
                self.last_script_dir = os.path.dirname(f)
                self.save_settings()
                
                # Add the script action with 'wait' set to True
                new_action = Action("Script", f, True)
                self.actions.append(new_action)
                self.update_display()

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

        # 2. AUDIO: Open the specialized sequence editor from editors.py
        if a.type == "Audio":
            # Assuming 'editors' is imported at the top of your script
            editors.AudioSequenceEditor(self, a)

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



    def move_action(self, d):
        idx = self.selected_index.get()
        if 0 <= idx + d < len(self.actions):
            self.actions[idx], self.actions[idx+d] = self.actions[idx+d], self.actions[idx]
            self.selected_index.set(idx+d); self.update_display()

    def remove_action(self):
        idx = self.selected_index.get()
        if 0 <= idx < len(self.actions):
            self.actions.pop(idx); self.selected_index.set(-1); self.update_display()

    def toggle_wait(self, i):
        self.actions[i].wait_on_completion = not self.actions[i].wait_on_completion

    def run_thread(self): 
        """Pre-enables buttons on the main thread, then starts the routine."""
        if self.actions:
            # Enable buttons here, BEFORE the thread starts
            self.play_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")
            
            threading.Thread(target=self.run_routine, daemon=True).start()

    def reset_ui_after_run(self):
        """Restores the button states when the routine ends."""
        self.play_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.skip_btn.configure(state="disabled")
        self.safe_status_update("Ready")


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
    RoutineApp().mainloop()
