#!/usr/bin/env python3
"""微信公众号一键发布脚本 v2。

用法:
    python scripts/publish_wechat.py              # 自动选择最新文章发布
    python scripts/publish_wechat.py --list       # 列出可发布的文章
    python scripts/publish_wechat.py --id <id>    # 指定文章 ID 发布
    python scripts/publish_wechat.py --dry-run    # 只生成不发布
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from pipeline.model_client import quick_chat
from pipeline.wechat_api import WeChatClient, render_markdown, THEMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"
WECHAT_DIR = PROJECT_ROOT / "knowledge" / "wechat"
CONTENT_DIR = WECHAT_DIR / "content"
IMAGES_DIR = WECHAT_DIR / "images"
GENERATED_FILE = WECHAT_DIR / "generated_articles.json"
METRICS_FILE = WECHAT_DIR / "publish_metrics.jsonl"


# ============================================================
# Prompt 模板
# ============================================================

SYSTEM_BASE = """你是一位资深的 AI/技术领域自媒体作者。

写作风格：
- 轻松科普，像懂技术的朋友在聊天
- 开头直接说这是什么、为什么值得关注
- 结尾给出明确判断，不要两头讨好

硬性约束：
- 禁止套话："你是否想象过""在当今时代""随着XX的发展""值得一提的是""众所周知"
- 禁止模糊评价："非常强大""十分优秀""受到了广泛关注"
- 全文 emoji ≤5 个，感叹号 ≤3 个
- 专业术语首次出现时用括号简要解释
- 至少引用 1 个具体数据点
- 总字数 1500-2500 字
- Markdown 格式，不在末尾加标签"""

TEMPLATES = {
    "github_project": {
        "system": SYSTEM_BASE + "\n\n重点：必须展示至少一段代码示例（≤20行，带注释），分析核心技术和应用场景。",
        "user": "为 GitHub 项目写公众号文章：\n\n项目名：{title}\n简介：{summary}\n亮点：{key_points}\n技术栈：{language}\nStars：{stars}\nForks：{forks}\n原文：{url}\n\n直接输出 Markdown。",
    },
    "tool_framework": {
        "system": SYSTEM_BASE + "\n\n重点：必须展示代码示例，说清和竞品的差异，给出使用建议。",
        "user": "为工具/框架写公众号文章：\n\n名称：{title}\n简介：{summary}\n特性：{key_points}\n技术栈：{language}\nStars：{stars}\n原文：{url}\n\n直接输出 Markdown。",
    },
    "research_paper": {
        "system": SYSTEM_BASE + "\n\n重点：用大白话解释核心思想，讨论落地可能性和局限性。",
        "user": "为研究内容写公众号文章：\n\n标题：{title}\n摘要：{summary}\n关键发现：{key_points}\n领域：{tags}\n原文：{url}\n\n直接输出 Markdown。",
    },
    "industry_news": {
        "system": SYSTEM_BASE + "\n\n重点：说清为什么重要，分析影响，给出判断是趋势还是噪音。",
        "user": "为行业动态写公众号文章：\n\n标题：{title}\n内容：{summary}\n关键点：{key_points}\n领域：{tags}\n原文：{url}\n\n直接输出 Markdown。",
    },
}


# ============================================================
# 文章分类
# ============================================================

def classify_article(article: dict) -> str:
    """根据元数据选择 prompt 模板。"""
    url = article.get("source_url", "")
    tags = [t.lower() for t in article.get("tags", [])]
    title = article.get("title", "").lower()
    tag_str = " ".join(tags)

    if "github.com" in url:
        tool_kws = {"framework", "library", "sdk", "tool", "cli", "engine", "runtime"}
        if tool_kws & set(tags) or any(kw in title for kw in tool_kws):
            return "tool_framework"
        return "github_project"

    paper_kws = {"paper", "research", "study", "arxiv"}
    if paper_kws & set(tags):
        return "research_paper"

    code_kws = {"python", "rust", "go", "javascript", "typescript", "api"}
    if code_kws & set(tags):
        return "tool_framework"

    return "industry_news"


# ============================================================
# 标题生成
# ============================================================

def generate_titles(article: dict, github_data: dict) -> List[str]:
    """生成 3 个候选标题。"""
    prompt = f"""为以下技术文章生成 3 个微信公众号标题，每行一个，不要编号。

