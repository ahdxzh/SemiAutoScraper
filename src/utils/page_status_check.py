from playwright.sync_api import TimeoutError, Page


def check_login_status(page: Page) -> bool:
    """
    检测是否已登录：针对包含特定登录/注册按钮的页面优化

    Args:
        page: Playwright的Page对象

    Returns:
        bool: 已登录返回True，未登录返回False
    """
    print("\n----- 开始检测登录状态 -----")

    # 1. 针对特定登录/注册按钮的未登录特征（精确匹配你提供的结构）
    unlogged_indicators = [
        'button.login-btn:has-text("登录")',  # 精确匹配登录按钮
        'button.register-btn:has-text("立即入驻")',  # 匹配注册按钮
        'div.login-actions:has(button.login-btn)'  # 检查包含登录按钮的容器
    ]

    # 2. 已登录特征（根据网站实际已登录状态展示的元素补充）
    logged_indicators = [
        # 示例：替换为网站实际的已登录元素（如用户头像、用户名等）
        'div.user-info',  # 假设登录后显示用户信息容器
        'span.username',  # 假设登录后显示用户名
        'button.logout-btn',  # 假设登录后显示退出按钮
        'a[href="/user/center"]'  # 假设登录后显示个人中心链接
    ]

    # 优先检测检测未登录特征（你的登录/注册按钮）
    print("检测未登录特征...")
    for selector in unlogged_indicators:
        try:
            page.wait_for_selector(selector, timeout=1500)
            print(f"检测到未登录特征: {selector}")
            return False
        except TimeoutError:
            continue

    # 已登录特征
    print("检测已登录特征...")
    for selector in logged_indicators:
        try:
            page.wait_for_selector(selector, timeout=2000)
            print(f"检测到已登录特征: {selector}")
            return True
        except TimeoutError:
            continue

    # 3. 额外判断：如果登录按钮容器消失，也可能表示已登录
    try:
        # 检查登录按钮容器是否不存在
        if not page.locator('div.login-actions').count():
            print("登录按钮容器已消失，可能已登录")
            return True
    except Exception as e:
        print(f"检查登录容器时出错: {e}")

    # 最终无法判断时的默认策略
    print("无法明确判断，默认视为未登录")
    return False


def check_captcha_status(page: Page) -> bool:
    """检测是否出现验证码"""
    print("\n----- 开始检测验证码 -----")
    captcha_selectors = [
        'text=请输入验证码',
        'div:has-text("安全验证")',
        'input[placeholder*="验证码"]',
        '.captcha-container',
        'img[alt*="验证码"]'
    ]
    if not page:
        print("目标页面不存在，跳过验证码检测")
        return False

    combined_selector = ", ".join(captcha_selectors)
    print(f"使用组合选择器检测验证码: {combined_selector} (超时时间2秒)")

    try:
        page.wait_for_selector(combined_selector, timeout=2000)
        print("检测到验证码存在")
        return True
    except TimeoutError:
        print("未检测到验证码")
        return False
