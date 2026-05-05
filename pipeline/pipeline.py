"""四步知识库自动化流水线。macos系统推荐使用launchd设置定时任务，具体目录在：mkdir -p ~/Library/LaunchAgents

配置文件：
- ~/Library/LaunchAgents/com.kailiang.ai-kb-collect.plist - 每天 08:00 采集
- ~/Library/LaunchAgents/com.kailiang.ai-kb-analyze.plist - 每周日 10:00 分析
状态：
launchctl list | grep kailiang
# -	0	com.kailiang.ai-kb-analyze
# -	0	com.kailiang.ai-kb-collect
常用命令：
# 手动触发采集
launchctl start com.kailiang.ai-kb-collect
# 查看日志
tail -f logs/collect.log
# 暂停任务
launchctl unload ~/Library/LaunchAgents/com.kailiang.ai-kb-collect.plist
# 重新启用
launchctl load ~/Library/LaunchAgents/com.kailiang.ai-kb-collect.plist

Step 1: 采集（Collect）— 从 GitHub Search API 和 RSS 源采集 AI 相关内容
Step 2: 分析（Analyze）— 调用 LLM 对每条内容进行摘要/评分/标签分析
Step 3: 整理（Organize）— 去重 + 格式标准化 + 校验
Step 4: 保存（Save）— 将文章保存为独立 JSON 文件到 knowledge/articles/

Example:
    $ python pipeline/pipeline.py --sources github,rss --limit 20
    $ python pipeline/pipeline.py --sources github --limit 5 --dry-run
"""

import argparse
import html
import json
import logging
import os
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from model_client import chat_with_retry, get_provider

logger = logging.getLogger(__name__)

# 数据目录
RAW_DIR = PROJECT_ROOT / "knowledge" / "raw"
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"

# GitHub Search API 配置
GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_QUERIES = [
    "llm framework language:python stars:>100",
    "ai agent language:python pushed:>2025-01-01",
    "rag retrieval augmented generation stars:>50",
]

# RSS 源配置文件路径
RSS_SOURCES_FILE = PROJECT_ROOT / "pipeline" / "rss_sources.yaml"

# 请求配置
REQUEST_TIMEOUT = 30.0
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

# create_provider 别名，兼容用户导入习惯
create_provider = get_provider


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(UTC).isoformat()


# ============================================================================
# Step 1: 采集（Collect）
# ============================================================================


def load_rss_sources() -> list[dict[str, str]]:
    """从 YAML 配置文件加载 RSS 源列表。

    Returns:
        启用的 RSS 源列表，每项包含 name, url, category。
    """
    if not RSS_SOURCES_FILE.exists():
        logger.warning("RSS 源配置文件不存在: %s", RSS_SOURCES_FILE)
        return []

    try:
        with open(RSS_SOURCES_FILE, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        sources = config.get("sources", [])
        enabled = [s for s in sources if s.get("enabled", True)]
        logger.info("加载 %d 个 RSS 源（%d 个启用）", len(sources), len(enabled))
        return enabled

    except (yaml.YAMLError, OSError) as exc:
        logger.error("读取 RSS 源配置失败: %s", exc)
        return []


def collect_from_github(limit: int = 20) -> list[dict[str, Any]]:
    """从 GitHub Search API 采集 AI 相关项目。

    Args:
        limit: 最大采集数量。

    Returns:
        原始采集数据列表。
    """

    token = os.getenv(GITHUB_TOKEN_ENV)
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    all_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=REQUEST_TIMEOUT, headers=headers) as client:
        for query in GITHUB_SEARCH_QUERIES:
            if len(all_items) >= limit:
                break

            try:
                logger.info("GitHub 搜索: %s", query)
                response = client.get(
                    f"{GITHUB_API_BASE}/search/repositories",
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": min(limit, 30),
                    },
                )
                response.raise_for_status()
                data = response.json()

                for item in data.get("items", []):
                    repo_id = str(item["id"])
                    if repo_id not in seen_ids:
                        seen_ids.add(repo_id)
                        all_items.append({
                            "source": "github",
                            "source_id": repo_id,
                            "title": item["full_name"],
                            "url": item["html_url"],
                            "description": item.get("description", ""),
                            "language": item.get("language", ""),
                            "stars": item.get("stargazers_count", 0),
                            "forks": item.get("forks_count", 0),
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "topics": item.get("topics", []),
                            "collected_at": datetime.now(UTC).isoformat(),
                        })

            except httpx.HTTPStatusError as exc:
                logger.warning("GitHub API 请求失败: %s", exc)
            except httpx.TimeoutException:
                logger.warning("GitHub API 请求超时")

    return all_items[:limit]


