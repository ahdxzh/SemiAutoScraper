import time

from playwright.sync_api import TimeoutError

from src.scrapers.live_author_scraper import AnchorProcessor
from src.utils.captcha_util import with_captcha_handling
from src.utils.csv_util import save_dict_list_to_csv
from src.utils.page_operate import scroll_multiple_times
from src.utils.page_status_check import check_login_status, check_captcha_status
from src.utils.page_user_interaction import wait_for_user_action
from src.utils.page_util import jump_to_target_page

PAGE_SIZE = 20  # 每页显示的主播数量


class LiveScraper:
    def __init__(self, browser_manager):
        print("===== 初始化LiveScraper实例 =====")
        self.browser_manager = browser_manager
        self.page = browser_manager.context.new_page()
        print("LiveScraper初始化完成")

    def _initialize_page(self):
        """初始化页面：加载星图平台"""
        print("----- 开始初始化页面 -----")
        page = self.page
        target_url = "https://www.xingtu.cn/ad/creator/market"
        print(f"开始加载目标URL: {target_url} (超时时间60秒)")
        try:
            page.goto(target_url, timeout=60000)
            print("星图平台首页加载完成（复用BrowserManager的context状态）")
        except TimeoutError:
            print(f"错误：加载{target_url}超时（60秒）")
            # 可添加重试逻辑或其他处理
        except Exception as e:
            print(f"错误：加载页面失败，原因：{str(e)}")

    @with_captcha_handling()
    def search_author(self, category: str):
        self.page.get_by_text("内容找人").first.click()
        self.page.get_by_role("textbox", name="按内容关键词找达人").click()
        self.page.get_by_role("textbox", name="按内容关键词找达人").fill(category)
        self.page.get_by_role("textbox", name="按内容关键词找达人").press("Enter")
        print("===== 休眠60秒等待用户自行调整筛选参数' =====")
        time.sleep(60)

    def category_task(self, category: str, limit: int = 3):
        """执行星图平台搜索流程，包含登录和验证码检测"""
        print(f"\n\n===== 开始执行任务：搜索关键词 '{category}' =====")
        self._initialize_page()

        try:
            page = self.page
            # 检测登录状态
            print("\n----- 流程步骤1：检测登录状态 -----")
            if not check_login_status(page):
                wait_for_user_action("请先完成登录操作")

            # 检测主页面验证码
            print("\n----- 流程步骤2：检测主页面验证码 -----")
            if check_captcha_status(page):
                wait_for_user_action("主页面出现验证码，请完成验证")

            # 搜索对应的类别
            print("\n----- 流程步骤3：执行搜索操作 -----")
            self.search_author(category)

            print("\n----- 流程步骤4：分页处理榜单数据 -----")
            rank = 1
            page_limit = (limit + PAGE_SIZE - 1) // PAGE_SIZE
            processor = AnchorProcessor(page)
            all_results = []
            failed_tasks = []

            for page_number in range(1, page_limit + 1):
                jump_to_target_page(page, page_number)
                page.locator("body").focus()
                page.wait_for_timeout(100)
                # 点击一下达人信息转移走焦点
                page.get_by_text("达人信息").first.click()
                scroll_multiple_times(page)
                print(f"滚动完成并等待数据加载，第 {page_number} 页")

                for author_number in range(1, PAGE_SIZE + 1):
                    if rank > limit:
                        break
                    page.locator("body").focus()

                    # 执行任务并重试，不影响整体流程
                    result = self._process_task_safe(processor, author_number, rank)
                    if result is not None:
                        all_results.append(result)
                    else:
                        failed_tasks.append((page_number, author_number, rank))

                    rank += 1
                    time.sleep(0.5)  # 任务间隔

                if rank > limit:
                    break

            save_dict_list_to_csv(all_results, "outPut/anchor_data.csv")
            print(f"总共处理了 {rank - 1} 条榜单数据")
            if failed_tasks:
                print(f"[警告] 以下任务处理失败：{failed_tasks}")

        except TimeoutError as te:
            print(f"\n===== 操作超时错误：{str(te)} =====")
            print("可能原因：页面元素未出现、网络延迟或页面加载缓慢")
        except Exception as e:
            print(f"\n===== 操作执行错误：{str(e)} =====")
            print("错误发生在任务执行过程中")
        finally:
            self.browser_manager.close()

    @staticmethod
    def _process_task_safe(processor, author_number, rank, max_retry=3):
        """单条榜单处理任务，失败不影响整体"""
        attempt = 0
        while attempt < max_retry:
            try:
                processor.process_anchor(author_number, rank)
                return processor.current_data
            except Exception as e:
                attempt += 1
                print(f"[警告] 处理第 {rank} 条主播失败，第 {attempt} 次重试，错误: {e}")
                time.sleep(1)
        print(f"[错误] 第 {rank} 条主播处理失败，跳过该任务")
        return None
