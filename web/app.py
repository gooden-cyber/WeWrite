"""WeWrite Web UI - 知识库可视化界面。

使用 FastAPI + Jinja2 模板构建。

启动方式：
    python web/app.py
    # 或
    uvicorn web.app:app --reload --port 8000

访问：
    http://localhost:8000
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"

# 添加项目根目录到 sys.path
sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(
    title="WeWrite - AI 知识库助手",
    description="自动化采集 · AI 智能分析 · 结构化存储 · 多渠道分发",
    version="0.1.0",
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# 挂载封面图静态文件
covers_dir = PROJECT_ROOT / "knowledge" / "wechat" / "covers"
covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=covers_dir), name="covers")

# 模板引擎
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def load_articles() -> list[dict]:
    """加载所有知识条目。"""
    articles = []
    if not ARTICLES_DIR.exists():
        return articles

    for json_file in ARTICLES_DIR.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "id" in data:
                    articles.append(data)
        except (OSError, json.JSONDecodeError):
            continue

    # 按创建时间倒序
    articles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return articles


def get_article(article_id: str) -> dict | None:
    """获取单个知识条目。"""
    filepath = ARTICLES_DIR / f"{article_id}.json"
    if not filepath.exists():
        return None

    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def get_categories(articles: list[dict]) -> list[str]:
    """获取所有分类。"""
    categories = set()
    for article in articles:
        category = article.get("category", "")
        if category:
            categories.add(category)
    return sorted(categories)


def get_tags(articles: list[dict]) -> list[str]:
    """获取所有标签。"""
    tags = set()
    for article in articles:
        for tag in article.get("tags", []):
            if tag:
                tags.add(tag)
    return sorted(tags)


def get_stats(articles: list[dict]) -> dict:
    """获取统计信息。"""
    return {
        "total": len(articles),
        "categories": len(get_categories(articles)),
        "tags": len(get_tags(articles)),
        "github": len([a for a in articles if a.get("source_type") == "github"]),
        "rss": len([a for a in articles if a.get("source_type") == "rss"]),
    }


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    category: str | None = Query(None, description="按分类筛选"),
    tag: str | None = Query(None, description="按标签筛选"),
    search: str | None = Query(None, description="搜索关键词"),
    source_type: str | None = Query(None, description="按来源筛选"),
):
    """首页 - 知识库列表。"""
    articles = load_articles()

    # 筛选
    if category:
        articles = [a for a in articles if a.get("category") == category]
    if tag:
        articles = [a for a in articles if tag in a.get("tags", [])]
    if source_type:
        articles = [a for a in articles if a.get("source_type") == source_type]
    if search:
        search_lower = search.lower()
        articles = [
            a for a in articles
            if search_lower in a.get("title", "").lower()
            or search_lower in a.get("summary", "").lower()
            or search_lower in a.get("content", "").lower()
        ]

    # 统计
    all_articles = load_articles()
    stats = get_stats(all_articles)
    categories = get_categories(all_articles)
    tags = get_tags(all_articles)

    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "articles": articles,
            "stats": stats,
            "categories": categories,
            "tags": tags,
            "current_category": category,
            "current_tag": tag,
            "current_search": search,
            "current_source_type": source_type,
        },
    )


@app.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: str):
    """文章详情页。"""
    article = get_article(article_id)
    if not article:
        return templates.TemplateResponse(
            name="404.html",
            request=request,
            status_code=404,
        )

    return templates.TemplateResponse(
        name="detail.html",
        request=request,
        context={"article": article},
    )


@app.get("/publish", response_class=HTMLResponse)
async def publish_page(request: Request):
    """发布文章页面。"""
    return templates.TemplateResponse(
        name="publish.html",
        request=request,
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """管理后台页面。"""
    return templates.TemplateResponse(
        name="admin.html",
        request=request,
    )


@app.get("/api/articles")
async def api_articles(
    category: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    """API - 获取文章列表。"""
    articles = load_articles()

    if category:
        articles = [a for a in articles if a.get("category") == category]
    if tag:
        articles = [a for a in articles if tag in a.get("tags", [])]
    if search:
        search_lower = search.lower()
        articles = [
            a for a in articles
            if search_lower in a.get("title", "").lower()
            or search_lower in a.get("summary", "").lower()
        ]

    return {"articles": articles[:limit], "total": len(articles)}


@app.get("/api/article/{article_id}")
async def api_article(article_id: str):
    """API - 获取单篇文章。"""
    article = get_article(article_id)
    if not article:
        return {"error": "Article not found"}
    return article


@app.get("/api/stats")
async def api_stats():
    """API - 获取统计信息。"""
    articles = load_articles()
    return get_stats(articles)


@app.post("/api/pipeline/run")
async def api_run_pipeline():
    """API - 触发 pipeline 运行。"""
    import subprocess
    import sys

    try:
        # 记录运行历史
        history_file = PROJECT_ROOT / "knowledge" / "pipeline_history.jsonl"
        start_time = datetime.now()

        result = subprocess.run(
            [sys.executable, "pipeline/pipeline.py"],
            capture_output=True,
            text=True,
            timeout=3600,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 记录到历史文件
        record = {
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "duration_seconds": round(duration, 1),
            "success": result.returncode == 0,
            "output_tail": result.stdout[-500:] if result.stdout else "",
            "error_tail": result.stderr[-500:] if result.stderr else "",
        }

        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Pipeline 运行成功",
                "duration": round(duration, 1),
                "output": result.stdout[-1000:] if result.stdout else "",
            }
        else:
            return {
                "status": "error",
                "message": "Pipeline 运行失败",
                "duration": round(duration, 1),
                "error": result.stderr[-1000:] if result.stderr else "",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Pipeline 运行超时"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/preview")
async def api_preview(request: Request):
    """API - 预览文章（调用 AI 生成微信文章并渲染）。

    生成的内容会缓存到 knowledge/wechat/preview/，发布时可复用。
    """
    try:
        body = await request.json()
        article_id = body.get("article_id")
        theme = body.get("theme", "default")
        force_regenerate = body.get("force_regenerate", False)

        if not article_id:
            return {"status": "error", "message": "缺少 article_id"}

        article = get_article(article_id)
        if not article:
            return {"status": "error", "message": "文章不存在"}

        from pipeline.model_client import chat_with_retry
        from pipeline.wechat_api import THEMES, render_markdown

        if theme not in THEMES:
            theme = "default"

        # 检查缓存
        preview_dir = PROJECT_ROOT / "knowledge" / "wechat" / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        cache_file = preview_dir / f"{article_id}.md"

        content = None
        from_cache = False

        if cache_file.exists() and not force_regenerate:
            content = cache_file.read_text(encoding="utf-8")
            from_cache = True

        # 缓存不存在或强制重新生成
        if not content:
            system_prompt = """你是一位资深的 AI/技术领域自媒体作者。

