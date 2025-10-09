import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Callable, Optional


def save_dict_list_to_csv(
        data_list: List[Dict],
        save_path: str = "outPut/anchor_data.csv",
        sort_fields: bool = False,
        sort_key: Callable = None,
        append: bool = False,  # 是否追加模式
        primary_key: Optional[str] = None  # 主键字段，用于替换模式
) -> None:
    """
    将字典列表数据保存到CSV文件，支持控制字段排序、追加模式和替换模式

    参数:
        data_list: 要保存的数据列表，每个元素为字典
        save_path: 保存的文件路径，默认值为"outPut/anchor_data.csv"
        sort_fields: 是否对字段进行排序，默认为False
        sort_key: 排序的key函数，仅当sort_fields为True时有效，默认为None（自然排序）
        append: 是否以追加模式写入，True表示追加，False表示覆盖，默认为False
        primary_key: 主键字段名，指定后启用替换模式，根据主键值替换已有记录，默认为None

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

    # 如果启用了替换模式且文件存在，需要读取已有数据并合并字段
    existing_data = []
    file_exists = os.path.exists(save_path) and os.path.getsize(save_path) > 0

    if primary_key and append and file_exists:
        # 读取已有数据
        with open(save_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            existing_data = list(reader)
            # 合并字段
            fieldnames.update(reader.fieldnames)

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
        # 先添加已有数据中的字段
        if existing_data:
            for key in existing_data[0].keys():
                if key not in seen:
                    seen.add(key)
                    ordered_fields.append(key)
        # 再添加新数据中的字段
        for data in data_list:
            for key in data.keys():
                if key not in seen:
                    seen.add(key)
                    ordered_fields.append(key)
        fieldnames = ordered_fields

    # 确保输出目录存在
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    # 处理替换逻辑
    if primary_key and append:
        # 检查主键是否存在于所有数据中
        for data in data_list:
            if primary_key not in data:
                raise ValueError(f"数据中缺少主键字段: {primary_key}")

        # 创建主键值到数据的映射（使用字符串比较，避免类型问题）
        new_data_map = {str(data[primary_key]): data for data in data_list}

        # 合并数据：存在主键则替换，不存在则保留原有数据
        merged_data = []
        for item in existing_data:
            key_value = str(item.get(primary_key, ""))
            if key_value in new_data_map:
                # 替换数据
                merged_data.append(new_data_map[key_value])
                del new_data_map[key_value]
            else:
                # 保留原有数据
                merged_data.append(item)

        # 添加剩余的新数据
        merged_data.extend(new_data_map.values())

        # 使用合并后的数据
        data_list = merged_data
        # 强制使用覆盖模式，因为我们已经处理了合并
        append = False
        action = "替换并保存"
    else:
        action = "追加到" if append else "保存到"

    # 写入CSV文件
    mode = 'a' if append else 'w'
    with open(save_path, mode=mode, encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # 只有非追加模式或文件不存在时才写表头
        if not append or not file_exists:
            writer.writeheader()

        # 写入数据
        writer.writerows(data_list)

    print(f"✅ 数据已成功{action} {save_path}，共 {len(data_list)} 条记录")


def save_single_dict_to_csv(
        data: Dict,
        save_path: str = "outPut/anchor_data.csv",
        sort_fields: bool = False,
        sort_key: Callable = None,
        append: bool = True,  # 单条保存默认使用追加模式
        primary_key: Optional[str] = None  # 主键字段，用于替换模式
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
        append=append,
        primary_key=primary_key
    )


if __name__ == '__main__':
    # 准备测试数据
    data1 = {"id": 1, "name": "张三", "age": 25}
    data2 = {"id": 2, "name": "李四", "age": 26}
    data3 = {"id": 1, "name": "张三", "age": 26}  # 与data1主键相同，会替换data1
    data4 = {"id": 3, "name": "王五", "age": 27, "email": "wangwu@example.com"}  # 包含新字段

    # 测试基本保存功能
    print("首次保存数据:")
    save_single_dict_to_csv(data1, primary_key="id")
    save_single_dict_to_csv(data2, primary_key="id")

    # 测试替换功能
    print("\n替换id=1的数据:")
    save_single_dict_to_csv(data3, primary_key="id")

    # 测试批量保存和替换，以及新字段添加
    print("\n批量保存并添加新字段:")
    save_dict_list_to_csv([data1, data4], primary_key="id")
