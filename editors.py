"""
Author: Michael
Project: Routine Orchestrator
File: editors.py
Description: Audio editor with per-item output device (speaker) selection.
Version: 1.4
Date: 2026-03-23
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import tkinter as tk
import audio_engine

class AudioSequenceEditor(ctk.CTkToplevel):
    def __init__(self, parent, action):
        super().__init__(parent)
        
        # 1. Window Configuration
        self.title("Audio Configuration")
        self.geometry("1000x800")
        self.action = action
        self.parent_app = parent
        self.attributes("-topmost", True)
        self.repeat_entries = []
        self.duration_entries = []
        self.device_vars = []
        self.volume_entries = []

        # 2. Directory Tracking
        self.editor_last_dir = parent.last_audio_dir
        
        # 3. Menu and Close Protocol
        self.setup_editor_menu()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 4. UI - MAIN SCROLLABLE LIST
        # This frame holds all the audio files you add
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 5. UI - CONTROL PANEL (Buttons)
        # Creating a dedicated frame at the bottom for the buttons
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(fill="x", padx=20, pady=10)
        
        # Add Single File Button
        ctk.CTkButton(ctrl, 
                      text="+ Add Play Single File", 
                      command=self.add_file).pack(side="left", padx=5)
        
        # Add Multiple Files Button
        ctk.CTkButton(ctrl, 
                      text="+ Add Playing Multiple Files", 
                      command=self.add_folder).pack(side="left", padx=5)
        
        # Exit without saving
        ctk.CTkButton(ctrl,
                      text="Exit (No Save)",
                      fg_color="#333333", width=100,
                      command=self.exit_no_save).pack(side="right", padx=5)

        # Save & Close Button (Linked to our cleanup logic)
        ctk.CTkButton(ctrl,
                      text="Save & Close",
                      fg_color="green",
                      command=self.on_closing).pack(side="right", padx=5)
        
        # 6. INITIAL POPULATE
        self.update_list()

    def setup_editor_menu(self):
        menu_bar = tk.Menu(self)
        
        # --- List Actions (Updated Labels) ---
        list_menu = tk.Menu(menu_bar, tearoff=0)
        # Updated to match your new button labels
        list_menu.add_command(label="Add Play Single File", command=self.add_file)
        list_menu.add_command(label="Add Play Multiple Files", command=self.add_folder)
        list_menu.add_separator()
        list_menu.add_command(label="Clear All", command=self.clear_all_items)
        menu_bar.add_cascade(label="Actions", menu=list_menu)

        self.configure(menu=menu_bar)

    def clear_all_items(self):
        if messagebox.askyesno("Clear List", "Remove all audio items from this sequence?"):
            self.action.data = []
            self.update_list()

    def _safe_int(self, value, default=0, minimum=0):
        """Converts a string to int, returning default if invalid."""
        try:
            result = int(value)
            return max(result, minimum)
        except (ValueError, TypeError):
            return default

    def sync_data(self):
        """Updates the underlying action data with values from the entry boxes."""
        for i in range(len(self.action.data)):
            try:
                # Sync Repeat Count (minimum 1)
                self.action.data[i]['repeat'] = self._safe_int(
                    self.repeat_entries[i].get(), default=1, minimum=1)

                # Sync Duration (0 = full playback)
                self.action.data[i]['duration'] = self._safe_int(
                    self.duration_entries[i].get(), default=0)

                # Sync Output Device (speaker)
                device = self.device_vars[i].get()
                if device == "System Default":
                    self.action.data[i]['device'] = None
                else:
                    self.action.data[i]['device'] = device
                    # Auto-save Cast speakers so they appear even when not discovered
                    if device.startswith("[Cast]") and device not in self.parent_app.saved_speakers:
                        self.parent_app.saved_speakers.append(device)
                        self.parent_app.save_settings()

                # Sync Volume (0 = don't change)
                self.action.data[i]['volume'] = self._safe_int(
                    self.volume_entries[i].get(), default=0)
            except IndexError:
                pass

    def close_and_refresh(self):
        self.sync_data()
        self.parent_app.update_display()
        self.destroy()


    def add_file(self):
        """Opens a file dialog to add a single audio file and updates the tracker."""
        self.sync_data()
        self.attributes("-topmost", False) 
        
        f = filedialog.askopenfilename(
            initialdir=self.parent_app.last_audio_dir,
            title="Select Audio File",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.m4a"), ("All Files", "*.*")]
        )
        
        if f:
            new_dir = os.path.dirname(f)
            self.parent_app.last_audio_dir = new_dir
            self.parent_app.save_settings()
            
            self.action.data.append({"path": f, "mode": "Single", "repeat": 1})
            self.update_list()
            
        self.attributes("-topmost", True)

    def add_folder(self):
        """Uses a file picker to select a folder (via a file inside it) and updates the tracker."""
        self.sync_data()
        self.attributes("-topmost", False) 
        
        f = filedialog.askopenfilename(
            initialdir=self.parent_app.last_audio_dir,
            title="Pick any file inside the target folder"
        )
        
        if f:
            folder = os.path.dirname(f)
            self.parent_app.last_audio_dir = folder
            self.parent_app.save_settings()
            
            self.action.data.append({"path": folder, "mode": "Random", "repeat": 1})
            self.update_list()
            
        self.attributes("-topmost", True)
 

    def update_list(self):
        """Rebuilds the list and restores the file-preview text box for folders."""
        for w in self.list_frame.winfo_children(): w.destroy()
        self.repeat_entries = []
        self.duration_entries = []
        self.device_vars = []
        self.volume_entries = []
        valid_exts = ('.mp3', '.wav', '.m4a')

        # Get available output devices, merged with saved speakers from settings
        saved = getattr(self.parent_app, 'saved_speakers', [])
        output_devices = ["System Default"] + audio_engine.get_output_devices(saved)

        for i, item in enumerate(self.action.data):
            is_file = os.path.isfile(item['path'])
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=10, padx=5)

            header = ctk.CTkFrame(row, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=5)

            prefix = "📄 File: " if is_file else "📁 Folder: "
            ctk.CTkLabel(header, text=f"{prefix}{os.path.basename(item['path'])}",
                         font=("Arial", 13, "bold")).pack(side="left")

            if not is_file:
                ctk.CTkButton(header, text=item['mode'], width=90,
                             command=lambda idx=i: self.toggle_mode(idx)).pack(side="left", padx=20)

            # Repeat Count
            ctk.CTkLabel(header, text="Play:").pack(side="left", padx=(10, 0))
            ent = ctk.CTkEntry(header, width=40)
            ent.insert(0, str(item.get('repeat', 1)))
            ent.pack(side="left", padx=5)
            self.repeat_entries.append(ent)

            # Duration (Timed Playback)
            ctk.CTkLabel(header, text="Sec (0=Full):").pack(side="left", padx=(10, 0))
            dur_ent = ctk.CTkEntry(header, width=45)
            dur_ent.insert(0, str(item.get('duration', 0)))
            dur_ent.pack(side="left", padx=5)
            self.duration_entries.append(dur_ent)

            ctk.CTkButton(header, text="Remove", fg_color="darkred", width=70,
                         command=lambda idx=i: self.remove_item(idx)).pack(side="right")

            # Speaker / Output Device dropdown (second row)
            device_row = ctk.CTkFrame(row, fg_color="transparent")
            device_row.pack(fill="x", padx=10, pady=(0, 5))

            ctk.CTkLabel(device_row, text="Speaker:", font=("Arial", 11)).pack(side="left")
            saved_device = item.get('device', None)
            device_var = ctk.StringVar(value=saved_device if saved_device else "System Default")
            device_menu = ctk.CTkOptionMenu(device_row, variable=device_var,
                                            values=output_devices, width=250)
            device_menu.pack(side="left", padx=5)
            self.device_vars.append(device_var)

            # Volume (0 = don't change, 1-100 = set volume on Cast devices)
            ctk.CTkLabel(device_row, text="Vol%:", font=("Arial", 11)).pack(side="left", padx=(15, 0))
            vol_ent = ctk.CTkEntry(device_row, width=40)
            vol_ent.insert(0, str(item.get('volume', 0)))
            vol_ent.pack(side="left", padx=5)
            self.volume_entries.append(vol_ent)

            # --- RESTORED: File Preview Box ---
            if not is_file:
                try:
                    files = sorted([f for f in os.listdir(item['path']) if f.lower().endswith(valid_exts)])
                    file_text = "\n".join(files) if files else "Empty Folder"
                except Exception:
                    file_text = "Error reading folder."
                
                txt = ctk.CTkTextbox(row, height=80, font=("Consolas", 11))
                txt.pack(fill="x", padx=10, pady=(0, 5))
                txt.insert("1.0", file_text)
                txt.configure(state="disabled")

    def toggle_mode(self, idx):
        self.sync_data()
        current = self.action.data[idx]["mode"]
        self.action.data[idx]["mode"] = "Sequential" if current == "Random" else "Random"
        self.update_list()

    def remove_item(self, idx):
        self.action.data.pop(idx)
        self.update_list()

    def exit_no_save(self):
        """Close the editor without saving. Remove empty actions."""
        if not self.action.data:
            if self.action in self.parent_app.actions:
                self.parent_app.actions.remove(self.action)
                self.parent_app.safe_status_update("Empty audio action discarded.")
        self.parent_app.update_display()
        self.parent_app._audio_editor = None
        self.destroy()

    def on_closing(self):
        """Final sync and cleanup before closing the window."""
        self.sync_data()

        # If the user didn't add any files or folders, delete the action
        if not self.action.data:
            if self.action in self.parent_app.actions:
                self.parent_app.actions.remove(self.action)
                self.parent_app.safe_status_update("Empty audio action discarded.")
        else:
            self.parent_app._mark_dirty()

        self.parent_app.update_display()
        self.parent_app._audio_editor = None
        self.destroy()


class AnnouncementEditor(ctk.CTkToplevel):
    """Editor for announcement text, speaker, and volume."""

    def __init__(self, parent, action):
        super().__init__(parent)
        self.title("Announcement Configuration")
        self.geometry("600x250")
        self.action = action
        self.parent_app = parent
        self.attributes("-topmost", True)

        # Handle old format (plain string) by converting to dict
        if isinstance(action.data, str):
            action.data = {"text": action.data, "device": None, "volume": 0}

        # Text entry
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(text_frame, text="Announcement Text:", font=("Arial", 12, "bold")).pack(anchor="w")
        self.text_entry = ctk.CTkEntry(text_frame, width=550)
        self.text_entry.insert(0, action.data.get("text", ""))
        self.text_entry.pack(fill="x", pady=5)

        # Speaker + Volume row
        device_frame = ctk.CTkFrame(self, fg_color="transparent")
        device_frame.pack(fill="x", padx=20, pady=5)

        # Build device list: System Default + Cast devices only
        cast_devices = ["[Cast] " + n for n in audio_engine.discover_cast_devices()]
        saved = [s for s in getattr(parent, 'saved_speakers', []) if s.startswith("[Cast]")]
        all_devices = ["System Default"] + cast_devices
        for s in saved:
            if s not in all_devices:
                all_devices.append(s)

        ctk.CTkLabel(device_frame, text="Speaker:", font=("Arial", 11)).pack(side="left")
        saved_device = action.data.get("device", None)
        self.device_var = ctk.StringVar(value=saved_device if saved_device else "System Default")
        ctk.CTkOptionMenu(device_frame, variable=self.device_var,
                          values=all_devices, width=250).pack(side="left", padx=5)

        ctk.CTkLabel(device_frame, text="Vol%:", font=("Arial", 11)).pack(side="left", padx=(15, 0))
        self.volume_entry = ctk.CTkEntry(device_frame, width=40)
        self.volume_entry.insert(0, str(action.data.get("volume", 0)))
        self.volume_entry.pack(side="left", padx=5)

        # Save button
        ctk.CTkButton(self, text="Save & Close", fg_color="green",
                       command=self.on_closing).pack(pady=15)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        text = self.text_entry.get().strip()
        device = self.device_var.get()
        try:
            volume = int(self.volume_entry.get())
        except ValueError:
            volume = 0

        if device == "System Default":
            device = None

        self.action.data = {"text": text, "device": device, "volume": volume}

        # Auto-save Cast speaker
        if device and device not in self.parent_app.saved_speakers:
            self.parent_app.saved_speakers.append(device)
            self.parent_app.save_settings()

        self.parent_app._mark_dirty()
        self.parent_app.update_display()
        self.destroy()
