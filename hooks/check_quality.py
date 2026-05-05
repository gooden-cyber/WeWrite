"""知识条目质量评分脚本。

对知识条目 JSON 文件进行 5 维度质量评估，输出可视化评分报告。

维度及权重（满分 100）：
    - 摘要质量 (25): 长度 + 技术关键词奖励
    - 技术深度 (25): 基于文章 score 字段映射
    - 格式规范 (20): id/title/source_url/status/时间戳 各 4 分
    - 标签精度 (15): 1-3 个合法标签为最佳
    - 空洞词检测 (15): 不含空洞词得满分

等级标准: A >= 80, B >= 60, C < 60

用法:
    python hooks/check_quality.py <json_file> [json_file2 ...]
    python hooks/check_quality.py knowledge/articles/*.json

退出码:
    0 - 无 C 级条目
    1 - 存在 C 级条目
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DimensionScore:
    """单维度评分明细。"""
    name: str
    score: float
    max_score: float
    details: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.score / self.max_score if self.max_score else 0.0


@dataclass
class QualityReport:
    """单个知识条目的质量报告。"""
    filepath: Path
    item_id: str
    title: str
    dimensions: list[DimensionScore] = field(default_factory=list)
    total_score: float = 0.0
    grade: str = ""

    def compute_grade(self) -> None:
        self.total_score = sum(d.score for d in self.dimensions)
        if self.total_score >= 80:
            self.grade = "A"
        elif self.total_score >= 60:
            self.grade = "B"
        else:
            self.grade = "C"


# ── 常量定义 ──────────────────────────────────────────────────────────

TECH_KEYWORDS: set[str] = {
    "llm", "agent", "transformer", "embedding", "rag", "fine-tune",
    "inference", "tokenizer", "prompt", "vector", "gpu", "cuda",
    "attention", "neural", "model", "training", "api", "sdk",
    "framework", "benchmark", "latency", "throughput", "quantization",
    "diffusion", "multimodal", "reasoning", "retrieval", "pipeline",
    "架构", "算法", "模型", "推理", "训练", "微调", "向量", "检索",
    "分布式", "高性能", "内核", "优化", "部署",
}

STANDARD_TAGS: set[str] = {
    "llm", "agent", "rag", "code-generation", "tool-use", "inference",
    "training", "fine-tuning", "multimodal", "nlp", "cv", "embedding",
    "vector-db", "framework", "sdk", "api", "benchmark", "deployment",
    "optimization", "cuda", "gpu", "distributed", "open-source",
    "research", "paper", "tutorial", "python", "rust", "go", "c++",
    "transformer", "diffusion", "gpt", "claude", "gemini", "deepseek",
    "machine-learning", "deep-learning", "reinforcement-learning",
    "data-engineering", "mlops", "devops", "security", "privacy",
}

VACANCY_WORDS_CN: set[str] = {
    "赋能", "抓手", "闭环", "打通", "全链路", "底层逻辑",
    "颗粒度", "对齐", "拉通", "沉淀", "强大的", "革命性的",
}

VACANCY_WORDS_EN: set[str] = {
    "groundbreaking", "revolutionary", "game-changing", "cutting-edge",
    "next-generation", "state-of-the-art", "world-class", "best-in-class",
    "disruptive", "paradigm-shifting", "unprecedented", "synergy",
    "holistic", "scalable", "robust", "seamless",
}

# 阈值常量
SUMMARY_FULL_LEN = 50
SUMMARY_BASIC_LEN = 20

# ── 评分函数 ──────────────────────────────────────────────────────────


def score_summary(data: dict) -> DimensionScore:
    """摘要质量评分（满分 25）。"""
    max_score = 25
    score = 0.0
    details: list[str] = []
    summary: str = data.get("summary", "")

    length = len(summary)
    if length >= SUMMARY_FULL_LEN:
        score += 18
        details.append(f"长度 {length} 字 >= {SUMMARY_FULL_LEN}，+18")
    elif length >= SUMMARY_BASIC_LEN:
        score += 10
        details.append(f"长度 {length} 字 >= {SUMMARY_BASIC_LEN}，+10")
    else:
        details.append(f"长度 {length} 字 < {SUMMARY_BASIC_LEN}，+0")

    found_keywords = {kw for kw in TECH_KEYWORDS if kw in summary.lower()}
    if found_keywords:
        bonus = min(len(found_keywords) * 2, 7)
        score += bonus
        details.append(f"技术关键词 {found_keywords}，+{bonus}")

    score = min(score, max_score)
    return DimensionScore("摘要质量", score, max_score, details)


def score_depth(data: dict) -> DimensionScore:
    """技术深度评分（满分 25），基于 score 字段 1-10 映射。"""
    max_score = 25
    details: list[str] = []
    raw_score = data.get("score")

    if raw_score is None:
        details.append("缺少 score 字段，按 0 分计")
        return DimensionScore("技术深度", 0, max_score, details)

    if not isinstance(raw_score, (int, float)):
        details.append(f"score 类型无效: {type(raw_score).__name__}")
        return DimensionScore("技术深度", 0, max_score, details)

    clamped = max(1, min(10, raw_score))
    mapped = clamped / 10 * max_score
    details.append(f"score={raw_score} -> {mapped:.1f}/{max_score}")
    return DimensionScore("技术深度", mapped, max_score, details)


def score_format(data: dict) -> DimensionScore:
    """格式规范评分（满分 20），id/title/source_url/status/时间戳各 4 分。"""
    max_score = 20
    score = 0.0
    details: list[str] = []

    checks: list[tuple[str, str]] = [
        ("id", "str"),
        ("title", "str"),
        ("source_url", "str"),
        ("status", "str"),
    ]
    for field_name, expected in checks:
        val = data.get(field_name)
        if val and isinstance(val, str) and val.strip():
            score += 4
            details.append(f"{field_name}: 存在且有效，+4")
        else:
            details.append(f"{field_name}: 缺失或无效，+0")

    has_created = bool(data.get("created_at"))
    has_updated = bool(data.get("updated_at"))
    if has_created and has_updated:
        score += 4
        details.append("时间戳: created_at + updated_at 齐全，+4")
    elif has_created or has_updated:
        score += 2
        details.append("时间戳: 仅一个时间戳，+2")
    else:
        details.append("时间戳: 缺失，+0")

    return DimensionScore("格式规范", score, max_score, details)


def score_tags(data: dict) -> DimensionScore:
    """标签精度评分（满分 15），1-3 个合法标签为最佳。"""
    max_score = 15
    score = 0.0
    details: list[str] = []
    tags = data.get("tags", [])

    if not isinstance(tags, list):
        details.append("tags 字段类型无效")
        return DimensionScore("标签精度", 0, max_score, details)

    count = len(tags)
    if count == 0:
        details.append("无标签，+0")
        return DimensionScore("标签精度", 0, max_score, details)

    # 数量评分
    if 1 <= count <= 3:
        score += 8
        details.append(f"标签数量 {count} (最佳 1-3)，+8")
    elif count <= 5:
        score += 5
        details.append(f"标签数量 {count} (偏多)，+5")
    else:
        score += 2
        details.append(f"标签数量 {count} (过多)，+2")

    # 合法性评分
    valid_count = sum(1 for t in tags if isinstance(t, str) and t.lower() in STANDARD_TAGS)
    if valid_count == count and count > 0:
        score += 7
        details.append(f"全部 {valid_count} 个标签命中标准列表，+7")
    elif valid_count > 0:
        ratio = valid_count / count
        bonus = round(7 * ratio)
        score += bonus
        details.append(f"{valid_count}/{count} 标签命中标准列表，+{bonus}")
    else:
        details.append("无标签命中标准列表，+0")

    score = min(score, max_score)
    return DimensionScore("标签精度", score, max_score, details)


def score_vacancy(data: dict) -> DimensionScore:
    """空洞词检测（满分 15），不含空洞词得满分。"""
    max_score = 15
    score = float(max_score)
    details: list[str] = []
    found: list[str] = []

    text_fields = ["summary", "title", "analyst_notes"]
    for fname in text_fields:
        val = data.get(fname, "")
        if not isinstance(val, str):
            continue
        lower = val.lower()
        for word in VACANCY_WORDS_CN:
            if word in lower:
                found.append(f"[中] {word} (in {fname})")
        for word in VACANCY_WORDS_EN:
            if word in lower:
                found.append(f"[英] {word} (in {fname})")

    if found:
        penalty = min(len(found) * 3, max_score)
        score = max_score - penalty
        details.append(f"发现 {len(found)} 个空洞词: {found}，-{penalty}")
    else:
        details.append("未发现空洞词，满分")

    return DimensionScore("空洞词检测", score, max_score, details)


def evaluate_file(filepath: Path) -> QualityReport:
    """评估单个 JSON 文件，返回质量报告。"""
    try:
        text = filepath.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        report = QualityReport(
            filepath=filepath,
            item_id="(parse error)",
            title=str(exc),
        )
        report.grade = "C"
        return report

    if not isinstance(data, dict):
        report = QualityReport(filepath=filepath, item_id="(error)", title="JSON 非对象")
        report.grade = "C"
        return report

    report = QualityReport(
        filepath=filepath,
        item_id=str(data.get("id", "N/A")),
        title=str(data.get("title", "N/A")),
        dimensions=[
            score_summary(data),
            score_depth(data),
            score_format(data),
            score_tags(data),
            score_vacancy(data),
        ],
    )
    report.compute_grade()
    return report


# ── 输出格式化 ─────────────────────────────────────────────────────────


def progress_bar(ratio: float, width: int = 20) -> str:
    """生成文本进度条，ratio 0.0-1.0。"""
    filled = round(ratio * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def grade_color(grade: str) -> str:
    """ANSI 颜色标记等级。"""
    colors = {"A": "\033[92m", "B": "\033[93m", "C": "\033[91m"}
    reset = "\033[0m"
    return f"{colors.get(grade, '')}{grade}{reset}"


def print_report(report: QualityReport) -> None:
    """打印单个条目的质量报告。"""
    print(f"\n{'─' * 60}")
    print(f"文件: {report.filepath}")
    print(f"ID:   {report.item_id}")
    print(f"标题: {report.title}")
    print()

    for dim in report.dimensions:
        bar = progress_bar(dim.ratio)
        print(f"  {dim.name:<8} {bar} {dim.score:5.1f}/{dim.max_score:.0f}")
        for detail in dim.details:
            print(f"           {detail}")

    print()
    grade_str = grade_color(report.grade)
    print(f"  总分: {report.total_score:.1f}/100  等级: {grade_str}")


def print_summary(reports: list[QualityReport]) -> None:
    """打印汇总统计。"""
    total = len(reports)
    counts = {"A": 0, "B": 0, "C": 0}
    for r in reports:
        counts[r.grade] = counts.get(r.grade, 0) + 1

    avg = sum(r.total_score for r in reports) / total if total else 0

    print(f"\n{'═' * 60}")
    print(f"汇总: 共 {total} 个条目")
    print(f"  平均分: {avg:.1f}")
    print(f"  A 级: {counts['A']}  B 级: {counts['B']}  C 级: {counts['C']}")
    print(f"{'═' * 60}")


# ── 主入口 ─────────────────────────────────────────────────────────────


def main() -> None:
    """命令行入口。"""
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <json_file> [json_file2 ...]")
        sys.exit(1)

    files = [Path(arg) for arg in sys.argv[1:]]
    reports: list[QualityReport] = []

    for filepath in files:
        if not filepath.is_file():
            print(f"✗ {filepath}: 文件不存在")
            continue
        reports.append(evaluate_file(filepath))

    for report in reports:
        print_report(report)

    if reports:
        print_summary(reports)

    has_c = any(r.grade == "C" for r in reports)
    sys.exit(1 if has_c else 0)


if __name__ == "__main__":
    main()