def fetch_article_content(url: str, client: httpx.Client) -> str:
    """从URL抓取文章正文内容。

    Args:
        url: 文章URL
        client: httpx客户端

    Returns:
        文章正文内容（截取前2000字）
    """
    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        html_content = response.text

        # 提取正文的简单策略
        # 1. 尝试提取 <article> 标签
        article_match = re.search(r"<article[^>]*>(.*?)</article>", html_content, re.DOTALL)
        if article_match:
            content = article_match.group(1)
        else:
            # 2. 尝试提取 <main> 标签
            main_match = re.search(r"<main[^>]*>(.*?)</main>", html_content, re.DOTALL)
            if main_match:
                content = main_match.group(1)
            else:
                # 3. 提取 <body> 标签
                body_match = re.search(r"<body[^>]*>(.*?)</body>", html_content, re.DOTALL)
                content = body_match.group(1) if body_match else html_content

        # 去除HTML标签，保留文本
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)
        content = re.sub(r"<[^>]+>", " ", content)
        content = html.unescape(content)
        # 清理多余空白
        content = re.sub(r"\s+", " ", content).strip()
        return content[:2000]

    except Exception as exc:
        logger.debug("抓取文章内容失败 [%s]: %s", url, exc)
        return ""


def collect_from_rss(limit: int = 20) -> list[dict[str, Any]]:
    """从 RSS 源采集 AI 相关内容。

    使用简易正则解析 RSS XML，不依赖第三方 RSS 解析库。
    数据源从 rss_sources.yaml 配置文件读取。
    对于描述过短的条目，会尝试从URL抓取完整内容。

    Args:
        limit: 最大采集数量。

    Returns:
        原始采集数据列表。
    """
    all_items: list[dict[str, Any]] = []
    seen_links: set[str] = set()

    # 从 YAML 加载 RSS 源
    rss_sources = load_rss_sources()
    if not rss_sources:
        logger.warning("无可用的 RSS 源")
        return all_items

    # RSS XML 解析正则
    item_pattern = re.compile(r"<item>(.*?)</item>", re.DOTALL)
    title_pattern = re.compile(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>")
    link_pattern = re.compile(r"<link>(.*?)</link>")
    desc_pattern = re.compile(
        r"<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>",
        re.DOTALL,
    )
    pubdate_pattern = re.compile(r"<pubDate>(.*?)</pubDate>")

    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        for source in rss_sources:
            if len(all_items) >= limit:
                break

            feed_url = source["url"]
            feed_name = source.get("name", feed_url)
            category = source.get("category", "")

            try:
                logger.info("RSS 采集: %s (%s)", feed_name, category)
                response = client.get(feed_url)
                response.raise_for_status()
                xml_content = response.text

                for match in item_pattern.finditer(xml_content):
                    if len(all_items) >= limit:
                        break

                    item_xml = match.group(1)

                    title_m = title_pattern.search(item_xml)
                    title = ""
                    if title_m:
                        title = title_m.group(1) or title_m.group(2) or ""
                        title = title.strip()

                    link_m = link_pattern.search(item_xml)
                    link = link_m.group(1).strip() if link_m else ""

                    desc_m = desc_pattern.search(item_xml)
                    description = ""
                    if desc_m:
                        description = desc_m.group(1) or desc_m.group(2) or ""
                        # 先去除HTML标签，再解码HTML实体
                        description = re.sub(r"<[^>]+>", "", description).strip()
                        description = html.unescape(description)

                    pub_m = pubdate_pattern.search(item_xml)
                    pub_date = pub_m.group(1).strip() if pub_m else ""

                    if link and link not in seen_links:
                        seen_links.add(link)

                        # 如果描述过短或只是URL元信息，尝试抓取完整内容
                        if len(description) < 100 or description.startswith("Article URL:"):
                            logger.info("描述过短，尝试抓取完整内容: %s", title[:50])
                            full_content = fetch_article_content(link, client)
                            if full_content and len(full_content) > len(description):
                                description = full_content

                        all_items.append({
                            "source": "rss",
                            "source_id": str(uuid.uuid4()),
                            "source_name": feed_name,
                            "category": category,
                            "title": title,
                            "url": link,
                            "description": description[:2000],
                            "published_at": pub_date,
                            "collected_at": datetime.now(UTC).isoformat(),
                        })

            except httpx.HTTPStatusError as exc:
                logger.warning("RSS 请求失败 [%s]: %s", feed_name, exc)
            except httpx.TimeoutException:
                logger.warning("RSS 请求超时 [%s]", feed_name)

    return all_items[:limit]


def save_raw_data(items: list[dict[str, Any]], source: str) -> Path:
    """保存原始采集数据到 knowledge/raw/。

    Args:
        items: 原始数据列表。
        source: 数据源标识（github/rss）。

    Returns:
        保存的文件路径。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DIR / f"{source}_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    logger.info("原始数据已保存: %s (%d 条)", filepath.name, len(items))
    return filepath


# ============================================================================
# Step 2: 分析（Analyze）
# ============================================================================

ANALYSIS_SYSTEM_PROMPT = """分析技术内容，返回JSON。只返回JSON，无其他文字。

格式：{"summary":"摘要","score":分数,"tags":["标签"],"category":"分类","key_points":["要点"]}

要求：
- summary: 100-200字中文摘要，包含：这是什么、解决什么问题、核心亮点
- score: 1-10评分（10=最有价值）
- tags: 3-5个标签（LLM/Agent/RAG/框架/工具/研究/开源/Python等）
- category: 技术动态|开源项目|研究论文|行业新闻
- key_points: 3-5个具体要点"""


def analyze_item(item: dict[str, Any], max_retries: int = 2) -> dict[str, Any]:
    """调用 LLM 分析单条内容。

    Args:
        item: 原始采集数据。
        max_retries: 最大重试次数

    Returns:
        包含分析结果的字典。
    """
    content = f"标题: {item.get('title', '')}\n"
    content += f"描述: {item.get('description', '')[:1500]}\n"
    content += f"URL: {item.get('url', '')}\n"

    if item.get("language"):
        content += f"语言: {item['language']}\n"
    if item.get("stars"):
        content += f"Stars: {item['stars']}\n"
    if item.get("topics"):
        content += f"标签: {', '.join(item['topics'])}\n"
    if item.get("source_name"):
        content += f"来源: {item['source_name']}\n"

    for attempt in range(max_retries + 1):
        try:
            response = chat_with_retry(
                prompt=content,
                system_prompt=ANALYSIS_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=800,
            )

            # 解析 JSON 响应
            result_text = response.content.strip()
            # 移除可能的 markdown 代码块标记
            result_text = re.sub(r"^```json?\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)
            # 移除可能的换行符和多余空白
            result_text = result_text.strip()

            # 尝试直接解析
            try:
                analysis = json.loads(result_text)
            except json.JSONDecodeError:
                # 尝试提取JSON对象
                json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise json.JSONDecodeError("无法找到有效的JSON", result_text, 0)

            # 验证必要字段
            summary = analysis.get("summary", "")
            score = analysis.get("score", 5)
            tags = analysis.get("tags", [])
            key_points = analysis.get("key_points", [])

            # 如果摘要太短或关键字段缺失，重试
            if len(summary) < 50 or not tags or not key_points:
                if attempt < max_retries:
                    logger.warning("分析结果不完整，重试 %d/%d: %s", attempt + 1, max_retries, item.get("title", "")[:50])
                    continue
                else:
                    # 最后一次尝试，使用默认值
                    if len(summary) < 50:
                        summary = item.get("description", "")[:200] or f"关于 {item.get('title', '')} 的技术文章"
                    if not tags:
                        tags = ["AI", "技术"]
                    if not key_points:
                        key_points = [f"来自 {item.get('source_name', '技术社区')} 的热门内容"]

            return {
                "summary": summary,
                "score": max(1, min(10, score)),  # 确保分数在1-10之间
                "tags": tags[:5],
                "category": analysis.get("category", "技术动态"),
                "key_points": key_points[:5],
                "analysis_model": response.model,
                "analysis_provider": response.provider,
                "analysis_tokens": response.usage.total_tokens,
            }

        except (json.JSONDecodeError, Exception) as exc:
            if attempt < max_retries:
                logger.warning("分析失败，重试 %d/%d: %s - %s", attempt + 1, max_retries, item.get("title", ""), exc)
            else:
                logger.warning("分析最终失败: %s - %s", item.get("title", ""), exc)
                # 使用降级策略：从描述中提取关键信息
                description = item.get("description", "")
                return {
                    "summary": description[:200] if description else f"来自 {item.get('source_name', '技术社区')} 的技术内容",
                    "score": 5,  # 默认中等分数，而不是0
                    "tags": ["AI", "技术"],
                    "category": "技术动态",
                    "key_points": [f"来自 {item.get('source_name', '技术社区')} 的热门内容"],
                    "analysis_error": str(exc),
                }


def analyze_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量分析采集内容。

    Args:
        items: 原始采集数据列表。

    Returns:
        包含分析结果的数据列表。
    """
    analyzed: list[dict[str, Any]] = []
    total = len(items)

    for i, item in enumerate(items, 1):
        logger.info("分析进度: %d/%d - %s", i, total, item.get("title", "")[:50])
        analysis = analyze_item(item)
        merged = {**item, **analysis}
        merged["analyzed"] = True  # 标记为已分析
        analyzed.append(merged)

    logger.info("分析完成: %d 条内容", len(analyzed))
    return analyzed


# ============================================================================
# Step 3: 整理（Organize）
# ============================================================================


def deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 URL 去重。

    Args:
        items: 待去重的数据列表。

    Returns:
        去重后的数据列表。
    """
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []

    for item in items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)

    removed = len(items) - len(unique)
    if removed > 0:
        logger.info("去重: 移除 %d 条重复内容", removed)

    return unique


def validate_item(item: dict[str, Any]) -> bool:
    """校验单条数据的完整性。

    Args:
        item: 待校验的数据。

    Returns:
        是否通过校验。
    """
    required_fields = ["title", "url", "source"]
    return all(item.get(field) for field in required_fields)


def standardize_item(item: dict[str, Any]) -> dict[str, Any]:
    """标准化数据格式，生成最终知识条目。

    Args:
        item: 原始数据。

    Returns:
        标准化的知识条目。
    """
    now = datetime.now(UTC).isoformat()

    return {
        "id": str(uuid.uuid4()),
        "title": item.get("title", "").strip(),
        "source_url": item.get("url", ""),
        "source_type": item.get("source", "unknown"),
        "source_metadata": {
            "stars": item.get("stars", 0),
            "language": item.get("language", ""),
            "topics": item.get("topics", []),
            "published_at": item.get("published_at", ""),
            "collected_at": item.get("collected_at", now),
        },
        "content": item.get("description", ""),
        "summary": item.get("summary", ""),
        "key_points": item.get("key_points", []),
        "tags": item.get("tags", []),
        "category": item.get("category", "技术动态"),
        "score": item.get("score", 0),
        "status": "analyzed",
        "created_at": now,
        "updated_at": now,
    }


def organize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """整理数据：去重 + 校验 + 标准化。

    Args:
        items: 待整理的数据列表。

    Returns:
        整理后的知识条目列表。
    """
    # 去重
    unique_items = deduplicate(items)

    # 校验 + 标准化
    organized: list[dict[str, Any]] = []
    for item in unique_items:
        if validate_item(item):
            standardized = standardize_item(item)
            standardized["organized"] = True  # 标记为已整理
            organized.append(standardized)
        else:
            logger.warning("校验失败，跳过: %s", item.get("title", "unknown"))

    logger.info("整理完成: %d 条有效条目", len(organized))
    return organized


# ============================================================================
# Step 4: 保存（Save）
# ============================================================================


def save_articles(articles: list[dict[str, Any]]) -> list[Path]:
    """将知识条目保存为独立 JSON 文件（跳过已存在的文章）。

    Args:
        articles: 知识条目列表。

    Returns:
        保存的文件路径列表。
    """
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    # 加载已有文章的 URL 和标题用于去重
    existing_urls: set[str] = set()
    existing_titles: set[str] = set()
    for existing_file in ARTICLES_DIR.glob("*.json"):
        try:
            with open(existing_file, encoding="utf-8") as f:
                data = json.load(f)
                if data.get("source_url"):
                    existing_urls.add(data["source_url"])
                if data.get("title"):
                    existing_titles.add(data["title"])
        except (json.JSONDecodeError, OSError):
            continue

    skipped = 0
    for article in articles:
        url = article.get("source_url", "")
        title = article.get("title", "")

        # 跳过已存在的文章
        if url in existing_urls or title in existing_titles:
            skipped += 1
            continue

        article_id = article.get("id", str(uuid.uuid4()))
        filepath = ARTICLES_DIR / f"{article_id}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)

        saved_paths.append(filepath)
        # 记录已保存的 URL 和标题
        if url:
            existing_urls.add(url)
        if title:
            existing_titles.add(title)

    logger.info("保存 %d 篇文章，跳过 %d 篇已存在文章", len(saved_paths), skipped)
    return saved_paths


# ============================================================================
# CLI 入口
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。

    Returns:
        配置好的 ArgumentParser 实例。
    """
    parser = argparse.ArgumentParser(
        description="AI 知识库自动化流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python pipeline/pipeline.py --sources github,rss --limit 20
  python pipeline/pipeline.py --sources github --limit 5 --dry-run
  python pipeline/pipeline.py --verbose
""",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="github,rss",
        help="数据源，逗号分隔 (default: github,rss)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="每个源的最大采集数量 (default: 20)",
    )
    parser.add_argument(
        "--step",
        type=int,
        nargs="+",
        choices=[1, 2, 3, 4],
        help="指定要运行的步骤 (1=采集, 2=分析, 3=整理, 4=保存)，默认运行全部",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式：只采集，不调用 LLM 分析",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="日期过滤，格式 YYYYMMDD，只处理该日期的数据",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志",
    )
    return parser


def load_raw_data(
    status_filter: str | None = None,
    date_filter: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """从 knowledge/raw/ 加载原始采集数据（增量加载，避免全量加载）。

    优化策略：
    1. 按日期过滤：只加载特定日期的文件
    2. 懒加载：找到足够数据就停止
    3. 状态过滤：只加载需要处理的数据

    Args:
        status_filter: 状态过滤器，可选值：
            - None: 加载所有数据
            - "unanalyzed": 只加载未分析的数据
            - "unorganized": 只加载已分析但未整理的数据
            - "organized": 只加载已分析且已整理的数据
        date_filter: 日期过滤器，格式 "YYYYMMDD"，只加载该日期的文件
        limit: 最大加载数量，找到足够数据就停止

    Returns:
        去重后的原始数据列表。
    """
    all_items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    if not RAW_DIR.exists():
        logger.warning("原始数据目录不存在: %s", RAW_DIR)
        return all_items

    # 根据日期过滤文件
    if date_filter:
        raw_files = sorted(RAW_DIR.glob(f"*{date_filter}*.json"), reverse=True)
    else:
        raw_files = sorted(RAW_DIR.glob("*.json"), reverse=True)

    if not raw_files:
        logger.warning("未找到原始数据文件")
        return all_items

    for filepath in raw_files:
        # 懒加载：已找到足够数据就停止
        if limit and len(all_items) >= limit:
            break

        try:
            with open(filepath, encoding="utf-8") as f:
                items = json.load(f)
                if isinstance(items, list):
                    added_count = 0
                    for item in items:
                        # 懒加载：已找到足够数据就停止
                        if limit and len(all_items) >= limit:
                            break

                        # 统一字段名：source_url -> url
                        if "source_url" in item and "url" not in item:
                            item["url"] = item["source_url"]

                        url = item.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            # 根据状态过滤
                            if status_filter == "unanalyzed" and item.get("analyzed", False):
                                continue
                            if status_filter == "unorganized" and not item.get("analyzed", False):
                                continue
                            if status_filter == "unorganized" and item.get("organized", False):
                                continue
                            if status_filter == "organized" and not item.get("organized", False):
                                continue
                            all_items.append(item)
                            added_count += 1
                    logger.info("加载原始数据: %s (%d 条，新增 %d 条)", filepath.name, len(items), added_count)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("读取原始数据失败: %s - %s", filepath.name, exc)

    logger.info("共加载 %d 条原始数据（去重后）", len(all_items))
    return all_items


def load_raw_data_by_date(date_str: str) -> list[dict[str, Any]]:
    """按日期加载原始数据（用于增量处理）。

    Args:
        date_str: 日期字符串，格式 "YYYYMMDD"

    Returns:
        该日期的原始数据列表。
    """
    return load_raw_data(date_filter=date_str)


def load_unanalyzed_data(
    date_filter: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """加载未分析的数据（增量处理专用）。

    Args:
        date_filter: 日期过滤器，格式 "YYYYMMDD"
        limit: 最大加载数量

    Returns:
        未分析的数据列表。
    """
    return load_raw_data(status_filter="unanalyzed", date_filter=date_filter, limit=limit)


def load_unorganized_data(
    date_filter: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """加载已分析但未整理的数据（增量处理专用）。

    Args:
        date_filter: 日期过滤器，格式 "YYYYMMDD"
        limit: 最大加载数量

    Returns:
        已分析但未整理的数据列表。
    """
    return load_raw_data(status_filter="unorganized", date_filter=date_filter, limit=limit)


def load_organized_data(
    date_filter: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """加载已分析且已整理的数据（用于保存）。

    Args:
        date_filter: 日期过滤器，格式 "YYYYMMDD"
        limit: 最大加载数量

    Returns:
        已分析且已整理的数据列表。
    """
    return load_raw_data(status_filter="organized", date_filter=date_filter, limit=limit)


def update_raw_data_status(url: str, status_key: str, status_value: bool) -> bool:
    """更新原始数据文件中指定URL的状态字段。

    Args:
        url: 要更新的数据URL
        status_key: 状态字段名（如 "analyzed", "organized"）
        status_value: 状态值（True/False）

    Returns:
        是否更新成功
    """
    if not RAW_DIR.exists():
        return False

    for filepath in RAW_DIR.glob("*.json"):
        try:
            with open(filepath, encoding="utf-8") as f:
                items = json.load(f)

            if not isinstance(items, list):
                continue

            updated = False
            for item in items:
                if item.get("url") == url:
                    item[status_key] = status_value
                    updated = True
                    break

            if updated:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                logger.debug("更新状态: %s -> %s=%s", url, status_key, status_value)
                return True

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("更新状态失败: %s - %s", filepath.name, exc)
            continue

    return False


def load_existing_raw_urls() -> set[str]:
    """加载已有原始数据的 URL 集合，用于采集去重。

    Returns:
        已有原始数据的 URL 集合。
    """
    existing_urls: set[str] = set()

    if not RAW_DIR.exists():
        return existing_urls

    for filepath in RAW_DIR.glob("*.json"):
        try:
            with open(filepath, encoding="utf-8") as f:
                items = json.load(f)
                if isinstance(items, list):
                    for item in items:
                        url = item.get("url", "")
                        if url:
                            existing_urls.add(url)
        except (json.JSONDecodeError, OSError):
            continue

    return existing_urls


def run_pipeline(
    sources: list[str],
    limit: int = 20,
    dry_run: bool = False,
    steps: list[int] | None = None,
    date_filter: str | None = None,
) -> dict[str, Any]:
    """执行流水线。

    Args:
        sources: 数据源列表。
        limit: 每个源的最大采集数量。
        dry_run: 是否为干跑模式。
        steps: 要运行的步骤列表，None 表示运行全部。
        date_filter: 日期过滤器，格式 "YYYYMMDD"，只处理该日期的数据。

    Returns:
        流水线执行统计。
    """
    if steps is None:
        steps = [1, 2, 3, 4]

    steps_set = set(steps)
    run_step = lambda s: s in steps_set

    stats: dict[str, Any] = {
        "sources": sources,
        "limit": limit,
        "dry_run": dry_run,
        "steps": steps,
        "collected": 0,
        "analyzed": 0,
        "saved": 0,
        "started_at": datetime.now(UTC).isoformat(),
    }

    all_raw_items: list[dict[str, Any]] = []

    # Step 1: 采集
    if run_step(1):
        logger.info("=" * 60)
        logger.info("Step 1: 采集（Collect）")
        logger.info("=" * 60)

        # 加载已有 URL，用于去重
        existing_urls = load_existing_raw_urls()
        logger.info("已有原始数据 %d 条", len(existing_urls))

        new_items: list[dict[str, Any]] = []

        if "github" in sources:
            github_items = collect_from_github(limit)
            # 过滤已存在的
            new_github = [i for i in github_items if i.get("url") not in existing_urls]
            logger.info("GitHub: 采集 %d 条，新增 %d 条", len(github_items), len(new_github))
            if new_github:
                save_raw_data(new_github, "github")
                new_items.extend(new_github)
                existing_urls.update(i.get("url") for i in new_github)

        if "rss" in sources:
            rss_items = collect_from_rss(limit)
            # 过滤已存在的
            new_rss = [i for i in rss_items if i.get("url") not in existing_urls]
            logger.info("RSS: 采集 %d 条，新增 %d 条", len(rss_items), len(new_rss))
            if new_rss:
                save_raw_data(new_rss, "rss")
                new_items.extend(new_rss)

        all_raw_items = new_items
        stats["collected"] = len(all_raw_items)
        logger.info("采集完成: 新增 %d 条原始数据", stats["collected"])
    else:
        # 不运行 Step 1 时，不需要加载数据（Step 2/3会增量加载）
        logger.info("跳过 Step 1，后续步骤将增量加载数据")

    # 检查是否有数据需要处理
    if run_step(2):
        # 增量加载：只加载未分析的数据（支持日期过滤）
        unanalyzed_items = load_unanalyzed_data(date_filter=date_filter)
        if not unanalyzed_items:
            logger.info("没有未分析的数据，跳过 Step 2")
        else:
            logger.info("=" * 60)
            logger.info("Step 2: 分析（Analyze）- %d 条待处理", len(unanalyzed_items))
            logger.info("=" * 60)

            if dry_run:
                logger.info("干跑模式：跳过 LLM 分析")
                for item in unanalyzed_items:
                    item["summary"] = item.get("description", "")[:200]
                    item["score"] = 0
                    item["tags"] = item.get("topics", [])
                    item["category"] = "技术动态"
                    item["key_points"] = []
                    item["analyzed"] = True
            else:
                analyzed_items = analyze_items(unanalyzed_items)
                # 更新原始数据状态
                for item in analyzed_items:
                    update_raw_data_status(item.get("url", ""), "analyzed", True)
                stats["analyzed"] = len(analyzed_items)

    if run_step(3):
        # 增量加载：只加载已分析但未整理的数据（支持日期过滤）
        unorganized_items = load_unorganized_data(date_filter=date_filter)
        if not unorganized_items:
            logger.info("没有待整理的数据，跳过 Step 3")
        else:
            logger.info("=" * 60)
            logger.info("Step 3: 整理（Organize）- %d 条待处理", len(unorganized_items))
            logger.info("=" * 60)

            organized_items = organize_items(unorganized_items)
            # 更新原始数据状态
            for item in organized_items:
                update_raw_data_status(item.get("source_url", ""), "organized", True)
            stats["organized"] = len(organized_items)

    # Step 4: 保存（只保存已整理的数据）
    if run_step(4):
        logger.info("=" * 60)
        logger.info("Step 4: 保存（Save）")
        logger.info("=" * 60)

        # 只加载已整理的数据用于保存
        organized_items = load_organized_data(date_filter=date_filter)
        if organized_items:
            saved_paths = save_articles(organized_items)
            stats["saved"] = len(saved_paths)
        else:
            logger.info("没有已整理的数据需要保存")

    stats["finished_at"] = datetime.now(UTC).isoformat()
    return stats


def main() -> None:
    """CLI 主入口。"""
    parser = build_parser()
    args = parser.parse_args()

    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 解析数据源
    sources = [s.strip().lower() for s in args.sources.split(",")]
    valid_sources = {"github", "rss"}
    invalid = set(sources) - valid_sources
    if invalid:
        logger.error("无效的数据源: %s，可选: %s", invalid, valid_sources)
        sys.exit(1)

    logger.info("AI 知识库流水线启动")
    logger.info("数据源: %s, 限制: %d, 干跑: %s, 步骤: %s, 日期: %s",
                sources, args.limit, args.dry_run, args.step or "全部", args.date or "全部")

    try:
        stats = run_pipeline(
            sources=sources,
            limit=args.limit,
            dry_run=args.dry_run,
            steps=args.step,
            date_filter=args.date,
        )

        # 输出统计
        logger.info("=" * 60)
        logger.info("流水线执行完成")
        logger.info("=" * 60)
        logger.info("采集: %d 条", stats["collected"])
        logger.info("分析: %d 条", stats["analyzed"])
        logger.info("保存: %d 篇", stats["saved"])

    except KeyboardInterrupt:
        logger.info("用户中断，流水线停止")
        sys.exit(130)
    except Exception as exc:
        logger.error("流水线执行失败: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
