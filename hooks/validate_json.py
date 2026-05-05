"""知识条目 JSON 文件校验脚本。

支持单文件和多文件（通配符）两种输入模式，校验 JSON 结构、
必填字段、ID 格式、status 枚举、URL 格式、摘要长度、标签数量、
可选字段 score 和 audience 的取值范围。

用法:
    python hooks/validate_json.py <json_file> [json_file2 ...]
    python hooks/validate_json.py knowledge/articles/*.json

退出码:
    0 - 全部校验通过
    1 - 存在校验失败
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "source_url": str,
    "summary": str,
    "tags": list,
    "status": str,
}

VALID_STATUSES = {"draft", "review", "published", "archived", "analyzed", "raw", "curated", "distributed"}

VALID_AUDIENCES = {"beginner", "intermediate", "advanced"}

ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

URL_PATTERN = re.compile(r"^https?://\S+$")

MIN_SUMMARY_LENGTH = 20
MIN_TAGS_COUNT = 1
SCORE_MIN = 1
SCORE_MAX = 10


def validate_file(filepath: Path) -> list[str]:
    """校验单个 JSON 文件，返回错误列表（空列表表示通过）。"""
    errors: list[str] = []

    # 1. JSON 解析
    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"文件读取失败: {exc}"]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"JSON 解析失败: {exc}"]

    if not isinstance(data, dict):
        return ["JSON 顶层结构必须是对象（dict）"]

    # 2. 必填字段存在性与类型
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"缺少必填字段: {field}")
        elif not isinstance(data[field], expected_type):
            actual = type(data[field]).__name__
            errors.append(
                f"字段 '{field}' 类型错误: 期望 {expected_type.__name__}，实际 {actual}"
            )

    # 以下校验仅在字段存在且类型正确时执行
    # 3. ID 格式
    if "id" in data and isinstance(data["id"], str):
        if not ID_PATTERN.match(data["id"]):
            errors.append(
                f"ID 格式错误: '{data['id']}' 不符合 UUID 格式规范"
            )

    # 4. status 枚举
    if "status" in data and isinstance(data["status"], str):
        if data["status"] not in VALID_STATUSES:
            errors.append(
                f"status 值无效: '{data['status']}'，"
                f"允许值: {', '.join(sorted(VALID_STATUSES))}"
            )

    # 5. URL 格式
    if "source_url" in data and isinstance(data["source_url"], str):
        if not URL_PATTERN.match(data["source_url"]):
            errors.append(f"URL 格式无效: '{data['source_url']}'")

    # 6. 摘要长度
    if "summary" in data and isinstance(data["summary"], str):
        if len(data["summary"]) < MIN_SUMMARY_LENGTH:
            errors.append(
                f"摘要过短: {len(data['summary'])} 字，最少 {MIN_SUMMARY_LENGTH} 字"
            )

    # 7. 标签数量
    if "tags" in data and isinstance(data["tags"], list):
        if len(data["tags"]) < MIN_TAGS_COUNT:
            errors.append(f"标签数量不足: {len(data['tags'])} 个，最少 {MIN_TAGS_COUNT} 个")

    # 8. 可选字段: score
    if "score" in data:
        score = data["score"]
        if not isinstance(score, (int, float)):
            errors.append(f"score 类型错误: 期望数值，实际 {type(score).__name__}")
        elif not (SCORE_MIN <= score <= SCORE_MAX):
            errors.append(f"score 超出范围: {score}，允许范围 [{SCORE_MIN}, {SCORE_MAX}]")

    # 9. 可选字段: audience
    if "audience" in data:
        audience = data["audience"]
        if not isinstance(audience, str):
            errors.append(f"audience 类型错误: 期望 str，实际 {type(audience).__name__}")
        elif audience not in VALID_AUDIENCES:
            errors.append(
                f"audience 值无效: '{audience}'，"
                f"允许值: {', '.join(sorted(VALID_AUDIENCES))}"
            )

    return errors


def main() -> None:
    """命令行入口。"""
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <json_file> [json_file2 ...]")
        sys.exit(1)

    files = [Path(arg) for arg in sys.argv[1:]]

    total = len(files)
    passed = 0
    failed = 0

    for filepath in files:
        if not filepath.is_file():
            print(f"✗ {filepath}: 文件不存在")
            failed += 1
            continue

        errors = validate_file(filepath)
        if errors:
            failed += 1
            print(f"✗ {filepath}:")
            for err in errors:
                print(f"    - {err}")
        else:
            passed += 1
            print(f"✓ {filepath}")

    # 汇总统计
    print(f"\n校验完成: 共 {total} 个文件，{passed} 通过，{failed} 失败")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
