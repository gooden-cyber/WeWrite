"""微信公众号 API 封装 + HTML 渲染。

提供：
- WeChatClient: 微信 API 客户端
- render_markdown: 主题化 Markdown → HTML
- THEMES: 内置主题字典

环境变量：WECHAT_APP_ID, WECHAT_APP_SECRET
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"


# ============================================================
# 主题系统
# ============================================================

THEMES = {
    "default": {
        "name": "简约白",
        "desc": "清爽简洁，适合长文阅读",
        "body": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:16px;line-height:1.8;color:#333;padding:10px;",
        "h1": "font-size:24px;font-weight:bold;margin:30px 0 15px;color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;",
        "h2": "font-size:20px;font-weight:bold;margin:25px 0 12px;color:#1a1a1a;",
        "h3": "font-size:17px;font-weight:bold;margin:20px 0 10px;color:#333;",
        "p": "font-size:16px;line-height:1.8;color:#333;margin:12px 0;",
        "strong": "color:#1a1a1a;font-weight:600;",
        "em": "color:#555;font-style:italic;",
        "a": "color:#576b95;text-decoration:none;border-bottom:1px solid #576b95;",
        "blockquote": "border-left:4px solid #42b983;background:#f8f8f8;padding:12px 16px;margin:15px 0;color:#666;font-size:15px;",
        "code_inline": "background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:14px;color:#e96900;font-family:Consolas,Monaco,monospace;",
        "code_block": "background:#f6f8fa;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:15px 0;font-family:Consolas,Monaco,monospace;color:#333;",
        "code_keyword": "color:#d73a49;",
        "code_string": "color:#032f62;",
        "code_comment": "color:#6a737d;",
        "ul": "padding-left:20px;margin:10px 0;",
        "ol": "padding-left:20px;margin:10px 0;",
        "li": "margin:6px 0;line-height:1.7;",
        "hr": "border:none;border-top:1px solid #eee;margin:25px 0;",
        "table": "border-collapse:collapse;width:100%;margin:15px 0;font-size:14px;",
        "th": "background:#f6f8fa;border:1px solid #ddd;padding:10px 12px;text-align:left;font-weight:600;",
        "td": "border:1px solid #ddd;padding:8px 12px;",
        "img": "max-width:100%;height:auto;display:block;margin:15px auto;border-radius:4px;",
        "caption": "text-align:center;font-size:13px;color:#999;margin-top:6px;",
        "footer": "margin-top:30px;padding-top:20px;border-top:1px solid #eee;font-size:14px;color:#999;text-align:center;",
    },
    "dark": {
        "name": "暗夜蓝",
        "desc": "深色背景，护眼阅读",
        "body": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:16px;line-height:1.8;color:#d4d4d4;padding:10px;background:#1e1e1e;",
        "h1": "font-size:24px;font-weight:bold;margin:30px 0 15px;color:#fff;border-bottom:2px solid #333;padding-bottom:8px;",
        "h2": "font-size:20px;font-weight:bold;margin:25px 0 12px;color:#fff;",
        "h3": "font-size:17px;font-weight:bold;margin:20px 0 10px;color:#e0e0e0;",
        "p": "font-size:16px;line-height:1.8;color:#d4d4d4;margin:12px 0;",
        "strong": "color:#fff;font-weight:600;",
        "em": "color:#aaa;font-style:italic;",
        "a": "color:#6cb6ff;text-decoration:none;border-bottom:1px solid #6cb6ff;",
        "blockquote": "border-left:4px solid #42b983;background:#2d2d2d;padding:12px 16px;margin:15px 0;color:#aaa;font-size:15px;",
        "code_inline": "background:#2d2d2d;padding:2px 6px;border-radius:4px;font-size:14px;color:#f97583;font-family:Consolas,Monaco,monospace;",
        "code_block": "background:#2d2d2d;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:15px 0;font-family:Consolas,Monaco,monospace;color:#d4d4d4;",
        "code_keyword": "color:#f97583;",
        "code_string": "color:#9ecbff;",
        "code_comment": "color:#6a737d;",
        "ul": "padding-left:20px;margin:10px 0;",
        "ol": "padding-left:20px;margin:10px 0;",
        "li": "margin:6px 0;line-height:1.7;",
        "hr": "border:none;border-top:1px solid #333;margin:25px 0;",
        "table": "border-collapse:collapse;width:100%;margin:15px 0;font-size:14px;",
        "th": "background:#2d2d2d;border:1px solid #444;padding:10px 12px;text-align:left;font-weight:600;color:#fff;",
        "td": "border:1px solid #444;padding:8px 12px;color:#d4d4d4;",
        "img": "max-width:100%;height:auto;display:block;margin:15px auto;border-radius:4px;",
        "caption": "text-align:center;font-size:13px;color:#666;margin-top:6px;",
        "footer": "margin-top:30px;padding-top:20px;border-top:1px solid #333;font-size:14px;color:#666;text-align:center;",
    },
    "tech": {
        "name": "科技紫",
        "desc": "渐变紫蓝，科技感强",
        "body": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:16px;line-height:1.8;color:#2c3e50;padding:10px;",
        "h1": "font-size:24px;font-weight:bold;margin:30px 0 15px;color:#6c5ce7;border-bottom:2px solid #6c5ce7;padding-bottom:8px;",
        "h2": "font-size:20px;font-weight:bold;margin:25px 0 12px;color:#6c5ce7;",
        "h3": "font-size:17px;font-weight:bold;margin:20px 0 10px;color:#a29bfe;",
        "p": "font-size:16px;line-height:1.8;color:#2c3e50;margin:12px 0;",
        "strong": "color:#2d3436;font-weight:600;",
        "em": "color:#636e72;font-style:italic;",
        "a": "color:#6c5ce7;text-decoration:none;border-bottom:1px solid #6c5ce7;",
        "blockquote": "border-left:4px solid #6c5ce7;background:#f8f7ff;padding:12px 16px;margin:15px 0;color:#636e72;font-size:15px;",
        "code_inline": "background:#f0edff;padding:2px 6px;border-radius:4px;font-size:14px;color:#e84393;font-family:Consolas,Monaco,monospace;",
        "code_block": "background:#f6f8fa;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:15px 0;font-family:Consolas,Monaco,monospace;border-left:3px solid #6c5ce7;",
        "code_keyword": "color:#e84393;",
        "code_string": "color:#00b894;",
        "code_comment": "color:#b2bec3;",
        "ul": "padding-left:20px;margin:10px 0;",
        "ol": "padding-left:20px;margin:10px 0;",
        "li": "margin:6px 0;line-height:1.7;",
        "hr": "border:none;border-top:1px solid #dfe6e9;margin:25px 0;",
        "table": "border-collapse:collapse;width:100%;margin:15px 0;font-size:14px;",
        "th": "background:#f0edff;border:1px solid #ddd;padding:10px 12px;text-align:left;font-weight:600;color:#6c5ce7;",
        "td": "border:1px solid #ddd;padding:8px 12px;",
        "img": "max-width:100%;height:auto;display:block;margin:15px auto;border-radius:4px;",
        "caption": "text-align:center;font-size:13px;color:#999;margin-top:6px;",
        "footer": "margin-top:30px;padding-top:20px;border-top:1px solid #dfe6e9;font-size:14px;color:#999;text-align:center;",
    },
    "warm": {
        "name": "暖阳橙",
        "desc": "温暖色调，轻松阅读",
        "body": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:16px;line-height:1.8;color:#3d3d3d;padding:10px;",
        "h1": "font-size:24px;font-weight:bold;margin:30px 0 15px;color:#e17055;border-bottom:2px solid #fab1a0;padding-bottom:8px;",
        "h2": "font-size:20px;font-weight:bold;margin:25px 0 12px;color:#e17055;",
        "h3": "font-size:17px;font-weight:bold;margin:20px 0 10px;color:#fab1a0;",
        "p": "font-size:16px;line-height:1.8;color:#3d3d3d;margin:12px 0;",
        "strong": "color:#2d3436;font-weight:600;",
        "em": "color:#636e72;font-style:italic;",
        "a": "color:#e17055;text-decoration:none;border-bottom:1px solid #e17055;",
        "blockquote": "border-left:4px solid #fab1a0;background:#fff5f3;padding:12px 16px;margin:15px 0;color:#636e72;font-size:15px;",
        "code_inline": "background:#fff5f3;padding:2px 6px;border-radius:4px;font-size:14px;color:#d63031;font-family:Consolas,Monaco,monospace;",
        "code_block": "background:#fff5f3;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:15px 0;font-family:Consolas,Monaco,monospace;color:#3d3d3d;",
        "code_keyword": "color:#d63031;",
        "code_string": "color:#00b894;",
        "code_comment": "color:#b2bec3;",
        "ul": "padding-left:20px;margin:10px 0;",
        "ol": "padding-left:20px;margin:10px 0;",
        "li": "margin:6px 0;line-height:1.7;",
        "hr": "border:none;border-top:1px solid #fab1a0;margin:25px 0;",
        "table": "border-collapse:collapse;width:100%;margin:15px 0;font-size:14px;",
        "th": "background:#fff5f3;border:1px solid #fab1a0;padding:10px 12px;text-align:left;font-weight:600;color:#e17055;",
        "td": "border:1px solid #fab1a0;padding:8px 12px;",
        "img": "max-width:100%;height:auto;display:block;margin:15px auto;border-radius:4px;",
        "caption": "text-align:center;font-size:13px;color:#999;margin-top:6px;",
        "footer": "margin-top:30px;padding-top:20px;border-top:1px solid #fab1a0;font-size:14px;color:#999;text-align:center;",
    },
}


# ============================================================
# WeChat API 客户端
# ============================================================

class WeChatClient:
    """微信公众号 API 客户端。"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def get_access_token(self) -> str:
        """获取 access_token（自动缓存和刷新）。"""
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{WECHAT_API_BASE}/token", params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            })
            resp.raise_for_status()
            data = resp.json()

        if "errcode" in data:
            raise Exception(f"获取 access_token 失败: {data}")

        self._access_token = data["access_token"]
        self._token_expires_at = now + data.get("expires_in", 7200) - 300
        return self._access_token

    def upload_thumb(self, image_path: Path) -> str:
        """上传封面图片，返回 media_id。"""
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            files = {"media": (image_path.name, f, "image/png")}
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{WECHAT_API_BASE}/material/add_material",
                    params={"access_token": token, "type": "thumb"},
                    files=files,
                )
                resp.raise_for_status()
                data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"上传封面失败: {data}")
        return data["media_id"]

    def upload_image(self, image_path: Path) -> str:
        """上传正文图片，返回 url。"""
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            files = {"media": (image_path.name, f, "image/png")}
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{WECHAT_API_BASE}/media/uploadimg",
                    params={"access_token": token},
                    files=files,
                )
                resp.raise_for_status()
                data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"上传图片失败: {data}")
        return data["url"]

    def create_draft(self, title: str, content: str, thumb_media_id: str,
                     author: str = "", digest: str = "") -> str:
        """创建草稿，返回 media_id。"""
        token = self.get_access_token()
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{WECHAT_API_BASE}/draft/add",
                params={"access_token": token},
                json={"articles": [{
                    "title": title,
                    "author": author,
                    "content": content,
                    "thumb_media_id": thumb_media_id,
                    "digest": digest,
                    "content_source_url": "",
                    "need_open_comment": 1,
                    "only_fans_can_comment": 0,
                }]},
            )
            resp.raise_for_status()
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"创建草稿失败: {data}")
        return data["media_id"]


