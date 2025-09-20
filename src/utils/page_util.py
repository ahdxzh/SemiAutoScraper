from playwright.sync_api import Page


def jump_to_target_page(page: Page, target_page: int) -> bool:
    """
    跳转到指定页码（自动适配可见页码点击和输入框跳转）

    参数:
        page: Playwright的页面对象（已加载包含分页的页面）
        target_page: 目标页码（正整数）

    返回:
        跳转成功返回True，失败返回False
    """
    if not isinstance(target_page, int) or target_page < 1:
        print(f"❌ 无效页码：{target_page}（必须是≥1的整数）")
        return False

    try:
        # 定位当前激活的页码（用于后续验证）
        active_page_selector = ".pagination .el-pager .number.active"
        page.wait_for_selector(active_page_selector, timeout=5000)

        # 场景1：目标页码在可见的数字列表中（直接点击）
        target_selector = f".pagination .el-pager .number:text('{target_page}')"
        if page.locator(target_selector).count() > 0:
            # 记录当前页码，用于验证跳转结果
            current_page = page.locator(active_page_selector).text_content()
            if current_page == str(target_page):
                print(f"ℹ️ 已在第{target_page}页，无需跳转")
                return True

            # 点击目标页码
            page.locator(target_selector).click()
            # 等待页码切换完成
            page.wait_for_function(
                f"document.querySelector('{active_page_selector}').textContent === '{target_page}'"
            )
            print(f"✅ 成功点击跳转到第{target_page}页")
            return True

        # 场景2：目标页码不可见（通过输入框跳转）
        else:
            # 定位跳转输入框
            input_selector = ".pagination .xt-input-number__input .el-input__inner"
            input_locator = page.locator(input_selector)
            input_locator.wait_for(state="visible", timeout=5000)

            # 输入目标页码并确认
            input_locator.click()
            input_locator.fill("")  # 清空原有内容
            input_locator.fill(str(target_page))
            input_locator.press("Enter")  # 触发跳转

            # 等待页码切换完成
            page.wait_for_function(
                f"document.querySelector('{active_page_selector}').textContent === '{target_page}'"
            )
            print(f"✅ 成功通过输入框跳转到第{target_page}页")
            return True

    except Exception as e:
        # 检查是否因超出最大页码导致失败
        try:
            max_page = int(page.locator(".pagination .el-pager .number:last-child").text_content())
            if target_page > max_page:
                print(f"❌ 跳转失败：目标页码{target_page}超过最大页码{max_page}")
                return False
        except:
            pass  # 无法获取最大页码时不处理

        print(f"❌ 跳转至第{target_page}页失败：{str(e)}")
        return False
