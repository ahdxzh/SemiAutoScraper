import os
import sys
import time
from typing import Optional

from playwright.sync_api import Locator  # 需导入Locator类型


def scroll_multiple_times(page,
                          total_scrolls: int = 1,  # 总滚动次数
                          key_presses_per_scroll: int = 100,  # 每次滚动按箭头键的次数
                          press_delay: float = 0.1,  # 每次按键间隔
                          after_scroll_pause: float = 2,  # 每次滚动后的等待时间
                          max_total_time: Optional[int] = None):
    """
    执行固定次数的滚动，不判断是否有新内容加载

    参数:
        page: Playwright页面对象
        total_scrolls: 总滚动次数
        key_presses_per_scroll: 每次滚动按向下箭头的次数
        press_delay: 每次按键之间的延迟(秒)
        after_scroll_pause: 每次滚动后等待的时间
        max_total_time: 最大总耗时(秒)，None表示无限制
    """
    # 确保body元素获得焦点
    page.locator("body").click()

    start_time = time.time()

    for scroll_count in range(1, total_scrolls + 1):
        # 检查是否超时
        if max_total_time and (time.time() - start_time > max_total_time):
            print(f"已超过最大等待时间 {max_total_time} 秒，停止滚动")
            break

        # 模拟按下向下箭头键多次
        for _ in range(key_presses_per_scroll):
            page.locator("body").press("ArrowDown")
            time.sleep(press_delay)

        # 每次滚动后等待
        time.sleep(after_scroll_pause)

        print(f"已完成 {scroll_count}/{total_scrolls} 次滚动")

    print("所有滚动操作已完成")


def screenshot_element(
        page,
        save_path: str,
        locator: Locator = None,  # 接收Locator对象，默认None
        timeout: int = 10000,
        crop_top: int = 0  # 顶部需要裁剪的像素数，0表示不裁剪
) -> bool:
    """
    对指定元素或整个页面进行截图并保存（支持全屏截图时裁剪顶部区域，不依赖额外库）

    参数:
        page: Playwright页面对象
        locator: Playwright元素定位器（可选），不传入则截取整个页面
        save_path: 截图保存路径
        timeout: 等待元素超时时间（毫秒，仅当传入locator时有效）
        crop_top: 顶部需要裁剪的像素数，仅对全屏截图有效

    返回:
        bool: 截图成功返回True，失败返回False
    """
    try:
        print(f"\n----- 开始截图 -----")
        # 构建保存路径
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        save_path = os.path.join(current_dir, save_path)
        print(f"保存路径: {save_path}")

        # 路径检查：自动创建不存在的目录
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            print(f"已自动创建保存目录: {save_dir}")

        # 区分：截取元素还是整个页面
        if locator:
            # 有定位器：截取指定元素
            print(f"目标元素Locator: {locator}")
            locator.wait_for(state="visible", timeout=timeout)
            locator.screenshot(path=save_path, scale="device")
            print(f"元素截图成功，已保存至: {save_path}")
        else:
            # 无定位器：截取整个页面
            print("未指定元素Locator，将截取整个页面")

            # 获取页面视口信息（用于裁剪计算）
            viewport = page.viewport_size
            if not viewport:
                # 如果视口未定义，使用页面实际尺寸
                viewport = {
                    "width": page.evaluate("window.innerWidth"),
                    "height": page.evaluate("window.innerHeight")
                }

            # 计算裁剪参数（仅当需要裁剪且参数有效时）
            clip_params = None
            if crop_top > 0:
                # 获取页面完整高度
                page_height = page.evaluate("document.body.scrollHeight")
                # 检查裁剪高度是否有效
                if crop_top < page_height:
                    clip_params = {
                        "x": 0,
                        "y": crop_top,  # 从顶部裁剪指定像素
                        "width": viewport["width"],
                        "height": page_height - crop_top  # 剩余高度
                    }
                    print(f"将裁剪顶部{crop_top}px区域")
                else:
                    print(f"警告：裁剪高度({crop_top})超过页面高度，将不进行裁剪")

            # 执行截图（带裁剪参数或完整截图）
            page.screenshot(
                path=save_path,
                full_page=True,
                scale="device",
                clip=clip_params  # 使用Playwright原生裁剪功能
            )
            print(f"全页面截图{'并裁剪' if clip_params else ''}成功，已保存至: {save_path}")

        return True

    except TimeoutError:
        print(f"错误：元素未在{timeout}ms内出现或不可见，Locator: {locator}")
        return False
    except Exception as e:
        print(f"截图失败：{str(e)}，Locator: {locator if locator else '无（全页面截图）'}")
        return False


def click_left_screen(page):
    try:
        # 修复：viewport_size是属性，不是方法，去掉括号()
        viewport_size = page.viewport_size
        if not viewport_size:
            # 若未设置视口，使用默认值（1280x720）
            viewport_size = {"width": 1280, "height": 720}

        # 计算屏幕左侧区域的坐标（左侧10%宽度，垂直居中）
        x = viewport_size["width"] * 0.1  # 左侧区域
        y = viewport_size["height"] * 0.5  # 垂直中间位置

        # 模拟鼠标点击左侧区域
        page.mouse.click(x, y)
        print(f"已点击屏幕左侧区域（坐标：x={int(x)}, y={int(y)}）")  # 格式化坐标为整数

    except Exception as e:
        print(f"点击左侧区域失败：{str(e)}")
