from pathlib import Path
from typing import Optional, Dict

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.utils.captcha_util import with_captcha_handling, handle_captcha
from src.utils.csv_util import save_single_dict_to_csv
from src.utils.extract_util import find_ancestor_texts_with_value
from src.utils.page_operate import screenshot_element, scroll_multiple_times


class AnchorProcessor:
    def __init__(self, page: Page):
        self.page = page
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
    def _open_anchor_detail(self, i: int):
        """打开主播详情页面"""
        target_card = self.page.locator(f".content-cell:nth-child({i}) .video-card-wrapper:first-child").first
        target_card.wait_for(state="visible", timeout=5000)
        target_card.click(timeout=5000)
        print("已打开主播详情页面")

    @with_captcha_handling()
    def _take_anchor_card_screenshot(self, rank: int, anchor_name: str):
        card_wrapper = None
        try:
            """截图主播卡片元素"""
            # 1. 先定位卡片容器，并等待容器加载（确保容器存在于DOM中）
            card_wrapper = self.page.locator(".video-card__wrapper:has(video[autoplay])")
            card_wrapper.wait_for(state="visible")

            # 2. 在容器内定位带autoplay的视频，并等待视频可见
            autoplay_video = card_wrapper.locator("video[autoplay]")
            autoplay_video.wait_for(state="visible")

            screenshot_path = f"outPut/曝光量/{rank}_{anchor_name}.png"
            screenshot_element(
                page=self.page,
                locator=card_wrapper,
                save_path=screenshot_path,
                timeout=5000
            )
            link_element = card_wrapper.locator("a:has-text('打开视频')").first
            video_url = link_element.get_attribute("href")
            if video_url:
                # 处理URL中的特殊字符（如&amp;可能需要转换为&）
                video_url = video_url.replace("&amp;", "&")
                self.current_data["视频链接"] = video_url
                print(f"成功提取视频URL: {video_url[:50]}...")  # 只显示前50字符避免过长

            # 替代原有的视频播放数、点赞数、评论数提取逻辑
            data_list = card_wrapper.locator(".detail-container").first
            video_views = find_ancestor_texts_with_value(self.page, "视频播放数", data_list)
            release_time = data_list.get_by_text("发布日期").first.text_content().replace("发布日期: ", "")
            self.current_data["视频播放数"] = video_views
            self.current_data["发布日期"] = release_time
        except Exception as e:
            print(f"获取主播详情发生异常：{str(e)}")
            raise e
        finally:
            card_wrapper.locator(".i-icon-xt-icon-close").click()
            print("关闭主播详情页面")

    @with_captcha_handling()
    def _open_anchor_new_page(self, anchor_card) -> Page:
        """打开主播新页面"""
        with self.page.expect_popup() as popup_info:
            anchor_card.click(timeout=5000)
        new_page = popup_info.value
        page_title = new_page.title()
        print(f"新页面已弹出，页面标题: {page_title}")

        return new_page

    @with_captcha_handling()
    def _extract_anchor_new_page(self, new_page: Page):
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
    def _switch_to_connect_user_tab(self, new_page: Page):
        """切换到连接用户标签并执行相关操作"""
        connect_user_tab = new_page.get_by_role("tab", name="连接用户")
        connect_user_tab.click()
        print("将连接用户漏斗洞察顶部对齐")
        new_page.get_by_text("用户漏斗").first.click()
        scroll_multiple_times(new_page, total_scrolls=1, key_presses_per_scroll=15)
        print("已成功将连接用户漏斗洞察顶部对齐")
        return True

    @with_captcha_handling()
    def _take_anchor_home_screenshot(self, new_page: Page, rank: int, anchor_name: str):
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
    def _click_order_button(self, new_page: Page, rank: int, anchor_name: str):
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
            print("\n----- 主播处理流程1：获取主播信息 -----")
            anchor_card = self.page.locator(f".content-cell:nth-child({i}) .author-nickname:first-child").first
            anchor_name = anchor_card.text_content().strip()
            self.current_data["达人名称"] = anchor_name
            print(f"处理主播: {anchor_name}")

            print("\n----- 主播处理流程2：点开主播详情 -----")
            self._open_anchor_detail(i)

            print("\n----- 主播处理流程3：截图主播卡片元素 -----")
            self._take_anchor_card_screenshot(rank, anchor_name)

            print("\n----- 主播处理流程4：打开详情新页面 -----")
            new_page = self._open_anchor_new_page(anchor_card)

            # 主动检查一次新页面（非异常场景）
            print("\n----- 主播处理流程5：检测新页面验证码，然后解析主播信息 -----")
            self._extract_anchor_new_page(new_page)

            print("\n----- 主播处理流程6：切换到'连接用户'标签 -----")
            connect_user_tab = new_page.get_by_role("tab", name="连接用户")
            if connect_user_tab.count() == 0:
                print("⚠️ '连接用户'标签不存在，跳过该步骤")
            else:
                self._switch_to_connect_user_tab(new_page)

            print("\n----- 主播处理流程7：截图达人主页 -----")
            self._take_anchor_home_screenshot(new_page, rank, anchor_name)

            print("\n----- 主播处理流程8：点击下单按钮 -----")
            try:
                self._click_order_button(new_page, rank, anchor_name)
            except PlaywrightTimeoutError:
                print("下单按钮未找到，已自动跳过该步骤")
            except Exception as e:
                print(f"处理下单按钮时发生错误：{str(e)}，已跳过该步骤")

        except Exception as e:
            print(f"处理主播过程中发生错误: {str(e)}")
            self.current_data["操作错误信息"] = str(e)
        finally:
            if new_page and not new_page.is_closed():
                new_page.close()

        save_path = "outPut/数据总结.csv"
        save_single_dict_to_csv(self.current_data, primary_key="达人名称", save_path=save_path)
