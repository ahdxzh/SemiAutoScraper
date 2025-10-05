import sys

from src.scraper_gui import start_gui

# 为PyInstaller的_MEIPASS添加类型提示
if not hasattr(sys, '_MEIPASS'):
    sys._MEIPASS: str = ""  # type: ignore[attr-defined]


def main() -> None:
    try:
        print("=" * 50)
        print("半自动工具启动中...")
        print(f"当前环境: {'打包后环境' if getattr(sys, 'frozen', False) else '开发环境'}")
        print("=" * 50)

        # 启动GUI
        print("\n启动图形界面...")
        start_gui()

    except Exception as e:
        print(f"\n运行错误: {str(e)}")
    finally:
        print("\n操作完成")
        input("按任意键关闭窗口...")


if __name__ == "__main__":
    main()
