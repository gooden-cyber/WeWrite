"""可插拔的配图生成系统。

支持多种生成后端：
- matplotlib: 科学图表风格，渐变+几何装饰
- svg: 矢量图风格，清晰可缩放
- pillow: 位图风格，快速生成
- html: 网页截图风格（需要 playwright）

用法:
    from cover_generator import generate_cover
    
    # 自动生成（根据内容选择最佳后端）
    path = generate_cover(title, category, output_dir)
    
    # 指定后端
    path = generate_cover(title, category, output_dir, backend="svg")
"""

import logging
import math
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CoverBackend(ABC):
    """配图生成后端基类。"""

    @abstractmethod
    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        """生成配图。

        Args:
            title: 主标题。
            subtitle: 副标题。
            category: 内容分类。
            output_path: 输出路径。

        Returns:
            生成的图片路径，或 None。
        """
        pass


class MatplotlibBackend(CoverBackend):
    """matplotlib 后端 - 科学图表风格。"""

    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.patches as patches
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.colors import LinearSegmentedColormap

            # 配置中文字体
            font_prop = self._get_chinese_font()

            # 创建画布 (3:4 比例)
            fig, ax = plt.subplots(figsize=(9, 12), dpi=100)

            # 配色方案
            colors = self._get_colors(category)

            # 渐变背景
            self._draw_gradient(ax, colors, np, LinearSegmentedColormap)

            # 装饰元素
            self._draw_decorations(ax, title, np, plt)

            # 文字
            self._draw_text(ax, title, subtitle, font_prop, patches)

            # 设置坐标轴
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 14)
            ax.set_aspect('equal')
            ax.axis('off')

            # 保存
            plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=100)
            plt.close(fig)

            return output_path

        except Exception as e:
            logger.warning("matplotlib 生成失败: %s", e)
            return None

    def _get_chinese_font(self):
        from matplotlib import font_manager
        font_paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                return font_manager.FontProperties(fname=fp)
        return None

    def _get_colors(self, category: str) -> list:
        schemes = {
            "开源项目": ['#10B981', '#3B82F6', '#06B6D4'],
            "技术动态": ['#6366F1', '#8B5CF6', '#A855F7'],
            "行业新闻": ['#F43F5E', '#FB923C', '#FBBF24'],
            "研究论文": ['#6366F1', '#8B5CF6', '#EC4899'],
        }
        return schemes.get(category, schemes["技术动态"])

    def _draw_gradient(self, ax, colors, np, LinearSegmentedColormap):
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        gradient = np.vstack([gradient] * 256)
        cmap = LinearSegmentedColormap.from_list('custom', colors, N=256)
        ax.imshow(gradient, aspect='auto', cmap=cmap, extent=[0, 10, 0, 14])

    def _draw_decorations(self, ax, title, np, plt):
        np.random.seed(hash(title) % 2**32)

        # 圆形
        for _ in range(15):
            x, y = np.random.uniform(0, 10), np.random.uniform(0, 14)
            r = np.random.uniform(0.2, 1.2)
            ax.add_patch(plt.Circle((x, y), r, color='white', alpha=np.random.uniform(0.05, 0.2)))

        # 线条
        for _ in range(8):
            x1, y1 = np.random.uniform(0, 10), np.random.uniform(0, 14)
            angle = np.random.uniform(0, 2 * np.pi)
            length = np.random.uniform(1, 3)
            ax.plot([x1, x1 + length * np.cos(angle)], [y1, y1 + length * np.sin(angle)],
                    color='white', alpha=np.random.uniform(0.1, 0.3), linewidth=1.5)

    def _draw_text(self, ax, title, subtitle, font_prop, patches):
        # 标题背景
        ax.add_patch(patches.FancyBboxPatch((1, 5.5), 8, 3, boxstyle="round,pad=0.3",
                                            facecolor='black', alpha=0.4))

        # 标题
        kwargs = {'fontsize': 36, 'fontweight': 'bold', 'color': 'white', 'ha': 'center', 'va': 'center'}
        if font_prop:
            kwargs['fontproperties'] = font_prop
        ax.text(5, 7, title[:20], **kwargs)

        # 副标题
        kwargs = {'fontsize': 20, 'color': 'white', 'alpha': 0.9, 'ha': 'center', 'va': 'center'}
        if font_prop:
            kwargs['fontproperties'] = font_prop
        ax.text(5, 5.8, subtitle, **kwargs)