# ============================================================
# Markdown → HTML 渲染（主题化）
# ============================================================

def _highlight_code(code: str, lang: str, theme: dict) -> str:
    """简单代码高亮。"""
    # 转义 HTML
    code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 注释高亮
    comment_patterns = [
        (r'(#.*?)$', theme.get("code_comment", "color:#6a737d;")),
        (r'(//.*?)$', theme.get("code_comment", "color:#6a737d;")),
        (r'(/\*.*?\*/)', theme.get("code_comment", "color:#6a737d;")),
    ]
    for pattern, style in comment_patterns:
        code = re.sub(pattern, f'<span style="{style}">\\1</span>', code, flags=re.MULTILINE)

    # 字符串高亮
    code = re.sub(r'(&quot;.*?&quot;|&#39;.*?&#39;|\".*?\"|\'.*?\')',
                  f'<span style="{theme.get("code_string", "color:#032f62;")}">\\1</span>', code)

    # 关键词高亮
    keywords = (r'\b(def|class|import|from|return|if|else|elif|for|while|try|except|'
                r'finally|with|as|in|not|and|or|is|None|True|False|self|lambda|'
                r'async|await|yield|break|continue|pass|raise|del|global|nonlocal|'
                r'function|const|let|var|new|this|typeof|instanceof|void|'
                r'public|private|protected|static|final|abstract|interface|extends|implements|'
                r'fn|let|mut|pub|use|mod|struct|enum|impl|trait|match|loop|where)\b')
    code = re.sub(keywords, f'<span style="{theme.get("code_keyword", "color:#d73a49;")}">\\1</span>', code)

    return code


