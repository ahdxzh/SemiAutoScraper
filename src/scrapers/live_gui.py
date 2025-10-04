import asyncio
import json
import os
import platform
import sys
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk, messagebox, filedialog

from src.browser_manager import BrowserManager
from src.scrapers.keywords_search_scraper import KeywordsSearchScraper
from src.utils.dir_util import get_exe_dir_storage

STORAGE_FILE = get_exe_dir_storage("runtime_data", "gui_storage.json")


class ScraperGUI:
    """主播搜索工具的GUI界面类，提供友好的用户交互界面"""

    DEFAULTS = {
        "browser_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "keywords": "办公用品",
        "limit": "50"
    }

    def __init__(self, root):
        """初始化GUI实例，创建界面元素"""
        self.root = root
        self.style = ttk.Style()
        self.runtime_data = self.load_runtime_data()
        self.setup_ui_config()
        self.init_ui()
        self.bind_shortcuts()

    def load_runtime_data(self):
        """读取JSON存储文件，如果不存在则使用默认值"""
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {**self.DEFAULTS, **data}  # 合并默认值
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
        self.root.title("半自动化搜索工具")
        self.root.geometry("700x350")
        self.root.minsize(600, 300)
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

        # 限额
        ttk.Label(main_frame, text="限额：", style="Title.TLabel").pack(anchor="w")
        self.limit_var = tk.StringVar(value=self.runtime_data.get("limit"))
        self.limit_entry = ttk.Entry(main_frame, textvariable=self.limit_var)
        self.limit_entry.pack(fill=tk.X, pady=(0, 15))

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, font=self.fonts["small"], foreground="#666666").pack(
            anchor="w")

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
        limit = self.limit_var.get().strip()

        if not browser_path or not keywords or not limit:
            messagebox.showwarning("提示", "请填写所有参数！")
            return

        try:
            limit_int = int(limit)
        except ValueError:
            messagebox.showwarning("提示", "限额必须为整数！")
            return

        # 保存当前输入
        self.runtime_data.update({
            "browser_path": browser_path,
            "keywords": keywords,
            "limit": str(limit_int)
        })
        self.save_runtime_data()

        # 后台线程运行，不阻塞GUI
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            loop.run_in_executor(
                executor,
                run_task,
                browser_path,
                keywords,
                limit_int
            )

        # 立即提示任务开始执行
        messagebox.showinfo(
            "开始执行",
            f"任务已开始执行！\n"
            f"关键词：{keywords}\n"
            f"计划爬取数量：{limit_int}"
        )

    def handle_clear(self):
        self.browser_var.set(self.runtime_data.get("browser_path"))
        self.keywords_var.set(self.runtime_data.get("keywords"))
        self.limit_var.set(self.runtime_data.get("limit"))
        self.status_var.set("已重置为上次保存的值")

    def handle_exit(self):
        if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
            self.root.destroy()
            sys.exit(0)


def run_task(browser_path, keywords, limit_int):
    browser_manager = BrowserManager(browser_path)
    search_scraper = KeywordsSearchScraper(browser_manager)
    search_scraper.search_task(keywords, limit_int)


def start_gui():
    root = tk.Tk()
    root.option_add("*Font", ("SimHei", 10))
    app = ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
