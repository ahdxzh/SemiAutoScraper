from pathlib import Path
from typing import Optional, List, Dict

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.utils.captcha_util import with_captcha_handling, handle_captcha
from src.utils.csv_util import save_single_dict_to_csv
from src.utils.extract_util import find_ancestor_texts_with_value
from src.utils.page_operate import screenshot_element, scroll_multiple_times


class AnchorProcessor:
    def __init__(self, page: Page):
        self.page = page
        # 存储所有主播数据的列表
        self.data_list: List[Dict[str, str]] = []
        # 当前处理的主播数据
        self.current_data: Dict[str, str] = {}

        # 确保输出目录存在
        self._ensure_directories()

    @staticmethod
    def _ensure_directories():
        """确保所有输出目录存在"""
        directories = [
            "outPut/曝光量",
            "outPut/达人主页",
            "outPut/订单截图"
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @with_captcha_handling()
    def open_first_note_detail(self):
        """打开笔记案例中第一个笔记"""
        first_note_card = self.page.locator("div.note-card__mask").first
        first_note_card.wait_for(state="visible", timeout=5000)
        first_note_card.click(timeout=5000)
        print("已打开笔记详情页面")

    @with_captcha_handling()
    def take_anchor_card_screenshot(self, rank: int, anchor_name: str):
        card_wrapper = self.page.locator("div.d-drawer-content")
        card_wrapper.wait_for(state="visible")
        # 截图曝光量
        screenshot_path = f"outPut/曝光量/{rank}_{anchor_name}.png"
        screenshot_element(
            page=self.page,
            locator=card_wrapper,
            save_path=screenshot_path,
            timeout=5000
        )

        self.current_data["视频播放数"] = find_ancestor_texts_with_value(self.page, "曝光量", card_wrapper)
        self.current_data["粉丝数"] = find_ancestor_texts_with_value(self.page, "粉丝数", card_wrapper)
        self.current_data["视频发布时间"] = self.page.locator(
            "div.note-create-time span:nth-child(2)").first.text_content().strip()
        # 复制笔记链接
        copy_link = self.page.locator("div.copy-note-link-container span").first
        copy_link.click(timeout=5000)

        # 尝试读取剪贴板
        try:
            copied_text = self.page.evaluate("""async () => {
                return await navigator.clipboard.readText();
            }""")
            self.current_data["视频链接"] = copied_text

        except Exception as e:
            print("权限问题:", e)

    @with_captcha_handling()
    def open_anchor_new_page(self, anchor_card) -> Page:
        """打开主播新页面"""
        with self.page.expect_popup() as popup_info:
            anchor_card.click(timeout=5000)
        new_page = popup_info.value
        page_title = new_page.title()
        print(f"新页面已弹出，页面标题: {page_title}")

        return new_page

    @with_captcha_handling()
    def extract_anchor_new_page(self, new_page: Page):
        handle_captcha(new_page)
        anchor_detail_card = new_page.locator(".main").first
        # 粉丝数 → 明确为粉丝数量
        fan_count = find_ancestor_texts_with_value(new_page, "粉丝数", anchor_detail_card)
        # 星图ID → 突出"星图"标识
        star_map_id = find_ancestor_texts_with_value(new_page, "星图ID", anchor_detail_card)
        # 达人类型 → "达人"常用talent表示，更贴合行业术语
        talent_type = find_ancestor_texts_with_value(new_page, "达人类型", anchor_detail_card)
        # 内容主题 → 直接对应"内容主题"的含义
        content_topic = find_ancestor_texts_with_value(new_page, "内容主题", anchor_detail_card)
        # 行业标签 → 明确为行业相关的标签
        industry_tag = find_ancestor_texts_with_value(new_page, "行业标签", anchor_detail_card)
        self.current_data["粉丝数"] = fan_count
        self.current_data["星图ID"] = star_map_id
        self.current_data["达人类型"] = talent_type
        self.current_data["内容主题"] = content_topic
        self.current_data["行业标签"] = industry_tag

    @with_captcha_handling()
    def switch_to_connect_user_tab(self, new_page: Page):
        """切换到连接用户标签并执行相关操作"""
        connect_user_tab = new_page.get_by_role("tab", name="连接用户")
        connect_user_tab.click()
        print("将连接用户漏斗洞察顶部对齐")
        new_page.get_by_text("用户漏斗").first.click()
        scroll_multiple_times(new_page, total_scrolls=1, key_presses_per_scroll=15)
        print("已成功将连接用户漏斗洞察顶部对齐")
        return True

    @with_captcha_handling()
    def take_anchor_home_screenshot(self, new_page: Page, rank: int, anchor_name: str):
        """截图达人主页"""
        screenshot_path = f"outPut/达人主页/{rank}_{anchor_name}.png"
        screenshot_element(
            page=new_page,
            save_path=screenshot_path,
            timeout=5000,
            crop_top=150
        )
        print(f"✅ 达人主页截图成功：{rank}_{anchor_name}.png")
        anchor_fan_card = new_page.locator(".content-container .right").first
        fan_summarize = find_ancestor_texts_with_value(new_page, "总结", anchor_fan_card)
        fan_type = find_ancestor_texts_with_value(new_page, "连接用户类型", anchor_fan_card)
        self.current_data["总结"] = fan_summarize
        self.current_data["连接用户类型"] = fan_type

    @with_captcha_handling()
    def click_order_button(self, new_page: Page, rank: int, anchor_name: str):
        """点击下单按钮并截图"""
        order_button_selector = "div[data-btm='add']:has(div.desc:has-text(' 21-60s视频 ')) button:has-text('下单')"
        order_button = new_page.locator(order_button_selector)

        order_button.wait_for(timeout=3000)
        order_button.click(force=True)
        print("下单按钮点击成功")

        order_card = new_page.locator(".selected-author-list.select-author-list")
        screenshot_path = f"outPut/订单截图/{rank}_{anchor_name}.png"
        screenshot_element(
            page=new_page,
            locator=order_card,
            save_path=screenshot_path,
            timeout=10000
        )
        order_amount = find_ancestor_texts_with_value(new_page, "合计", order_card)
        self.current_data["报价"] = order_amount

    def process_single_task(self, i: int, rank: int):
        """处理单个主播的完整流程"""
        new_page: Optional[Page] = None
        # 重置当前主播数据
        self.current_data = {"排名": str(rank)}

        try:
            print("\n----- 主播处理流程1：进入主播详情 -----")
            anchor_card = self.page.locator(
                f"div.blogger-list_list tr:nth-child({i}) div.kol-info_detail > div:nth-child(1) > span").first
            anchor_name = anchor_card.text_content().strip()
            self.current_data["达人名称"] = anchor_name
            anchor_card.click(timeout=5000)
            print(f"开始处理主播: {anchor_name}")

            print("\n----- 主播处理流程2：点开主播笔记案例 -----")
            self.open_first_note_detail()

            print("\n----- 主播处理流程3：复制笔记链接 -----")
            self.take_anchor_card_screenshot(rank, anchor_name)

            print("\n----- 主播处理流程4：打开详情新页面 -----")
            new_page = self.open_anchor_new_page(anchor_card)

            # 主动检查一次新页面（非异常场景）
            print("\n----- 主播处理流程5：检测新页面验证码，然后解析主播信息 -----")
            self.extract_anchor_new_page(new_page)

            print("\n----- 主播处理流程6：切换到'连接用户'标签 -----")
            connect_user_tab = new_page.get_by_role("tab", name="连接用户")
            if connect_user_tab.count() == 0:
                print("⚠️ '连接用户'标签不存在，跳过该步骤")
            else:
                self.switch_to_connect_user_tab(new_page)

            print("\n----- 主播处理流程7：截图达人主页 -----")
            self.take_anchor_home_screenshot(new_page, rank, anchor_name)

            print("\n----- 主播处理流程8：点击下单按钮 -----")
            try:
                self.click_order_button(new_page, rank, anchor_name)
            except PlaywrightTimeoutError:
                print("下单按钮未找到，已自动跳过该步骤")
            except Exception as e:
                print(f"处理下单按钮时发生错误：{str(e)}，已跳过该步骤")

            # 将当前主播数据添加到列表
            self.data_list.append(self.current_data.copy())
            print(f"\n===== 任务 '{anchor_name}' 执行完成 =====")

        except Exception as e:
            print(f"处理主播过程中发生错误: {str(e)}")
            self.current_data["操作错误信息"] = str(e)
            self.data_list.append(self.current_data.copy())
        finally:
            if new_page and not new_page.is_closed():
                new_page.close()

        save_single_dict_to_csv(self.current_data)
