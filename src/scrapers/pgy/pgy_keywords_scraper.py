import logging
import time

from src.scrapers.keywords_scraper_base import KeywordsSearchScraperBase
from src.scrapers.pgy.pgy_anchor_scraper import AnchorProcessor

logger = logging.getLogger(__name__)


class PgyKeywordsSearchScraper(KeywordsSearchScraperBase):
    """蒲公英关键词爬虫"""
    SEARCH_WAIT_SECONDS = 60

    TARGET_URL = "https://pgy.xiaohongshu.com/solar/pre-trade/note/kol"
    PAGE_TEXT = "博主信息"
    PAGE_INPUT_SELECTOR = "div.d-pagination.hide-pagination-page-size > div:nth-child(2) div.d-pagination-goto input.d-text.d-text-monospace"

    def create_processor(self):
        return AnchorProcessor(self.page)

    # ===== 搜索逻辑 =====
    def _search_keywords(self, keywords: str):
        """执行关键词搜索操作，不使用填充词定位输入框"""
        logger.info(f"开始搜索关键词: {keywords}")

        try:
            # 仅使用class和type属性定位，移除填充词条件
            selector = 'input.d-text[type="text"]'
            search_input = self.page.locator(selector).first

            # 等待输入框可见
            search_input.wait_for(state='visible', timeout=10000)
            logger.debug("目标搜索框已加载并可见")

            # 检查元素是否可编辑
            if not search_input.is_enabled():
                raise Exception("搜索框不可编辑")
            logger.debug("目标搜索框可编辑")

            # 输入关键词
            search_input.fill(keywords)
            logger.debug(f"已在搜索框中输入关键词: {keywords}")
            search_input.press("Enter")
            if self.SEARCH_WAIT_SECONDS > 0:
                logger.info(f"等待 {self.SEARCH_WAIT_SECONDS} 秒供用户调整筛选条件")
                time.sleep(self.SEARCH_WAIT_SECONDS)

        except Exception as e:
            logger.error(f"搜索操作失败: {str(e)}")
            raise  # 重新抛出异常，让上层处理
        return True

    def process_single_item(self, processor, item_index: int, rank: int):
        processor.process_single_task(item_index, rank)
