#!/usr/bin/env python3
"""
MCP Knowledge Server - 让 AI 工具搜索本地知识库

基于 JSON-RPC 2.0 over stdio 协议，实现 MCP (Model Context Protocol)。
无第三方依赖，只用 Python 标准库。

提供的工具:
    - search_articles(keyword, limit=5): 按关键词搜索文章
    - get_article(article_id): 获取文章完整内容
    - knowledge_stats(): 获取知识库统计信息

用法:
    # 直接运行（stdin/stdout 模式）
    python mcp_knowledge_server.py

    # Claude Desktop 配置 (claude_desktop_config.json):
    {
      "mcpServers": {
        "knowledge": {
          "command": "python3",
          "args": ["/path/to/mcp_knowledge_server.py"]
        }
      }
    }
"""

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# 配置日志输出到 stderr（stdout 用于 JSON-RPC 通信）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# 知识库文章目录
ARTICLES_DIR = Path(__file__).parent / "knowledge" / "articles"


def load_articles() -> list[dict[str, Any]]:
    """加载所有文章 JSON 文件"""
    articles = []
    if not ARTICLES_DIR.exists():
        logger.warning(f"文章目录不存在: {ARTICLES_DIR}")
        return articles

    for json_file in ARTICLES_DIR.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "id" in data:
                    articles.append(data)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"跳过文件 {json_file.name}: {e}")

    logger.info(f"已加载 {len(articles)} 篇文章")
    return articles


# 启动时加载文章缓存
ARTICLES_CACHE: list[dict[str, Any]] = []


def ensure_cache_loaded():
    """确保缓存已加载"""
    global ARTICLES_CACHE
    if not ARTICLES_CACHE:
        ARTICLES_CACHE = load_articles()


# ──────────────────── MCP 工具实现 ────────────────────


def search_articles(keyword: str, limit: int = 5) -> dict[str, Any]:
    """按关键词搜索文章标题和摘要"""
    ensure_cache_loaded()
    keyword_lower = keyword.lower()
    results = []

    for article in ARTICLES_CACHE:
        title = article.get("title", "")
        summary = article.get("summary", "")
        content = article.get("content", "")

        # 在标题、摘要、内容中搜索
        if (
            keyword_lower in title.lower()
            or keyword_lower in summary.lower()
            or keyword_lower in content.lower()
        ):
            results.append({
                "id": article.get("id"),
                "title": title,
                "source_type": article.get("source_type"),
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "tags": article.get("tags", []),
                "score": article.get("score"),
            })

        if len(results) >= limit:
            break

    return {
        "keyword": keyword,
        "total_matches": len(results),
        "articles": results,
    }


def get_article(article_id: str) -> dict[str, Any]:
    """按 ID 获取文章完整内容"""
    ensure_cache_loaded()

    for article in ARTICLES_CACHE:
        if article.get("id") == article_id:
            return article

    return {"error": f"文章不存在: {article_id}"}


def knowledge_stats() -> dict[str, Any]:
    """返回统计信息（文章总数、来源分布、热门标签）"""
    ensure_cache_loaded()

    source_counter = Counter()
    tag_counter = Counter()
    category_counter = Counter()
    score_sum = 0
    score_count = 0

    for article in ARTICLES_CACHE:
        # 来源分布
        source_type = article.get("source_type", "unknown")
        source_counter[source_type] += 1

        # 标签统计
        for tag in article.get("tags", []):
            tag_counter[tag] += 1

        # 分类统计
        category = article.get("category", "未分类")
        category_counter[category] += 1

        # 分数统计
        score = article.get("score")
        if score is not None:
            score_sum += score
            score_count += 1

    return {
        "total_articles": len(ARTICLES_CACHE),
        "source_distribution": dict(source_counter.most_common(20)),
        "top_tags": dict(tag_counter.most_common(30)),
        "category_distribution": dict(category_counter.most_common(10)),
        "average_score": round(score_sum / score_count, 2) if score_count > 0 else None,
    }


# ──────────────────── MCP 协议处理 ────────────────────

# 工具定义
TOOLS = [
    {
        "name": "search_articles",
        "description": "按关键词搜索知识库文章。在标题、摘要、正文中匹配关键词，返回匹配的文章列表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限，默认 5",
                    "default": 5,
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_article",
        "description": "根据文章 ID 获取完整内容。使用 search_articles 先找到文章 ID，再用此工具获取详情。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "文章的唯一 ID",
                },
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "knowledge_stats",
        "description": "获取知识库统计信息，包括文章总数、来源分布、热门标签等。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

# 工具分发映射
TOOL_HANDLERS = {
    "search_articles": lambda args: search_articles(
        keyword=args.get("keyword", ""),
        limit=args.get("limit", 5),
    ),
    "get_article": lambda args: get_article(
        article_id=args.get("article_id", ""),
    ),
    "knowledge_stats": lambda args: knowledge_stats(),
}


def handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    """处理 MCP initialize 请求"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": "mcp-knowledge-server",
            "version": "1.0.0",
        },
    }


def handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    """处理 tools/list 请求"""
    return {"tools": TOOLS}


def handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    """处理 tools/call 请求"""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "content": [
                {"type": "text", "text": f"未知工具: {tool_name}"}
            ],
            "isError": True,
        }

    try:
        result = handler(arguments)
        return {
            "content": [
                {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
            ],
        }
    except Exception as e:
        logger.exception(f"工具执行失败: {tool_name}")
        return {
            "content": [
                {"type": "text", "text": f"工具执行错误: {str(e)}"}
            ],
            "isError": True,
        }


# 方法路由
METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def create_response(request_id: Any, result: Any) -> dict[str, Any]:
    """创建 JSON-RPC 成功响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def create_error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    """创建 JSON-RPC 错误响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """处理单个 JSON-RPC 请求"""
    request_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    logger.info(f"收到请求: method={method}, id={request_id}")

    handler = METHOD_HANDLERS.get(method)
    if not handler:
        return create_error_response(request_id, -32601, f"方法不存在: {method}")

    try:
        result = handler(params)
        return create_response(request_id, result)
    except Exception as e:
        logger.exception(f"处理请求失败: {method}")
        return create_error_response(request_id, -32603, str(e))


def main():
    """主循环：从 stdin 读取 JSON-RPC 请求，输出响应到 stdout"""
    logger.info("MCP Knowledge Server 启动")
    logger.info(f"文章目录: {ARTICLES_DIR}")

    # 预加载文章缓存
    ensure_cache_loaded()

    # 通知客户端服务器已就绪（发送 initialized 通知）
    # 注意：通知没有 id，客户端不应响应
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    print(json.dumps(initialized_notification), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"无效的 JSON: {e}")
            error_resp = create_error_response(None, -32700, "解析错误")
            print(json.dumps(error_resp), flush=True)
            continue

        # 处理批量请求
        if isinstance(request, list):
            responses = [handle_request(req) for req in request if isinstance(req, dict)]
            print(json.dumps(responses), flush=True)
        else:
            response = handle_request(request)
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