项目：{article.get('title', '')}
简介：{article.get('summary', '')[:100]}
Stars：{github_data.get('stars', '')}

要求：15-25字，不用 emoji，不用"震惊""重磅"，必须有具体数据或明确收益。"""

    try:
        result = quick_chat(prompt=prompt, temperature=0.8)
        titles = [t.strip().strip('"').strip("'") for t in result.strip().split("\n") if t.strip()]
        return titles[:3] if titles else [article.get("title", "")]
    except Exception as e:
        logger.warning("标题生成失败: %s", e)
        return [article.get("title", "")]


def pick_best_title(titles: List[str]) -> str:
    """从候选标题中选最优。"""
    if len(titles) <= 1:
        return titles[0] if titles else ""

    candidates = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = f"从以下标题中选最好的一个，只输出选中的标题：\n\n{candidates}\n\n选择标准：有数据、能引发好奇、15-25字。"

    try:
        result = quick_chat(prompt=prompt, temperature=0.3)
        return result.strip().strip('"').strip("'")
    except Exception:
        return titles[0]


# ============================================================
# 内容生成
# ============================================================

def generate_content(article: dict, github_data: dict, template_key: str, title: str) -> Optional[str]:
    """生成正文。"""
    tmpl = TEMPLATES.get(template_key, TEMPLATES["industry_news"])
    system = tmpl["system"] + f"\n\n标题已定：「{title}」，围绕此标题展开。"

    user = tmpl["user"].format(
        title=title,
        summary=article.get("summary", "")[:300],
        key_points=", ".join(article.get("key_points", [])[:5]) or "暂无",
        language=github_data.get("language", ""),
        stars=github_data.get("stars", "未知"),
        forks=github_data.get("forks", "未知"),
        tags=", ".join(article.get("tags", [])[:5]) or "",
        url=article.get("source_url", ""),
    )

    try:
        return quick_chat(prompt=user, system_prompt=system, max_tokens=3000)
    except Exception as e:
        logger.error("内容生成失败: %s", e)
        return None


# ============================================================
# 自检 + 修复
# ============================================================

BANNED_PHRASES = [
    "你是否想象过", "在当今时代", "随着科技的发展", "随着技术的发展",
    "受到了广泛", "非常强大", "十分优秀", "值得一提的是", "众所周知",
]


def self_check(content: str) -> List[dict]:
    """自检，返回问题列表。"""
    issues = []
    first_3 = "。".join(content.split("。")[:3])

    # 套话：只检查开头
    for phrase in BANNED_PHRASES:
        if phrase in first_3:
            issues.append({"type": "cliche", "detail": f"开头含套话「{phrase}」", "severity": "high"})

    # 字数
    wc = len(content)
    if wc < 1500:
        issues.append({"type": "wordcount", "detail": f"字数不足: {wc}", "severity": "high"})
    elif wc > 2500:
        issues.append({"type": "wordcount", "detail": f"字数过多: {wc}", "severity": "medium"})

    # 代码（工具类）
    if "```" not in content and len(content) > 1000:
        issues.append({"type": "no_code", "detail": "无代码示例", "severity": "medium"})

    return issues


def auto_fix(content: str, issues: List[dict], title: str) -> Optional[str]:
    """修复高优先级问题。"""
    high = [i for i in issues if i["severity"] == "high"]
    if not high:
        return content

    fixes = []
    for i in high:
        if i["type"] == "cliche":
            fixes.append("重写开头，去掉套话")
        elif i["type"] == "wordcount":
            fixes.append("扩充内容" if "不足" in i["detail"] else "精简内容")

    prompt = f"""修改以下文章，解决问题：{'; '.join(i['detail'] for i in high)}

修改要求：{'; '.join(fixes)}
保持标题「{title}」和整体风格不变。

原文：
{content}

输出修改后的完整文章。"""

    try:
        return quick_chat(prompt=prompt, max_tokens=3000)
    except Exception as e:
        logger.warning("自动修复失败: %s", e)
        return None


# ============================================================
# 评分
# ============================================================

def score_content(content: str, title: str) -> float:
    """给文章打分，返回平均分。"""
    prompt = f"""给文章打分（1-10），只输出 JSON：{{"avg": X}}

标题：{title}
内容前600字：{content[:600]}

