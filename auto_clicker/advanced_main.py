import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, Menu
import threading
import time
from pynput import mouse, keyboard
import json
import os
import platform
import subprocess
import re
import random
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, List

CONFIG_FILE = "advanced_config.json"
PROFILES_DIR = "profiles"

class PingMeasurer:
    """Real-time ping monitoring"""
    def __init__(self):
        self.current_ping = 0
        self.is_measuring = False
        self.target_host = "8.8.8.8"
        self.measurement_interval = 2
        self.ping_history = []
        
    def measure_ping(self, host):
        """Measure ping to host and return latency in ms"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', host]
            
            # Hide console window on Windows
            startupinfo = None
            creationflags = 0
            if platform.system().lower() == 'windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            output = subprocess.check_output(
                command, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True, 
                timeout=3,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if platform.system().lower() == 'windows':
                match = re.search(r'time[=<](\d+)ms', output, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                if 'time<1ms' in output.lower():
                    return 1
            else:
                match = re.search(r'time=(\d+\.?\d*)\s*ms', output, re.IGNORECASE)
                if match:
                    return int(float(match.group(1)))
            return None
        except:
            return None
    
    def start_monitoring(self, callback):
        """Start continuous ping monitoring"""
        self.is_measuring = True
        
        def monitor_loop():
            while self.is_measuring:
                ping = self.measure_ping(self.target_host)
                if ping is not None:
                    self.current_ping = ping
                    self.ping_history.append(ping)
                    if len(self.ping_history) > 100:
                        self.ping_history.pop(0)
                    callback(ping)
                time.sleep(self.measurement_interval)
        
        threading.Thread(target=monitor_loop, daemon=True).start()
    
    def get_average_ping(self):
        """Get average ping from history"""
        if not self.ping_history:
            return 0
        return sum(self.ping_history) / len(self.ping_history)
    
    def stop_monitoring(self):
        """Stop ping monitoring"""
        self.is_measuring = False

class ClickStatistics:
    """Track clicking statistics"""
    def __init__(self):
        self.total_clicks = 0
        self.start_time = None
        self.click_positions = defaultdict(int)
        self.reset()
    
    def reset(self):
        self.total_clicks = 0
        self.start_time = datetime.now()
        self.click_positions.clear()
    
    def record_click(self, x, y):
        self.total_clicks += 1
        pos_key = f"{x},{y}"
        self.click_positions[pos_key] += 1
    
    def get_session_duration(self):
        if self.start_time:
            delta = datetime.now() - self.start_time
            return delta.total_seconds()
        return 0
    
    def get_clicks_per_minute(self):
        duration = self.get_session_duration()
        if duration > 0:
            return (self.total_clicks / duration) * 60
        return 0

class AdvancedStepEditor(simpledialog.Dialog):
    """Enhanced step editor with more options"""
    def __init__(self, parent, title, current_data):
        self.current_data = current_data
        super().__init__(parent, title)

    def body(self, master):
        # Click Type
        ttk.Label(master, text="Click Type:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.type_var = tk.StringVar(value=self.current_data.get('type', 'Left'))
        ttk.Combobox(master, textvariable=self.type_var, 
                    values=["Left", "Right", "Double", "Triple"], 
                    state="readonly").grid(row=0, column=1, pady=5, padx=5, sticky=tk.EW)
        
        # Separator
        ttk.Separator(master, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Delay Mode Selection
        ttk.Label(master, text="Delay Mode:", font=('Arial', 9, 'bold')).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5,0), padx=5)
        
        # Ping-based delay with custom multiplier
        ping_frame = ttk.LabelFrame(master, text="Ping-Based Delay", padding=5)
        ping_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(ping_frame, text="Ping Multiplier:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ping_multiplier_var = tk.DoubleVar(value=self.current_data.get('ping_multiplier', 0.0))
        mult_spinbox = ttk.Spinbox(ping_frame, from_=0.0, to=10000.0, increment=0.5, 
                                    textvariable=self.ping_multiplier_var, width=10)
        mult_spinbox.grid(row=0, column=1, pady=2, sticky=tk.W)
        
        ttk.Label(ping_frame, text="(0 = use global)", font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Label(ping_frame, text="Ex: 3.0 → delay = ping × 3", font=('Arial', 8, 'italic')).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # OR
        ttk.Label(master, text="── OR ──", font=('Arial', 8)).grid(row=4, column=0, columnspan=2, pady=5)
        
        # Fixed delay
        fixed_frame = ttk.LabelFrame(master, text="Fixed Delay (Ignore Ping)", padding=5)
        fixed_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(fixed_frame, text="Custom Delay (ms):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.custom_delay_var = tk.IntVar(value=self.current_data.get('custom_delay', 0))
        ttk.Entry(fixed_frame, textvariable=self.custom_delay_var, width=10).grid(row=0, column=1, pady=2, sticky=tk.W)
        ttk.Label(fixed_frame, text="(0 = use ping mode)", font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Separator
        ttk.Separator(master, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Click Count
        ttk.Label(master, text="Click Count:").grid(row=7, column=0, sticky=tk.W, pady=5, padx=5)
        self.count_var = tk.IntVar(value=self.current_data.get('count', 1))
        ttk.Spinbox(master, from_=1, to=10, textvariable=self.count_var, width=10).grid(row=7, column=1, pady=5, padx=5, sticky=tk.W)
        
        return None

    def apply(self):
        self.result = {
            'type': self.type_var.get(),
            'ping_multiplier': self.ping_multiplier_var.get(),
            'custom_delay': self.custom_delay_var.get(),
            'count': self.count_var.get()
        }

class ProfileManager:
    """Manage multiple clicking profiles"""
    def __init__(self):
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR)
    
    def get_profiles(self) -> List[str]:
        """Get list of saved profiles"""
        if not os.path.exists(PROFILES_DIR):
            return []
        return [f[:-5] for f in os.listdir(PROFILES_DIR) if f.endswith('.json')]
    
    def save_profile(self, name: str, data: dict):
        """Save a profile"""
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_profile(self, name: str) -> Optional[dict]:
        """Load a profile"""
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return None
    
    def delete_profile(self, name: str):
        """Delete a profile"""
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)

class AdvancedAutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("CTAutoClick Pro - Advanced Edition")
        self.root.geometry("900x700")
        
        # Core Data
        self.steps = []
        self.is_running = False
        self.is_paused = False
        self.capture_mode = False
        self.mouse_controller = mouse.Controller()
        
        # Advanced Features
        self.ping_measurer = PingMeasurer()
        self.statistics = ClickStatistics()
        self.profile_manager = ProfileManager()
        self.current_profile = "Default"
        
        # Settings
        self.randomize_position = tk.BooleanVar(value=False)
        self.randomize_timing = tk.BooleanVar(value=False)
        self.position_variance = tk.IntVar(value=5)
        self.timing_variance = tk.IntVar(value=10)
        self.use_ping_delay = tk.BooleanVar(value=True)
        self.ping_multiplier = tk.DoubleVar(value=1.0)
        self.fallback_delay = tk.IntVar(value=100)
        self.server_var = tk.StringVar(value="8.8.8.8")
        
        # UI
        self.create_menu()
        self.create_ui()
        
        # Keyboard Listener
        self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
        self.kb_listener.start()
        
        # Start Services
        self.ping_measurer.start_monitoring(self.update_ping_display)
        self.load_last_session()
        
        # Update stats display
        self.update_statistics_display()

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Script", command=self.new_script, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Script...", command=self.load_script, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Script", command=self.quick_save_script, accelerator="Ctrl+S")
        file_menu.add_command(label="Save Script As...", command=self.save_script)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close, accelerator="Alt+F4")
        
        # Edit Menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add Step Manually...", command=self.add_step_manually)
        edit_menu.add_command(label="Edit Selected", command=self.edit_selected_step)
        edit_menu.add_command(label="Delete Selected", command=self.delete_step, accelerator="Delete")
        edit_menu.add_command(label="Clear All", command=self.clear_steps, accelerator="Ctrl+Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="Move Up", command=lambda: self.move_step(-1))
        edit_menu.add_command(label="Move Down", command=lambda: self.move_step(1))
        
        # Profiles Menu
        profiles_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Profiles", menu=profiles_menu)
        profiles_menu.add_command(label="Save as Profile...", command=self.save_as_profile)
        profiles_menu.add_command(label="Load Profile...", command=self.load_profile_dialog)
        profiles_menu.add_command(label="Manage Profiles...", command=self.manage_profiles)
        
        # Help Menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Hotkeys Reference", command=self.show_hotkeys)
        help_menu.add_command(label="About", command=self.show_about)

    def create_ui(self):
        # Main container with left and right panels
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel - Steps Table
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=3)
        
        self.create_steps_panel(left_panel)
        
        # Right Panel - Settings
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=2)
        
        self.create_settings_panel(right_panel)
        
        # Bottom - Execution Controls
        bottom_frame = ttk.LabelFrame(self.root, text="Execution Control", padding=10)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.create_execution_controls(bottom_frame)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Press F3 to start capturing points.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, 
                 anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def create_steps_panel(self, parent):
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=5)
        
        self.btn_capture = ttk.Button(toolbar, text="🎯 Enable Capture (F3)", 
                                      command=self.toggle_capture)
        self.btn_capture.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text="➕ Add", command=self.add_step_manually).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ Edit", command=self.edit_selected_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ Delete", command=self.delete_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🧹 Clear All", command=self.clear_steps).pack(side=tk.LEFT, padx=2)
        
        # Table Frame
        table_frame = ttk.LabelFrame(parent, text="Click Steps", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview
        columns = ("no", "coords", "action", "delay", "count")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", 
                                selectmode="browse", height=15)
        
        self.tree.heading("no", text="#")
        self.tree.column("no", width=40, anchor=tk.CENTER)
        
        self.tree.heading("coords", text="Position (X, Y)")
        self.tree.column("coords", width=120, anchor=tk.CENTER)
        
        self.tree.heading("action", text="Action")
        self.tree.column("action", width=80, anchor=tk.CENTER)
        
        self.tree.heading("delay", text="Delay")
        self.tree.column("delay", width=80, anchor=tk.CENTER)
        
        self.tree.heading("count", text="Count")
        self.tree.column("count", width=50, anchor=tk.CENTER)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<Double-1>", lambda e: self.edit_selected_step())

    def create_settings_panel(self, parent):
        # Create notebook for organized settings
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Ping Settings
        ping_tab = ttk.Frame(notebook, padding=10)
        notebook.add(ping_tab, text="⚡ Ping")
        self.create_ping_settings(ping_tab)
        
        # Tab 2: Randomization
        random_tab = ttk.Frame(notebook, padding=10)
        notebook.add(random_tab, text="🎲 Randomize")
        self.create_randomization_settings(random_tab)
        
        # Tab 3: Statistics
        stats_tab = ttk.Frame(notebook, padding=10)
        notebook.add(stats_tab, text="📊 Statistics")
        self.create_statistics_panel(stats_tab)

    def create_ping_settings(self, parent):
        # Enable/Disable Ping
        ttk.Checkbutton(parent, text="Use Ping-Based Delays", 
                       variable=self.use_ping_delay).pack(anchor=tk.W, pady=5)
        
        # Server Selection
        server_frame = ttk.LabelFrame(parent, text="Target Server", padding=10)
        server_frame.pack(fill=tk.X, pady=5)
        
        servers = [
            ("Google DNS", "8.8.8.8"),
            ("Cloudflare", "1.1.1.1"),
            ("OpenDNS", "208.67.222.222"),
        ]
        
        for name, ip in servers:
            ttk.Radiobutton(server_frame, text=f"{name} ({ip})", 
                           variable=self.server_var, value=ip,
                           command=self.on_server_change).pack(anchor=tk.W)
        
        custom_frame = ttk.Frame(server_frame)
        custom_frame.pack(fill=tk.X, pady=5)
        ttk.Label(custom_frame, text="Custom:").pack(side=tk.LEFT)
        custom_entry = ttk.Entry(custom_frame, textvariable=self.server_var, width=15)
        custom_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(custom_frame, text="Apply", command=self.on_server_change).pack(side=tk.LEFT)
        
        # Ping Display
        ping_display = ttk.LabelFrame(parent, text="Current Status", padding=10)
        ping_display.pack(fill=tk.X, pady=5)
        
        self.ping_label = ttk.Label(ping_display, text="-- ms", 
                                    font=('Arial', 16, 'bold'), foreground='green')
        self.ping_label.pack()
        
        self.avg_ping_label = ttk.Label(ping_display, text="Avg: -- ms", 
                                       font=('Arial', 10))
        self.avg_ping_label.pack()
        
        # Multiplier
        mult_frame = ttk.LabelFrame(parent, text="Delay Settings", padding=10)
        mult_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mult_frame, text="Multiplier:").pack(anchor=tk.W)
        ttk.Scale(mult_frame, from_=0.1, to=1000.0, variable=self.ping_multiplier,
                 orient=tk.HORIZONTAL).pack(fill=tk.X)
        ttk.Label(mult_frame, textvariable=self.ping_multiplier, 
                 font=('Arial', 10, 'bold')).pack()
        
        ttk.Label(mult_frame, text="Fallback Delay (ms):").pack(anchor=tk.W, pady=(10,0))
        ttk.Entry(mult_frame, textvariable=self.fallback_delay).pack(fill=tk.X)

    def create_randomization_settings(self, parent):
        # Position Randomization
        pos_frame = ttk.LabelFrame(parent, text="Position Randomization", padding=10)
        pos_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(pos_frame, text="Enable Position Randomization",
                       variable=self.randomize_position).pack(anchor=tk.W)
        
        ttk.Label(pos_frame, text="Max Variance (pixels):").pack(anchor=tk.W, pady=(10,0))
        ttk.Scale(pos_frame, from_=1, to=50, variable=self.position_variance,
                 orient=tk.HORIZONTAL).pack(fill=tk.X)
        ttk.Label(pos_frame, textvariable=self.position_variance).pack()
        
        # Timing Randomization
        time_frame = ttk.LabelFrame(parent, text="Timing Randomization", padding=10)
        time_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(time_frame, text="Enable Timing Randomization",
                       variable=self.randomize_timing).pack(anchor=tk.W)
        
        ttk.Label(time_frame, text="Variance (%):").pack(anchor=tk.W, pady=(10,0))
        ttk.Scale(time_frame, from_=1, to=50, variable=self.timing_variance,
                 orient=tk.HORIZONTAL).pack(fill=tk.X)
        ttk.Label(time_frame, textvariable=self.timing_variance).pack()
        
        # Info
        info = ttk.Label(parent, text="ℹ️ Randomization makes clicking patterns\nmore natural and less detectable",
                        justify=tk.CENTER, foreground='blue')
        info.pack(pady=20)

    def create_statistics_panel(self, parent):
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # Stats Display
        self.stats_total = ttk.Label(stats_frame, text="Total Clicks: 0", 
                                    font=('Arial', 12, 'bold'))
        self.stats_total.pack(pady=5)
        
        self.stats_duration = ttk.Label(stats_frame, text="Duration: 0s")
        self.stats_duration.pack(pady=5)
        
        self.stats_cpm = ttk.Label(stats_frame, text="Clicks/min: 0")
        self.stats_cpm.pack(pady=5)
        
        # Control Buttons
        ttk.Button(stats_frame, text="Reset Statistics", 
                  command=self.reset_statistics).pack(pady=20)

    def create_execution_controls(self, parent):
        # Loop Settings
        loop_frame = ttk.Frame(parent)
        loop_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(loop_frame, text="Loops (0 = Infinite):").pack(side=tk.LEFT, padx=5)
        self.loops_var = tk.StringVar(value="0")
        ttk.Entry(loop_frame, textvariable=self.loops_var, width=10).pack(side=tk.LEFT)
        
        ttk.Label(loop_frame, text="Current Profile:").pack(side=tk.LEFT, padx=(20,5))
        self.profile_label = ttk.Label(loop_frame, text=self.current_profile,
                                      font=('Arial', 10, 'bold'), foreground='blue')
        self.profile_label.pack(side=tk.LEFT)
        
        # Control Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = ttk.Button(btn_frame, text="▶️ START (F6)", 
                                    command=self.start_clicking)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_pause = ttk.Button(btn_frame, text="⏸️ PAUSE (F8)", 
                                   command=self.pause_clicking, state=tk.DISABLED)
        self.btn_pause.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_stop = ttk.Button(btn_frame, text="⏹️ STOP (F7)", 
                                  command=self.stop_clicking, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    # ===== Event Handlers =====
    
    def update_ping_display(self, ping_ms):
        """Update ping display on UI thread"""
        def update():
            self.ping_label.config(text=f"{ping_ms} ms")
            avg = int(self.ping_measurer.get_average_ping())
            self.avg_ping_label.config(text=f"Avg: {avg} ms")
            
            # Color coding
            if ping_ms < 50:
                self.ping_label.config(foreground='green')
            elif ping_ms < 100:
                self.ping_label.config(foreground='orange')
            else:
                self.ping_label.config(foreground='red')
        
        self.root.after(0, update)
    
    def on_server_change(self):
        """Change ping target server"""
        new_server = self.server_var.get()
        self.ping_measurer.target_host = new_server
        self.status_var.set(f"Ping target changed to {new_server}")
    
    def toggle_capture(self):
        """Toggle coordinate capture mode"""
        self.capture_mode = not self.capture_mode
        if self.capture_mode:
            self.btn_capture.config(text="🎯 Capture ON (F3)")
            self.status_var.set("Capture Mode: Move mouse and press F3 to save position.")
        else:
            self.btn_capture.config(text="🎯 Enable Capture (F3)")
            self.status_var.set("Capture Mode OFF")
    
    def add_step(self, x, y):
        """Add a new click step"""
        step = {
            'x': x,
            'y': y,
            'type': 'Left',
            'ping_multiplier': 0.0,  # 0 = use global
            'custom_delay': 0,
            'count': 1
        }
        self.steps.append(step)
        self.refresh_table()
        self.status_var.set(f"Added step at ({x}, {y})")
    
    def add_step_manually(self):
        """Add step with manual coordinate entry"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Step Manually")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="X Coordinate:").grid(row=0, column=0, padx=10, pady=5)
        x_var = tk.IntVar(value=0)
        ttk.Entry(dialog, textvariable=x_var).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="Y Coordinate:").grid(row=1, column=0, padx=10, pady=5)
        y_var = tk.IntVar(value=0)
        ttk.Entry(dialog, textvariable=y_var).grid(row=1, column=1, padx=10, pady=5)
        
        def add():
            self.add_step(x_var.get(), y_var.get())
            dialog.destroy()
        
        ttk.Button(dialog, text="Add", command=add).grid(row=2, column=0, columnspan=2, pady=20)
    
    def edit_selected_step(self):
        """Edit the selected step"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to edit.")
            return
        
        index = self.tree.index(selection[0])
        step = self.steps[index]
        
        editor = AdvancedStepEditor(self.root, "Edit Step", step)
        if editor.result:
            step.update(editor.result)
            self.refresh_table()
    
    def delete_step(self):
        """Delete selected step"""
        selection = self.tree.selection()
        if not selection:
            return
        index = self.tree.index(selection[0])
        del self.steps[index]
        self.refresh_table()
        self.status_var.set("Step deleted")
    
    def clear_steps(self):
        """Clear all steps"""
        if messagebox.askyesno("Confirm", "Clear all steps?"):
            self.steps = []
            self.refresh_table()
            self.status_var.set("All steps cleared")
    
    def move_step(self, direction):
        """Move step up or down"""
        selection = self.tree.selection()
        if not selection:
            return
        
        index = self.tree.index(selection[0])
        new_index = index + direction
        
        if 0 <= new_index < len(self.steps):
            self.steps[index], self.steps[new_index] = self.steps[new_index], self.steps[index]
            self.refresh_table()
            self.tree.selection_set(self.tree.get_children()[new_index])
    
    def refresh_table(self):
        """Refresh the steps table"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, step in enumerate(self.steps):
            # Display delay info
            if step.get('custom_delay', 0) > 0:
                delay_text = f"{step.get('custom_delay', 0)} ms"
            elif step.get('ping_multiplier', 0.0) > 0:
                delay_text = f"Ping×{step.get('ping_multiplier')}"
            else:
                delay_text = "Ping (global)"
            
            self.tree.insert("", tk.END, values=(
                i + 1,
                f"({step['x']}, {step['y']})",
                step.get('type', 'Left'),
                delay_text,
                step.get('count', 1)
            ))
    
    def on_key_press(self, key):
        """Handle keyboard shortcuts"""
        try:
            if key == keyboard.Key.f3 and self.capture_mode:
                x, y = self.mouse_controller.position
                self.root.after(0, self.add_step, x, y)
            elif key == keyboard.Key.f6:
                self.root.after(0, self.start_clicking)
            elif key == keyboard.Key.f7:
                self.root.after(0, self.stop_clicking)
            elif key == keyboard.Key.f8:
                self.root.after(0, self.pause_clicking)
        except AttributeError:
            pass
    
    # ===== Execution Control =====
    
    def start_clicking(self):
        """Start the auto-clicking sequence"""
        if self.is_running:
            return
        
        if not self.steps:
            messagebox.showwarning("No Steps", "Please add some click steps first.")
            return
        
        try:
            self.total_loops = int(self.loops_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Loop count must be a number.")
            return
        
        self.is_running = True
        self.is_paused = False
        self.statistics.reset()
        
        self.btn_start.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Running...")
        
        if self.capture_mode:
            self.toggle_capture()
        
        threading.Thread(target=self.run_loop, daemon=True).start()
    
    def pause_clicking(self):
        """Pause/Resume clicking"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="▶️ RESUME (F8)")
            self.status_var.set("Paused")
        else:
            self.btn_pause.config(text="⏸️ PAUSE (F8)")
            self.status_var.set("Running...")
    
    def stop_clicking(self):
        """Stop clicking"""
        self.is_running = False
        self.is_paused = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED, text="⏸️ PAUSE (F8)")
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Stopped")
    
    def get_current_delay(self, step=None):
        """Calculate delay based on settings and optional step-specific multiplier"""
        if self.use_ping_delay.get() and self.ping_measurer.current_ping > 0:
            # Check if step has its own multiplier
            if step and step.get('ping_multiplier', 0.0) > 0:
                # Use step-specific multiplier
                delay = self.ping_measurer.current_ping * step.get('ping_multiplier')
            else:
                # Use global multiplier
                delay = self.ping_measurer.current_ping * self.ping_multiplier.get()
        else:
            delay = self.fallback_delay.get()
        
        # Apply randomization
        if self.randomize_timing.get():
            variance = self.timing_variance.get() / 100.0
            delay *= random.uniform(1 - variance, 1 + variance)
        
        return max(1, int(delay))
    
    def get_randomized_position(self, x, y):
        """Get randomized position if enabled"""
        if self.randomize_position.get():
            variance = self.position_variance.get()
            x += random.randint(-variance, variance)
            y += random.randint(-variance, variance)
        return x, y
    
    def run_loop(self):
        """Main clicking loop"""
        loop_count = 0
        
        while self.is_running:
            if self.total_loops > 0 and loop_count >= self.total_loops:
                break
            
            for step in self.steps:
                if not self.is_running:
                    break
                
                # Wait while paused
                while self.is_paused and self.is_running:
                    time.sleep(0.1)
                
                if not self.is_running:
                    break
                
                # Get position (with randomization)
                x, y = self.get_randomized_position(step['x'], step['y'])
                
                # Move mouse
                self.mouse_controller.position = (x, y)
                
                # Determine button
                btn = mouse.Button.left
                if step.get('type') == 'Right':
                    btn = mouse.Button.right
                
                # Click
                click_count = 1
                if step.get('type') == 'Double':
                    click_count = 2
                elif step.get('type') == 'Triple':
                    click_count = 3
                else:
                    click_count = step.get('count', 1)
                
                for _ in range(click_count):
                    self.mouse_controller.click(btn, 1)
                    self.statistics.record_click(x, y)
                    time.sleep(0.05)  # Small delay between multiple clicks
                
                # Update stats display
                self.root.after(0, self.update_statistics_display)
                
                # Delay
                if step.get('custom_delay', 0) > 0:
                    delay = step['custom_delay']
                else:
                    delay = self.get_current_delay(step)
                
                time.sleep(delay / 1000.0)
            
            loop_count += 1
        
        self.is_running = False
        self.root.after(0, self.stop_clicking)
    
    def update_statistics_display(self):
        """Update statistics display"""
        self.stats_total.config(text=f"Total Clicks: {self.statistics.total_clicks}")
        duration = int(self.statistics.get_session_duration())
        self.stats_duration.config(text=f"Duration: {duration}s")
        cpm = int(self.statistics.get_clicks_per_minute())
        self.stats_cpm.config(text=f"Clicks/min: {cpm}")
    
    def reset_statistics(self):
        """Reset statistics"""
        self.statistics.reset()
        self.update_statistics_display()
        self.status_var.set("Statistics reset")
    
    # ===== Profile Management =====
    
    def save_as_profile(self):
        """Save current setup as a profile"""
        name = simpledialog.askstring("Save Profile", "Enter profile name:")
        if name:
            data = {
                'steps': self.steps,
                'settings': {
                    'server': self.server_var.get(),
                    'ping_multiplier': self.ping_multiplier.get(),
                    'fallback_delay': self.fallback_delay.get(),
                    'use_ping_delay': self.use_ping_delay.get(),
                    'randomize_position': self.randomize_position.get(),
                    'randomize_timing': self.randomize_timing.get(),
                    'position_variance': self.position_variance.get(),
                    'timing_variance': self.timing_variance.get()
                }
            }
            self.profile_manager.save_profile(name, data)
            self.current_profile = name
            self.profile_label.config(text=name)
            self.status_var.set(f"Profile '{name}' saved")
    
    def load_profile_dialog(self):
        """Load a profile"""
        profiles = self.profile_manager.get_profiles()
        if not profiles:
            messagebox.showinfo("No Profiles", "No saved profiles found.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Profile")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select Profile:", font=('Arial', 12, 'bold')).pack(pady=10)
        
        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for profile in profiles:
            listbox.insert(tk.END, profile)
        
        def load():
            selection = listbox.curselection()
            if selection:
                profile_name = listbox.get(selection[0])
                self.load_profile(profile_name)
                dialog.destroy()
        
        ttk.Button(dialog, text="Load", command=load).pack(pady=10)
    
    def load_profile(self, name):
        """Load a specific profile"""
        data = self.profile_manager.load_profile(name)
        if data:
            self.steps = data.get('steps', [])
            settings = data.get('settings', {})
            
            self.server_var.set(settings.get('server', '8.8.8.8'))
            self.ping_multiplier.set(settings.get('ping_multiplier', 1.0))
            self.fallback_delay.set(settings.get('fallback_delay', 100))
            self.use_ping_delay.set(settings.get('use_ping_delay', True))
            self.randomize_position.set(settings.get('randomize_position', False))
            self.randomize_timing.set(settings.get('randomize_timing', False))
            self.position_variance.set(settings.get('position_variance', 5))
            self.timing_variance.set(settings.get('timing_variance', 10))
            
            self.on_server_change()
            self.refresh_table()
            self.current_profile = name
            self.profile_label.config(text=name)
            self.status_var.set(f"Loaded profile '{name}'")
    
    def manage_profiles(self):
        """Open profile management dialog"""
        profiles = self.profile_manager.get_profiles()
        if not profiles:
            messagebox.showinfo("No Profiles", "No saved profiles found.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Profiles")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Saved Profiles", font=('Arial', 12, 'bold')).pack(pady=10)
        
        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for profile in profiles:
            listbox.insert(tk.END, profile)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def delete():
            selection = listbox.curselection()
            if selection:
                profile = listbox.get(selection[0])
                if messagebox.askyesno("Confirm", f"Delete profile '{profile}'?"):
                    self.profile_manager.delete_profile(profile)
                    listbox.delete(selection[0])
                    self.status_var.set(f"Profile '{profile}' deleted")
        
        ttk.Button(btn_frame, text="Delete", command=delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    # ===== File Operations =====
    
    def new_script(self):
        """Create new script"""
        if messagebox.askyesno("New Script", "Clear current script?"):
            self.steps = []
            self.refresh_table()
            self.current_profile = "Untitled"
            self.profile_label.config(text=self.current_profile)
            self.status_var.set("New script created")
    
    def save_script(self):
        """Save script to file"""
        if not self.steps:
            messagebox.showwarning("Empty", "Nothing to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                data = {
                    'steps': self.steps,
                    'settings': {
                        'server': self.server_var.get(),
                        'ping_multiplier': self.ping_multiplier.get(),
                        'fallback_delay': self.fallback_delay.get(),
                        'use_ping_delay': self.use_ping_delay.get(),
                        'randomize_position': self.randomize_position.get(),
                        'randomize_timing': self.randomize_timing.get(),
                        'position_variance': self.position_variance.get(),
                        'timing_variance': self.timing_variance.get()
                    }
                }
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)
                self.update_config(file_path)
                self.status_var.set(f"Saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
    
    def quick_save_script(self):
        """Quick save to last location"""
        # Implementation would track last save location
        self.save_script()
    
    def load_script(self):
        """Load script from file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.load_from_file(file_path)
    
    def load_from_file(self, file_path):
        """Load data from file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.steps = data
            else:
                self.steps = data.get('steps', [])
                settings = data.get('settings', {})
                
                self.server_var.set(settings.get('server', '8.8.8.8'))
                self.ping_multiplier.set(settings.get('ping_multiplier', 1.0))
                self.fallback_delay.set(settings.get('fallback_delay', 100))
                self.use_ping_delay.set(settings.get('use_ping_delay', True))
                self.randomize_position.set(settings.get('randomize_position', False))
                self.randomize_timing.set(settings.get('randomize_timing', False))
                self.position_variance.set(settings.get('position_variance', 5))
                self.timing_variance.set(settings.get('timing_variance', 10))
                
                self.on_server_change()
            
            self.refresh_table()
            self.update_config(file_path)
            self.status_var.set(f"Loaded {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
    
    def update_config(self, file_path):
        """Update config with last file"""
        try:
            config = {'last_file': file_path}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except:
            pass
    
    def load_last_session(self):
        """Load last session"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    last_file = config.get('last_file')
                    if last_file and os.path.exists(last_file):
                        self.load_from_file(last_file)
            except:
                pass
    
    # ===== Help & Info =====
    
    def show_hotkeys(self):
        """Show hotkey reference"""
        help_text = """
        ⌨️ HOTKEY REFERENCE
        
        F3 - Toggle Capture Mode / Capture Point
        F6 - Start Auto-Clicking
        F7 - Stop Auto-Clicking
        F8 - Pause/Resume
        
        Ctrl+N - New Script
        Ctrl+O - Open Script
        Ctrl+S - Save Script
        
        Delete - Delete Selected Step
        Ctrl+Del - Clear All Steps
        """
        messagebox.showinfo("Hotkeys", help_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        CTAutoClick Pro
        Advanced Edition v2.0
        
        Features:
        • Ping-based dynamic delays
        • Click randomization
        • Profile management
        • Statistics tracking
        • Advanced hotkeys
        
        © 2025 - Made with ❤️
        """
        messagebox.showinfo("About", about_text)
    
    def on_close(self):
        """Handle window close"""
        self.is_running = False
        self.ping_measurer.stop_monitoring()
        self.kb_listener.stop()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = AdvancedAutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
