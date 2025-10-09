# common.py
from queue import Queue

# 用于后台线程发送弹窗请求
request_queue = Queue()
# 用于主线程返回用户操作结果（如是否点击确定）
result_queue = Queue()

# 页码爬取步骤操作间隔
STEP_SLEEP_MIN_TIME = 1
STEP_SLEEP_MAX_TIME = 3
