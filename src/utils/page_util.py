from playwright.sync_api import Page
import re


def jump_to_target_page(page: Page, target_page: int) -> bool:
    """
    跳转到目标页码

    Args:
        page: Playwright 的 Page 对象
        target_page: 目标页码

    Returns:
        成功跳转返回 True，否则返回 False
    """
    try:
        # 检查目标页码是否为有效整数
        if not isinstance(target_page, int) or target_page < 1:
            return False

        # 定位分页容器
        pagination_selector = "div.d-pagination.hide-pagination-page-size > div:nth-child(2)"
        if not page.locator(pagination_selector).is_visible():
            return False

        # 检查当前页码
        current_page_selector = ".--color-bg-primary-light"
        current_page_element = page.locator(current_page_selector)
        if current_page_element.is_visible():
            current_page_text = current_page_element.text_content().strip()
            current_page = int(re.search(r'\d+', current_page_text).group()) if current_page_text else None

            # 如果已经在目标页，直接返回True
            if current_page == target_page:
                return True

        # 尝试直接点击目标页码
        target_page_selector = f".d-pagination-page:has-text('{target_page}'):not(.disabled)"
        target_page_element = page.locator(target_page_selector)

        if target_page_element.is_visible() and target_page_element.is_enabled():
            target_page_element.click()
            # 等待页面加载完成
            page.wait_for_load_state('networkidle')
            return True

        # 如果直接点击失败，尝试使用跳转输入框
        input_selector = ".d-pagination-goto input"
        input_element = page.locator(input_selector)

        if input_element.is_visible() and input_element.is_enabled():
            # 清空输入框并输入目标页码
            input_element.fill("")
            input_element.fill(str(target_page))

            # 按回车键确认跳转
            input_element.press("Enter")

            # 等待页面加载完成
            page.wait_for_load_state('networkidle')

            # 验证是否成功跳转
            new_current_page = page.locator(current_page_selector).text_content().strip()
            new_current_page_num = int(re.search(r'\d+', new_current_page).group()) if new_current_page else None

            return new_current_page_num == target_page

        # 所有方法都失败
        return False

    except Exception as e:
        print(f"跳转页码时发生错误: {str(e)}")
        return False
