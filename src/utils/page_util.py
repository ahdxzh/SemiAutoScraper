from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


def jump_to_target_page(page: Page, target_page: int) -> bool:
    """
    简化版页码跳转函数，仅使用"跳至"输入框

    Args:
        page: Playwright的Page对象
        target_page: 目标页码

    Returns:
        是否成功跳转到目标页
    """
    try:
        # 仅验证页码为正整数
        if not isinstance(target_page, int) or target_page < 1:
            print(f"无效的页码: {target_page}")
            return False

        # 定位分页容器
        pagination_container = page.locator('div.d-pagination.hide-pagination-page-size > div:nth-child(2)').first

        # 定位跳至输入框
        goto_input = pagination_container.locator('div.d-pagination-goto input.d-text.d-text-monospace').first

        # 等待输入框可编辑
        goto_input.wait_for(timeout=10000)

        # 清空并输入目标页码
        goto_input.fill(str(target_page))

        # 按Enter确认
        page.keyboard.press('Enter')

        return True

    except PlaywrightTimeoutError:
        print(f"超时：无法完成页码 {target_page} 的跳转")
        return False
    except Exception as e:
        print(f"跳转失败: {str(e)}")
        return False
