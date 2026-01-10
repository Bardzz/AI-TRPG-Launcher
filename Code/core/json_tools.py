from __future__ import annotations
import json

def _extract_first_json_object(s: str) -> str | None:
    """
    从字符串中提取第一段括号平衡的 {...}。
    """
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def parse_json_object(s: str) -> dict:
    # 轻量替换中文符号（不做 destructive 变换）
    s2 = (s.replace("：", ":")
            .replace("“", '"').replace("”", '"')
            .replace("（", "(").replace("）", ")"))
    try:
        return json.loads(s2)
    except json.JSONDecodeError:
        block = _extract_first_json_object(s2)
        if not block:
            raise
        return json.loads(block)