def render_markdown(md: str, theme_name: str = "default", footer_text: str = "") -> str:
    """Markdown 转微信公众号 HTML（主题化）。

    Args:
        md: Markdown 内容。
        theme_name: 主题名称（default/dark/tech/warm）。
        footer_text: 文末引导语（可选）。

    Returns:
        HTML 内容。
    """
    theme = THEMES.get(theme_name, THEMES["default"])
    html = md

    # 1. 先处理代码块（避免内部被其他规则影响）
    code_blocks = []
    def save_code_block(m):
        lang = m.group(1) or ""
        code = m.group(2).strip()
        highlighted = _highlight_code(code, lang, theme)
        placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
        code_blocks.append(f'<pre style="{theme["code_block"]}"><code>{highlighted}</code></pre>')
        return placeholder

    html = re.sub(r'```(\w*)\n(.*?)```', save_code_block, html, flags=re.DOTALL)

    # 2. 标题（h1 → h3 顺序不能变）
    html = re.sub(r'^### (.+)$', f'<h3 style="{theme["h3"]}">\\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', f'<h2 style="{theme["h2"]}">\\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', f'<h1 style="{theme["h1"]}">\\1</h1>', html, flags=re.MULTILINE)

    # 3. 引用块
    html = re.sub(r'^> (.+)$', f'<blockquote style="{theme["blockquote"]}">\\1</blockquote>', html, flags=re.MULTILINE)

    # 4. 表格
    def render_table(m):
        rows = [r.strip() for r in m.group(0).strip().split("\n") if r.strip()]
        if len(rows) < 2:
            return m.group(0)

        # 解析表头
        headers = [c.strip() for c in rows[0].split("|") if c.strip()]
        # 跳过分隔行
        body_rows = rows[2:] if len(rows) > 2 else []

        table_html = f'<table style="{theme["table"]}">'
        table_html += "<thead><tr>"
        for h in headers:
            table_html += f'<th style="{theme["th"]}">{h}</th>'
        table_html += "</tr></thead><tbody>"
        for row in body_rows:
            cells = [c.strip() for c in row.split("|") if c.strip()]
            table_html += "<tr>"
            for cell in cells:
                table_html += f'<td style="{theme["td"]}">{cell}</td>'
            table_html += "</tr>"
        table_html += "</tbody></table>"
        return table_html

    html = re.sub(r'^\|.+\|$\n^\|[-| :]+\|$\n(?:^\|.+\|$\n?)+', render_table, html, flags=re.MULTILINE)

    # 5. 分割线
    html = re.sub(r'^---+$', f'<hr style="{theme["hr"]}">', html, flags=re.MULTILINE)

    # 6. 图片（带说明文字）
    html = re.sub(r'!\[(.*?)\]\((.*?)\)',
                  f'<img src="\\2" alt="\\1" style="{theme["img"]}"><p style="{theme["caption"]}">\\1</p>', html)

    # 7. 链接
    html = re.sub(r'\[(.+?)\]\((.+?)\)',
                  f'<a href="\\2" style="{theme["a"]}">\\1</a>', html)

    # 8. 粗体、斜体
    html = re.sub(r'\*\*(.+?)\*\*', f'<strong style="{theme["strong"]}">\\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', f'<em style="{theme["em"]}">\\1</em>', html)

    # 9. 有序列表
    html = re.sub(r'^(\d+)\. (.+)$', f'<li style="{theme["li"]}">\\2</li>', html, flags=re.MULTILINE)

    # 10. 无序列表
    html = re.sub(r'^[-*] (.+)$', f'<li style="{theme["li"]}">\\1</li>', html, flags=re.MULTILINE)

    # 11. 行内代码
    html = re.sub(r'`(.+?)`', f'<code style="{theme["code_inline"]}">\\1</code>', html)

    # 12. 段落（连续换行）
    html = re.sub(r'\n\n', '</p><p style="{theme["p"]}">', html)

    # 13. 恢复代码块
    for i, block in enumerate(code_blocks):
        html = html.replace(f"__CODE_BLOCK_{i}__", block)

    # 14. 包装
    html = f'<div style="{theme["body"]}">\n<p style="{theme["p"]}">{html}</p>\n</div>'

    # 15. 文末引导语
    if footer_text:
        html += f'\n<div style="{theme["footer"]}">{footer_text}</div>'

    return html


# ============================================================
# 兼容旧接口
# ============================================================

def markdown_to_html(md: str) -> str:
    """兼容旧接口，默认使用简约白主题。"""
    return render_markdown(md, theme_name="default")
