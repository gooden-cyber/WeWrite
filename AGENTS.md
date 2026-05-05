# AI 知识库助手项目 - Agents 文档

## 1. 项目概述

本项目是一个 AI 知识库助手，自动从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent 领域的技术动态，通过 AI 分析后结构化存储为 JSON 知识条目，并支持微信公众号等渠道分发。

## 2. 技术栈

- **编程语言**: Python 3.12+
- **AI 模型**: DeepSeek / Qwen / OpenAI / Mimo（通过 API）
- **数据采集**: httpx + GitHub API + RSS
- **数据存储**: JSON 文件
- **消息推送**: 微信公众号 API
- **网站生成**: Tailwind CSS + Alpine.js
- **定时调度**: macOS launchd / schedule 库

## 3. 编码规范

- **代码风格**: PEP 8
- **命名约定**: snake_case（变量、函数、文件），CamelCase（类）
- **文档字符串**: Google 风格 docstring（包含 Args、Returns、Raises）
- **日志记录**: 使用 `logging` 模块，禁止裸 `print()`，日志级别区分 DEBUG/INFO/WARNING/ERROR
- **类型提示**: 强制使用 Python 类型提示（type hints）
- **异常处理**: 明确捕获特定异常，避免裸 `except:`，异常信息需记录上下文
- **配置文件**: 使用 YAML 或 `.env` 文件，禁止硬编码密钥

## 4. 项目结构

```
WeWrite/
├── pipeline/                    # 核心流水线模块
│   ├── pipeline.py              # 四步流水线主程序（采集→分析→整理→保存）
│   ├── model_client.py          # LLM 统一调用客户端（4 家提供商）
│   ├── wechat_api.py            # 微信公众号 API + Markdown→HTML 渲染
│   ├── cover_generator.py       # 可插拔配图生成（5 种后端）
│   └── rss_sources.yaml         # RSS 数据源配置
├── knowledge/                   # 数据层
│   ├── articles/                # 结构化知识条目（68 个 JSON）
│   └── raw/                     # 原始采集数据
├── scripts/                     # 辅助脚本
│   ├── publish_wechat.py        # 微信公众号一键发布
│   ├── scheduler.py             # 定时任务调度器
│   └── generate_knowledge_site.py # 知识库静态网站生成器
├── hooks/                       # 质量门禁
│   ├── check_quality.py         # 5 维度质量评分
│   └── validate_json.py         # JSON Schema 校验
├── mcp_knowledge_server.py      # MCP 协议知识库服务器
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── AGENTS.md                    # 本文档
└── README.md                    # 项目说明
```

## 5. 知识条目 JSON 格式

每个知识条目存储为独立的 `.json` 文件，文件名格式为 `{uuid}.json`。

```json
{
  "id": "uuid4",
  "title": "项目/文章标题",
  "source_url": "https://...",
  "source_type": "github | rss",
  "source_metadata": {
    "stars": 1500,
    "language": "Python",
    "topics": ["llm", "agent"],
    "collected_at": "2026-05-01T07:43:57Z"
  },
  "content": "原始描述",
  "summary": "AI 生成的摘要（100-200 字）",
  "key_points": ["要点1", "要点2", "要点3"],
  "tags": ["LLM", "Agent", "Python"],
  "category": "技术动态 | 开源项目 | 行业新闻",
  "score": 8,
  "status": "analyzed",
  "analyzed": true,
  "organized": true,
  "created_at": "2026-05-01T07:53:41Z",
  "updated_at": "2026-05-01T07:53:41Z"
}
```

## 6. 流水线步骤

| 步骤 | 名称 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| Step 1 | 采集（Collect） | 从 GitHub API 和 RSS 源采集数据 | 配置的源列表 | 原始数据保存到 `knowledge/raw/` |
| Step 2 | 分析（Analyze） | 调用 LLM 生成摘要、评分、标签 | 未分析的原始数据 | 更新原始数据状态 |
| Step 3 | 整理（Organize） | 去重 + 校验 + 格式标准化 | 已分析的数据 | 标准化知识条目 |
| Step 4 | 保存（Save） | 保存到 `knowledge/articles/` | 已整理的数据 | JSON 文件 |

### 增量处理机制

- **状态标记**: 原始数据中包含 `analyzed` 和 `organized` 布尔字段
- **增量加载**: `load_raw_data()` 支持按状态过滤，只加载需要处理的数据
- **日期过滤**: 支持 `--date YYYYMMDD` 参数，只处理特定日期的数据
- **懒加载**: 支持 `limit` 参数，找到足够数据即停止

## 7. LLM 提供商

| 提供商 | 环境变量 | 默认模型 |
|--------|----------|----------|
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| Qwen | `QWEN_API_KEY` | qwen-turbo |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| Mimo | `MIMO_API_KEY` | mimo-v2.5-pro |

切换方式：设置环境变量 `LLM_PROVIDER=deepseek|qwen|openai|mimo`

## 8. 质量保障

### validate_json.py
- 校验 JSON 结构、必填字段、ID 格式（UUID）、status 枚举
- 退出码：0=全部通过，1=存在失败

### check_quality.py
- 5 维度评分（满分 100）：
  - 摘要质量 (25): 长度 + 技术关键词
  - 技术深度 (25): 基于 score 字段
  - 格式规范 (20): 必填字段完整性
  - 标签精度 (15): 1-3 个合法标签
  - 空洞词检测 (15): 不含空洞词
- 等级：A >= 80, B >= 60, C < 60

## 9. MCP 服务器

`mcp_knowledge_server.py` 实现 MCP（Model Context Protocol）协议，让 AI 工具可以直接搜索知识库。

提供的工具：
- `search_articles(keyword, limit)`: 按关键词搜索文章
- `get_article(article_id)`: 获取文章完整内容
- `knowledge_stats()`: 获取知识库统计信息

## 10. 定时调度

### 方式一：schedule 库（推荐）

```bash
python scripts/scheduler.py          # 启动调度器
python scripts/scheduler.py --test   # 测试模式（立即执行一次）
```

### 方式二：macOS launchd

```bash
# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.kailiang.ai-kb-collect.plist

# 手动触发
launchctl start com.kailiang.ai-kb-collect
```

## 11. 红线（绝对禁止的操作）

1. **禁止硬编码敏感信息**：API 密钥、Token、密码等必须通过环境变量或配置文件读取
2. **禁止裸 `print()`**：所有输出必须通过 `logging` 模块
3. **禁止直接写入文件而无异常处理**：必须使用 try/except 包裹 IO 操作
4. **禁止无限循环或未设置超时的网络请求**：所有网络操作必须设置 timeout
5. **禁止忽略证书验证**：HTTPS 请求必须验证证书
6. **禁止手动修改 `knowledge/articles/` 下的 JSON 文件**：所有修改必须通过流水线

---

*最后更新：2026-05-05*
