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
    # 可配置参数
    PAGE_SIZE = 20  # 每页显示的条目数量
    SEARCH_WAIT_SECONDS = 0  # 搜索后等待用户调整筛选条件的时间
    TASK_INTERVAL = 0.5  # 任务间隔时间(秒)
    PAGE_TEXT = "达人信息"  # 用来回到焦点
    TARGET_URL = "https://www.xingtu.cn/ad/creator/market"

    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.page = browser_manager.context.new_page()

    def _initialize_page(self):
        """初始化页面，打开目标URL"""
        try:
            logger.info("开始打开搜索页面")
            self.page.goto(self.TARGET_URL, timeout=60000)
            logger.info("搜索页面打开成功")
        except Exception as e:
            logger.error(f"加载页面失败: {str(e)}", exc_info=True)
            raise

    def _perform_preliminary_checks(self):
        """执行登录和验证码的初步检查"""
        # 检测登录状态
        logger.info("----- 流程步骤1：检测登录状态 -----")
        if not check_login_status(self.page):
            wait_for_user_action("请先完成登录操作")
            if not check_login_status(self.page):
                raise Exception("用户未完成登录，无法继续执行任务")
            self._initialize_page()  # 登录后重新初始化
        logger.info("登录状态验证通过")

        # 检测验证码
        logger.info("----- 流程步骤2：检测主页面验证码 -----")
        if check_captcha_status(self.page):
            wait_for_user_action("主页面出现验证码，请完成验证")
            if check_captcha_status(self.page):
                raise Exception("用户未完成验证码验证，无法继续执行任务")
        logger.info("验证码状态验证通过")

    def _search_keywords(self, keywords: str):
        """执行关键词搜索"""
        logger.info("----- 流程步骤3：执行搜索操作 -----")
        self.page.get_by_text("内容找人").first.click()
        search_box = self.page.get_by_role("textbox", name="按内容关键词找达人")
        search_box.click()
        search_box.fill(keywords)
        search_box.press("Enter")

        logger.info(f"等待{self.SEARCH_WAIT_SECONDS}秒供用户调整筛选参数")
        time.sleep(self.SEARCH_WAIT_SECONDS)

    def _calculate_rank(self, page_number: int, item_index: int) -> int:
        """根据页码和条目索引计算排名"""
        return (page_number - 1) * self.PAGE_SIZE + item_index

    def _get_page_processing_range(self, page_number: int, limit_range: ProcessingRange):
        """计算当前页需要处理的条目范围"""
        page_start_rank = self._calculate_rank(page_number, 1)
        page_end_rank = self._calculate_rank(page_number, self.PAGE_SIZE)

        # 检查页面是否在处理范围内
        if page_end_rank < limit_range.start:
            return None, "before_range"  # 页面在范围之前
        if page_start_rank > limit_range.end:
            return None, "after_range"  # 页面在范围之后

        # 计算当前页需要处理的条目索引范围
        start_item = max(1, limit_range.start - page_start_rank + 1)
        end_item = min(self.PAGE_SIZE, limit_range.end - page_start_rank + 1)

        return (start_item, end_item, page_start_rank), "in_range"

    def _process_page_items(self, page_number: int, item_range, processor, current_rank):
        """处理页面中的条目"""
        start_item, end_item, page_start_rank = item_range

        logger.debug(f"第{page_number}页处理条目索引: {start_item}-{end_item}")

        for item_index in range(start_item, end_item + 1):
            rank = self._calculate_rank(page_number, item_index)

            # 检查是否超出范围上限
            if rank > current_rank["limit_end"]:
                logger.info(f"已超出设置的上限{current_rank['limit_end']}条，停止处理")
                return False

            logger.debug(f"处理第{rank}条数据（第{page_number}页第{item_index}项）")
            self.page.locator("body").focus()
            processor.process_single_task(item_index, rank)

            current_rank["value"] = rank
            time.sleep(self.TASK_INTERVAL)

        return True

    def _process_single_page(self, page_number, processor, limit_range, current_rank):
        """处理单页数据"""
        logger.info(f"开始处理第{page_number}页数据，当前排名: {current_rank['value']}")

        try:
            # 跳转到目标页并准备
            jump_to_target_page(self.page, page_number)
            self.page.get_by_text(self.PAGE_TEXT).first.click()
            scroll_multiple_times(self.page)
            logger.info(f"第{page_number}页滚动完成，开始处理条目")

            # 获取处理范围
            item_range, status = self._get_page_processing_range(page_number, limit_range)

            if status == "before_range":
                logger.info(f"第{page_number}页完全在目标范围之前，跳过处理")
                current_rank["value"] = self._calculate_rank(page_number, self.PAGE_SIZE)
                return True

            if status == "after_range":
                logger.info(f"第{page_number}页完全在目标范围之后，停止处理")
                return False

            # 处理当前页条目
            return self._process_page_items(page_number, item_range, processor, current_rank)

        except Exception as e:
            logger.error(f"处理第{page_number}页时发生错误: {str(e)}", exc_info=True)
            return True  # 出错仍尝试处理下一页

    def _calculate_page_range(self, limit_range: ProcessingRange):
        """计算需要处理的页码范围"""
        start_page = (limit_range.start - 1) // self.PAGE_SIZE + 1
        end_page = (limit_range.end - 1) // self.PAGE_SIZE + 1
        logger.info(f"目标范围涉及页码: 第{start_page}页 - 第{end_page}页")
        return start_page, end_page

    def search_task(self, keyword: str, limit_range: ProcessingRange):
        """执行平台搜索流程主入口"""
        # 验证输入范围的有效性
        if limit_range.start < 1 or limit_range.end < limit_range.start:
            raise ValueError(f"无效的范围参数: start={limit_range.start}, end={limit_range.end}")

        logger.info(
            f"\n===== 开始执行任务：搜索关键词 '{keyword}'，"
            f"获取范围 {limit_range.start}-{limit_range.end} 条数据 ====="
        )

        try:
            # 初始化页面和前置检查
            self._initialize_page()
            self._perform_preliminary_checks()

            # 执行搜索
            self._search_keywords(keyword)

            # 计算页面范围并处理
            start_page, end_page = self._calculate_page_range(limit_range)
            processor = AnchorProcessor(self.page)

            # 当前排名跟踪，包含限制范围信息
            current_rank = {
                "value": limit_range.start - 1,
                "limit_end": limit_range.end
            }

            # 处理指定范围的页面
            for page_number in range(start_page, end_page + 1):
                if not self._process_single_page(page_number, processor, limit_range, current_rank):
                    break

            logger.info(f"任务执行完成，最终处理到第{current_rank['value']}条数据")

        except TimeoutError as te:
            logger.error(f"操作超时错误: {str(te)}", exc_info=True)
            logger.error("可能原因：页面元素未出现、网络延迟或页面加载缓慢")
        except Exception as e:
            logger.error(f"任务执行过程中发生错误: {str(e)}", exc_info=True)
        finally:
            logger.info("关闭浏览器实例")
            self.browser_manager.close()