class SvgBackend(CoverBackend):
    """SVG 后端 - 矢量图风格。"""

    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        try:
            # 配色方案
            colors = self._get_colors(category)

            # 生成 SVG 内容
            svg = self._build_svg(title, subtitle, category, colors)

            # 保存为 SVG
            svg_path = output_path.with_suffix('.svg')
            svg_path.write_text(svg, encoding='utf-8')

            # 如果需要 PNG，转换
            if output_path.suffix == '.png':
                self._convert_to_png(svg_path, output_path)
                return output_path

            return svg_path

        except Exception as e:
            logger.warning("SVG 生成失败: %s", e)
            return None

    def _get_colors(self, category: str) -> dict:
        schemes = {
            "开源项目": {"primary": "#10B981", "secondary": "#3B82F6", "accent": "#06B6D4"},
            "技术动态": {"primary": "#6366F1", "secondary": "#8B5CF6", "accent": "#A855F7"},
            "行业新闻": {"primary": "#F43F5E", "secondary": "#FB923C", "accent": "#FBBF24"},
            "研究论文": {"primary": "#6366F1", "secondary": "#8B5CF6", "accent": "#EC4899"},
        }
        return schemes.get(category, schemes["技术动态"])

    def _build_svg(self, title: str, subtitle: str, category: str, colors: dict) -> str:
        # 基于标题的伪随机
        seed = hash(title) % 2**32
        random.seed(seed)

        # 清理标题
        clean_title = "".join(c for c in title if ord(c) < 0x1F600 or ord(c) > 0x1F9FF).strip()[:20]

        # 装饰元素
        decorations = []
        for _ in range(15):
            x, y = random.uniform(0, 900), random.uniform(0, 1200)
            r = random.uniform(20, 120)
            opacity = random.uniform(0.05, 0.2)
            decorations.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" opacity="{opacity}"/>')

        for _ in range(8):
            x1, y1 = random.uniform(0, 900), random.uniform(0, 1200)
            angle = random.uniform(0, 2 * math.pi)
            length = random.uniform(100, 300)
            x2, y2 = x1 + length * math.cos(angle), y1 + length * math.sin(angle)
            opacity = random.uniform(0.1, 0.3)
            decorations.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="white" opacity="{opacity}" stroke-width="2"/>')

        # 网格点
        grid_points = []
        for x in range(50, 900, 150):
            for y in range(50, 1200, 150):
                if random.random() > 0.6:
                    grid_points.append(f'<circle cx="{x}" cy="{y}" r="3" fill="white" opacity="0.15"/>')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1200" width="900" height="1200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{colors['primary']};stop-opacity:1"/>
      <stop offset="50%" style="stop-color:{colors['secondary']};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{colors['accent']};stop-opacity:1"/>
    </linearGradient>
  </defs>

  <!-- 背景 -->
  <rect width="900" height="1200" fill="url(#bg)"/>

  <!-- 装饰元素 -->
  {"".join(decorations)}
  {"".join(grid_points)}

  <!-- 标题背景 -->
  <rect x="50" y="420" width="800" height="250" rx="20" fill="black" opacity="0.4"/>

  <!-- 标题 -->
  <text x="450" y="540" text-anchor="middle" font-family="PingFang SC, sans-serif" font-size="48" font-weight="bold" fill="white">{clean_title}</text>

  <!-- 副标题 -->
  <text x="450" y="620" text-anchor="middle" font-family="PingFang SC, sans-serif" font-size="28" fill="white" opacity="0.9">{subtitle}</text>

  <!-- 底部装饰线 -->
  <line x1="200" y1="950" x2="700" y2="950" stroke="white" stroke-width="3" opacity="0.6"/>
