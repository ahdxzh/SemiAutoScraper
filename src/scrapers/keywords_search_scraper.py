import logging
import time
from dataclasses import dataclass

from playwright.sync_api import TimeoutError

from src.scrapers.live_author_scraper import AnchorProcessor
from src.utils.page_operate import scroll_multiple_times
from src.utils.page_status_check import check_login_status, check_captcha_status
from src.utils.page_user_interaction import wait_for_user_action
from src.utils.page_util import jump_to_target_page

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingRange:
    """处理范围数据类，使参数传递更清晰"""
    start: int
    end: int


class KeywordsSearchScraper:
    """精简结构版关键词搜索爬虫"""
    PAGE_SIZE = 20
    SEARCH_WAIT_SECONDS = 60
    TASK_INTERVAL = 0.5
    PAGE_TEXT = "达人信息"
    TARGET_URL = "https://www.xingtu.cn/ad/creator/market"

    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.page = browser_manager.context.new_page()

    # ===== 核心工作流 =====
    def search_task(self, keyword: str, limit_range: ProcessingRange):
        """主流程：搜索 + 翻页 + 处理"""
        if limit_range.start < 1 or limit_range.end < limit_range.start:
            raise ValueError(f"无效范围: {limit_range}")

        logger.info(f"开始任务: 搜索'{keyword}' 数据范围 {limit_range.start}-{limit_range.end}")
        processor = AnchorProcessor(self.page)

        try:
            self._prepare_page()
            self._search_keyword(keyword)

            start_page, end_page = self._page_range(limit_range)
            end_rank = 1
            for page_number in range(start_page, end_page + 1):
                end_rank = self._process_page(page_number, limit_range, processor)
                if end_rank >= limit_range.end:
                    break

            logger.info(f"任务完成，最终处理到第 {end_rank} 条")

        except TimeoutError as te:
            logger.error(f"超时错误: {te}")
        except Exception as e:
            logger.error(f"任务出错: {e}", exc_info=True)
        finally:
            self.browser_manager.close()

    # ===== 页面初始化与检查 =====
    def _prepare_page(self):
        """打开页面并确保登录与验证码正常"""
        logger.info("加载目标页面中...")
        self.page.goto(self.TARGET_URL, timeout=60000)
        logger.info("页面加载完成")

        if not check_login_status(self.page):
            wait_for_user_action("请先登录")
            if not check_login_status(self.page):
                raise Exception("用户未登录，无法继续执行任务")

        if check_captcha_status(self.page):
            wait_for_user_action("请完成验证码验证")
            if check_captcha_status(self.page):
                raise Exception("验证码未完成")

        logger.info("登录与验证码状态检查通过")

    # ===== 搜索逻辑 =====
    def _search_keyword(self, keyword: str):
        """执行关键词搜索"""
        logger.info(f"执行关键词搜索: {keyword}")
        self.page.get_by_text("内容找人").first.click()
        box = self.page.get_by_role("textbox", name="按内容关键词找达人")
        box.fill(keyword)
        box.press("Enter")
        if self.SEARCH_WAIT_SECONDS > 0:
            logger.info(f"等待 {self.SEARCH_WAIT_SECONDS} 秒供用户调整筛选条件")
            time.sleep(self.SEARCH_WAIT_SECONDS)

    # ===== 页码逻辑 =====
    def _page_range(self, limit_range: ProcessingRange):
        start = (limit_range.start - 1) // self.PAGE_SIZE + 1
        end = (limit_range.end - 1) // self.PAGE_SIZE + 1
        logger.info(f"页码范围: {start}-{end}")
        return start, end

    # ===== 单页处理逻辑 =====
    def _process_page(self, page_number, limit_range, processor):
        """处理单页数据"""
        jump_to_target_page(self.page, page_number)
        self.page.get_by_text(self.PAGE_TEXT).first.click()
        scroll_multiple_times(self.page)

        start_rank = (page_number - 1) * self.PAGE_SIZE + 1
        end_rank = start_rank + self.PAGE_SIZE - 1

        if end_rank < limit_range.start:
            logger.info(f"第{page_number}页在范围之前，跳过")
            return end_rank
        if start_rank > limit_range.end:
            logger.info(f"第{page_number}页在范围之后，终止")
            return limit_range.end

        start_item = max(1, limit_range.start - start_rank + 1)
        end_item = min(self.PAGE_SIZE, limit_range.end - start_rank + 1)

        for item_index in range(start_item, end_item + 1):
            rank = start_rank + item_index - 1
            self.page.locator("body").focus()
            processor.process_single_task(item_index, rank)
            time.sleep(self.TASK_INTERVAL)

        return end_rank
