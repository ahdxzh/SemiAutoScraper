import logging
from typing import Optional, Set

from playwright.sync_api import Page, Locator

logger = logging.getLogger(__name__)


def _collect_texts(node: Locator, seen: Set[str], keyword: str, max_depth: int, current_depth: int = 0) -> list[str]:
    """递归收集子节点文本（辅助函数）"""
    if current_depth > max_depth:
        return []

    results = []
    try:
        children = node.locator("xpath=./child::*").all()
    except Exception as e:
        logger.debug(f"无法获取子节点: {e}")
        return results

    for child in children:
        try:
            raw_text = child.text_content() or ""
            clean_text = raw_text.strip()

            # 排除空文本、包含关键字的文本、已收集过的文本
            if clean_text and keyword not in clean_text and clean_text not in seen:
                seen.add(clean_text)
                results.append(clean_text)

            # 递归检查子节点
            results.extend(_collect_texts(child, seen, keyword, max_depth, current_depth + 1))

        except Exception as e:
            logger.debug(f"读取节点文本失败: {e}")

    return results


def _cleanup_results(raw_results: str) -> str:
    """
    智能清理结果字符串，仅处理存在包含关系的元素

    参数:
        raw_results: 原始的逗号分隔字符串

    返回:
        清理后去重的逗号分隔字符串
    """
    if not raw_results:
        return ""

    # 先按逗号分割成原始部分列表
    original_parts = [p.strip() for p in raw_results.split(',') if p.strip()]

    # 检查是否存在包含关系
    has_containment = False
    for i in range(len(original_parts)):
        for j in range(len(original_parts)):
            if i != j and original_parts[i] in original_parts[j]:
                has_containment = True
                break
        if has_containment:
            break

    # 如果没有包含关系，直接去重返回
    if not has_containment:
        seen = set()
        unique_parts = []
        for part in original_parts:
            if part not in seen:
                seen.add(part)
                unique_parts.append(part)
        return ','.join(unique_parts)

    # 存在包含关系时，进行深度处理
    processed_parts = []
    for part in original_parts:
        # 按空格分割可能的组合项
        sub_parts = part.split()
        sub_parts = [p.strip() for p in sub_parts if p.strip()]
        processed_parts.extend(sub_parts)

    # 去重并保持顺序
    seen = set()
    unique_parts = []
    for part in processed_parts:
        if part not in seen:
            seen.add(part)
            unique_parts.append(part)

    return ','.join(unique_parts)


def find_ancestor_texts_with_value(
        page: Page,
        keyword: str,
        locator: Optional[Locator] = None,
        max_level: int = 5,
        max_depth: int = 3  # 限制递归深度，避免DOM过大
) -> Optional[str]:
    """
    查找包含关键字的元素，并获取其父节点下的去重文本内容（递归子节点）

    参数:
        page: Playwright的Page对象
        keyword: 用于定位的关键词
        locator: 可选的定位范围
        max_level: 最大向上查找层级（默认5层）
        max_depth: 子节点递归深度（默认3层）

    返回:
        去重后拼接的文本，未找到则返回None
    """
    try:
        search_scope = locator if locator is not None else page
        target_elements = search_scope.get_by_text(keyword, exact=False).all()

        if not target_elements:
            logger.info(f"未找到包含关键词 '{keyword}' 的元素")
            return None

        for single_element in target_elements:
            try:
                single_element.wait_for(state="visible", timeout=10000)
            except Exception as e:
                logger.debug(f"等待元素可见失败: {e}")
                continue

            for level in range(max_level + 1):
                xpath = "." if level == 0 else "/".join([".."] * level)
                ancestor = single_element.locator(f"xpath={xpath}")

                # 调用平级的辅助函数，传递必要的参数
                unique_parts = _collect_texts(ancestor, seen=set(), keyword=keyword, max_depth=max_depth)

                if unique_parts:
                    # 先拼接原始结果，再进行清理
                    raw_result = ",".join(unique_parts)
                    cleaned_result = _cleanup_results(raw_result)
                    return cleaned_result if cleaned_result else None

        logger.info("未找到包含有效文本的父节点")
        return None

    except Exception as e:
        logger.error(f"查找过程出错: {str(e)}")
        return None
