import asyncio
import json
import os
import platform
import sys
import tkinter as tk
import uuid
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk, messagebox, filedialog

from src.browser_manager import BrowserManager
from src.common import request_queue, result_queue
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
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.check_message_queue()

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
            request_id = str(uuid.uuid4())
            request_queue.put(("warning", request_id, "提示", "请填写所有参数！"))
            return

        try:
            limit_int = int(limit)
        except ValueError:
            request_id = str(uuid.uuid4())
            request_queue.put(("warning", request_id, "提示", "限额必须为整数！"))
            return

        self.runtime_data.update({
            "browser_path": browser_path,
            "keywords": keywords,
            "limit": str(limit_int)
        })
        self.save_runtime_data()

        # 提交任务到线程池（替代asyncio方式）
        self.executor.submit(
            run_task,
            browser_path,
            keywords,
            limit_int
        )

        # 关键修改：将任务开始的弹窗通过队列发送，避免直接阻塞主线程
        request_id = str(uuid.uuid4())
        request_queue.put((
            "info",
            request_id,
            "开始执行",
            f"任务已开始执行！\n关键词：{keywords}\n计划爬取数量：{limit_int}"
        ))

    def handle_clear(self):
        self.browser_var.set(self.runtime_data.get("browser_path"))
        self.keywords_var.set(self.runtime_data.get("keywords"))
        self.limit_var.set(self.runtime_data.get("limit"))
        self.status_var.set("已重置为上次保存的值")

    def handle_exit(self):
        if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
            self.root.destroy()
            sys.exit(0)

    def show_non_modal_info(self, title, content):
        """创建非模态信息弹窗，不阻塞主线程"""
        # 1. 创建顶层窗口（非模态）
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("350x150")  # 固定弹窗大小
        top.resizable(False, False)  # 禁止缩放
        # 2. 让弹窗在主窗口居中（提升用户体验）
        top.transient(self.root)  # 绑定到主窗口，关闭主窗口时弹窗也关闭
        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - top.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - top.winfo_height()) // 2
        top.geometry(f"+{x}+{y}")

        # 3. 添加内容标签
        label = ttk.Label(top, text=content, font=self.fonts["default"], wraplength=300)
        label.pack(pady=20, padx=10)

        # 4. 添加“确定”按钮（点击关闭弹窗）
        btn = ttk.Button(top, text="确定", command=top.destroy, width=10)
        btn.pack(pady=10)

        # 5. 关键：设置为非模态（不阻塞主线程）
        top.attributes("-topmost", True)  # 弹窗置顶，避免被遮挡
        top.focus_set()  # 聚焦弹窗，但不阻塞主线程

    # 新增：检查消息队列，处理后台线程的弹窗请求（主线程执行）
    def check_message_queue(self):
        print("开始监听" + str(uuid.uuid4()))
        while not request_queue.empty():
            # 统一参数结构：(消息类型, 请求ID, 标题, 内容)
            # 确保所有类型的请求都遵循这个结构，避免解包错误
            msg_type, request_id, title, content = request_queue.get()

            try:
                if msg_type == "wait":
                    # 等待用户处理的弹窗（只有确定按钮）
                    messagebox.showinfo(
                        title,
                        f"{content}\n\n请在浏览器中完成操作后，\n点击本窗口的确定按钮继续..."
                    )
                    # 返回确定结果（始终为True，因为没有取消按钮）
                    result_queue.put((request_id, True))
                    print(f"[交互完成] 请求ID: {request_id} - 用户点击确定")

                elif msg_type == "info":
                    # 关键修改：用非模态弹窗，不阻塞监听
                    self.show_non_modal_info(title, content)
                    # 非模态弹窗不阻塞，直接返回“已展示”结果（后台线程无需等待）
                    result_queue.put((request_id, True))
                    print(f"[信息提示] 请求ID: {request_id} - 已展示（非模态）")

                elif msg_type == "warning":
                    # 警告弹窗（只有确定按钮）
                    messagebox.showwarning(title, content)
                    result_queue.put((request_id, True))
                    print(f"[警告提示] 请求ID: {request_id} - 已展示")

                elif msg_type == "error":
                    # 错误弹窗（只有确定按钮）
                    messagebox.showerror(title, content)
                    result_queue.put((request_id, True))
                    print(f"[错误提示] 请求ID: {request_id} - 已展示")

                elif msg_type == "confirm":
                    # 确认弹窗（有确定和取消按钮）
                    user_choice = messagebox.askyesno(title, content)
                    result_queue.put((request_id, user_choice))  # 返回True/False
                    print(f"[确认选择] 请求ID: {request_id} - 用户选择: {'确定' if user_choice else '取消'}")

                else:
                    # 未知类型处理
                    print(f"[未知消息类型] {msg_type}，请求ID: {request_id}")
                    result_queue.put((request_id, False))  # 返回错误标识

            except Exception as e:
                print(f"[处理弹窗出错] 请求ID: {request_id}，错误: {str(e)}")
                result_queue.put((request_id, False))  # 出错时返回失败标识

        # 继续监听队列（递归调用，保持循环）
        self.root.after(100, self.check_message_queue)


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
