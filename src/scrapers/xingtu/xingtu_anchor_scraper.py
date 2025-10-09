from pathlib import Path
from typing import Optional, Dict

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.utils.captcha_util import with_captcha_handling, handle_captcha
from src.utils.csv_util import save_single_dict_to_csv
from src.utils.extract_util import find_ancestor_texts_with_value
from src.utils.page_operate import screenshot_element, scroll_multiple_times


class AnchorProcessor:
    def __init__(self, page: Page):
        self.main_page: Page = page
        self.anchor_page: Optional[Page] = None
        self.order_page: Optional[Page] = None

        self.rank: Optional[int] = None
        self.anchor_name: Optional[str] = None
        self.current_data: Dict[str, str] = {}

        self._ensure_directories()

    @staticmethod
    def _ensure_directories():
        """确保所有输出目录存在"""
        for dir_path in ["outPut/曝光量", "outPut/达人主页", "outPut/订单截图"]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    # === 主入口 ===
    def process_single_task(self, i: int, rank: int):
        self.rank = rank
        self.current_data = {"排名": str(rank)}
        self.anchor_page = None
        self.order_page = None

        try:
            self._open_anchor_detail(i)
            self._load_anchor_info(i)
            self._capture_anchor_card()
            self._open_anchor_new_page()
            self._extract_anchor_new_page()
            self._switch_to_connect_user_tab()
            self._capture_anchor_home()
            self._click_order_button()
        except Exception as e:
            print(f"处理主播过程中发生错误: {e}")
            self.current_data["操作错误信息"] = str(e)
        finally:
            self._close_page(self.anchor_page, "anchor_page")
            self._close_page(self.order_page, "order_page")
            self._save_to_csv()

    # === 各步骤实现 ===
    @with_captcha_handling()
    def _open_anchor_detail(self, i: int):
        """打开主播详情页面"""
        card = self.main_page.locator(f".content-cell:nth-child({i}) .video-card-wrapper:first-child").first
        card.wait_for(state="visible", timeout=5000)
        card.click(timeout=5000)
        print("✅ 已打开主播详情页面")

    @with_captcha_handling()
    def _load_anchor_info(self, i: int):
        """读取主播名称"""
        anchor_card = self.main_page.locator(f".content-cell:nth-child({i}) .author-nickname:first-child").first
        self.anchor_name = anchor_card.text_content().strip()
        self.current_data["达人名称"] = self.anchor_name
        print(f"\n🎯 开始处理主播: {self.anchor_name}")

    @with_captcha_handling()
    def _capture_anchor_card(self):
        """截图主播卡片"""
        wrapper = None
        try:
            wrapper = self.main_page.locator(".video-card__wrapper:has(video[autoplay])")
            wrapper.wait_for(state="visible")

            # 截图
            screenshot_path = f"outPut/曝光量/{self.rank}_{self.anchor_name}.png"
            screenshot_element(self.main_page, locator=wrapper, save_path=screenshot_path, timeout=5000)

            # 视频链接
            link_el = wrapper.locator("a:has-text('打开视频')").first
            video_url = link_el.get_attribute("href")
            if video_url:
                video_url = video_url.replace("&amp;", "&")
                self.current_data["视频链接"] = video_url
                print(f"✅ 成功提取视频URL: {video_url[:50]}...")

            # 视频信息
            data_list = wrapper.locator(".detail-container").first
            views = find_ancestor_texts_with_value(self.main_page, "视频播放数", data_list)
            release = data_list.get_by_text("发布日期").first.text_content().replace("发布日期: ", "")
            self.current_data["视频播放数"] = views
            self.current_data["发布日期"] = release
        except Exception as e:
            print(f"获取主播详情发生异常：{e}")
            raise e
        finally:
            wrapper.locator(".i-icon-xt-icon-close").click()

    @with_captcha_handling()
    def _open_anchor_new_page(self):
        """打开主播新页面"""
        card = self.main_page.get_by_text(self.anchor_name).first
        with self.main_page.expect_popup() as popup_info:
            card.click(timeout=5000)
        self.anchor_page = popup_info.value
        print(f"✅ 新页面已弹出，标题: {self.anchor_page.title()}")

    @with_captcha_handling()
    def _extract_anchor_new_page(self):
        """提取达人主页信息"""
        page = self.anchor_page
        handle_captcha(page)
        detail = page.locator(".main").first

        self.current_data["粉丝数"] = find_ancestor_texts_with_value(page, "粉丝数", detail)
        self.current_data["星图ID"] = find_ancestor_texts_with_value(page, "星图ID", detail)
        self.current_data["达人类型"] = find_ancestor_texts_with_value(page, "达人类型", detail)
        self.current_data["内容主题"] = find_ancestor_texts_with_value(page, "内容主题", detail)
        self.current_data["行业标签"] = find_ancestor_texts_with_value(page, "行业标签", detail)

    @with_captcha_handling()
    def _switch_to_connect_user_tab(self):
        """切换到“连接用户”标签"""
        page = self.anchor_page
        connect_tab = page.get_by_role("tab", name="连接用户")
        if connect_tab.count() == 0:
            print("⚠️ 未找到‘连接用户’标签，跳过该步骤")
            return

        connect_tab.click()
        page.get_by_text("用户漏斗").first.click()
        scroll_multiple_times(page, total_scrolls=1, key_presses_per_scroll=15)
        print("✅ 已对齐连接用户漏斗顶部")

    @with_captcha_handling()
    def _capture_anchor_home(self):
        """截图达人主页"""
        page = self.anchor_page
        screenshot_path = f"outPut/达人主页/{self.rank}_{self.anchor_name}.png"
        screenshot_element(page, screenshot_path, timeout=5000, crop_top=150)
        print(f"✅ 达人主页截图成功：{self.rank}_{self.anchor_name}.png")

        fan_card = page.locator(".content-container .right").first
        self.current_data["总结"] = find_ancestor_texts_with_value(page, "总结", fan_card)
        self.current_data["连接用户类型"] = find_ancestor_texts_with_value(page, "连接用户类型", fan_card)

    @with_captcha_handling()
    def _click_order_button(self):
        """点击下单按钮并截图 + 存储订单页面"""
        page = self.anchor_page
        selector = "div[data-btm='add']:has(div.desc:has-text(' 21-60s视频 ')) button:has-text('下单')"
        try:
            btn = page.locator(selector)
            btn.wait_for(timeout=3000)

            # 打开订单页面
            with page.expect_popup() as popup_info:
                btn.click(force=True)
            self.order_page = popup_info.value
            print(f"✅ 订单页面已弹出，标题: {self.order_page.title()}")

            # 截图订单卡片
            order_card = self.order_page.locator(".selected-author-list.select-author-list")
            screenshot_path = f"outPut/订单截图/{self.rank}_{self.anchor_name}.png"
            screenshot_element(self.order_page, locator=order_card, save_path=screenshot_path, timeout=10000)

            # 提取订单信息
            order_amount = find_ancestor_texts_with_value(self.order_page, "合计", order_card)
            self.current_data["报价"] = order_amount

        except PlaywrightTimeoutError:
            print("⚠️ 下单按钮未找到，跳过该步骤")
        except Exception as e:
            print(f"⚠️ 处理订单页面异常: {e}")

    @staticmethod
    def _close_page(page: Optional[Page], page_name: str = "页面"):
        """安全关闭 page 对象"""
        if page is not None:
            try:
                if not page.is_closed():
                    page.close()
                    print(f"✅ {page_name} 已关闭")
            except Exception as e:
                print(f"⚠️ 关闭 {page_name} 时出错: {e}")

    def _save_to_csv(self):
        """保存结果"""
        save_single_dict_to_csv(
            self.current_data,
            primary_key="达人名称",
            save_path="outPut/数据总结.csv"
        )
        print(f"✅ 数据已保存: {self.anchor_name}")
