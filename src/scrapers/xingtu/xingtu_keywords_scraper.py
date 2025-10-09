import logging
import time

from src.scrapers.keywords_scraper_base import KeywordsSearchScraperBase
from src.scrapers.xingtu.xingtu_anchor_scraper import AnchorProcessor

logger = logging.getLogger(__name__)


class XingtuKeywordsSearchScraper(KeywordsSearchScraperBase):
    """星图达人关键词爬虫"""
    SEARCH_WAIT_SECONDS = 60

    TARGET_URL = "https://www.xingtu.cn/ad/creator/market"
    PAGE_TEXT = "达人信息"
    PAGE_INPUT_SELECTOR = ".pagination .xt-input-number__input .el-input__inner"

    def create_processor(self):
        return AnchorProcessor(self.page)

    def _search_keyword(self, keyword: str):
        """平台特定的搜索逻辑"""
        logger.info(f"执行关键词搜索: {keyword}")
        self.page.get_by_text("内容找人").first.click()
        box = self.page.get_by_role("textbox", name="按内容关键词找达人")
        box.fill(keyword)
        if self.SEARCH_WAIT_SECONDS > 0:
            logger.info(f"等待 {self.SEARCH_WAIT_SECONDS} 秒供用户调整筛选条件")
            time.sleep(self.SEARCH_WAIT_SECONDS)
        box.press("Enter")

    def process_single_item(self, processor, item_index: int, rank: int):
        processor.process_single_task(item_index, rank)
