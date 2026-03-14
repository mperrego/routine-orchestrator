"""
Author: Michael
Project: Routine Orchestrator
File: editors.py
Description: Secondary UI windows for configuring complex action types 
             (e.g., Multiple Audio folders).
Version: 1.1
Date: 2026-03-14
"""

import customtkinter as ctk
from tkinter import filedialog
import os

class MultipleMp3Editor(ctk.CTkToplevel):
    """
    A pop-up window to manage a list of folders, their play counts, 
    and their randomization modes.
    """
    def __init__(self, parent, action):
        super().__init__(parent)
        self.title("Collection Configuration")
        self.geometry("1000x800")
        self.action = action
        self.parent_app = parent
        self.attributes("-topmost", True)
        self.repeat_entries = [] 

        # Layout setup
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(fill="x", padx=20, pady=10)
        
        self.mode_var = ctk.StringVar(value="Random")
        ctk.CTkOptionMenu(ctrl, variable=self.mode_var, values=["Random", "Sequential"]).pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="Add Folder", command=self.add_folder).pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="Save & Close", fg_color="green", command=self.close_and_refresh).pack(side="right", padx=5)
        
        self.update_list()

    def sync_data(self):
        """Syncs GUI entry values back to the Action object before UI refreshes."""
        for idx, entry in self.repeat_entries:
            val = entry.get()
            self.action.data[idx]["repeat"] = int(val) if val.isdigit() else 1

    def close_and_refresh(self):
        """Saves current state and updates the main application display."""
        self.sync_data()
        self.parent_app.update_display()
        self.destroy()

    def add_folder(self):
        """Prompts user for a file, extracts the folder path, and adds it to the collection."""
        self.sync_data()
        self.attributes("-topmost", False) 
        f = filedialog.askopenfilename(title="Pick a file inside the folder")
        if f:
            folder = os.path.dirname(f)
            self.action.data.append({"path": folder, "mode": self.mode_var.get(), "repeat": 1})
            self.update_list()
        self.attributes("-topmost", True)

    def update_list(self):
        """Rebuilds the UI list of folders and their play settings."""
        for w in self.list_frame.winfo_children(): w.destroy()
        self.repeat_entries = []
        valid_exts = ('.mp3', '.wav', '.m4a')
        
        for i, item in enumerate(self.action.data):
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=10, padx=5)
            
            header = ctk.CTkFrame(row, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(header, text=f"Folder: {os.path.basename(item['path'])}", font=("Arial", 14, "bold")).pack(side="left")
            ctk.CTkButton(header, text=item['mode'], width=90, command=lambda idx=i: self.toggle_mode(idx)).pack(side="left", padx=20)
            ctk.CTkLabel(header, text="Play:").pack(side="left")
            
            ent = ctk.CTkEntry(header, width=50)
            ent.insert(0, str(item.get('repeat', 1)))
            ent.pack(side="left", padx=5)
            self.repeat_entries.append((i, ent))
            
            ctk.CTkButton(header, text="Remove", fg_color="darkred", width=70, command=lambda idx=i: self.remove_folder(idx)).pack(side="right")
            
            # Show a preview of files in the folder
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
        """Switches folder mode between Random and Sequential."""
        self.sync_data()
        self.action.data[idx]["mode"] = "Sequential" if self.action.data[idx]["mode"] == "Random" else "Random"
        self.update_list()

    def remove_folder(self, idx):
        """Deletes a folder entry from the collection."""
        self.action.data.pop(idx)
        self.update_list()
