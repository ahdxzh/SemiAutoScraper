import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from playwright.sync_api import TimeoutError

from src.utils.page_operate import scroll_multiple_times
from src.utils.page_status_check import check_login_status, check_captcha_status
from src.utils.page_user_interaction import wait_for_user_action
from src.utils.page_util import jump_to_target_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingRange:
    start: int
    end: int


class KeywordsSearchScraperBase(ABC):
    """关键词搜索爬虫模板类（Template Method Pattern）"""

    PAGE_SIZE = 20
    TASK_INTERVAL = 0.5

    TARGET_URL = None
    PAGE_TEXT = None
    PAGE_INPUT_SELECTOR = None

    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.page = browser_manager.context.new_page()

    # ======= 主模板流程 =======
    def run(self, keyword: str, limit_range: ProcessingRange):
        """完整执行流程"""
        if limit_range.start < 1 or limit_range.end < limit_range.start:
            raise ValueError(f"无效范围: {limit_range}")

        logger.info(f"开始任务: 搜索 '{keyword}' 数据范围 {limit_range.start}-{limit_range.end}")
        processor = self.create_processor()

        try:
            self._prepare_page()
            self._search_keywords(keyword)
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

    # ======= 由子类实现的抽象方法 =======
    @abstractmethod
    def create_processor(self):
        """创建具体数据处理器"""
        pass

    @abstractmethod
    def _search_keywords(self, keyword: str):
        """执行关键词搜索（各平台不同）"""
        pass

    @abstractmethod
    def process_single_item(self, processor, item_index: int, rank: int):
        """处理单个 item"""
        pass

    # ======= 通用逻辑 =======
    def _prepare_page(self):
        """加载页面并通过登录/验证码检查"""
        logger.info("加载目标页面中...")
        self.page.goto(self.TARGET_URL, timeout=60000)
        logger.info("页面加载完成")

        if not check_login_status(self.page):
            wait_for_user_action("请先登录")
            if not check_login_status(self.page):
                raise Exception("用户未登录")

        if check_captcha_status(self.page):
            wait_for_user_action("请完成验证码验证")
            if check_captcha_status(self.page):
                raise Exception("验证码未完成")

        logger.info("登录与验证码状态检查通过")

    def _page_range(self, limit_range: ProcessingRange):
        start = (limit_range.start - 1) // self.PAGE_SIZE + 1
        end = (limit_range.end - 1) // self.PAGE_SIZE + 1
        logger.info(f"页码范围: {start}-{end}")
        return start, end

    def _process_page(self, page_number, limit_range, processor):
        """统一的翻页与循环逻辑"""
        jump_to_target_page(self.page, page_number, input_selector=self.PAGE_INPUT_SELECTOR)
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
            self.process_single_item(processor, item_index, rank)
            time.sleep(self.TASK_INTERVAL)

        return end_rank
