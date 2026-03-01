import pyautogui
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import random

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macro_config.json")

DEFAULT_CONFIG = {
    "macro_speed": 1.0,
    "wait_after_up_left": 1.0,
    "wait_after_down_left": 0.2,
    "wait_after_down_right": 0.2,
    "wait_after_up_left_2": 0.03,
    "wait_after_up_right": 0.06,
    "wait_after_down_left_3": 0.15,
    "wait_after_down_right_3": 0.1,
    "wait_after_up_left_4": 0.03,
    "wait_after_up_right_4": 0.06,
    "wait_after_down_left_5": 0.15,
    "wait_after_down_right_5": 0.1,
    "wait_after_up_left_6": 0.03,
    "wait_after_up_right_6": 0.06,
    "wait_after_down_left_7": 0.15,
    "wait_after_down_right_7": 0.1,
    "wait_final": 0.8,
    "enable_randomization": True,
    "random_range": 0.05
}

MACRO_SCRIPT = "mousedown(left),wait({wait_after_up_left}),mouseup(left),wait({wait_after_down_left}),mousedown(right),wait({wait_after_down_right}),mouseup(left),wait({wait_after_up_left_2}),mouseup(right),wait({wait_after_up_right}),mousedown(left),wait({wait_after_down_left_3}),mousedown(right),wait({wait_after_down_right_3}),mouseup(left),wait({wait_after_up_left_4}),mouseup(right),wait({wait_after_up_right_4}),mousedown(left),wait({wait_after_down_left_5}),mousedown(right),wait({wait_after_down_right_5}),mouseup(left),wait({wait_after_up_left_6}),mouseup(right),wait({wait_after_up_right_6}),mousedown(left),wait({wait_after_down_left_7}),mousedown(right),wait({wait_after_down_right_7}),mouseup(left),wait({wait_final})"

class MacroEngine:
    def __init__(self, config):
        self.config = config
        self.stop_macro = False
        self.pause_macro = False
    
    def wait(self, seconds):
        actual_time = seconds * (1.0 / self.config["macro_speed"])
        if self.config["enable_randomization"]:
            actual_time += (random.random() - 0.5) * self.config["random_range"]
        actual_time = max(0.001, actual_time)
        start = time.time()
        while time.time() - start < actual_time and not self.stop_macro:
            if self.pause_macro:
                time.sleep(0.01)
            else:
                time.sleep(0.001)
    
    def execute_action(self, action):
        action = action.strip().lower()
        if not action:
            return
        
        if action.startswith("wait(") and action.endswith(")"):
            try:
                wait_time = float(action[5:-1])
                self.wait(wait_time)
            except:
                pass
        elif action.startswith("mousedown(") and action.endswith(")"):
            button = action[10:-1]
            if button in ['left', 'right', 'middle']:
                pyautogui.mouseDown(button=button)
        elif action.startswith("mouseup(") and action.endswith(")"):
            button = action[8:-1]
            if button in ['left', 'right', 'middle']:
                pyautogui.mouseUp(button=button)
        elif action.startswith("keydown(") and action.endswith(")"):
            key = action[8:-1]
            try:
                pyautogui.keyDown(key)
            except:
                pass
        elif action.startswith("keyup(") and action.endswith(")"):
            key = action[6:-1]
            try:
                pyautogui.keyUp(key)
            except:
                pass
        elif action == "leftclick" or action == "lclick":
            pyautogui.click(button='left')
        elif action == "rightclick" or action == "rclick":
            pyautogui.click(button='right')
        elif action.startswith("press(") and action.endswith(")"):
            key = action[6:-1]
            try:
                pyautogui.press(key)
            except:
                pass
    
    def run_script(self, script_str):
        actions = [a.strip() for a in script_str.split(",") if a.strip()]
        for action in actions:
            if self.stop_macro:
                break
            self.execute_action(action)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置已保存到: {CONFIG_FILE}")
    except Exception as e:
        print(f"保存配置失败: {e}")

