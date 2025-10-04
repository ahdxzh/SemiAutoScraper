from playwright.sync_api import TimeoutError, Page


def check_login_status(page: Page) -> bool:
    """
    检测是否已登录：通过多种特征判断登录状态，提高准确性

    Args:
        page: Playwright的Page对象

    Returns:
        bool: 已登录返回True，未登录返回False
    """
    print("\n----- 开始检测登录状态 -----")

    # 定义多种登录/未登录状态特征
    # 未登录特征：登录按钮、注册按钮、登录链接等
    unlogged_indicators = [
        'text=登录',
        'a[href*="login"]',
        'button:has-text("登录")',
        'text=注册',
        'a[href*="register"]',
        'button:has-text("注册")',
        'text=请登录',
        'text=登录后查看'
    ]

    # 已登录特征：用户头像、退出登录按钮、用户名等
    logged_indicators = [
        'img[alt*="头像"], img[src*="avatar"]',
        'text=退出, a[href*="logout"], button:has-text("退出")',
        'text=个人中心, a[href*="profile"]',
        'text=我的账户, a[href*="account"]'
    ]

    # 先检查是否有已登录特征（权重更高）
    print("检测已登录特征...")
    for selector in logged_indicators:
        try:
            # 放宽超时时间，给页面足够加载时间
            page.wait_for_selector(selector, timeout=2000)
            print(f"检测到已登录特征: {selector}")
            return True
        except TimeoutError:
            continue

    # 再检查是否有未登录特征
    print("检测未登录特征...")
    for selector in unlogged_indicators:
        try:
            page.wait_for_selector(selector, timeout=1000)
            print(f"检测到未登录特征: {selector}")
            return False
        except TimeoutError:
            continue

    # 如果两种特征都未检测到，使用URL辅助判断
    current_url = page.url
    print(f"特征检测不明确，使用URL辅助判断: {current_url}")
    if any(keyword in current_url for keyword in ['login', 'signin', 'register', 'signup']):
        print("URL包含未登录相关关键词")
        return False
    elif any(keyword in current_url for keyword in ['profile', 'account', 'user']):
        print("URL包含已登录相关关键词")
        return True

    # 所有检测都无法确定时，默认视为未登录（安全策略）
    print("无法明确判断登录状态，默认视为未登录")
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
