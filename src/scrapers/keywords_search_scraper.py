import logging
import time
from pathlib import Path

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


class KeywordsSearchScraper:
    # 可配置参数
    PAGE_SIZE = 20  # 每页显示的条目数量
    SEARCH_WAIT_SECONDS = 60  # 搜索后等待用户调整筛选条件的时间
    TASK_INTERVAL = 0.5  # 任务间隔时间(秒)
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

            # 可选：触发搜索
            search_input.press('Enter')
            logger.debug("已提交搜索")

        except Exception as e:
            logger.error(f"搜索操作失败: {str(e)}")
            raise  # 重新抛出异常，让上层处理

        return True

    def _process_single_page(self, page_number, processor, limit_start, limit_end, current_rank):
        """处理单页数据，支持范围参数"""
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
                # 检查是否超出范围上限
                if current_rank["value"] > limit_end:
                    logger.info(f"已达到设置的上限{limit_end}条，停止处理")
                    return False  # 已达到上限，停止处理

                # 只处理范围内的条目
                if current_rank["value"] >= limit_start:
                    page.locator("body").focus()
                    processor.process_single_task(item_number, current_rank["value"])

                current_rank["value"] += 1
                time.sleep(self.TASK_INTERVAL)

            logger.info(f"第{page_number}页数据处理完成")
            return True  # 继续处理下一页

        except Exception as e:
            logger.error(f"处理第{page_number}页时发生错误: {str(e)}", exc_info=True)
            return True  # 即使当前页出错，仍尝试处理下一页

    def search_task(self, keyword: str, limit_range):
        """执行平台搜索流程，接收范围参数（包含start和end属性的对象）"""
        # 从范围对象中提取起始值和结束值
        limit_start = limit_range.start
        limit_end = limit_range.end

        logger.info(
            f"\n===== 开始执行任务：搜索关键词 '{keyword}'，"
            f"获取范围 {limit_start}-{limit_end} 条数据 ====="
        )

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
                else:
                    # 登录完成后重新初始化页面
                    self._initialize_page()
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
            self._search_keywords(keyword)

            # 分页处理列表数据
            logger.info("----- 流程步骤4：分页处理列表数据 -----")
            # 根据范围结束值计算总页数
            total_pages = (limit_end + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            logger.info(f"预计需要处理{total_pages}页数据")
            processor = AnchorProcessor(page)

            # 关键修改：根据起始值初始化current_rank
            current_rank = {"value": limit_start}  # 从起始值开始计数
            logger.info(f"从第{limit_start}条开始处理，到第{limit_end}条结束")

            # 处理每一页
            for page_number in range(1, total_pages + 1):
                continue_processing = self._process_single_page(
                    page_number,
                    processor,
                    limit_start,
                    limit_end,
                    current_rank
                )
                if not continue_processing:
                    break

        except TimeoutError as te:
            logger.error(f"操作超时错误: {str(te)}", exc_info=True)
            logger.error("可能原因：页面元素未出现、网络延迟或页面加载缓慢")
        except Exception as e:
            logger.error(f"任务执行过程中发生错误: {str(e)}", exc_info=True)
        finally:
            logger.info("关闭浏览器实例")
            self.browser_manager.close()
