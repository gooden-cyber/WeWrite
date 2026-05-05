"""知识库展示网站生成器 - 亮色清爽风格。

用法:
    python scripts/generate_knowledge_site.py
    python scripts/generate_knowledge_site.py --output docs/
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"
DEFAULT_OUTPUT = PROJECT_ROOT / "site" / "knowledge"

CATEGORY_COLORS = {
    "开源项目": {"bg": "bg-emerald-50", "text": "text-emerald-700", "border": "border-emerald-200", "dot": "bg-emerald-500"},
    "技术动态": {"bg": "bg-blue-50", "text": "text-blue-700", "border": "border-blue-200", "dot": "bg-blue-500"},
    "研究论文": {"bg": "bg-purple-50", "text": "text-purple-700", "border": "border-purple-200", "dot": "bg-purple-500"},
    "行业新闻": {"bg": "bg-amber-50", "text": "text-amber-700", "border": "border-amber-200", "dot": "bg-amber-500"},
}

DEFAULT_COLOR = {"bg": "bg-gray-50", "text": "text-gray-700", "border": "border-gray-200", "dot": "bg-gray-500"}


def load_articles() -> list[dict[str, Any]]:
    """加载所有知识条目。"""
    articles = []
    if not ARTICLES_DIR.exists():
        return articles

    for f in ARTICLES_DIR.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
                data["_file"] = f.stem
                articles.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    articles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return articles


def get_all_tags(articles: list[dict]) -> list[str]:
    """获取所有标签。"""
    tags = set()
    for a in articles:
        tags.update(a.get("tags", []))
    return sorted(tags)


def get_all_categories(articles: list[dict]) -> list[str]:
    """获取所有分类。"""
    cats = set()
    for a in articles:
        if a.get("category"):
            cats.add(a["category"])
    return sorted(cats)


def get_category_color(category: str) -> dict:
    """获取分类对应的颜色。"""
    return CATEGORY_COLORS.get(category, DEFAULT_COLOR)


def format_date(date_str: str) -> str:
    """格式化日期。"""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str[:10] if len(date_str) >= 10 else date_str


def format_stars(stars: int) -> str:
    """格式化星标数。"""
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def generate_article_html(article: dict, all_articles: list[dict]) -> str:
    """生成单篇文章详情页HTML。"""
    cat_color = get_category_color(article.get("category", ""))
    tags_html = "".join(
        f'<span class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">{t}</span>'
        for t in article.get("tags", [])
    )
    key_points_html = "".join(
        f'<li class="flex items-start gap-3"><span class="mt-1.5 w-2 h-2 rounded-full bg-indigo-400 flex-shrink-0"></span><span>{p}</span></li>'
        for p in article.get("key_points", [])
    )

    meta_items = []
    if article.get("source_type"):
        meta_items.append(f'<span class="flex items-center gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>{article["source_type"]}</span>')
    if article.get("source_metadata", {}).get("stars"):
        stars = article["source_metadata"]["stars"]
        meta_items.append(f'<span class="flex items-center gap-1"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>{format_stars(stars)}</span>')
    if article.get("source_metadata", {}).get("language"):
        meta_items.append(f'<span class="flex items-center gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>{article["source_metadata"]["language"]}</span>')
    meta_html = " ".join(meta_items)

    # 相关文章（同分类）
    related_html = ""
    related = [a for a in all_articles if a.get("category") == article.get("category") and a["id"] != article["id"]][:4]
    if related:
        related_cards = ""
        for r in related:
            rc = get_category_color(r.get("category", ""))
            related_cards += f'''
            <a href="../articles/{r["_file"]}.html" class="block p-4 bg-white rounded-xl border border-gray-100 hover:border-indigo-200 hover:shadow-md transition-all">
                <h4 class="font-medium text-gray-900 mb-1 line-clamp-1">{r["title"]}</h4>
                <p class="text-sm text-gray-500 line-clamp-2">{r.get("summary", "")[:80]}</p>
            </a>'''
        related_html = f'''
        <section class="mt-16">
            <h2 class="text-2xl font-bold text-gray-900 mb-6">相关文章</h2>
            <div class="grid md:grid-cols-2 gap-4">{related_cards}</div>
        </section>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article["title"]} - AI 知识库</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
        * {{ font-family: 'Inter', 'Noto Sans SC', sans-serif; }}
        .line-clamp-1 {{ display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }}
        .line-clamp-2 {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="bg-white border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
            <a href="../index.html" class="flex items-center gap-2 text-gray-400 hover:text-gray-600 transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
                </svg>
                <span class="text-sm font-medium">返回知识库</span>
            </a>
            <div class="flex items-center gap-3">
                <span class="px-3 py-1 {cat_color["bg"]} {cat_color["text"]} rounded-full text-xs font-medium">{article.get("category", "未分类")}</span>
            </div>
        </div>
    </header>

    <!-- Content -->
    <main class="max-w-4xl mx-auto px-6 py-12">
        <!-- Title -->
        <div class="mb-8">
            <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4 leading-tight">{article["title"]}</h1>
            <div class="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                {meta_html}
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    {format_date(article.get("created_at", ""))}
                </span>
            </div>
        </div>

        <!-- Summary -->
        <div class="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-8">
            <h2 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <span class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                    <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                </span>
                摘要
            </h2>
            <p class="text-gray-600 leading-relaxed text-lg">{article.get("summary", "暂无摘要")}</p>
        </div>

        <!-- Key Points -->
        {"" if not article.get("key_points") else f'''
        <div class="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-8">
            <h2 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <span class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                    <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                    </svg>
                </span>
                要点
            </h2>
            <ul class="space-y-3 text-gray-600">{key_points_html}</ul>
        </div>'''}

        <!-- Original Content -->
        {"" if not article.get("content") else f'''
        <div class="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-8">
            <h2 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <span class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                    <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
                    </svg>
                </span>
                原始内容
            </h2>
            <p class="text-gray-500 leading-relaxed">{article["content"]}</p>
        </div>'''}

        <!-- Tags -->
        <div class="mb-8">
            <h3 class="text-sm font-medium text-gray-500 mb-3">标签</h3>
            <div class="flex flex-wrap gap-2">{tags_html}</div>
        </div>

        <!-- Source Link -->
        <div class="mb-12">
            <a href="{article.get("source_url", "#")}" target="_blank" rel="noopener"
               class="inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
                查看原文
            </a>
        </div>

        {related_html}
    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-100 py-8 mt-16">
        <div class="max-w-4xl mx-auto px-6 text-center text-gray-400 text-sm">
            <p>AI 知识库 · 持续追踪 AI/LLM 领域技术动态</p>
        </div>
    </footer>
</body>
</html>'''


def generate_index_html(articles: list[dict], tags: list[str], categories: list[str]) -> str:
    """生成主页HTML。"""
    # 统计
    total = len(articles)
    cat_counts = {}
    for a in articles:
        c = a.get("category", "未分类")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    stats_html = f'''
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-center">
            <div class="text-3xl font-bold text-gray-900 mb-1">{total}</div>
            <div class="text-sm text-gray-500">知识条目</div>
        </div>
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-center">
            <div class="text-3xl font-bold text-indigo-600 mb-1">{len(categories)}</div>
            <div class="text-sm text-gray-500">分类</div>
        </div>
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-center">
            <div class="text-3xl font-bold text-emerald-600 mb-1">{len(tags)}</div>
            <div class="text-sm text-gray-500">标签</div>
        </div>
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-center">
            <div class="text-3xl font-bold text-amber-600 mb-1">{cat_counts.get("开源项目", 0)}</div>
            <div class="text-sm text-gray-500">开源项目</div>
        </div>
    </div>'''

    # 分类筛选按钮
    cat_buttons = '<button onclick="filterCategory(\'all\')" class="cat-btn active px-4 py-2 rounded-xl text-sm font-medium transition-all" data-cat="all">全部</button>'
    for cat in categories:
        color = get_category_color(cat)
        cat_buttons += f'<button onclick="filterCategory(\'{cat}\')" class="cat-btn px-4 py-2 rounded-xl text-sm font-medium transition-all {color["bg"]} {color["text"]}" data-cat="{cat}">{cat} ({cat_counts.get(cat, 0)})</button>'

    # 文章卡片
    cards_html = ""
    for a in articles:
        cat_color = get_category_color(a.get("category", ""))
        tags_html = "".join(
            f'<span class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">{t}</span>'
            for t in a.get("tags", [])[:3]
        )
        meta_parts = []
        if a.get("source_metadata", {}).get("stars"):
            meta_parts.append(f'<span class="flex items-center gap-1"><svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>{format_stars(a["source_metadata"]["stars"])}</span>')
        if a.get("source_type"):
            meta_parts.append(f'<span>{a["source_type"]}</span>')
        meta_html = " · ".join(meta_parts)

        cards_html += f'''
        <article class="article-card bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-lg hover:border-indigo-200 transition-all duration-300 overflow-hidden group"
                 data-category="{a.get("category", "")}" data-tags="{'|'.join(a.get("tags", []))}">
            <a href="articles/{a["_file"]}.html" class="block p-6">
                <div class="flex items-center gap-2 mb-3">
                    <span class="w-2 h-2 rounded-full {cat_color["dot"]}"></span>
                    <span class="text-xs font-medium {cat_color["text"]}">{a.get("category", "未分类")}</span>
                    <span class="text-xs text-gray-400 ml-auto">{format_date(a.get("created_at", ""))}</span>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors line-clamp-2">{a["title"]}</h3>
                <p class="text-sm text-gray-500 mb-4 line-clamp-2">{a.get("summary", "")[:100]}</p>
                <div class="flex flex-wrap gap-1.5 mb-3">{tags_html}</div>
                <div class="text-xs text-gray-400">{meta_html}</div>
            </a>
        </article>'''

    # 标签云
    tags_html = "".join(
        f'<button onclick="filterTag(\'{t}\')" class="tag-btn px-3 py-1.5 bg-white border border-gray-200 text-gray-600 rounded-lg text-sm hover:border-indigo-300 hover:text-indigo-600 transition-all" data-tag="{t}">{t}</button>'
        for t in tags[:30]
    )

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 知识库 - 技术动态追踪</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
        * {{ font-family: 'Inter', 'Noto Sans SC', sans-serif; }}
        .line-clamp-1 {{ display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }}
        .line-clamp-2 {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .cat-btn.active {{ background: #1e1b4b; color: white; }}
        .tag-btn.active {{ background: #eef2ff; color: #4f46e5; border-color: #a5b4fc; }}
        .article-card.hidden {{ display: none; }}
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="bg-white border-b border-gray-100">
        <div class="max-w-7xl mx-auto px-6 py-16 text-center">
            <div class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-full text-sm font-medium mb-6">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                AI 技术动态追踪
            </div>
            <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-4">AI 知识库</h1>
            <p class="text-lg text-gray-500 max-w-2xl mx-auto">持续采集 GitHub Trending、Hacker News 等源的 AI/LLM/Agent 领域技术动态，AI 分析后结构化存储</p>

            <!-- Search -->
            <div class="mt-8 max-w-xl mx-auto">
                <div class="relative">
                    <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    <input type="text" id="searchInput" placeholder="搜索标题、摘要、标签..."
                           class="w-full pl-12 pr-4 py-4 bg-gray-50 border border-gray-200 rounded-2xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all">
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-12">
        {stats_html}

        <!-- Filters -->
        <div class="mb-8">
            <!-- Categories -->
            <div class="flex flex-wrap gap-2 mb-4">{cat_buttons}</div>

            <!-- Tags -->
            <div class="flex flex-wrap gap-2">
                <span class="text-sm text-gray-400 self-center mr-2">标签:</span>
                {tags_html}
            </div>
        </div>

        <!-- Articles Grid -->
        <div id="articlesGrid" class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards_html}
        </div>

        <!-- Empty State -->
        <div id="emptyState" class="hidden text-center py-20">
            <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <p class="text-gray-500 text-lg">没有找到匹配的内容</p>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-100 py-8 mt-16">
        <div class="max-w-7xl mx-auto px-6 text-center text-gray-400 text-sm">
            <p>AI 知识库 · 自动化采集与分析 · {datetime.now().strftime("%Y")}</p>
        </div>
    </footer>

    <script>
        let currentCategory = 'all';
        let currentTag = '';

        function filterCategory(cat) {{
            currentCategory = cat;
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`[data-cat="${{cat}}"]`).classList.add('active');
            applyFilters();
        }}

        function filterTag(tag) {{
            if (currentTag === tag) {{
                currentTag = '';
                document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
            }} else {{
                currentTag = tag;
                document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
                document.querySelector(`[data-tag="${{tag}}"]`).classList.add('active');
            }}
            applyFilters();
        }}

        function applyFilters() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.article-card');
            let visible = 0;

            cards.forEach(card => {{
                const cat = card.dataset.category;
                const tags = card.dataset.tags.split('|');
                const text = card.textContent.toLowerCase();

                const catMatch = currentCategory === 'all' || cat === currentCategory;
                const tagMatch = !currentTag || tags.includes(currentTag);
                const searchMatch = !search || text.includes(search);

                if (catMatch && tagMatch && searchMatch) {{
                    card.classList.remove('hidden');
                    visible++;
                }} else {{
                    card.classList.add('hidden');
                }}
            }});

            document.getElementById('emptyState').classList.toggle('hidden', visible > 0);
        }}

        document.getElementById('searchInput').addEventListener('input', applyFilters);
    </script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description="生成知识库展示网站")
    parser.add_argument("--output", "-o", type=str, default=str(DEFAULT_OUTPUT), help="输出目录")
    args = parser.parse_args()

    output_dir = Path(args.output)
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    articles = load_articles()
    if not articles:
        logger.warning("没有找到知识条目")
        return

    tags = get_all_tags(articles)
    categories = get_all_categories(articles)

    # 生成主页
    index_html = generate_index_html(articles, tags, categories)
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    logger.info("主页已生成: %s", output_dir / "index.html")

    # 生成详情页
    for article in articles:
        html = generate_article_html(article, articles)
        with open(articles_dir / f"{article['_file']}.html", "w", encoding="utf-8") as f:
            f.write(html)
    logger.info("生成 %d 个详情页", len(articles))

    logger.info("完成！共 %d 个条目，%d 个分类，%d 个标签", len(articles), len(categories), len(tags))


if __name__ == "__main__":
    main()
