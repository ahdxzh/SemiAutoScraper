# utils.py
import time  # 可选，用于避免循环等待时占用过高CPU
import uuid  # 用于生成唯一请求ID

from src.common import request_queue, result_queue


def wait_for_user_action(reason: str) -> bool:
    """
    向主线程发送弹窗请求，等待用户点击确定后返回
    :param reason: 需要用户处理的原因描述
    :return: True（用户点击确定）
    """
    # 1. 终端打印提示（原有逻辑保留）
    print(f"\n===== [用户交互] 需要人工处理：{reason} =====")
    print("请在浏览器中完成操作后，点击弹窗中的确定按钮继续...")

    # 2. 生成唯一请求ID（确保结果能正确匹配当前请求）
    request_id = str(uuid.uuid4())  # 用uuid生成全局唯一ID，避免冲突

    # 3. 向主线程的请求队列发送弹窗指令（严格匹配check_message_queue的参数结构）
    # 参数结构：(msg_type, request_id, 弹窗标题, 弹窗内容)
    request_queue.put(("wait", request_id, "需要人工处理", reason))

    # 4. 阻塞等待主线程返回结果（循环检查结果队列）
    while True:
        # 检查结果队列是否有数据（非阻塞，避免CPU占用过高）
        if not result_queue.empty():
            result_id, user_confirm = result_queue.get()
            # 匹配当前请求的结果（避免拿到其他请求的结果）
            if result_id == request_id:
                print(f"[交互完成] 用户已处理：{reason}，继续执行...\n")
                return user_confirm  # 返回用户操作结果（这里是True）

        # 每100ms检查一次，减少CPU占用
        time.sleep(0.1)
