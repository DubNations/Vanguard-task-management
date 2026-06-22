"""通用工具函数。"""
import re


def strip_html_tags(value):
    """去除字符串中的 HTML 标签，防止 XSS 注入。

    保留纯文本内容，移除所有 <tag> 和 </tag> 结构。
    """
    if not isinstance(value, str):
        return value
    return re.sub(r'<[^>]+>', '', value)


def sanitize_text_fields(data, fields):
    """清洗字典中指定文本字段的 HTML 标签。

    Args:
        data: 字典数据
        fields: 需要清洗的字段名列表
    """
    for field in fields:
        if field in data and isinstance(data[field], str):
            data[field] = strip_html_tags(data[field])
    return data
