# WeChat Publish Skill

微信公众号一键发布技能。将知识库文章转换为微信公众号格式并发布。

## 功能

- 文章分类（GitHub 项目、工具框架、研究论文、行业新闻）
- Markdown → HTML 渲染（支持 4 种主题）
- 自动生成标题和正文
- 自检修复（敏感词、格式检查）
- 多版本生成和评分选优
- 一键发布到微信公众号

## 使用方法

```bash
# 自动选择最新文章发布
python scripts/publish_wechat.py

# 列出可发布的文章
python scripts/publish_wechat.py --list

# 指定文章 ID 发布
python scripts/publish_wechat.py --id <article-id>

# 只生成不发布（预览模式）
python scripts/publish_wechat.py --dry-run
```

## 环境变量

```bash
WECHAT_APP_ID=your-app-id
WECHAT_APP_SECRET=your-app-secret
```

## 主题

| 主题 | 名称 | 说明 |
|------|------|------|
| `default` | 简约白 | 清爽简洁，适合长文阅读 |
| `dark` | 暗夜蓝 | 深色背景，护眼阅读 |
| `tech` | 科技紫 | 渐变紫蓝，科技感强 |
| `warm` | 暖阳橙 | 温暖色调，轻松阅读 |

## 文章分类逻辑

1. **GitHub 项目** (`github_project`)：URL 包含 github.com 的项目
2. **工具框架** (`tool_framework`)：标签包含 framework/library/sdk 等
3. **研究论文** (`research_paper`)：标签包含 paper/research 等
4. **行业新闻** (`industry_news`)：其他类型

## 依赖

- `pipeline/model_client.py` - LLM 调用
- `pipeline/wechat_api.py` - 微信 API 和 HTML 渲染
