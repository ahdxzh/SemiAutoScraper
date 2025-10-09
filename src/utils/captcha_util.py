import random
import time
from functools import wraps

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.common import STEP_SLEEP_MIN_TIME, STEP_SLEEP_MAX_TIME
from src.utils.page_status_check import check_captcha_status
from src.utils.page_user_interaction import wait_for_user_action


def handle_captcha(page: Page):
    """检查单个页面是否有验证码，有则等待用户处理"""
    if check_captcha_status(page):
        wait_for_user_action(f"页面出现验证码，请完成验证: {page.title()}")
        page.wait_for_load_state("networkidle", timeout=10000)


def with_captcha_handling(min_sleep=STEP_SLEEP_MIN_TIME, max_sleep=STEP_SLEEP_MAX_TIME):
    """
    装饰器：自动识别函数中的Page参数，异常时检查该页面的验证码
    代理执行方法时会在指定范围内随机休眠一段时间

    :param min_sleep: 最小休眠时间（秒）
    :param max_sleep: 最大休眠时间（秒）
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 执行前先随机休眠，模拟人类操作延迟
                sleep_time = random.uniform(min_sleep, max_sleep)
                time.sleep(sleep_time)
                return func(*args, **kwargs)
            except Exception as e:
                # 排除元素不存在的情况（不检查验证码）
                if isinstance(e, PlaywrightTimeoutError) and "not found" in str(e).lower():
                    raise e

                # 从参数中找到Page类型的对象
                current_page = None
                # 检查位置参数
                for arg in args:
                    if isinstance(arg, Page):
                        current_page = arg
                        break
                # 检查关键字参数
                if not current_page:
                    for val in kwargs.values():
                        if isinstance(val, Page):
                            current_page = val
                            break

                if current_page:
                    handle_captcha(current_page)  # 检查当前页面验证码

                    # 处理验证码后重试前也添加随机休眠
                    retry_sleep_time = random.uniform(min_sleep, max_sleep)
                    time.sleep(retry_sleep_time)

                    return func(*args, **kwargs)  # 重试操作
                else:
                    raise e  # 没有找到Page参数，直接抛出异常

        return wrapper

    return decorator
