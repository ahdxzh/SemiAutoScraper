import tkinter as tk
from tkinter import messagebox


def wait_for_user_action(reason: str):
    """暂停程序，等待用户手动处理（终端提示+图形弹窗）
    用户点击弹窗的确定按钮后，程序自动继续运行
    """
    print(f"\n===== [用户交互] 需要人工处理：{reason} =====")
    print("请在浏览器中完成操作后，点击弹窗中的确定按钮继续...")

    # 图形弹窗提示（使用tkinter）
    print("显示图形提示弹窗")

    # 创建Tk实例
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 显示消息框，这会阻塞程序直到用户点击"确定"
    messagebox.showinfo(
        title="需要人工处理",
        message=f"{reason}\n\n请在浏览器中完成操作后，\n点击本窗口的确定按钮继续..."
    )

    # 关闭Tk实例
    root.destroy()
    print("用户已确认操作完成，继续执行后续流程...\n")
