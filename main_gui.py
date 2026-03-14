"""
Main GUI Module: Routine Orchestrator (Sequencer Edition)
--------------------------------------------------------
Update: Hidden 'Wait' checkbox for the first item in the sequence.
"""

import customtkinter as ctk
from tkinter import filedialog, simpledialog
import audio_engine
import threading
import os
import sys
import pygame

class Action:
    def __init__(self, action_type, data, wait_on_completion=True):
        self.type = action_type
        self.data = data
        self.wait_on_completion = wait_on_completion

class MultipleMp3Editor(ctk.CTkToplevel):
    def __init__(self, parent, action):
        super().__init__(parent)
        self.title("Multiple mp3 Editor")
        self.geometry("850x700")
        self.action = action
        self.attributes("-topmost", True)
        self.repeat_entries = [] 

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        add_ctrl = ctk.CTkFrame(self)
        add_ctrl.pack(fill="x", padx=20, pady=10)
        
        self.mode_var = ctk.StringVar(value="Random")
        ctk.CTkOptionMenu(add_ctrl, variable=self.mode_var, values=["Random", "Sequential"]).pack(side="left", padx=5)
        ctk.CTkButton(add_ctrl, text="Add Another Folder", command=self.add_folder).pack(side="left", padx=5)
        ctk.CTkButton(add_ctrl, text="Close & Update", fg_color="green", command=self.close_and_refresh).pack(side="right", padx=5)
        
        self.update_list()

    def close_and_refresh(self):
        for index, entry_widget in self.repeat_entries:
            try:
                val = entry_widget.get()
                self.action.data[index]["repeat"] = int(val) if val.isdigit() else 1
            except:
                self.action.data[index]["repeat"] = 1
        self.master.update_display()
        self.destroy()

    def add_folder(self):
        self.attributes("-topmost", False)
        sample_file = filedialog.askopenfilename(title="Select ANY MP3 in folder", filetypes=[("MP3 Files", "*.mp3")])
        if sample_file:
            folder = os.path.dirname(sample_file)
            self.action.data.append({"path": folder, "mode": self.mode_var.get(), "repeat": 1})
            self.update_list()
        self.attributes("-topmost", True)

    def update_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.repeat_entries = []

        for i, item in enumerate(self.action.data):
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=10, padx=5)
            
            ctrl_row = ctk.CTkFrame(row, fg_color="transparent")
            ctrl_row.pack(fill="x", padx=10, pady=5)
            
            name = os.path.basename(item['path'])
            ctk.CTkLabel(ctrl_row, text=name, font=("Arial", 14, "bold"), width=300, anchor="w").pack(side="left")
            ctk.CTkButton(ctrl_row, text=item['mode'], width=90, command=lambda i=i: self.toggle_mode(i)).pack(side="left", padx=5)
            
            ctk.CTkLabel(ctrl_row, text="Plays:").pack(side="left", padx=5)
            ent = ctk.CTkEntry(ctrl_row, width=45)
            ent.insert(0, str(item.get('repeat', 1)))
            ent.pack(side="left", padx=2)
            self.repeat_entries.append((i, ent))
            
            ctk.CTkButton(ctrl_row, text="X", width=30, fg_color="red", command=lambda i=i: self.remove_folder(i)).pack(side="right", padx=5)

            preview_container = ctk.CTkFrame(row, fg_color="#2b2b2b")
            preview_container.pack(fill="x", padx=20, pady=(0, 10))

            try:
                files = [f for f in os.listdir(item['path']) if f.lower().endswith('.mp3')]
                if files:
                    file_list_str = "\n".join([f"• {f}" for f in files[:10]])
                    if len(files) > 10:
                        file_list_str += f"\n...and {len(files)-10} more files"
                    
                    preview_label = ctk.CTkLabel(preview_container, text=file_list_str, 
                                               font=("Arial", 11), text_color="gray75", 
                                               justify="left", anchor="nw")
                    preview_label.pack(fill="both", padx=15, pady=8)
                else:
                    ctk.CTkLabel(preview_container, text="No MP3 files found.", text_color="orange").pack(pady=10)
            except:
                ctk.CTkLabel(preview_container, text="Error reading directory.", text_color="red").pack(pady=10)

    def toggle_mode(self, idx):
        self.action.data[idx]["mode"] = "Sequential" if self.action.data[idx]["mode"] == "Random" else "Random"
        self.update_list()

    def remove_folder(self, idx):
        self.action.data.pop(idx)
        self.update_list()

class RoutineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Routine Orchestrator")
        self.geometry("1000x900")
        self.actions = []
        self.selected_index = ctk.IntVar(value=-1)
        self.is_running = False
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=20)

        creation_group = ctk.CTkFrame(self)
        creation_group.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(creation_group, text="ADD NEW ACTIONS", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10, pady=(5, 0))
        add_f = ctk.CTkFrame(creation_group, fg_color="transparent")
        add_f.pack(fill="x", padx=5, pady=5)
        for t in ["Single mp3", "Multiple mp3", "Wait", "Script"]:
            ctk.CTkButton(add_f, text=f"+ {t}", width=135, command=lambda t=t: self.add_action(t)).pack(side="left", padx=5, pady=5)

        mgmt_group = ctk.CTkFrame(self)
        mgmt_group.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(mgmt_group, text="MANAGE ROUTINE SEQUENCE", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10, pady=(5, 0))
        mgmt_f = ctk.CTkFrame(mgmt_group, fg_color="transparent")
        mgmt_f.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(mgmt_f, text="Edit Selected", command=self.edit_action).pack(side="left", padx=5)
        ctk.CTkButton(mgmt_f, text="Move Up", width=80, command=lambda: self.move_action(-1)).pack(side="left", padx=5)
        ctk.CTkButton(mgmt_f, text="Move Down", width=80, command=lambda: self.move_action(1)).pack(side="left", padx=5)
        ctk.CTkButton(mgmt_f, text="Remove", fg_color="red", command=self.remove_action).pack(side="right", padx=5)

        ctrl_f = ctk.CTkFrame(self)
        ctrl_f.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(ctrl_f, text="Save", command=self.save_profile).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_f, text="Load", command=self.load_profile).pack(side="left", padx=5)
        self.play_btn = ctk.CTkButton(ctrl_f, text="RUN ROUTINE", fg_color="green", font=("Arial", 13, "bold"), command=self.run_thread)
        self.play_btn.pack(side="left", fill="x", expand=True, padx=5)
        self.stop_btn = ctk.CTkButton(ctrl_f, text="STOP", fg_color="darkred", state="disabled", command=self.stop_routine)
        self.stop_btn.pack(side="left", padx=5)
        ctk.CTkButton(ctrl_f, text="EXIT", fg_color="#333333", command=self.on_closing).pack(side="right", padx=5)

        self.status = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status.pack(side="bottom", fill="x", padx=20, pady=5)

    def on_closing(self):
        self.is_running = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        self.destroy()
        sys.exit()

    def add_action(self, atype):
        data = None
        if atype == "Single mp3": data = filedialog.askopenfilename(filetypes=[("MP3", "*.mp3")])
        elif atype == "Multiple mp3":
            f = filedialog.askopenfilename(title="Select ANY MP3 in folder", filetypes=[("MP3 Files", "*.mp3")])
            if f: data = [{"path": os.path.dirname(f), "mode": "Random", "repeat": 1}]
        elif atype == "Wait": data = simpledialog.askinteger("Wait", "Seconds:", initialvalue=10)
        elif atype == "Script": data = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        
        if data is not None:
            self.actions.append(Action(atype, data))
            self.update_display()
            if atype == "Multiple mp3":
                self.selected_index.set(len(self.actions)-1)
                self.handle_selection()

    def toggle_wait(self, idx):
        self.actions[idx].wait_on_completion = not self.actions[idx].wait_on_completion
        self.update_display()

    def update_display(self):
        """Redraws main list. Checkbox is hidden for the first action."""
        for w in self.list_frame.winfo_children(): w.destroy()
        for i, a in enumerate(self.actions):
            container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            container.pack(fill="x", pady=5, padx=5)

            ctk.CTkLabel(container, text=f"{i+1}.", font=("Arial", 12, "bold"), width=30).pack(side="left", padx=(5, 0))

            content_f = ctk.CTkFrame(container)
            content_f.pack(side="left", fill="x", expand=True, padx=5)

            name = os.path.basename(str(a.data)) if a.type != "Wait" else f"{a.data} Seconds"
            if a.type == "Multiple mp3":
                name = f"COLLECTION ({len(a.data)} folders)"
            
            ctk.CTkRadioButton(content_f, text=f"{a.type.upper()}: {name}", 
                               variable=self.selected_index, value=i, 
                               font=("Arial", 13, "bold"),
                               command=self.handle_selection).pack(anchor="w", padx=10, pady=(5, 2))

            if a.type == "Multiple mp3":
                for item in a.data:
                    folder_name = os.path.basename(item['path'])
                    folder_detail = f"   ↳ {folder_name} ({item['mode']}, Plays: {item.get('repeat', 1)})"
                    ctk.CTkLabel(content_f, text=folder_detail, font=("Arial", 11, "italic"), text_color="gray").pack(anchor="w", padx=35)

            # NEW LOGIC: Hide checkbox for the first item (Index 0)
            if i > 0:
                cb = ctk.CTkCheckBox(container, text="Wait for Last Action to Finish", width=200,
                                     command=lambda i=i: self.toggle_wait(i))
                if a.wait_on_completion: cb.select()
                cb.pack(side="right", padx=10)

    def move_action(self, d):
        idx = self.selected_index.get()
        if 0 <= idx + d < len(self.actions):
            self.actions[idx], self.actions[idx+d] = self.actions[idx+d], self.actions[idx]
            self.selected_index.set(idx+d)
            self.update_display()

    def remove_action(self):
        idx = self.selected_index.get()
        if 0 <= idx < len(self.actions):
            self.actions.pop(idx)
            self.update_display()

    def edit_action(self): self.handle_selection()

    def handle_selection(self):
        idx = self.selected_index.get()
        if idx != -1:
            a = self.actions[idx]
            if a.type == "Multiple mp3": MultipleMp3Editor(self, a)
            elif a.type == "Wait":
                v = simpledialog.askinteger("Edit", "Seconds:", initialvalue=a.data)
                if v: a.data = v; self.update_display()

    def save_profile(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: audio_engine.save_routine_to_json(f, [{"type": a.type, "data": a.data, "wait": a.wait_on_completion} for a in self.actions])

    def load_profile(self):
        f = filedialog.askopenfilename()
        if f:
            d = audio_engine.load_routine_from_json(f)
            self.actions = [Action(i['type'], i['data'], i.get('wait', True)) for i in d]
            self.update_display()

    def stop_routine(self):
        self.is_running = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.status.configure(text="Stopping...")

    def run_routine(self):
        self.is_running = True
        self.play_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        for a in self.actions:
            if not self.is_running: break
            self.status.configure(text=f"Step: {a.type}")

            target_func = None
            args = []
            
            if a.type == "Single mp3":
                target_func = audio_engine.play_mp3; args = [a.data]
            elif a.type == "Multiple mp3":
                target_func = self.run_multiple_logic; args = [a.data]
            elif a.type == "Wait":
                target_func = audio_engine.wait_action; args = [a.data]
            elif a.type == "Script":
                target_func = audio_engine.run_external_script; args = [a.data]

            if target_func:
                if a.wait_on_completion:
                    target_func(*args)
                else:
                    threading.Thread(target=target_func, args=args, daemon=True).start()

        self.status.configure(text="Ready")
        self.play_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def run_multiple_logic(self, data):
        for item in data:
            if not self.is_running: break
            for _ in range(item.get('repeat', 1)):
                if not self.is_running: break
                audio_engine.process_directory(item['path'], mode=item['mode'])

    def run_thread(self):
        if self.actions: threading.Thread(target=self.run_routine, daemon=True).start()

if __name__ == "__main__":
    app = RoutineApp()
    app.mainloop()
