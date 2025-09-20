from playwright.sync_api import TimeoutError, Page


def check_login_status(page: Page) -> bool:
    """检测是否已登录：存在登录按钮则返回False"""
    print("\n----- 开始检测登录状态 -----")
    login_selector = 'text=登录, a[href*="login"], button:has-text("登录")'
    print(f"使用选择器检测登录状态: {login_selector} (超时时间1秒)")

    try:
        page.wait_for_selector(login_selector, timeout=1000)
        print("检测到登录按钮，用户当前未登录")
        return False
    except TimeoutError:
        print("未检测到登录按钮，用户已处于登录状态")
        return True


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
