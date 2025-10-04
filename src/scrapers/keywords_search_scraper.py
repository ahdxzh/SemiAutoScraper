import time
import logging
import os
from pathlib import Path
from playwright.sync_api import TimeoutError

from src.scrapers.live_author_scraper import AnchorProcessor
from src.utils.captcha_util import with_captcha_handling
from src.utils.csv_util import save_dict_list_to_csv
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


class KeywordsSearchScraper:
    # 可配置参数
    PAGE_SIZE = 20  # 每页显示的条目数量
    SEARCH_WAIT_SECONDS = 60  # 搜索后等待用户调整筛选条件的时间
    TASK_INTERVAL = 0.5  # 任务间隔时间(秒)
    MAX_RETRY = 3  # 最大重试次数
    OUTPUT_DIR = "output"  # 输出目录
    OUTPUT_FILENAME = "anchor_data.csv"  # 输出文件名

    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.page = browser_manager.context.new_page()
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        Path(self.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def _initialize_page(self):
        """初始化页面，打开目标URL"""
        page = self.page
        target_url = "https://pgy.xiaohongshu.com/solar/pre-trade/note/kol"

        try:
            logger.info("开始打开搜索页面")
            page.goto(target_url, timeout=60000)
            logger.info("搜索页面打开成功")
        except Exception as e:
            logger.error(f"加载页面失败: {str(e)}", exc_info=True)
            raise  # 重新抛出异常，让上层处理

    @with_captcha_handling()
    def _search_author(self, keywords: str):
        """执行关键词搜索操作，利用固定type属性精确定位输入框"""
        logger.info(f"开始搜索关键词: {keywords}")

        # 由于type="text"是固定不变的，优先使用该属性增强定位稳定性
        search_input_selector = (
            'input.d-text'
            '[type="text"]'  # 固定属性，优先使用
            '[placeholder="按笔记关键词找博主，试试搜"]'
        )
        search_input = self.page.locator(search_input_selector).first

        # 等待输入框可交互（确保type属性已正确加载）
        search_input.wait_for(state='editable', timeout=10000)
        logger.debug("目标搜索框已加载并可编辑")

        # 输入关键词
        search_input.fill(keywords)
        logger.debug(f"已在搜索框中输入关键词: {keywords}")

    def _process_single_page(self, page_number, processor, limit, current_rank, all_results, failed_tasks):
        """处理单页数据"""
        page = self.page
        logger.info(f"开始处理第{page_number}页数据")

        try:
            # 跳转到目标页
            jump_to_target_page(page, page_number)

            # 页面准备操作
            page.locator("body").focus()
            page.wait_for_timeout(100)
            page.get_by_text("博主信息").first.click()
            scroll_multiple_times(page)
            logger.info(f"第{page_number}页滚动完成，开始处理条目")

            # 处理当前页的每个条目
            for item_number in range(1, self.PAGE_SIZE + 1):
                if current_rank["value"] > limit:
                    logger.info(f"已达到设置的上限{limit}条，停止处理")
                    return False  # 已达到上限，停止处理

                page.locator("body").focus()
                # 处理单个条目信息
                result = self._process_task_safe(processor, item_number, current_rank["value"])

                if result is not None:
                    all_results.append(result)
                    logger.debug(f"第{current_rank['value']}条信息处理成功")
                else:
                    failed_tasks.append((page_number, item_number, current_rank["value"]))
                    logger.warning(f"第{current_rank['value']}条信息处理失败")

                current_rank["value"] += 1
                time.sleep(self.TASK_INTERVAL)

            logger.info(f"第{page_number}页数据处理完成")
            return True  # 继续处理下一页

        except Exception as e:
            logger.error(f"处理第{page_number}页时发生错误: {str(e)}", exc_info=True)
            return True  # 即使当前页出错，仍尝试处理下一页

    def search_task(self, keyword: str, limit: int = 3):
        """执行平台搜索流程，包含登录和验证码检测"""
        logger.info(f"\n===== 开始执行任务：搜索关键词 '{keyword}'，限制获取{limit}条数据 =====")

        try:
            # 初始化页面
            self._initialize_page()
            page = self.page

            # 检测登录状态
            logger.info("----- 流程步骤1：检测登录状态 -----")
            if not check_login_status(page):
                wait_for_user_action("请先完成登录操作")
                if not check_login_status(page):
                    raise Exception("用户未完成登录，无法继续执行任务")
            logger.info("登录状态验证通过")

            # 检测主页面验证码
            logger.info("----- 流程步骤2：检测主页面验证码 -----")
            if check_captcha_status(page):
                wait_for_user_action("主页面出现验证码，请完成验证")
                if check_captcha_status(page):
                    raise Exception("用户未完成验证码验证，无法继续执行任务")
            logger.info("验证码状态验证通过")

            # 执行搜索操作
            logger.info("----- 流程步骤3：执行搜索操作 -----")
            self._search_author(keyword)

            # 分页处理列表数据
            logger.info("----- 流程步骤4：分页处理列表数据 -----")
            total_pages = (limit + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            logger.info(f"预计需要处理{total_pages}页数据")

            processor = AnchorProcessor(page)
            all_results = []
            failed_tasks = []
            current_rank = {"value": 1}  # 使用字典实现可变整数

            # 处理每一页
            for page_number in range(1, total_pages + 1):
                continue_processing = self._process_single_page(
                    page_number, processor, limit, current_rank, all_results, failed_tasks
                )
                if not continue_processing:
                    break

            # 保存结果
            output_path = os.path.join(self.OUTPUT_DIR, self.OUTPUT_FILENAME)
            save_dict_list_to_csv(all_results, output_path)
            logger.info(f"结果已保存至: {output_path}")

            # 输出统计信息
            logger.info(f"任务执行完成，总共处理了 {len(all_results)} 条有效数据")
            if failed_tasks:
                logger.warning(f"存在{len(failed_tasks)}条处理失败的任务: {failed_tasks}")

            return all_results, failed_tasks

        except TimeoutError as te:
            logger.error(f"操作超时错误: {str(te)}", exc_info=True)
            logger.error("可能原因：页面元素未出现、网络延迟或页面加载缓慢")
        except Exception as e:
            logger.error(f"任务执行过程中发生错误: {str(e)}", exc_info=True)
        finally:
            logger.info("关闭浏览器实例")
            self.browser_manager.close()

    def _process_task_safe(self, processor, item_number, rank):
        """
        安全处理单条列表数据，包含重试机制
        :param processor: 处理工具
        :param item_number: 条目序号
        :param rank: 排名
        :return: 处理结果或None
        """
        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                processor.process_anchor(item_number, rank)
                return processor.current_data
            except Exception as e:
                logger.warning(
                    f"处理第{rank}条数据(第{attempt}/{self.MAX_RETRY}次尝试)失败: {str(e)}",
                    exc_info=(attempt == self.MAX_RETRY)  # 最后一次失败才打印详细堆栈
                )
                time.sleep(1)

        logger.error(f"第{rank}条数据处理失败，已达到最大重试次数{self.MAX_RETRY}，跳过该任务")
        return None
