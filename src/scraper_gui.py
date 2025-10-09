import json
import os
import platform
import sys
import tkinter as tk
import uuid
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk, messagebox, filedialog

from src.browser_manager import BrowserManager
from src.common import request_queue, result_queue
from src.scrapers.xingtu.xingtu_keywords_scraper import XingtuKeywordsSearchScraper
from src.utils.dir_util import get_exe_dir_storage

# 定义范围数据结构，使代码更具可读性
LimitRange = namedtuple('LimitRange', ['start', 'end'])

STORAGE_FILE = get_exe_dir_storage("runtime_data", "gui_storage.json")


class ScraperGUI:
    """主播搜索工具的GUI界面类，提供友好的用户交互界面"""

    DEFAULTS = {
        "browser_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "keywords": "办公用品",
        "limit_start": "10",  # 范围起始值
        "limit_end": "50"  # 范围结束值
    }

    def __init__(self, root: tk.Tk):
        """初始化GUI实例，创建界面元素"""
        self.root = root
        self.style = ttk.Style()
        self.runtime_data: dict = self.load_runtime_data()
        self.fonts: dict = {}

        # === 提前声明所有实例属性，方便静态检查 ===
        self.browser_var: tk.StringVar | None = None
        self.browser_entry: ttk.Entry | None = None
        self.keywords_var: tk.StringVar | None = None
        self.keywords_entry: ttk.Entry | None = None
        self.limit_start_var: tk.StringVar | None = None
        self.limit_start_entry: ttk.Entry | None = None
        self.limit_end_var: tk.StringVar | None = None
        self.limit_end_entry: ttk.Entry | None = None
        self.status_var: tk.StringVar | None = None

        self.executor: ThreadPoolExecutor | None = None

        # 初始化UI
        self.setup_ui_config()
        self.init_ui()
        self.bind_shortcuts()

        self.executor = ThreadPoolExecutor(max_workers=1)
        self.check_message_queue()

    def load_runtime_data(self):
        """读取JSON存储文件，如果不存在则使用默认值"""
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 处理旧版本数据迁移
                if "limit" in data and "limit_start" not in data:
                    data["limit_start"] = "10"
                    data["limit_end"] = data["limit"]
                    del data["limit"]
                return {**self.DEFAULTS, **data}
            except Exception:
                return self.DEFAULTS.copy()
        else:
            return self.DEFAULTS.copy()

    def save_runtime_data(self):
        """保存当前输入参数到JSON"""
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.runtime_data, f, ensure_ascii=False, indent=2)

    def setup_ui_config(self):
        """配置UI相关的样式和参数"""
        system = platform.system()
        if system == "Windows":
            default_font = ("Microsoft YaHei UI", 10)
            title_font = ("Microsoft YaHei UI", 11, "bold")
        elif system == "Darwin":
            default_font = ("PingFang SC", 10)
            title_font = ("PingFang SC", 11, "bold")
        else:
            default_font = ("SimHei", 10)
            title_font = ("SimHei", 11, "bold")

        self.fonts = {
            "default": default_font,
            "title": title_font,
            "small": (default_font[0], 9)
        }
        self.style.configure("TLabel", font=self.fonts["default"])
        self.style.configure("Title.TLabel", font=self.fonts["title"])
        self.style.configure("TButton", font=self.fonts["default"], padding=5)

    def init_ui(self):
        """构建界面布局和组件"""
        self.root.title("数据采集工具")
        self.root.geometry("700x400")
        self.root.minsize(600, 350)
        self.root.resizable(True, True)

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 浏览器路径
        ttk.Label(main_frame, text="浏览器路径：", style="Title.TLabel").pack(anchor="w")
        browser_frame = ttk.Frame(main_frame)
        browser_frame.pack(fill=tk.X, pady=(0, 10))
        self.browser_var = tk.StringVar(value=self.runtime_data.get("browser_path"))
        self.browser_entry = ttk.Entry(browser_frame, textvariable=self.browser_var)
        self.browser_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(browser_frame, text="选择", command=self.select_browser).pack(side=tk.LEFT, padx=5)

        # 关键词
        ttk.Label(main_frame, text="关键词：", style="Title.TLabel").pack(anchor="w")
        self.keywords_var = tk.StringVar(value=self.runtime_data.get("keywords"))
        self.keywords_entry = ttk.Entry(main_frame, textvariable=self.keywords_var)
        self.keywords_entry.pack(fill=tk.X, pady=(0, 10))

        # 限额范围
        ttk.Label(main_frame, text="爬取数量范围：", style="Title.TLabel").pack(anchor="w")
        limit_frame = ttk.Frame(main_frame)
        limit_frame.pack(fill=tk.X, pady=(0, 15))

        # 起始值
        self.limit_start_var = tk.StringVar(value=self.runtime_data.get("limit_start"))
        self.limit_start_entry = ttk.Entry(limit_frame, textvariable=self.limit_start_var, width=10)
        self.limit_start_entry.pack(side=tk.LEFT, padx=(0, 5))

        # 分隔符
        ttk.Label(limit_frame, text="至").pack(side=tk.LEFT, padx=5)

        # 结束值
        self.limit_end_var = tk.StringVar(value=self.runtime_data.get("limit_end"))
        self.limit_end_entry = ttk.Entry(limit_frame, textvariable=self.limit_end_var, width=10)
        self.limit_end_entry.pack(side=tk.LEFT, padx=(5, 0))

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, font=self.fonts["small"], foreground="#666666").pack(anchor="w")

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        btn_frame.grid_columnconfigure(0, weight=1)

        ttk.Button(btn_frame, text="确认 (Enter)", command=self.handle_confirm, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="清空 (Esc)", command=self.handle_clear, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="退出", command=self.handle_exit, width=15).grid(row=0, column=3, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.handle_exit)

    def bind_shortcuts(self):
        self.root.bind("<Return>", lambda event: self.handle_confirm())
        self.root.bind("<Escape>", lambda event: self.handle_clear())
        self.root.bind("<Control-w>", lambda event: self.handle_exit())

    def select_browser(self):
        path = filedialog.askopenfilename(title="选择浏览器", filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")])
        if path:
            self.browser_var.set(path)

    def handle_confirm(self):
        browser_path = self.browser_var.get().strip()
        keywords = self.keywords_var.get().strip()
        limit_start = self.limit_start_var.get().strip()
        limit_end = self.limit_end_var.get().strip()

        # 验证所有参数
        if not browser_path or not keywords or not limit_start or not limit_end:
            request_id = str(uuid.uuid4())
            request_queue.put(("warning", request_id, "提示", "请填写所有参数！"))
            return

        try:
            start_int = int(limit_start)
            end_int = int(limit_end)

            if start_int > end_int:
                request_id = str(uuid.uuid4())
                request_queue.put(("warning", request_id, "提示", "起始值不能大于结束值！"))
                return

            if start_int <= 0 or end_int <= 0:
                request_id = str(uuid.uuid4())
                request_queue.put(("warning", request_id, "提示", "数量必须为正整数！"))
                return

        except ValueError:
            request_id = str(uuid.uuid4())
            request_queue.put(("warning", request_id, "提示", "数量必须为整数！"))
            return

        limit_range = LimitRange(start=start_int, end=end_int)

        self.runtime_data.update({
            "browser_path": browser_path,
            "keywords": keywords,
            "limit_start": str(start_int),
            "limit_end": str(end_int)
        })
        self.save_runtime_data()

        self.executor.submit(run_task, browser_path, keywords, limit_range)

        request_id = str(uuid.uuid4())
        request_queue.put((
            "info",
            request_id,
            "开始执行",
            f"任务已开始执行！\n关键词：{keywords}\n计划爬取数量范围：{limit_range.start} - {limit_range.end}"
        ))

    def handle_clear(self):
        self.browser_var.set(self.runtime_data.get("browser_path"))
        self.keywords_var.set(self.runtime_data.get("keywords"))
        self.limit_start_var.set(self.runtime_data.get("limit_start"))
        self.limit_end_var.set(self.runtime_data.get("limit_end"))
        self.status_var.set("已重置为上次保存的值")

    def handle_exit(self):
        if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
            self.root.destroy()
            sys.exit(0)

    def show_non_modal_info(self, title, content):
        """创建非模态信息弹窗，不阻塞主线程"""
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("350x150")
        top.resizable(False, False)
        top.transient(self.root)
        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - top.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - top.winfo_height()) // 2
        top.geometry(f"+{x}+{y}")

        label = ttk.Label(top, text=content, font=self.fonts["default"], wraplength=300)
        label.pack(pady=20, padx=10)

        btn = ttk.Button(top, text="确定", command=top.destroy, width=10)
        btn.pack(pady=10)

        top.attributes("-topmost", True)
        top.focus_set()

    def check_message_queue(self):
        while not request_queue.empty():
            msg_type, request_id, title, content = request_queue.get()

            try:
                if msg_type == "wait":
                    messagebox.showinfo(title, f"{content}\n\n请在浏览器中完成操作后，\n点击本窗口的确定按钮继续...")
                    result_queue.put((request_id, True))
                    print(f"[交互完成] 请求ID: {request_id} - 用户点击确定")

                elif msg_type == "info":
                    self.show_non_modal_info(title, content)
                    result_queue.put((request_id, True))
                    print(f"[信息提示] 请求ID: {request_id} - 已展示（非模态）")

                elif msg_type == "warning":
                    messagebox.showwarning(title, content)
                    result_queue.put((request_id, True))
                    print(f"[警告提示] 请求ID: {request_id} - 已展示")

                elif msg_type == "error":
                    messagebox.showerror(title, content)
                    result_queue.put((request_id, True))
                    print(f"[错误提示] 请求ID: {request_id} - 已展示")

                elif msg_type == "confirm":
                    user_choice = messagebox.askyesno(title, content)
                    result_queue.put((request_id, user_choice))
                    print(f"[确认选择] 请求ID: {request_id} - 用户选择: {'确定' if user_choice else '取消'}")

                else:
                    print(f"[未知消息类型] {msg_type}，请求ID: {request_id}")
                    result_queue.put((request_id, False))

            except Exception as e:
                print(f"[处理弹窗出错] 请求ID: {request_id}，错误: {str(e)}")
                result_queue.put((request_id, False))

        self.root.after(100, self.check_message_queue)  # type: ignore


def run_task(browser_path, keywords, limit_range):
    browser_manager = BrowserManager(browser_path)
    search_scraper = XingtuKeywordsSearchScraper(browser_manager)
    search_scraper.run(keywords, limit_range)


def start_gui():
    root = tk.Tk()
    root.option_add("*Font", ("SimHei", 10))
    app = ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
