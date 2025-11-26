import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import time
from pynput import mouse, keyboard
import sys
import json
import os

CONFIG_FILE = "config.json"

class StepEditor(simpledialog.Dialog):
    def __init__(self, parent, title, current_data):
        self.current_data = current_data
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Delay (ms):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.IntVar(value=self.current_data.get('delay', 1000))
        ttk.Entry(master, textvariable=self.delay_var).grid(row=0, column=1, pady=5)

        ttk.Label(master, text="Click Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value=self.current_data.get('type', 'Left'))
        self.type_combo = ttk.Combobox(master, textvariable=self.type_var, values=["Left", "Right", "Double"], state="readonly")
        self.type_combo.grid(row=1, column=1, pady=5)

        return self.type_combo # initial focus

    def apply(self):
        self.result = {
            'delay': self.delay_var.get(),
            'type': self.type_var.get()
        }

class AutoClickerV2:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Auto Clicker")
        self.root.geometry("600x500")
        
        # Data
        self.steps = [] # List of dicts: {x, y, delay, type}
        self.is_running = False
        self.capture_mode = False
        self.mouse_controller = mouse.Controller()
        
        # UI
        self.create_menu()
        self.create_ui()
        
        # Listeners
        self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
        self.kb_listener.start()

        # Auto Load
        self.load_last_session()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Script...", command=self.load_script)
        file_menu.add_command(label="Save Script As...", command=self.save_script)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)

    def create_ui(self):
        # Top Toolbar
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(fill=tk.X)

        self.btn_capture = ttk.Button(toolbar, text="Enable Capture (F3)", command=self.toggle_capture)
        self.btn_capture.pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text="Clear All", command=self.clear_steps).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_step).pack(side=tk.RIGHT, padx=5)

        # Main Table
        tree_frame = ttk.Frame(self.root, padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("no", "coords", "action", "delay")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("no", text="#")
        self.tree.column("no", width=50, anchor=tk.CENTER)
        
        self.tree.heading("coords", text="Coordinates (X, Y)")
        self.tree.column("coords", width=150, anchor=tk.CENTER)
        
        self.tree.heading("action", text="Action")
        self.tree.column("action", width=100, anchor=tk.CENTER)
        
        self.tree.heading("delay", text="Delay After (ms)")
        self.tree.column("delay", width=100, anchor=tk.CENTER)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self.on_double_click)

        # Bottom Controls
        bottom_frame = ttk.LabelFrame(self.root, text="Execution Control", padding=10)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        # Loop Settings
        loop_frame = ttk.Frame(bottom_frame)
        loop_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(loop_frame, text="Loops (0 = Infinite):").pack(side=tk.LEFT)
        self.loops_var = tk.StringVar(value="0")
        ttk.Entry(loop_frame, textvariable=self.loops_var, width=10).pack(side=tk.LEFT, padx=5)

        # Start/Stop
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.btn_start = ttk.Button(btn_frame, text="START (F6)", command=self.start_clicking)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_stop = ttk.Button(btn_frame, text="STOP (F7)", command=self.stop_clicking, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Press 'Enable Capture' to start adding points.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_capture(self):
        self.capture_mode = not self.capture_mode
        if self.capture_mode:
            self.btn_capture.config(text="Capture ON (Press F3)")
            self.status_var.set("Capture Mode ON. Move mouse and press F3 to save coordinates.")
        else:
            self.btn_capture.config(text="Enable Capture (F3)")
            self.status_var.set("Capture Mode OFF.")

    def add_step(self, x, y):
        step = {
            'x': x,
            'y': y,
            'delay': 1000, # Default 1s
            'type': 'Left'
        }
        self.steps.append(step)
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, step in enumerate(self.steps):
            self.tree.insert("", tk.END, values=(
                i + 1,
                f"{step['x']}, {step['y']}",
                step['type'],
                f"{step['delay']} ms"
            ))

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        
        # Get index
        index = self.tree.index(item[0])
        step = self.steps[index]
        
        # Open Edit Dialog
        editor = StepEditor(self.root, "Edit Step", step)
        if editor.result:
            step['delay'] = editor.result['delay']
            step['type'] = editor.result['type']
            self.refresh_table()

    def delete_step(self):
        item = self.tree.selection()
        if not item: return
        index = self.tree.index(item[0])
        del self.steps[index]
        self.refresh_table()

    def clear_steps(self):
        self.steps = []
        self.refresh_table()

    def on_key_press(self, key):
        try:
            if key == key.f3 and self.capture_mode:
                x, y = self.mouse_controller.position
                # Schedule UI update on main thread
                self.root.after(0, self.add_step, x, y)
            elif key == key.f6:
                self.root.after(0, self.start_clicking)
            elif key == key.f7:
                self.root.after(0, self.stop_clicking)
        except AttributeError:
            pass

    def start_clicking(self):
        if self.is_running: return
        if not self.steps:
            messagebox.showwarning("Empty", "Please add some coordinates first.")
            return

        try:
            self.total_loops = int(self.loops_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid Loop Count")
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Running...")
        
        # Disable capture during run
        if self.capture_mode:
            self.toggle_capture()

        threading.Thread(target=self.run_loop, daemon=True).start()

    def stop_clicking(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Stopped.")

    def run_loop(self):
        loop_count = 0
        while self.is_running:
            if self.total_loops > 0 and loop_count >= self.total_loops:
                break
            
            for step in self.steps:
                if not self.is_running: break
                
                # Move
                self.mouse_controller.position = (step['x'], step['y'])
                
                # Click
                btn = mouse.Button.left
                if step['type'] == 'Right':
                    btn = mouse.Button.right
                
                if step['type'] == 'Double':
                    self.mouse_controller.click(btn, 2)
                else:
                    self.mouse_controller.click(btn, 1)
                
                # Delay
                time.sleep(step['delay'] / 1000.0)
            
            loop_count += 1
        
        self.is_running = False
        self.root.after(0, self.stop_clicking)

    # --- Persistence Methods ---
    def save_script(self):
        if not self.steps:
            messagebox.showwarning("Warning", "Nothing to save.")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.steps, f, indent=4)
            self.status_var.set(f"Saved to {os.path.basename(file_path)}")
            self.update_config(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def load_script(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        
        self.load_from_file(file_path)

    def load_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                self.steps = json.load(f)
            self.refresh_table()
            self.status_var.set(f"Loaded {os.path.basename(file_path)}")
            self.update_config(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def update_config(self, file_path):
        try:
            config = {'last_file': file_path}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except:
            pass # Ignore config errors

    def load_last_session(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    last_file = config.get('last_file')
                    if last_file and os.path.exists(last_file):
                        self.load_from_file(last_file)
            except:
                pass

    def on_close(self):
        self.is_running = False
        self.kb_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerV2(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