写作风格：
- 轻松科普，像懂技术的朋友在聊天
- 开头直接说这是什么、为什么值得关注
- 结尾给出明确判断，不要两头讨好

硬性约束：
- 禁止套话
- 全文 emoji ≤5 个，感叹号 ≤3 个
- 专业术语首次出现时用括号简要解释
- 至少引用 1 个具体数据点
- 总字数 1500-2500 字
- Markdown 格式"""

            user_prompt = f"""为以下技术内容写公众号文章：

标题：{article.get('title', '')}
摘要：{article.get('summary', '')[:300]}
要点：{', '.join(article.get('key_points', [])[:5]) or '暂无'}
标签：{', '.join(article.get('tags', [])[:5]) or ''}
来源：{article.get('source_url', '')}

直接输出 Markdown。"""

            response = chat_with_retry(prompt=user_prompt, system_prompt=system_prompt, max_tokens=3000)
            content = response.content

            if not content:
                return {"status": "error", "message": "AI 内容生成失败"}

            # 缓存生成结果
            cache_file.write_text(content, encoding="utf-8")
            from_cache = False

        # 渲染成微信 HTML
        html = render_markdown(content, theme_name=theme)

        # 生成封面图
        cover_url = None
        try:
            from pipeline.cover_generator import generate_cover

            # 创建封面图目录
            cover_dir = PROJECT_ROOT / "knowledge" / "wechat" / "covers"
            cover_dir.mkdir(parents=True, exist_ok=True)

            # 生成封面图文件名
            cover_filename = f"cover_{article_id}.png"
            cover_path = cover_dir / cover_filename

            # 如果封面图不存在或强制重新生成
            if not cover_path.exists() or force_regenerate:
                title = article.get("title", "")
                category = article.get("category", "")
                result = generate_cover(
                    title=title,
                    category=category,
                    output_dir=cover_dir,
                    filename=cover_filename
                )
                if result:
                    logger.info("封面图已生成: %s", result)
                else:
                    logger.warning("封面图生成失败")

            # 返回封面图URL
            if cover_path.exists():
                cover_url = f"/covers/{cover_filename}"
        except Exception as e:
            logger.warning("封面图生成失败: %s", e)

        return {
            "status": "success",
            "html": html,
            "title": article.get("title", ""),
            "theme": theme,
            "content_length": len(content),
            "from_cache": from_cache,
            "cover_url": cover_url,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/publish")
async def api_publish(request: Request):
    """API - 触发文章发布。"""
    import subprocess
    import sys

    try:
        body = await request.json()
        article_id = body.get("article_id")
        theme = body.get("theme", "default")
        generate_cover = body.get("generate_cover", True)

        if not article_id:
            return {"status": "error", "message": "缺少 article_id"}

        filename = f"{article_id}.json" if not article_id.endswith(".json") else article_id

        cmd = [sys.executable, "scripts/publish_wechat.py", "--id", filename]
        if theme:
            cmd.extend(["--theme", theme])
        if not generate_cover:
            cmd.append("--no-cover")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "文章发布成功",
                "output": result.stdout[-1000:] if result.stdout else "",
            }
        else:
            return {
                "status": "error",
                "message": "文章发布失败",
                "error": result.stderr[-1000:] if result.stderr else "",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "文章发布超时"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/system/status")
async def api_system_status():
    """API - 获取系统状态。"""
    import os
    from pathlib import Path

    # 检查各个组件
    status = {
        "pipeline": {
            "exists": Path("pipeline/pipeline.py").exists(),
            "articles_count": len(list(Path("knowledge/articles").glob("*.json"))) if Path("knowledge/articles").exists() else 0,
        },
        "scheduler": {
            "exists": Path("scripts/scheduler.py").exists(),
        },
        "publish": {
            "exists": Path("scripts/publish_wechat.py").exists(),
            "wechat_configured": bool(os.getenv("WECHAT_APP_ID")) and bool(os.getenv("WECHAT_APP_SECRET")),
        },
        "web": {
            "exists": Path("web/app.py").exists(),
        },
        "env": {
            "mimo_key_set": bool(os.getenv("MIMO_API_KEY")),
            "deepseek_key_set": bool(os.getenv("DEEPSEEK_API_KEY")),
            "github_token_set": bool(os.getenv("GITHUB_TOKEN")),
        },
    }

    return status


@app.get("/api/token-stats")
async def api_token_stats():
    """API - 获取 token 使用统计。"""
    from pipeline.model_client import get_token_stats
    return get_token_stats()


@app.get("/api/ai-call-log")
async def api_ai_call_log(limit: int = 20):
    """API - 获取 AI 调用详细记录。"""
    log_file = PROJECT_ROOT / "knowledge" / "ai_call_log.jsonl"

    if not log_file.exists():
        return {"calls": [], "total": 0}

    try:
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        records = []
        for line in reversed(lines):  # 最新的在前
            if line.strip():
                records.append(json.loads(line))
            if len(records) >= limit:
                break

        return {"calls": records, "total": len(lines)}
    except Exception as e:
        return {"calls": [], "total": 0, "error": str(e)}


@app.get("/api/pipeline/history")
async def api_pipeline_history(limit: int = 10):
    """API - 获取 pipeline 运行历史。"""
    history_file = PROJECT_ROOT / "knowledge" / "pipeline_history.jsonl"

    if not history_file.exists():
        return {"history": [], "total": 0}

    try:
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        records = []
        for line in reversed(lines):  # 最新的在前
            if line.strip():
                records.append(json.loads(line))
            if len(records) >= limit:
                break

        return {"history": records, "total": len(lines)}
    except Exception as e:
        return {"history": [], "total": 0, "error": str(e)}


@app.get("/api/drafts")
async def api_list_drafts():
    """API - 获取草稿列表。"""
    draft_dir = PROJECT_ROOT / "knowledge" / "wechat" / "preview"

    if not draft_dir.exists():
        return {"drafts": []}

    drafts = []
    for md_file in draft_dir.glob("*.md"):
        article_id = md_file.stem
        # 获取文章信息
        article = get_article(article_id)
        if article:
            drafts.append({
                "article_id": article_id,
                "title": article.get("title", ""),
                "category": article.get("category", ""),
                "score": article.get("score", 0),
                "cached_at": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
                "content_length": md_file.stat().st_size,
            })

    drafts.sort(key=lambda x: x["cached_at"], reverse=True)
    return {"drafts": drafts}


@app.get("/api/publish/history")
async def api_publish_history(limit: int = 20):
    """API - 获取发布历史。"""
    history_file = PROJECT_ROOT / "knowledge" / "wechat" / "publish_metrics.jsonl"

    if not history_file.exists():
        return {"history": []}

    try:
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        records = []
        for line in reversed(lines):
            if line.strip():
                records.append(json.loads(line))
            if len(records) >= limit:
                break

        return {"history": records}
    except Exception as e:
        return {"history": [], "error": str(e)}


# 自动发布配置文件路径
AUTO_PUBLISH_CONFIG = PROJECT_ROOT / "config" / "auto_publish.json"


def load_auto_publish_config() -> dict:
    """加载自动发布配置。"""
    if AUTO_PUBLISH_CONFIG.exists():
        try:
            import json
            return json.loads(AUTO_PUBLISH_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": False}


def save_auto_publish_config(config: dict) -> None:
    """保存自动发布配置。"""
    import json
    AUTO_PUBLISH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    AUTO_PUBLISH_CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/settings/auto-publish")
async def api_get_auto_publish():
    """API - 获取自动发布设置。"""
    config = load_auto_publish_config()
    return {"enabled": config.get("enabled", False)}


@app.post("/api/settings/auto-publish")
async def api_set_auto_publish(request: Request):
    """API - 设置自动发布配置。"""
    try:
        body = await request.json()

        config = load_auto_publish_config()

        # 更新所有配置字段
        if "enabled" in body:
            config["enabled"] = body["enabled"]
        if "strategy" in body:
            config["strategy"] = body["strategy"]
        if "min_score" in body:
            config["min_score"] = body["min_score"]
        if "publish_count" in body:
            config["publish_count"] = body["publish_count"]
        if "publish_time" in body:
            config["publish_time"] = body["publish_time"]

        save_auto_publish_config(config)

        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
