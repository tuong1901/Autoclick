import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import time
from pynput import mouse, keyboard
import sys
import json
import os
import platform
import subprocess
import re

CONFIG_FILE = "ping_config.json"

class PingMeasurer:
    """Class to measure ping to a server"""
    def __init__(self):
        self.current_ping = 0
        self.is_measuring = False
        self.target_host = "8.8.8.8"  # Google DNS default
        self.measurement_interval = 2  # Update every 2 seconds
        
    def measure_ping(self, host):
        """Measure ping to a host and return latency in ms"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', host]
            
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True, timeout=3)
            
            # Parse ping time from output
            if platform.system().lower() == 'windows':
                # Windows format: "time=XXms" or "time<1ms"
                match = re.search(r'time[=<](\d+)ms', output, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                # Handle "time<1ms" case
                if 'time<1ms' in output.lower():
                    return 1
            else:
                # Linux/Mac format: "time=XX.X ms"
                match = re.search(r'time=(\d+\.?\d*)\s*ms', output, re.IGNORECASE)
                if match:
                    return int(float(match.group(1)))
            
            return None
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            return None
    
    def start_monitoring(self, callback):
        """Start continuous ping monitoring"""
        self.is_measuring = True
        
        def monitor_loop():
            while self.is_measuring:
                ping = self.measure_ping(self.target_host)
                if ping is not None:
                    self.current_ping = ping
                    callback(ping)
                time.sleep(self.measurement_interval)
        
        threading.Thread(target=monitor_loop, daemon=True).start()
    
    def stop_monitoring(self):
        """Stop ping monitoring"""
        self.is_measuring = False

class StepEditor(simpledialog.Dialog):
    def __init__(self, parent, title, current_data):
        self.current_data = current_data
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Click Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value=self.current_data.get('type', 'Left'))
        self.type_combo = ttk.Combobox(master, textvariable=self.type_var, values=["Left", "Right", "Double"], state="readonly")
        self.type_combo.grid(row=0, column=1, pady=5)

        ttk.Label(master, text="Note: Delay is auto-calculated from ping", font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=2, pady=5)

        return self.type_combo

    def apply(self):
        self.result = {
            'type': self.type_var.get()
        }

class PingAutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Ping-Based AutoClicker")
        self.root.geometry("700x600")
        
        # Data
        self.steps = []
        self.is_running = False
        self.capture_mode = False
        self.mouse_controller = mouse.Controller()
        self.ping_measurer = PingMeasurer()
        
        # UI
        self.create_menu()
        self.create_ui()
        
        # Listeners
        self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
        self.kb_listener.start()

        # Auto Load
        self.load_last_session()
        
        # Start ping monitoring
        self.ping_measurer.start_monitoring(self.update_ping_display)

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
        # Ping Settings Frame
        ping_frame = ttk.LabelFrame(self.root, text="Ping Settings", padding=10)
        ping_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Server Selection
        server_row = ttk.Frame(ping_frame)
        server_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(server_row, text="Target Server:").pack(side=tk.LEFT, padx=5)
        self.server_var = tk.StringVar(value="8.8.8.8")
        server_combo = ttk.Combobox(server_row, textvariable=self.server_var, width=15, 
                                     values=["8.8.8.8", "1.1.1.1", "208.67.222.222"])
        server_combo.pack(side=tk.LEFT, padx=5)
        server_combo.bind('<<ComboboxSelected>>', self.on_server_change)
        
        ttk.Button(server_row, text="Apply", command=self.on_server_change).pack(side=tk.LEFT, padx=5)
        
        # Ping Display
        ping_display = ttk.Frame(ping_frame)
        ping_display.pack(fill=tk.X, pady=5)
        
        ttk.Label(ping_display, text="Current Ping:").pack(side=tk.LEFT, padx=5)
        self.ping_label = ttk.Label(ping_display, text="-- ms", font=('Arial', 12, 'bold'), foreground='green')
        self.ping_label.pack(side=tk.LEFT, padx=5)
        
        # Multiplier
        mult_row = ttk.Frame(ping_frame)
        mult_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(mult_row, text="Delay Multiplier:").pack(side=tk.LEFT, padx=5)
        self.multiplier_var = tk.DoubleVar(value=1.0)
        mult_spin = ttk.Spinbox(mult_row, from_=0.1, to=10.0, increment=0.1, 
                                textvariable=self.multiplier_var, width=10)
        mult_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(mult_row, text="(Actual Delay = Ping × Multiplier)").pack(side=tk.LEFT, padx=5)
        
        # Fallback Delay
        fallback_row = ttk.Frame(ping_frame)
        fallback_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(fallback_row, text="Fallback Delay (ms):").pack(side=tk.LEFT, padx=5)
        self.fallback_var = tk.IntVar(value=100)
        ttk.Entry(fallback_row, textvariable=self.fallback_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(fallback_row, text="(When ping fails)", font=('Arial', 8, 'italic')).pack(side=tk.LEFT, padx=5)
        
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

        columns = ("no", "coords", "action")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("no", text="#")
        self.tree.column("no", width=50, anchor=tk.CENTER)
        
        self.tree.heading("coords", text="Coordinates (X, Y)")
        self.tree.column("coords", width=150, anchor=tk.CENTER)
        
        self.tree.heading("action", text="Action")
        self.tree.column("action", width=100, anchor=tk.CENTER)

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
        self.status_var = tk.StringVar(value="Ready. Monitoring ping...")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def update_ping_display(self, ping_ms):
        """Update ping display on UI thread"""
        def update():
            self.ping_label.config(text=f"{ping_ms} ms")
            # Color code based on ping
            if ping_ms < 50:
                self.ping_label.config(foreground='green')
            elif ping_ms < 100:
                self.ping_label.config(foreground='orange')
            else:
                self.ping_label.config(foreground='red')
        
        self.root.after(0, update)
    
    def on_server_change(self, event=None):
        """Change target server for ping"""
        new_server = self.server_var.get()
        self.ping_measurer.target_host = new_server
        self.status_var.set(f"Changed ping target to {new_server}")

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
                step['type']
            ))

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        
        index = self.tree.index(item[0])
        step = self.steps[index]
        
        editor = StepEditor(self.root, "Edit Step", step)
        if editor.result:
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
        self.status_var.set("Running with ping-based delays...")
        
        if self.capture_mode:
            self.toggle_capture()

        threading.Thread(target=self.run_loop, daemon=True).start()

    def stop_clicking(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Stopped.")

    def get_current_delay(self):
        """Calculate current delay based on ping and multiplier"""
        if self.ping_measurer.current_ping > 0:
            delay_ms = self.ping_measurer.current_ping * self.multiplier_var.get()
            return max(1, int(delay_ms))  # Minimum 1ms
        else:
            return self.fallback_var.get()

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
                
                # Dynamic delay based on current ping
                delay_ms = self.get_current_delay()
                time.sleep(delay_ms / 1000.0)
            
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
            data = {
                'steps': self.steps,
                'settings': {
                    'server': self.server_var.get(),
                    'multiplier': self.multiplier_var.get(),
                    'fallback': self.fallback_var.get()
                }
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
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
                data = json.load(f)
            
            # Support both old and new format
            if isinstance(data, list):
                self.steps = data
            else:
                self.steps = data.get('steps', [])
                settings = data.get('settings', {})
                if settings:
                    self.server_var.set(settings.get('server', '8.8.8.8'))
                    self.multiplier_var.set(settings.get('multiplier', 1.0))
                    self.fallback_var.set(settings.get('fallback', 100))
                    self.on_server_change()
            
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
            pass

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
        self.ping_measurer.stop_monitoring()
        self.kb_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PingAutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
