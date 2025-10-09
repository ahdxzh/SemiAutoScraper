import os
import random
import sys

from playwright.sync_api import sync_playwright

from src.utils.dir_util import get_exe_dir_storage


class BrowserManager:
    def __init__(self, edge_path: str = None):
        self.edge_path = edge_path
        self.storage_path = get_exe_dir_storage("runtime_data", "browser_storage.json")
        print(f"浏览器状态存储路径: {self.storage_path}")
        self._check_browser_exists()  # 检查指定的浏览器是否存在
        self.playwright = sync_playwright().start()
        self.browser = self._launch_browser()
        self.context = self._create_context()

    def _check_browser_exists(self):
        """检查指定的浏览器是否存在"""
        if not os.path.exists(self.edge_path):
            print(f"❌ 未找到指定的浏览器: {self.edge_path}")
            print("请检查路径是否正确或浏览器是否已安装")
            sys.exit(1)
        print(f"✅ 已找到指定的浏览器: {self.edge_path}")

    def _launch_browser(self):
        launch_args = [
            "--allow-insecure-localhost",
            "--enable-clipboard-read",
            "--enable-clipboard-write",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--window-size=1920,1080"
        ]

        print(f"使用指定的浏览器: {self.edge_path}")
        # Edge基于Chromium，因此使用playwright.chromium.launch
        return self.playwright.chromium.launch(
            headless=False,  # 禁用无头模式以支持视频播放
            args=launch_args,
            slow_mo=50,
            executable_path=self.edge_path  # 使用指定的Edge路径
        )

    def _create_context(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.51",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58"
        ]

        storage_options = {}
        if os.path.exists(self.storage_path):
            print(f"✅ 加载已存在的浏览器状态: {self.storage_path}")
            storage_options["storage_state"] = self.storage_path
        else:
            print(f"ℹ️ 未找到浏览器状态文件，将创建新文件: {self.storage_path}")

        return self.browser.new_context(
            user_agent=random.choice(user_agents),
            locale="zh-CN",  # ✅ 中国地区语言
            timezone_id="Asia/Shanghai",  # ✅ 中国时区
            permissions=["geolocation"],
            geolocation={"latitude": 39.9042, "longitude": 116.4074},  # 北京经纬度
            color_scheme="light",
            viewport={"width": 1920, "height": 1080},  # ✅ 指定 viewport
            **storage_options
        )

    def new_page(self):
        page = self.context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete window.__playwright_evaluate;
        """)
        return page

    def close(self):
        try:
            print(f"尝试保存浏览器状态到: {self.storage_path}")
            self.context.storage_state(path=self.storage_path)
            if os.path.exists(self.storage_path):
                file_size = os.path.getsize(self.storage_path)
                print(f"✅ 状态保存成功，文件大小: {file_size} 字节")
            else:
                print("❌ 状态保存失败，文件未创建")
        except Exception as e:
            print(f"❌ 保存状态时发生错误: {str(e)}")

        self.context.close()
        self.browser.close()
        self.playwright.stop()
        print("浏览器资源已释放")
