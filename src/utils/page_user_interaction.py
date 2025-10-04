from src.common import message_queue


def wait_for_user_action(reason: str):
    """暂停程序，等待用户手动处理（终端提示+图形弹窗）
    用户点击弹窗的确定按钮后，程序自动继续运行
    """
    # 1. 终端打印提示（原有逻辑不变）
    print(f"\n===== [用户交互] 需要人工处理：{reason} =====")
    print("请在浏览器中完成操作后，点击弹窗中的确定按钮继续...")

    # 2. 关键修改：向全局队列发送弹窗请求（不直接创建弹窗）
    # 参数格式：(弹窗类型, 弹窗标题, 弹窗内容)
    message_queue.put(("wait", "需要人工处理", reason))
