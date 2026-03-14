"""
Author: Michael
Project: Routine Orchestrator
File: Orchestrator_main_gui.py
Description: Added SKIP button and renamed folder addition button.
Version: 7.0
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
import tkinter as tk

class Action:
    def __init__(self, action_type, data, wait_on_completion=True):
        self.type = action_type
        self.data = data 
        self.wait_on_completion = wait_on_completion

class RoutineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Routine Orchestrator")
        self.geometry("1100x950")
        self.actions = []
        self.selected_index = ctk.IntVar(value=-1)
        self.is_running = False
        self.setup_menu()
        # Define the dedicated Routines directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.routines_dir = os.path.join(self.base_dir, "Routines")
        # Automatically create the folder if it doesn't exist
        if not os.path.exists(self.routines_dir):
            os.makedirs(self.routines_dir)
        # --------------------------------


        # --- Top Menu ---
        f_io = ctk.CTkFrame(self)
        f_io.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(f_io, text="Save Routine", command=self.save_routine).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(f_io, text="Load Routine", command=self.load_routine).pack(side="left", padx=10, pady=5)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Actions Group ---
        f_actions_container = ctk.CTkFrame(self)
        f_actions_container.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_actions_container, text="Actions", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10)
        
        f_create = ctk.CTkFrame(f_actions_container, fg_color="transparent")
        f_create.pack(fill="x", padx=5, pady=(0, 5))
        ctk.CTkButton(f_create, text="+ Add Audio", width=140, command=lambda: self.add_action("Audio")).pack(side="left", padx=5)
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
        
        # 1. Create the Play Button
        self.play_btn = ctk.CTkButton(f_run, text="RUN ROUTINE", fg_color="green", 
                                     font=("Arial", 14, "bold"), command=self.run_thread)
        self.play_btn.pack(side="left", fill="x", expand=True, padx=5)
        
        # 2. Create the Skip Button (Must be defined BEFORE packing)
        self.skip_btn = ctk.CTkButton(f_run, text="SKIP", fg_color="#cc8400", 
                                     state="disabled", width=80, command=self.skip_item)
        self.skip_btn.pack(side="left", padx=5)

        # 3. Create the Stop Button
        self.stop_btn = ctk.CTkButton(f_run, text="STOP", fg_color="darkred", 
                                     state="disabled", width=80, command=self.stop_routine)
        self.stop_btn.pack(side="left", padx=5)

        # 4. Create the Exit Button
        self.exit_btn = ctk.CTkButton(f_run, text="EXIT", fg_color="#333333", 
                                     width=80, command=self.on_closing)
        self.exit_btn.pack(side="right", padx=5)

        # --- Status Bar ---
        self.status = ctk.CTkLabel(self, text="Ready", anchor="w", text_color="#00d4ff", 
                                   font=("Arial", 12, "bold"))
        self.status.pack(side="bottom", fill="x", padx=20, pady=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_menu(self):
        self.menu_bar = tk.Menu(self)
        
        # --- File Menu (Unchanged) ---
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New Routine", command=self.new_routine)
        file_menu.add_command(label="Load Routine", command=self.load_routine)
        file_menu.add_command(label="Save Routine", command=self.save_routine)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # --- Edit Menu (Updated Labels) ---
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        # Updated to match your new button labels
        edit_menu.add_command(label="Add Play Single File", command=lambda: self.add_action("Audio"))
        edit_menu.add_command(label="Add Wait", command=lambda: self.add_action("Wait"))
        edit_menu.add_command(label="Add Script", command=lambda: self.add_action("Script"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Remove Selected", command=self.remove_action)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)

        # --- Help Menu ---
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=self.menu_bar)
        
    def new_routine(self):
        if tk.messagebox.askyesno("New Routine", "Clear current actions?"):
            self.actions = []
            self.update_display()

    def show_about(self):
        tk.messagebox.showinfo("About", "Routine Orchestrator v7.1\nPersonal Automation Suite")

    def skip_item(self):
        """Interrupts current audio. The loop will then move to the next item."""
        audio_engine.stop_audio()
        self.safe_status_update("Skipping current item...") 

    def stop_routine(self):
        """Stops the entire routine and the audio."""
        self.is_running = False
        audio_engine.stop_audio()
        self.safe_status_update("Routine Stopped.")

    def run_routine(self):
        """Sequentially executes actions and handles the Skip/Stop states."""
        self.is_running = True
        
        # UI State Management
        self.after(0, lambda: self.play_btn.configure(state="disabled"))
        self.after(0, lambda: self.stop_btn.configure(state="normal"))
        self.after(0, lambda: self.skip_btn.configure(state="normal"))
        
        for a in self.actions:
            if not self.is_running: 
                break
            
            if a.type == "Audio":
                for item in a.data:
                    repeat_count = item.get('repeat', 1)
                    for i in range(repeat_count):
                        if not self.is_running: break
                        
                        # Get filename and update status BEFORE playing
                        full_path, display_name = audio_engine.get_next_filename(item)
                        msg = f"({i+1}/{repeat_count}) Playing: {display_name}"
                        self.after(0, lambda m=msg: self.safe_status_update(m))
                        
                        if full_path:
                            audio_engine.play_audio(full_path)
            
            elif a.type == "Wait":
                self.after(0, lambda: self.safe_status_update(f"Wait: {a.data}s..."))
                audio_engine.wait_action(a.data)
                
            elif a.type == "Script":
                self.after(0, lambda: self.safe_status_update(f"Running: {os.path.basename(a.data)}"))
                audio_engine.run_external_script(a.data)
        
        # Reset UI when finished
        self.safe_status_update("Ready")
        self.after(0, lambda: self.play_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.after(0, lambda: self.skip_btn.configure(state="disabled"))

    def safe_status_update(self, msg):
        """Ensures the status label is updated safely across threads."""
        try: self.status.configure(text=msg)
        except: pass

    def on_closing(self):
        """Safely shuts down the audio engine and closes the app."""
        self.is_running = False
        pygame.mixer.quit(); self.destroy(); sys.exit()

    def save_routine(self):
        path = filedialog.asksaveasfilename(
            initialdir=self.routines_dir, # Set the default starting folder
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            data = [{"type": a.type, "data": a.data, "wait": a.wait_on_completion} for a in self.actions]
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)    

    def load_routine(self):
        path = filedialog.askopenfilename(
            initialdir=self.routines_dir, # Set the default starting folder
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
            self.actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in data]
            self.update_display()

            

    def add_action(self, atype):
        if atype == "Audio":
            new_action = Action("Audio", [])
            self.actions.append(new_action)
            self.selected_index.set(len(self.actions)-1)
            self.update_display()
            editors.AudioSequenceEditor(self, new_action)
        elif atype == "Wait":
            v = simpledialog.askinteger("Wait", "Seconds:")
            if v: self.actions.append(Action("Wait", v)); self.update_display()
        elif atype == "Script":
            f = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
            if f: self.actions.append(Action("Script", f)); self.update_display()

    def update_display(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        for i, a in enumerate(self.actions):
            row_frame = ctk.CTkFrame(self.list_frame)
            row_frame.pack(fill="x", pady=4, padx=5)
            
            label_text = f"{i+1}. {a.type.upper()}: {a.data}"
            if a.type == "Audio":
                label_text = f"{i+1}. PLAY AUDIO FILES"
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

            if a.type == "Audio":
                sub_list = ctk.CTkFrame(self.list_frame, fg_color="transparent")
                sub_list.pack(fill="x", padx=45)
                for item in a.data:
                    name = os.path.basename(item['path'])
                    txt = f"↳ {name} ({item['mode']}) x{item['repeat']}"
                    ctk.CTkLabel(sub_list, text=txt, font=("Arial", 11, "italic"), text_color="#3a7ebf").pack(anchor="w")

            if i > 0:
                cb = ctk.CTkCheckBox(row_frame, text="Wait", width=80, command=lambda idx=i: self.toggle_wait(idx))
                if a.wait_on_completion: cb.select()
                cb.pack(side="right", padx=10)

    def edit_action(self):
        idx = self.selected_index.get()
        if idx < 0 or idx >= len(self.actions): return
        a = self.actions[idx]
        if a.type == "Audio":
            editors.AudioSequenceEditor(self, a)
        elif a.type == "Wait":
            v = simpledialog.askinteger("Edit Wait", "Seconds:", initialvalue=a.data)
            if v: a.data = v; self.update_display()
        else:
            f = filedialog.askopenfilename()
            if f: a.data = f; self.update_display()

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
    
    def stop_routine(self): 
        self.is_running = False
        pygame.mixer.music.stop()

    def run_thread(self): 
        """Pre-enables buttons on the main thread, then starts the routine."""
        if self.actions:
            # Enable buttons here, BEFORE the thread starts
            self.play_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")
            
            threading.Thread(target=self.run_routine, daemon=True).start()

    def run_routine(self):
        """Executes the routine logic."""
        self.is_running = True
        
        for a in self.actions:
            if not self.is_running: break
            
            if a.type == "Audio":
                for item in a.data:
                    repeat_count = item.get('repeat', 1)
                    for i in range(repeat_count):
                        if not self.is_running: break
                        
                        full_path, display_name = audio_engine.get_next_filename(item)
                        msg = f"({i+1}/{repeat_count}) Playing: {display_name}"
                        self.after(0, lambda m=msg: self.safe_status_update(m))
                        
                        if full_path:
                            audio_engine.play_audio(full_path)
            
            # ... (Wait and Script logic) ...

        # When the loop finishes, reset the buttons
        self.is_running = False
        self.after(0, self.reset_ui_after_run)

    def reset_ui_after_run(self):
        """Restores the button states when the routine ends."""
        self.play_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.skip_btn.configure(state="disabled")
        self.safe_status_update("Ready")

if __name__ == "__main__":
    RoutineApp().mainloop()