</svg>'''

    def _convert_to_png(self, svg_path: Path, png_path: Path):
        """SVG 转 PNG（需要 cairosvg 或 rsvg-convert）。"""
        try:
            import cairosvg
            cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=100)
        except ImportError:
            # 尝试使用 rsvg-convert
            import subprocess
            subprocess.run(['rsvg-convert', '-o', str(png_path), str(svg_path)], check=True)


class PillowBackend(CoverBackend):
    """Pillow 后端 - 位图风格（快速）。"""

    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        try:
            import random

            from PIL import Image, ImageDraw, ImageFont

            width, height = 900, 1200
            colors = self._get_colors(category)

            # 创建渐变
            img = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(img)

            color1, color2 = random.choice(colors)
            for y in range(height):
                r = int(color1[0] + (color2[0] - color1[0]) * y / height)
                g = int(color1[1] + (color2[1] - color1[1]) * y / height)
                b = int(color1[2] + (color2[2] - color1[2]) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # 装饰
            for _ in range(10):
                x, y = random.randint(0, width), random.randint(0, height)
                r = random.randint(20, 80)
                draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, random.randint(15, 40)))

            # 标题
            clean_title = "".join(c for c in title if ord(c) < 0x1F600 or ord(c) > 0x1F9FF).strip()[:20]
            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 48)
            except OSError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), clean_title, font=font)
            text_w = bbox[2] - bbox[0]
            x = (width - text_w) // 2
            y = height // 2 - 50

            draw.rounded_rectangle([x-20, y-20, x+text_w+20, y+70], radius=12, fill=(0, 0, 0, 100))
            draw.text((x, y), clean_title, fill=(255, 255, 255), font=font)

            # 副标题
            try:
                font_small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 28)
            except OSError:
                font_small = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), subtitle, font=font_small)
            sub_w = bbox[2] - bbox[0]
            draw.text(((width - sub_w) // 2, y + 80), subtitle, fill=(255, 255, 255, 200), font=font_small)

            img.save(output_path, "PNG", quality=95)
            return output_path

        except Exception as e:
            logger.warning("Pillow 生成失败: %s", e)
            return None

    def _get_colors(self, category: str) -> list:
        schemes = {
            "开源项目": [((16, 185, 129), (59, 130, 246))],
            "技术动态": [((99, 102, 241), (139, 92, 246))],
            "行业新闻": [((244, 63, 94), (251, 146, 60))],
            "研究论文": [((99, 102, 241), (236, 72, 153))],
        }
        return schemes.get(category, schemes["技术动态"])


class HtmlBackend(CoverBackend):
    """HTML/CSS 截图后端 - 网页风格（需要 playwright）。"""

    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright 未安装，跳过 HTML 后端")
            return None

        try:
            colors = self._get_colors(category)
            clean_title = "".join(c for c in title if ord(c) < 0x1F600 or ord(c) > 0x1F9FF).strip()[:20]

            html = f'''<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 900px; height: 1200px;
    background: linear-gradient(135deg, {colors[0]}, {colors[1]}, {colors[2]});
    display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, PingFang SC, sans-serif;
    overflow: hidden; position: relative;
  }}
  .decoration {{
    position: absolute; border-radius: 50%; background: rgba(255,255,255,0.1);
  }}
  .title-box {{
    background: rgba(0,0,0,0.4); border-radius: 20px;
    padding: 40px 60px; text-align: center;
  }}
  h1 {{ color: white; font-size: 48px; font-weight: bold; margin-bottom: 20px; }}
  p {{ color: rgba(255,255,255,0.9); font-size: 28px; }}
</style>
</head>
<body>
  <div class="decoration" style="width:200px;height:200px;top:50px;left:50px;"></div>
  <div class="decoration" style="width:150px;height:150px;bottom:100px;right:80px;"></div>
  <div class="decoration" style="width:100px;height:100px;top:300px;right:200px;"></div>
  <div class="title-box">
    <h1>{clean_title}</h1>
    <p>{subtitle}</p>
  </div>
