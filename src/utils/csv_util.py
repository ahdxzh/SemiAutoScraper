import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Callable


def save_dict_list_to_csv(
        data_list: List[Dict],
        save_path: str = "outPut/anchor_data.csv",
        sort_fields: bool = False,
        sort_key: Callable = None,
        append: bool = False  # 新增参数：是否追加模式
) -> None:
    """
    将字典列表数据保存到CSV文件，支持控制字段排序和追加模式

    参数:
        data_list: 要保存的数据列表，每个元素为字典
        save_path: 保存的文件路径，默认值为"outPut/anchor_data.csv"
        sort_fields: 是否对字段进行排序，默认为False
        sort_key: 排序的key函数，仅当sort_fields为True时有效，默认为None（自然排序）
        append: 是否以追加模式写入，True表示追加，False表示覆盖，默认为False

    返回:
        无返回值
    """
    # 处理路径
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    save_path = os.path.join(current_dir, save_path)
    print(f"保存路径: {save_path}")

    # 检查数据列表是否为空
    if not data_list:
        print("没有数据可保存")
        return

    # 收集所有字段
    fieldnames = set()
    for data in data_list:
        fieldnames.update(data.keys())
    fieldnames = list(fieldnames)

    # 根据参数决定是否排序及排序方式
    if sort_fields:
        if sort_key:
            fieldnames.sort(key=sort_key)
        else:
            fieldnames.sort()  # 默认自然排序
    else:
        # 不排序时，按字段首次出现的顺序排列
        ordered_fields = []
        seen = set()
        for data in data_list:
            for key in data.keys():
                if key not in seen:
                    seen.add(key)
                    ordered_fields.append(key)
        fieldnames = ordered_fields

    # 确保输出目录存在
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    # 检查文件是否存在（用于追加模式）
    file_exists = os.path.exists(save_path) and os.path.getsize(save_path) > 0

    # 写入CSV文件
    # 追加模式且文件存在时，不写表头；否则写入表头
    mode = 'a' if append else 'w'
    with open(save_path, mode=mode, encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # 只有非追加模式或文件不存在时才写表头
        if not append or not file_exists:
            writer.writeheader()

        # 写入数据
        writer.writerows(data_list)

    print(f"✅ 数据已成功{'追加到' if append else '保存到'} {save_path}，共 {len(data_list)} 条记录")


# 新增：单条数据保存函数（内部调用批量保存函数）
def save_single_dict_to_csv(
        data: Dict,
        save_path: str = "outPut/anchor_data.csv",
        sort_fields: bool = False,
        sort_key: Callable = None,
        append: bool = True  # 单条保存默认使用追加模式
) -> None:
    """保存单条字典数据到CSV（默认追加模式）"""
    if not data:
        print("数据为空，不进行保存")
        return
    save_dict_list_to_csv(
        data_list=[data],
        save_path=save_path,
        sort_fields=sort_fields,
        sort_key=sort_key,
        append=append
    )


if __name__ == '__main__':
    # 准备测试数据
    data1 = {"name": "张三", "age": 25}
    data2 = {"name": "李四", "age": 26}

    save_single_dict_to_csv(data1)
    save_single_dict_to_csv(data2)