评分维度：信息密度、可读性、吸引力、独特性。"""

    try:
        result = quick_chat(prompt=prompt, temperature=0.3, max_tokens=50)
        match = re.search(r'\{[^}]+\}', result)
        if match:
            return json.loads(match.group()).get("avg", 5)
    except Exception:
        pass
    return 5.0


# ============================================================
# 生成最优版本
# ============================================================

def generate_best_version(article: dict, github_data: dict, template_key: str, title: str) -> Optional[str]:
    """生成 2 个版本，修复后选优。"""
    versions = []

    for i in range(2):
        logger.info("生成版本 %d...", i + 1)
        content = generate_content(article, github_data, template_key, title)
        if not content:
            continue

        # 自检 + 修复
        issues = self_check(content)
        if any(iss["severity"] == "high" for iss in issues):
            logger.info("版本 %d 有问题，修复中...", i + 1)
            fixed = auto_fix(content, issues, title)
            if fixed:
                content = fixed

        versions.append(content)

    if not versions:
        return None
    if len(versions) == 1:
        return versions[0]

    # 评分选优
    logger.info("评分选优...")
    scores = [score_content(v, title) for v in versions]
    best_idx = max(range(len(scores)), key=lambda i: scores[i])
    logger.info("选择版本 %d (评分: %.1f vs %.1f)", best_idx + 1, scores[best_idx], scores[1 - best_idx])

    return versions[best_idx]


# ============================================================
# 封面图
# ============================================================

def generate_cover(title: str, tags: List[str]) -> Optional[Path]:
    """用 cover_generator 生成封面。"""
    from pipeline.cover_generator import generate_cover as _generate_cover
    return _generate_cover(
        title=title,
        category="",
        output_dir=IMAGES_DIR,
        backend="pollinations",
        filename=f"cover_{datetime.now().strftime('%Y%m%d')}.png",
    )


# ============================================================
# 微信发布
# ============================================================

def publish_to_wechat(title: str, content: str, source_url: str,
                      cover_path: Optional[Path], theme: str = "default",
                      footer_text: str = "") -> Optional[str]:
    """发布到草稿箱。"""
    app_id = os.getenv("WECHAT_APP_ID")
    app_secret = os.getenv("WECHAT_APP_SECRET")
    if not app_id or not app_secret:
        logger.error("未配置 WECHAT_APP_ID 或 WECHAT_APP_SECRET")
        return None

    client = WeChatClient(app_id, app_secret)
    html = render_markdown(content, theme_name=theme, footer_text=footer_text)

    # 上传封面
    thumb_id = ""
    if cover_path and cover_path.exists():
        try:
            thumb_id = client.upload_thumb(cover_path)
        except Exception as e:
            logger.warning("封面上传失败: %s", e)

    # 创建草稿
    try:
        data = client.create_draft(
            title=title,
            content=html,
            thumb_media_id=thumb_id,
            author="",
            digest=content[:120].replace("\n", " "),
        )
        return data
    except Exception as e:
        logger.error("创建草稿失败: %s", e)
        return None


# ============================================================
# 数据记录
# ============================================================

def record_metrics(article_title: str, source_url: str, media_id: str,
                   word_count: int, template_key: str, score: float) -> None:
    """记录发布指标。"""
    record = {
        "published_at": datetime.now().isoformat(),
        "article_title": article_title,
        "source_url": source_url,
        "media_id": media_id,
        "word_count": word_count,
        "template_key": template_key,
        "score": score,
    }
    WECHAT_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ============================================================
# 文章管理
# ============================================================

def load_generated() -> set:
    if GENERATED_FILE.exists():
        try:
            return set(json.loads(GENERATED_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def save_generated(urls: set) -> None:
    WECHAT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_FILE.write_text(json.dumps(list(urls), ensure_ascii=False, indent=2), encoding="utf-8")


def list_articles() -> List[dict]:
    if not ARTICLES_DIR.exists():
        return []
    generated = load_generated()
    articles = []
    for f in sorted(ARTICLES_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            url = data.get("source_url", "")
            title = data.get("title", f.stem)
            articles.append({
                "file": f.name, "title": title, "source_url": url,
                "score": data.get("score", 0),
                "published": url in generated or title in generated,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return articles


def select_best_article() -> Optional[dict]:
    articles = list_articles()
    candidates = [a for a in articles if not a["published"]]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return json.loads((ARTICLES_DIR / candidates[0]["file"]).read_text(encoding="utf-8"))


def fetch_github_data(url: str) -> dict:
    match = re.search(r"github\.com/([^/]+/[^/]+)", url)
    if not match:
        return {}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"https://api.github.com/repos/{match.group(1)}",
                              headers={"Accept": "application/vnd.github.v3+json"})
            if resp.status_code == 200:
                d = resp.json()
                return {"stars": d.get("stargazers_count", 0), "forks": d.get("forks_count", 0),
                        "language": d.get("language", ""), "description": d.get("description", "")}
    except Exception as e:
        logger.warning("GitHub 数据获取失败: %s", e)
    return {}


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="微信公众号一键发布")
    parser.add_argument("--list", action="store_true", help="列出可发布文章")
    parser.add_argument("--id", type=str, help="指定文章文件名")
    parser.add_argument("--dry-run", action="store_true", help="只生成不发布")
    parser.add_argument("--theme", type=str, default="default",
                        choices=list(THEMES.keys()), help="主题风格")
    parser.add_argument("--list-themes", action="store_true", help="列出可用主题")
    parser.add_argument("--no-footer", action="store_true", help="不加文末引导语")
    args = parser.parse_args()

    if args.list_themes:
        print("\n可用主题：")
        for name, t in THEMES.items():
            print(f"  {name:<10} {t['name']} - {t['desc']}")
        return

    if args.list:
        articles = list_articles()
        if not articles:
            print("没有找到文章")
            return
        print(f"\n{'状态':<4} {'评分':<6} {'标题':<50} {'文件名'}")
        print("-" * 100)
        for a in articles:
            s = "✓" if a["published"] else " "
            sc = f"{a['score']:.1f}" if a.get("score") else "-"
            print(f"  {s}   {sc:<6} {a['title'][:48]:<50} {a['file']}")
        return

    # 选择文章
    if args.id:
        path = ARTICLES_DIR / args.id
        if not path.exists():
            logger.error("文章不存在: %s", args.id)
            return
        article = json.loads(path.read_text(encoding="utf-8"))
    else:
        article = select_best_article()
        if not article:
            logger.info("没有新的文章需要发布")
            return

    source_url = article.get("source_url", "")
    tags = article.get("tags", [])
    original_title = article.get("title", "")

    logger.info("=" * 50)
    logger.info("开始发布: %s", original_title)
    logger.info("=" * 50)

    # 分类 + GitHub 数据
    template_key = classify_article(article)
    github_data = fetch_github_data(source_url) if "github.com" in source_url else {}
    logger.info("类型: %s | Stars: %s", template_key, github_data.get("stars", "-"))

    # 阶段1：标题
    logger.info("生成标题...")
    titles = generate_titles(article, github_data)
    title = pick_best_title(titles)
    logger.info("标题: %s", title)

    # 阶段2：正文
    logger.info("生成正文...")
    content = generate_best_version(article, github_data, template_key, title)
    if not content:
        logger.error("文章生成失败")
        return

    # 自检报告
    issues = self_check(content)
    logger.info("自检: %s", "全部通过" if not issues else "; ".join(i["detail"] for i in issues))

    # 封面
    cover = generate_cover(title, tags)

    # 保存
    full_content = f"---\ntitle: {title}\n---\n\n" + content
    safe = "".join(c for c in title[:20] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    content_path = CONTENT_DIR / f"article_{datetime.now().strftime('%Y%m%d')}_{safe}.md"
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(full_content, encoding="utf-8")
    logger.info("已保存: %s", content_path)

    if args.dry_run:
        print(f"\n标题: {title}")
        print(f"字数: {len(content)}")
        print(f"文件: {content_path}")
        print(f"封面: {'有' if cover else '无'}")
        return

    # 发布
    logger.info("发布中...")
    media_id = publish_to_wechat(title, full_content, source_url, cover)
    if not media_id:
        logger.error("发布失败")
        sys.exit(1)

    logger.info("发布成功! media_id: %s", media_id)

    # 记录
    generated = load_generated()
    generated.update([source_url, original_title])
    save_generated(generated)
    score = score_content(content, title)
    record_metrics(original_title, source_url, media_id, len(content), template_key, score)


if __name__ == "__main__":
    main()
