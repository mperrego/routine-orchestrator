"""
Author: Michael
Project: Routine Orchestrator
File: editors.py
Description: Restored folder file-list preview and unified audio item management.
Version: 1.3
Date: 2026-03-14
"""

import customtkinter as ctk
from tkinter import filedialog
import os
import tkinter as tk

class AudioSequenceEditor(ctk.CTkToplevel):
    def __init__(self, parent, action):
        super().__init__(parent)
        self.title("Audio Configuration")
        self.geometry("1000x800")
        self.action = action
        self.parent_app = parent
        self.attributes("-topmost", True)
        self.repeat_entries = []
        self.setup_editor_menu()
        # Default to the parent app's last used directory
        self.editor_last_dir = parent.last_used_dir
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(ctrl, text="+ Add Playing Single File", command=self.add_file).pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="+ Add Playing Multiple Files", command=self.add_folder).pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="Save & Close", fg_color="green", command=self.on_closing).pack(side="right", padx=5)
        
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
        if tk.messagebox.askyesno("Clear List", "Remove all audio items from this sequence?"):
            self.action.data = []
            self.update_list()


    def sync_data(self):
        for idx, entry in self.repeat_entries:
            val = entry.get()
            if idx < len(self.action.data):
                self.action.data[idx]["repeat"] = int(val) if val.isdigit() else 1

    def close_and_refresh(self):
        self.sync_data()
        self.parent_app.update_display()
        self.destroy()

    def add_file(self):
        self.sync_data()
        self.attributes("-topmost", False) 
        f = filedialog.askopenfilename(
            initialdir=self.parent_app.last_audio_dir, # Use Audio-specific tracker
            title="Select Audio File"
        )
        if f:
            new_dir = os.path.dirname(f)
            self.parent_app.last_audio_dir = new_dir # Save it back to the main app
            self.action.data.append({"path": f, "mode": "Single", "repeat": 1})
            self.update_list()
        self.attributes("-topmost", True)

    def add_folder(self):
        self.sync_data()
        self.attributes("-topmost", False) 
        # We use askopenfilename here as a trick to pick a folder by picking a file inside it
        f = filedialog.askopenfilename(
            initialdir=self.parent_app.last_audio_dir, # Use Audio-specific tracker
            title="Pick any file inside the target folder"
        )
        if f:
            folder = os.path.dirname(f)
            self.parent_app.last_audio_dir = folder # Save it back to the main app
            self.action.data.append({"path": folder, "mode": "Random", "repeat": 1})
            self.update_list()
        self.attributes("-topmost", True)


    def update_list(self):
        """Rebuilds the list and restores the file-preview text box for folders."""
        for w in self.list_frame.winfo_children(): w.destroy()
        self.repeat_entries = []
        valid_exts = ('.mp3', '.wav', '.m4a')
        
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
            
            ctk.CTkLabel(header, text="Play:").pack(side="left", padx=(10, 0))
            ent = ctk.CTkEntry(header, width=40)
            ent.insert(0, str(item.get('repeat', 1)))
            ent.pack(side="left", padx=5)
            self.repeat_entries.append((i, ent))
            
            ctk.CTkButton(header, text="Remove", fg_color="darkred", width=70, 
                         command=lambda idx=i: self.remove_item(idx)).pack(side="right")

            # --- RESTORED: File Preview Box ---
            if not is_file:
                try:
                    files = sorted([f for f in os.listdir(item['path']) if f.lower().endswith(valid_exts)])
                    file_text = "\n".join(files) if files else "Empty Folder"
                except:
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

    def on_closing(self):
        """Final sync and cleanup before closing the window."""
        self.sync_data() # Ensure the action's data list is up to date
        
        # Logic: If the user didn't add any files or folders, delete the action
        if not self.action.data:
            if self.action in self.parent_app.actions:
                self.parent_app.actions.remove(self.action)
                self.parent_app.safe_status_update("Empty audio action discarded.")
        
        # Refresh the main GUI to show the updated list
        self.parent_app.update_display()
        self.destroy()