</body>
</html>'''

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 900, "height": 1200})
                page.set_content(html)
                page.screenshot(path=str(output_path))
                browser.close()

            return output_path

        except Exception as e:
            logger.warning("HTML 截图失败: %s", e)
            return None

    def _get_colors(self, category: str) -> list:
        schemes = {
            "开源项目": ["#10B981", "#3B82F6", "#06B6D4"],
            "技术动态": ["#6366F1", "#8B5CF6", "#A855F7"],
            "行业新闻": ["#F43F5E", "#FB923C", "#FBBF24"],
            "研究论文": ["#6366F1", "#8B5CF6", "#EC4899"],
        }
        return schemes.get(category, schemes["技术动态"])


# 后端注册表
class PollinationsBackend(CoverBackend):
    """Pollinations.ai 后端 - AI 生成图片（免费）。"""

    def generate(self, title: str, subtitle: str, category: str, output_path: Path) -> Path | None:
        try:
            from urllib.parse import quote

            import httpx

            # 根据标题和分类生成 prompt
            prompt = self._build_prompt(title, subtitle, category)
            encoded = quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=900&height=383&nologo=true"

            for attempt in range(2):
                try:
                    with httpx.Client(timeout=60) as client:
                        resp = client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            output_path.write_bytes(resp.content)
                            return output_path
                except Exception as e:
                    logger.warning("Pollinations 请求失败 (%d): %s", attempt + 1, e)
                    if attempt == 0:
                        import time
                        time.sleep(2)
            return None

        except Exception as e:
            logger.warning("Pollinations 后端失败: %s", e)
            return None

    def _build_prompt(self, title: str, subtitle: str, category: str) -> str:
        """根据内容生成图片 prompt。"""
        # 提取关键词
        keywords = title.lower()
        for word in ["the", "a", "an", "is", "are", "and", "or", "of", "in", "on"]:
            keywords = keywords.replace(f" {word} ", " ")

        return (
            f"abstract tech background, {keywords}, "
            "blue purple gradient, modern minimal design, "
            "circuit patterns, code elements, clean composition, "
            "no text, no watermark"
        )


BACKENDS = {
    "matplotlib": MatplotlibBackend,
    "svg": SvgBackend,
    "pillow": PillowBackend,
    "html": HtmlBackend,
    "pollinations": PollinationsBackend,
}


def generate_cover(
    title: str,
    category: str = "",
    output_dir: Path | None = None,
    backend: str | None = None,
    filename: str | None = None,
) -> Path | None:
    """生成配图（主入口函数）。

    Args:
        title: 文章标题。
        category: 内容分类。
        output_dir: 输出目录。
        backend: 指定后端（matplotlib/svg/pillow/html），None 为自动选择。
        filename: 指定文件名，None 为自动生成。

    Returns:
        生成的图片路径，或 None。
    """
    if output_dir is None:
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 副标题
    subtitles = {
        "开源项目": "开源项目推荐",
        "技术动态": "技术趋势解读",
        "行业新闻": "行业资讯速递",
        "研究论文": "前沿研究解读",
    }
    subtitle = subtitles.get(category, "AI 技术趋势")

    # 生成文件名
    if filename is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_{date_str}.png"

    output_path = output_dir / filename

    # 选择后端
    if backend is None:
        # 自动选择：优先 matplotlib，其次 svg，最后 pillow
        for name in ["matplotlib", "svg", "pillow"]:
            if name in BACKENDS:
                backend = name
                break

    if backend not in BACKENDS:
        logger.error("未知后端: %s，可选: %s", backend, list(BACKENDS.keys()))
        return None

    # 生成
    logger.info("使用 %s 后端生成配图", backend)
    backend_instance = BACKENDS[backend]()
    result = backend_instance.generate(title, subtitle, category, output_path)

    if result:
        logger.info("配图已生成: %s", result)
    else:
        logger.warning("配图生成失败")

    return result


if __name__ == "__main__":
    # 测试所有后端
    logging.basicConfig(level=logging.INFO)
    test_title = "测试标题：AI 技术趋势"
    test_dir = Path("test_covers")
    test_dir.mkdir(exist_ok=True)

    for name in BACKENDS:
        print(f"\n测试 {name} 后端...")
        result = generate_cover(test_title, "技术动态", test_dir, backend=name, filename=f"test_{name}.png")
        if result:
            print(f"  成功: {result}")
        else:
            print("  失败")