class MacroUI:
    def __init__(self):
        self.config = load_config()
        self.setup_window()
        self.setup_styles()
        self.setup_ui()
        self.setup_keyboard_listener()
        
        self.is_running = False
        self.stop_macro = False
        self.pause_macro = False
        self.round_count = 0
        self.macro_thread = None
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("宏控制")
        self.root.geometry("380x280")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.85)
        self.root.configure(bg='#1a1a2e')
        
        screen_x = self.root.winfo_screenwidth() - 400
        screen_y = 50
        self.root.geometry(f"380x280+{screen_x}+{screen_y}")
        
        self.root.overrideredirect(False)
        self.root.bind('<FocusIn>', lambda e: self.root.attributes('-alpha', 0.95))
        self.root.bind('<FocusOut>', lambda e: self.root.attributes('-alpha', 0.85))
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Macro.TFrame', background='#1a1a2e')
        style.configure('Macro.TLabel', background='#1a1a2e', foreground='#e0e0e0')
        style.configure('MacroTitle.TLabel', background='#1a1a2e', foreground='#00d4ff', 
                       font=('Microsoft YaHei UI', 13, 'bold'))
        style.configure('MacroStatus.TLabel', background='#1a1a2e', foreground='#00ff88',
                       font=('Microsoft YaHei UI', 11))
        style.configure('MacroRPM.TLabel', background='#1a1a2e', foreground='#ffaa00',
                       font=('Microsoft YaHei UI', 12, 'bold'))
        
        style.configure('Macro.TButton', font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=8, background='#2d2d44', foreground='#e0e0e0')
        style.map('Macro.TButton', 
                 background=[('active', '#3d3d5c'), ('pressed', '#4d4d6c')],
                 foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
        
        style.configure('MacroStart.TButton', font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=10, background='#00cc66', foreground='white')
        style.map('MacroStart.TButton',
                 background=[('active', '#00dd77'), ('pressed', '#00bb55')])
        
        style.configure('MacroStop.TButton', font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=10, background='#ff4444', foreground='white')
        style.map('MacroStop.TButton',
                 background=[('active', '#ff5555'), ('pressed', '#dd3333')])
        
        style.configure('MacroTLabelframe', background='#1a1a2e', bordercolor='#3d3d5c')
        style.configure('MacroTLabelframe.Label', background='#1a1a2e', 
                       foreground='#888888', font=('Microsoft YaHei UI', 9))
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, style='Macro.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        ttk.Label(main_frame, text="⚡ 宏控制", style='MacroTitle.TLabel').pack(pady=(0, 8))
        
        self.status_label = ttk.Label(main_frame, text="就绪 - 按 F1 启动", 
                                     style='MacroStatus.TLabel')
        self.status_label.pack(pady=4)
        
        self.rpm_label = ttk.Label(main_frame, text="0 RPM", style='MacroRPM.TLabel')
        self.rpm_label.pack(pady=2)
        
        self.round_label = ttk.Label(main_frame, text="已完成 0 轮", 
                                    style='Macro.TLabel', font=('Microsoft YaHei UI', 9))
        self.round_label.pack(pady=2)
        
        btn_frame = ttk.Frame(main_frame, style='Macro.TFrame')
        btn_frame.pack(pady=12)
        
        self.toggle_btn = ttk.Button(btn_frame, text="▶ 启动", style='MacroStart.TButton',
                                    command=self.toggle_macro, width=10)
        self.toggle_btn.pack(pady=4, fill=tk.X)
        
        self.pause_btn = ttk.Button(btn_frame, text="⏸ 暂停", style='Macro.TButton',
                                   command=self.toggle_pause, width=10, state=tk.DISABLED)
        self.pause_btn.pack(pady=4, fill=tk.X)
        
        ttk.Button(btn_frame, text="⚙ 设置", style='Macro.TButton',
                  command=self.show_settings, width=10).pack(pady=4, fill=tk.X)
        
        help_frame = ttk.LabelFrame(main_frame, text="快捷键")
        help_frame.pack(fill=tk.X, pady=(8, 0))
        help_frame.configure(labelanchor='n')
        
        help_text = "F1: 启动/停止  |  F2: 暂停/继续"
        ttk.Label(help_frame, text=help_text, style='Macro.TLabel', 
                 font=('Microsoft YaHei UI', 8)).pack(pady=6)
    
    def setup_keyboard_listener(self):
        try:
            from pynput import keyboard
            def on_press(key):
                try:
                    if hasattr(key, 'char'):
                        if key.char == '\x13':
                            self.root.after(0, self.toggle_macro)
                        elif key.char == '\x14':
                            self.root.after(0, self.toggle_pause)
                except:
                    pass
            
            self.keyboard_listener = keyboard.Listener(on_press=on_press)
            self.keyboard_listener.daemon = True
            self.keyboard_listener.start()
        except Exception as e:
            print(f"键盘监听启动失败: {e}")
    
    def toggle_macro(self):
        self.root.after(0, self._toggle_macro)
    
    def _toggle_macro(self):
        if not self.is_running:
            self.start_macro()
        else:
            self.stop_macro_execution()
    
    def start_macro(self):
        self.macro_engine = MacroEngine(self.config)
        self.is_running = True
        self.stop_macro = False
        self.pause_macro = False
        self.round_count = 0
        self.start_time = time.time()
        self.current_rpm = 0
        
        self.status_label.config(text="运行中... 按 F1 停止", style='MacroStatus.TLabel')
        self.status_label.config(foreground='#ff6666')
        self.toggle_btn.config(text="■ 停止", style='MacroStop.TButton')
        self.pause_btn.config(state=tk.NORMAL, text="⏸ 暂停")
        
        self.macro_thread = threading.Thread(target=self.run_macro, daemon=True)
        self.macro_thread.start()
        
        self.update_rpm_display()
    
    def stop_macro_execution(self):
        if hasattr(self, 'macro_engine'):
            self.macro_engine.stop_macro = True
        
        self.is_running = False
        self.status_label.config(text="已停止 - 按 F1 重新启动", style='MacroStatus.TLabel')
        self.status_label.config(foreground='#00ff88')
        self.toggle_btn.config(text="▶ 启动", style='MacroStart.TButton')
        self.pause_btn.config(state=tk.DISABLED, text="⏸ 暂停")
    
    def toggle_pause(self):
        if not hasattr(self, 'macro_engine'):
            return
        
        self.macro_engine.pause_macro = not self.macro_engine.pause_macro
        self.pause_macro = self.macro_engine.pause_macro
        
        if self.pause_macro:
            self.pause_btn.config(text="▶ 继续")
            self.status_label.config(text="已暂停 - 按 F2 继续", style='MacroStatus.TLabel')
            self.status_label.config(foreground='#ffaa00')
        else:
            self.pause_btn.config(text="⏸ 暂停")
            self.status_label.config(text="运行中... 按 F1 停止", style='MacroStatus.TLabel')
            self.status_label.config(foreground='#ff6666')
    
    def update_rpm_display(self):
        if self.is_running and self.round_count > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.current_rpm = (self.round_count / elapsed) * 60
                self.rpm_label.config(text=f"{self.current_rpm:.1f} RPM")
                self.round_label.config(text=f"已完成 {self.round_count} 轮")
        
        if self.is_running:
            self.root.after(500, self.update_rpm_display)
    
    def run_macro(self):
        script = MACRO_SCRIPT.format(**self.config)
        
        try:
            while not self.macro_engine.stop_macro:
                self.round_count += 1
                self.macro_engine.run_script(script)
        except Exception as e:
            self.root.after(0, self.stop_macro_execution)
            self.root.after(0, lambda: self.status_label.config(
                text=f"错误: {str(e)}", style='MacroStatus.TLabel'))
    
    def show_settings(self):
        SettingsDialog(self.root, self.config, self.save_settings)
    
    def save_settings(self, new_config):
        self.config = new_config
        save_config(new_config)
        messagebox.showinfo("提示", f"设置已保存！\n文件: {CONFIG_FILE}")
    
    def on_close(self):
        if hasattr(self, 'macro_engine'):
            self.macro_engine.stop_macro = True
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        self.root.destroy()
    
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            self.root.mainloop()
        except Exception as e:
            print(f"[MacroUI] GUI运行错误: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.root.destroy()
            except:
                pass

class SettingsDialog:
    def __init__(self, parent, config, callback):
        self.callback = callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("宏设置")
        self.dialog.geometry("520x580")
        self.dialog.attributes('-topmost', True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#1a1a2e')
        
        self.entries = {}
        
        main_frame = ttk.Frame(self.dialog, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(main_frame, bg='#1a1a2e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a2e')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        settings_info = [
            ("macro_speed", "宏速度倍率 (0.1-3.0)", 1.0),
            ("enable_randomization", "启用时间随机化", True),
            ("random_range", "随机范围 (±秒)", 0.05),
            ("wait_after_up_left", "松开左键后等待", 1.0),
            ("wait_after_down_left", "按下左键后等待", 0.2),
            ("wait_after_down_right", "按下右键后等待", 0.2),
            ("wait_after_up_left_2", "松开左键后等待(2)", 0.03),
            ("wait_after_up_right", "松开右键后等待", 0.06),
            ("wait_after_down_left_3", "按下左键后等待(3)", 0.15),
            ("wait_after_down_right_3", "按下右键后等待(3)", 0.1),
            ("wait_after_up_left_4", "松开左键后等待(4)", 0.03),
            ("wait_after_up_right_4", "松开右键后等待(4)", 0.06),
            ("wait_after_down_left_5", "按下左键后等待(5)", 0.15),
            ("wait_after_down_right_5", "按下右键后等待(5)", 0.1),
            ("wait_after_up_left_6", "松开左键后等待(6)", 0.03),
            ("wait_after_up_right_6", "松开右键后等待(6)", 0.06),
            ("wait_after_down_left_7", "按下左键后等待(7)", 0.15),
            ("wait_after_down_right_7", "按下右键后等待(7)", 0.1),
            ("wait_final", "最终等待时间", 0.8)
        ]
        
        style = ttk.Style()
        style.configure('Settings.TLabel', background='#1a1a2e', foreground='#e0e0e0',
                       font=('Microsoft YaHei UI', 9))
        style.configure('Settings.TCheckbutton', background='#1a1a2e', foreground='#e0e0e0')
        style.map('Settings.TCheckbutton', 
                 background=[('active', '#2d2d44')])
        
        row = 0
        for key, label, default in settings_info:
            if isinstance(default, bool):
                var = tk.BooleanVar(value=config.get(key, default))
                chk = ttk.Checkbutton(scrollable_frame, text=label, variable=var,
                                     style='Settings.TCheckbutton')
                chk.grid(row=row, column=0, columnspan=2, padx=8, pady=4, sticky='w')
            else:
                lbl = ttk.Label(scrollable_frame, text=label, style='Settings.TLabel')
                lbl.grid(row=row, column=0, padx=8, pady=4, sticky='w')
                var = tk.DoubleVar(value=config.get(key, default))
                entry = ttk.Entry(scrollable_frame, textvariable=var, width=12)
                entry.grid(row=row, column=1, padx=8, pady=4)
            self.entries[key] = var
            row += 1
        
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        
        btn_style = ttk.Style()
        btn_style.configure('Btn.TButton', font=('Microsoft YaHei UI', 9, 'bold'),
                           padding=6)
        
        ttk.Button(btn_frame, text="保存", command=self.save, width=10,
                  style='Btn.TButton').pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="重置默认", command=self.reset_default, width=10,
                  style='Btn.TButton').pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy, width=10,
                  style='Btn.TButton').pack(side=tk.LEFT, padx=8)
        
        self.dialog.geometry("+{}+{}".format(
            parent.winfo_x() + 30,
            parent.winfo_y() + 30
        ))
    
    def save(self):
        new_config = {}
        for key, var in self.entries.items():
            value = var.get()
            if isinstance(value, bool):
                new_config[key] = value
            else:
                try:
                    new_config[key] = float(value) if '.' in str(value) else int(value)
                except:
                    new_config[key] = value
        self.callback(new_config)
        self.dialog.destroy()
    
    def reset_default(self):
        defaults = DEFAULT_CONFIG.copy()
        for key, var in self.entries.items():
            var.set(defaults.get(key, 0))

if __name__ == "__main__":
    try:
        app = MacroUI()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"发生错误: {e}")
