"""
Author: Michael
Project: Routine Orchestrator
File: Orchestrator_main_gui.py
Description: Primary application entry point. Manages the main GUI, 
             routine execution threads, and file persistence.
Version: 6.7
Date: 2026-03-14
"""

import customtkinter as ctk
from tkinter import filedialog, simpledialog
import audio_engine
import editors
import threading
import os
import sys
import pygame
import json

class Action:
    """Standard data structure for a routine step."""
    def __init__(self, action_type, data, wait_on_completion=True):
        self.type = action_type
        self.data = data
        self.wait_on_completion = wait_on_completion

class RoutineApp(ctk.CTk):
    """Main Dashboard for the Routine Orchestrator."""
    def __init__(self):
        super().__init__()
        self.title("Routine Orchestrator")
        self.geometry("1100x950")
        self.actions = []
        self.selected_index = ctk.IntVar(value=-1)
        self.is_running = False

        # --- Top Menu (I/O) ---
        f_io = ctk.CTkFrame(self)
        f_io.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(f_io, text="Save Routine", command=self.save_routine).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(f_io, text="Load Routine", command=self.load_routine).pack(side="left", padx=10, pady=5)

        # --- Main Scrollable List ---
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Actions Group ---
        f_actions_container = ctk.CTkFrame(self)
        f_actions_container.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_actions_container, text="Actions", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10)
        
        f_create = ctk.CTkFrame(f_actions_container, fg_color="transparent")
        f_create.pack(fill="x", padx=5, pady=(0, 5))
        ctk.CTkButton(f_create, text="+ Single Audio", width=140, command=lambda: self.add_action("Single mp3")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Multiple Audio", width=140, command=lambda: self.add_action("Multiple mp3")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Wait", width=100, command=lambda: self.add_action("Wait")).pack(side="left", padx=5)
        ctk.CTkButton(f_create, text="+ Script", width=100, command=lambda: self.add_action("Script")).pack(side="left", padx=5)

        # --- Edit Actions Group ---
        f_edit_container = ctk.CTkFrame(self)
        f_edit_container.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_edit_container, text="Edit Actions", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10)

        f_mgmt = ctk.CTkFrame(f_edit_container, fg_color="transparent")
        f_mgmt.pack(fill="x", padx=5, pady=(0, 5))
        ctk.CTkButton(f_mgmt, text="Edit Selected", fg_color="#3a7ebf", command=self.edit_action).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Move Up", width=80, command=lambda: self.move_action(-1)).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Move Down", width=80, command=lambda: self.move_action(1)).pack(side="left", padx=5)
        ctk.CTkButton(f_mgmt, text="Delete Selection", fg_color="darkred", command=self.remove_action).pack(side="right", padx=5)

        # --- Playback Bar ---
        f_run = ctk.CTkFrame(self)
        f_run.pack(fill="x", padx=20, pady=10)
        self.play_btn = ctk.CTkButton(f_run, text="RUN ROUTINE", fg_color="green", font=("Arial", 14, "bold"), command=self.run_thread)
        self.play_btn.pack(side="left", fill="x", expand=True, padx=5)
        self.stop_btn = ctk.CTkButton(f_run, text="STOP", fg_color="darkred", state="disabled", command=self.stop_routine)
        self.stop_btn.pack(side="left", padx=5)
        ctk.CTkButton(f_run, text="EXIT", fg_color="#333333", width=80, command=self.on_closing).pack(side="right", padx=5)

        self.status = ctk.CTkLabel(self, text="Ready", anchor="w", text_color="#00d4ff", font=("Arial", 12, "bold"))
        self.status.pack(side="bottom", fill="x", padx=20, pady=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def safe_status_update(self, msg):
        """Ensures the status label is updated safely across threads."""
        try: self.status.configure(text=msg)
        except: pass

    def on_closing(self):
        """Safely shuts down the audio engine and closes the app."""
        self.is_running = False
        pygame.mixer.quit(); self.destroy(); sys.exit()

    def save_routine(self):
        """Serializes current action list to a JSON file."""
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            data = [{"type": a.type, "data": a.data, "wait": a.wait_on_completion} for a in self.actions]
            with open(path, 'w') as f: json.dump(data, f, indent=4)

    def load_routine(self):
        """Deserializes action list from a JSON file and updates the UI."""
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path, 'r') as f: data = json.load(f)
            self.actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in data]
            self.update_display()

    def add_action(self, atype):
        """Creates a new action based on type and adds it to the list."""
        data = None
        if atype == "Single mp3": data = filedialog.askopenfilename()
        elif atype == "Multiple mp3":
            f = filedialog.askopenfilename()
            if f:
                data = [{"path": os.path.dirname(f), "mode": "Random", "repeat": 1}]
                new_action = Action(atype, data)
                self.actions.append(new_action)
                self.selected_index.set(len(self.actions)-1)
                self.update_display()
                editors.MultipleMp3Editor(self, new_action)
                return
        elif atype == "Wait": data = simpledialog.askinteger("Wait", "Seconds:")
        elif atype == "Script": data = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if data:
            self.actions.append(Action(atype, data))
            self.selected_index.set(len(self.actions)-1)
            self.update_display()

    def update_display(self):
        """Refreshes the scrollable list of actions in the main window."""
        for w in self.list_frame.winfo_children(): w.destroy()
        for i, a in enumerate(self.actions):
            row_frame = ctk.CTkFrame(self.list_frame)
            row_frame.pack(fill="x", pady=4, padx=5)
            
            b_name = os.path.basename(str(a.data))
            label_text = f"{i+1}. {a.type.upper()}: {b_name}"
            if a.type == "Wait": label_text = f"{i+1}. WAIT: {a.data} Seconds"
            if a.type == "Multiple mp3": label_text = f"{i+1}. COLLECTION"

            rb = ctk.CTkRadioButton(row_frame, text=label_text, variable=self.selected_index, value=i, font=("Arial", 12, "bold"))
            rb.pack(side="left", padx=10, pady=5)
            
            def on_double_click(event, idx=i):
                self.selected_index.set(idx)
                self.edit_action()

            rb.bind("<Double-1>", on_double_click)
            row_frame.bind("<Double-1>", on_double_click)

            # Sub-display for folder collections
            if a.type == "Multiple mp3":
                sub_list = ctk.CTkFrame(self.list_frame, fg_color="transparent")
                sub_list.pack(fill="x", padx=45)
                for item in a.data:
                    txt = f"↳ {os.path.basename(item['path'])} | {item['mode']} | Play {item['repeat']}"
                    lbl = ctk.CTkLabel(sub_list, text=txt, font=("Arial", 11, "italic"), text_color="#3a7ebf")
                    lbl.pack(anchor="w")
                    lbl.bind("<Double-1>", on_double_click)

            if i > 0:
                cb = ctk.CTkCheckBox(row_frame, text="Wait", width=80, command=lambda idx=i: self.toggle_wait(idx))
                if a.wait_on_completion: cb.select()
                cb.pack(side="right", padx=10)

    def edit_action(self):
        """Opens the appropriate editor for the currently selected action."""
        idx = self.selected_index.get()
        if idx < 0 or idx >= len(self.actions): return
        a = self.actions[idx]
        if a.type == "Multiple mp3":
            editors.MultipleMp3Editor(self, a)
        elif a.type == "Wait":
            v = simpledialog.askinteger("Edit Wait", "Seconds:", initialvalue=a.data)
            if v: a.data = v; self.update_display()
        else:
            f = filedialog.askopenfilename()
            if f: a.data = f; self.update_display()

    def move_action(self, d):
        """Swaps the selected action's position in the routine list."""
        idx = self.selected_index.get()
        if 0 <= idx + d < len(self.actions):
            self.actions[idx], self.actions[idx+d] = self.actions[idx+d], self.actions[idx]
            self.selected_index.set(idx+d)
            self.update_display()

    def remove_action(self):
        """Deletes the selected action from the routine."""
        idx = self.selected_index.get()
        if 0 <= idx < len(self.actions):
            self.actions.pop(idx)
            self.selected_index.set(-1)
            self.update_display()

    def toggle_wait(self, i): 
        """Toggles the 'wait on completion' flag for an action."""
        self.actions[i].wait_on_completion = not self.actions[i].wait_on_completion
    
    def stop_routine(self): 
        """Immediately halts routine execution and stops audio."""
        self.is_running = False
        pygame.mixer.music.stop()

    def run_thread(self): 
        """Spawns a background thread to run the routine without freezing the GUI."""
        if self.actions: threading.Thread(target=self.run_routine, daemon=True).start()

    def run_routine(self):
        """Sequentially executes each action in the routine."""
        self.is_running = True
        self.play_btn.configure(state="disabled"); self.stop_btn.configure(state="normal")
        for a in self.actions:
            if not self.is_running: break
            if a.type == "Single mp3":
                self.safe_status_update(f"Playing: {os.path.basename(a.data)}")
                audio_engine.play_audio(a.data)
            elif a.type == "Multiple mp3":
                for folder in a.data:
                    for i in range(folder.get('repeat', 1)):
                        if not self.is_running: break
                        song = audio_engine.process_directory(folder['path'], mode=folder['mode'])
                        self.safe_status_update(f"({i+1}/{folder['repeat']}) {song}")
            elif a.type == "Wait":
                self.safe_status_update(f"Wait: {a.data}s...")
                audio_engine.wait_action(a.data)
            elif a.type == "Script":
                self.safe_status_update(f"Running: {os.path.basename(a.data)}")
                audio_engine.run_external_script(a.data)
        self.safe_status_update("Ready")
        self.play_btn.configure(state="normal"); self.stop_btn.configure(state="disabled")

if __name__ == "__main__":
    RoutineApp().mainloop()
