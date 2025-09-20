import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Callable


def save_dict_list_to_csv(
        data_list: List[Dict],
        save_path: str = "outPut/anchor_data.csv",
        sort_fields: bool = False,
        sort_key: Callable = None
) -> None:
    """
    将字典列表数据保存到CSV文件，支持控制字段排序

    参数:
        data_list: 要保存的数据列表，每个元素为字典
        save_path: 保存的文件路径，默认值为"outPut/anchor_data.csv"
        sort_fields: 是否对字段进行排序，默认为False
        sort_key: 排序的key函数，仅当sort_fields为True时有效，默认为None（自然排序）

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

    # 写入CSV文件
    with open(save_path, mode='w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for data in data_list:
            writer.writerow(data)

    print(f"✅ 数据已成功保存到 {save_path}，共 {len(data_list)} 条记录")


if __name__ == '__main__':
    # 准备测试数据
    data = [
        {"name": "张三", "age": 25},
        {"name": "李四", "age": 30, "city": "北京"},
        {"name": "王五", "gender": "女", "score": 95}
    ]

    # 测试1: 默认排序（按字母顺序）
    save_dict_list_to_csv(data, "data/sorted_people.csv")

    # 测试2: 不排序（按字段首次出现顺序）
    save_dict_list_to_csv(data, "data/unsorted_people.csv", sort_fields=False)

    # 测试3: 自定义排序（按字段长度）
    save_dict_list_to_csv(
        data,
        "data/custom_sorted_people.csv",
        sort_fields=True,
        sort_key=lambda x: len(x)  # 按字段名长度排序
    )
