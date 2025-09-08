import os
import subprocess
import threading
import customtkinter as ctk

MAIN_SCRIPT = "main.py"  # 注意：可根据实际后端文件调整路径

class AccountProcess:
    def __init__(self, account, config, widgets):
        self.account = account
        self.config = config
        self.proc = None
        self.log_buffer = []
        self.log_thread = None
        self.running = False
        self.widgets = widgets  # dict: {status, log_text}

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        log_path = self.config["log_file"]
        log_dir = os.path.dirname(log_path)
        os.makedirs(log_dir, exist_ok=True)
        open(log_path, "w").close()
        self.proc = subprocess.Popen(
            ["python", MAIN_SCRIPT, "-a", self.account],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8"
        )
        self.running = True
        self.log_thread = threading.Thread(target=self._read_log, daemon=True)
        self.log_thread.start()
        self.update_status()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.running = False
        self.update_status()

    def status(self):
        if not self.proc:
            return "未启动"
        if self.proc.poll() is None:
            return "运行中"
        return f"已退出({self.proc.returncode})"

    def _read_log(self):
        log_path = self.config["log_file"]
        with open(log_path, "a", encoding="utf-8") as f:
            for line in self.proc.stdout:
                f.write(line)
                f.flush()
                self.log_buffer.append(line)
                if len(self.log_buffer) > 1000:
                    self.log_buffer = self.log_buffer[-1000:]
                self.widgets["log_text"].after(0, self.update_log)
        self.update_status()

    def get_log(self, tail=100):
        return "".join(self.log_buffer[-tail:]) if self.log_buffer else self._read_logfile()

    def _read_logfile(self, tail=100):
        path = self.config["log_file"]
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-tail:])

    def update_log(self):
        log = self.get_log(100)
        self.widgets["log_text"].configure(state="normal")
        self.widgets["log_text"].delete("1.0", "end")
        self.widgets["log_text"].insert("end", log)
        self.widgets["log_text"].see("end")
        self.widgets["log_text"].configure(state="disabled")

    def update_status(self):
        self.widgets["status"].configure(text=self.status())

def build_account_frame(root, acc, config):
    # 主Frame
    frame = ctk.CTkFrame(root)
    frame.pack(side="left", padx=10, pady=10, fill="both", expand=True)

    # 标题
    title_label = ctk.CTkLabel(frame, text=f"账户：{acc}", font=("微软雅黑", 14, "bold"))
    title_label.pack(anchor="w", pady=(0, 6))

    status_label = ctk.CTkLabel(frame, text="未启动", text_color="#2779aa", font=("微软雅黑", 11, "bold"))
    status_label.pack(anchor="w", pady=2)

    # 按钮区
    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(fill="x", pady=3)
    btn_start = ctk.CTkButton(btn_frame, text="启动", width=80)
    btn_stop = ctk.CTkButton(btn_frame, text="停止", width=80)
    btn_start.pack(side="left", padx=3)
    btn_stop.pack(side="left", padx=3)

    # 日志区
    log_label = ctk.CTkLabel(frame, text="日志窗口：", font=("微软雅黑", 10))
    log_label.pack(anchor="w", pady=(6,0))

    # 日志文本框+滚动条
    log_text_frame = ctk.CTkFrame(frame, fg_color="transparent")
    log_text_frame.pack(fill="both", expand=True, pady=2)
    log_text = ctk.CTkTextbox(log_text_frame, height=200, font=("Consolas", 10), state="disabled")
    log_text.pack(side="left", fill="both", expand=True)
    log_scroll = ctk.CTkScrollbar(log_text_frame, command=log_text.yview)
    log_scroll.pack(side="right", fill="y")
    log_text.configure(yscrollcommand=log_scroll.set)

    btn_refresh = ctk.CTkButton(frame, text="刷新日志", width=120)
    btn_refresh.pack(pady=2)

    widgets = {"status": status_label, "log_text": log_text}
    proc = AccountProcess(acc, config, widgets)
    btn_start.configure(command=lambda: [proc.start(), proc.update_status()])
    btn_stop.configure(command=lambda: [proc.stop(), proc.update_status()])
    btn_refresh.configure(command=proc.update_log)
    return proc

def save_plan(plan_text, plan_file):
    os.makedirs(os.path.dirname(plan_file), exist_ok=True)
    with open(plan_file, "w", encoding="utf-8") as f:
        f.write(plan_text)
    # 简易消息弹窗
    msg = ctk.CTkToplevel()
    msg.title("提示")
    msg.geometry("300x100")
    label = ctk.CTkLabel(msg, text=f"计划已保存到\n{plan_file}")
    label.pack(expand=True, pady=20)
    ctk.CTkButton(msg, text="确定", command=msg.destroy).pack()
    msg.grab_set()

def load_plan(plan_file):
    if os.path.exists(plan_file):
        with open(plan_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""