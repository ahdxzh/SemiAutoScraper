from pathlib import Path
from typing import Dict

from playwright.sync_api import Page

from src.utils.captcha_util import with_captcha_handling
from src.utils.csv_util import save_single_dict_to_csv
from src.utils.extract_util import find_ancestor_texts_with_value
from src.utils.page_operate import screenshot_element, scroll_multiple_times


class AnchorProcessor:
    def __init__(self, page: Page):
        self.main_page = page
        self.anchor_page = None

        self.anchor_name = None
        self.rank = None
        # 存储主播详细数据
        self.current_data: Dict[str, str] = {}
        # 确保输出目录存在
        self._ensure_directories()

    @staticmethod
    def _ensure_directories():
        """确保所有输出目录存在"""
        directories = [
            "outPut/曝光量",
            "outPut/数据概览",
            "outPut/粉丝画像"
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @with_captcha_handling()
    def _open_anchor_page(self, i):
        anchor_card = self.main_page.locator(
            f"div.blogger-list_list tr:nth-child({i}) div.kol-info_detail > div:nth-child(1) > span").first
        anchor_name = anchor_card.text_content().strip()
        self.anchor_name = anchor_name
        self.current_data["达人名称"] = anchor_name
        print(f"开始处理主播: {anchor_name}")
        with self.main_page.expect_popup() as popup_info:
            anchor_card.click(timeout=5000)
        self.anchor_page = popup_info.value

    @with_captcha_handling()
    def _open_first_note_detail(self):
        """打开笔记案例中第一个笔记"""
        first_note_card = self.anchor_page.locator("div.note-card__mask").first
        first_note_card.wait_for(state="visible", timeout=5000)
        first_note_card.click(timeout=5000)
        print("已打开笔记详情页面")

    @with_captcha_handling()
    def _take_anchor_note_screenshot(self):
        note_wrapper = self.anchor_page.locator("div.d-drawer-content")
        note_wrapper.wait_for(state="visible")
        # 截图曝光量
        screenshot_path = f"outPut/曝光量/{self.rank}_{self.anchor_name}.png"
        screenshot_element(
            page=self.anchor_page,
            locator=note_wrapper,
            save_path=screenshot_path,
            timeout=5000
        )

        self.current_data["视频播放数"] = find_ancestor_texts_with_value(self.anchor_page, "曝光量", note_wrapper)
        self.current_data["粉丝数"] = find_ancestor_texts_with_value(self.anchor_page, "粉丝数", note_wrapper)
        self.current_data["视频发布时间"] = self.anchor_page.locator(
            "div.note-create-time span:nth-child(2)").first.text_content().strip()

    @with_captcha_handling()
    def _copy_note_link(self):
        # 复制笔记链接
        copy_link = self.anchor_page.locator("div.copy-note-link-container span").first
        copy_link.click(timeout=5000)

        # 尝试读取剪贴板
        try:
            copied_text = self.anchor_page.evaluate("""async () => {
                return await navigator.clipboard.readText();
            }""")
            self.current_data["视频链接"] = copied_text
        except Exception as e:
            print("权限问题:", e)
        finally:
            # 关闭笔记详情
            self.anchor_page.locator(".d-drawer-header > span > svg").first.click(timeout=5000)

    @with_captcha_handling()
    def _take_anchor_overview_screenshot(self):
        """打开数据概览"""
        data_overview_tab = self.anchor_page.locator(
            "div.d-tabs-headers-wrapper div.d-tabs-header:has(h6.d-tabs-header-label:text('数据概览'))"
        )
        data_overview_tab.click()
        anchor_overview_wrapper = self.anchor_page.locator(".blogger-detail-container")
        anchor_overview_wrapper.wait_for(state="visible")
        screenshot_path = f"outPut/数据概览/{self.rank}_{self.anchor_name}.png"
        screenshot_element(
            page=self.anchor_page,
            save_path=screenshot_path,
            crop_top=50,
            timeout=5000
        )

        self.current_data["小红书ID"] = find_ancestor_texts_with_value(self.anchor_page, "小红书号",
                                                                       anchor_overview_wrapper)
        self.current_data["达人类型"] = find_ancestor_texts_with_value(self.anchor_page, "博主优势",
                                                                       anchor_overview_wrapper)
        self.current_data["内容主题"] = find_ancestor_texts_with_value(self.anchor_page, "内容类目",
                                                                       anchor_overview_wrapper)
        self.current_data["行业标签"] = find_ancestor_texts_with_value(self.anchor_page, "合作行业",
                                                                       anchor_overview_wrapper)
        self.current_data["合作报价"] = find_ancestor_texts_with_value(self.anchor_page, "图文笔记一口价",
                                                                       anchor_overview_wrapper)

    @with_captcha_handling()
    def _take_anchor_fans_screenshot(self):
        fans_tab = self.anchor_page.locator(
            "div.d-tabs-headers-wrapper div.d-tabs-header:has(h6.d-tabs-header-label:text('粉丝分析'))"
        )
        fans_tab.click()

        print("将粉丝画像顶部对齐")
        scroll_multiple_times(self.anchor_page, total_scrolls=1, key_presses_per_scroll=18)
        anchor_overview_wrapper = self.anchor_page.locator(".blogger-detail-container")
        anchor_overview_wrapper.wait_for(state="visible")
        screenshot_path = f"outPut/粉丝画像/{self.rank}_{self.anchor_name}.png"
        screenshot_element(
            page=self.anchor_page,
            save_path=screenshot_path,
            timeout=5000,
            crop_top=50
        )

        self.current_data["性别"] = find_ancestor_texts_with_value(self.anchor_page, "性别分布",
                                                                   anchor_overview_wrapper)
        self.current_data["年龄"] = find_ancestor_texts_with_value(self.anchor_page, "年龄分布",
                                                                   anchor_overview_wrapper)
        self.current_data["地域"] = find_ancestor_texts_with_value(self.anchor_page, "地域分布",
                                                                   anchor_overview_wrapper)

    def process_single_task(self, i: int, rank: int):
        """处理单个主播的完整流程"""
        self.rank = rank
        self.current_data = {"排名": str(rank)}

        try:
            print("\n----- 主播处理流程1：进入主播详情 -----")
            self._open_anchor_page(i)

            print("\n----- 主播处理流程2：点开主播笔记案例 -----")
            self._open_first_note_detail()

            print("\n----- 主播处理流程3：处理笔记详情 -----")
            self._take_anchor_note_screenshot()

            print("\n----- 主播处理流程4：复制小红书链接 -----")
            self._copy_note_link()

            # 主动检查一次新页面（非异常场景）
            print("\n----- 主播处理流程5：处理数据概览 -----")
            self._take_anchor_overview_screenshot()

            print("\n----- 主播处理流程6：处理粉丝画像 -----")
            self._take_anchor_fans_screenshot()

        except Exception as e:
            print(f"处理主播过程中发生错误: {str(e)}")
            self.current_data["操作错误信息"] = str(e)
        finally:
            if self.anchor_page and not self.anchor_page.is_closed():
                self.anchor_page.close()

        save_single_dict_to_csv(self.current_data)
