# WeWrite - AI 知识库助手

<p align="center">
  <strong>自动化采集 · AI 智能分析 · 结构化存储 · 多渠道分发</strong>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#使用指南">使用指南</a> •
  <a href="#部署">部署</a>
</p>

---

## 简介

WeWrite 是一个端到端的 AI 知识库助手，自动从 GitHub Trending、Hacker News 等源采集 AI/LLM/Agent 领域的最新内容，通过大模型进行智能分析，生成结构化的知识条目，并支持微信公众号等渠道分发。

**核心价值**：让你专注于阅读高质量的 AI 技术内容，而不是花时间筛选信息。

## 功能特性

| 功能                 | 说明                                                |
| -------------------- | --------------------------------------------------- |
| **智能采集**   | 支持 GitHub Search API、RSS 源，自动去重            |
| **AI 分析**    | 调用 DeepSeek/Qwen 生成摘要、提取要点、自动分类打标 |
| **结构化存储** | 每篇文章独立 JSON，包含标题/摘要/要点/标签/评分     |
| **知识展示**   | 静态网站生成，支持搜索、筛选、详情查看              |
| **定时任务**   | macOS launchd 自动调度，每日采集、每周分析          |
| **多渠道分发** | 支持微信公众号发布                                  |

## 快速开始

### 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/gooden-cyber/WeWrite.git
cd WeWrite

# 设置 API 密钥（选择一种方式）
# 方式1：设置系统环境变量
export MIMO_API_KEY=your-mimo-api-key
# 或
export DEEPSEEK_API_KEY=your-deepseek-key

# 方式2：创建 .env 文件
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 启动
./start.sh          # 运行一次流水线
./start.sh web      # 启动 Web UI
```

### 手动安装（可选）

如果你想使用虚拟环境隔离依赖：

```bash
# 创建虚拟环境并安装依赖
./start.sh install

# 然后正常启动
./start.sh web
```

### 环境变量

| 变量                  | 必需 | 说明                          |
| --------------------- | ---- | ----------------------------- |
| `MIMO_API_KEY`      | 是   | Mimo API 密钥（默认使用）     |
| `DEEPSEEK_API_KEY`  | 否   | DeepSeek API 密钥             |
| `QWEN_API_KEY`      | 否   | Qwen API 密钥                 |
| `OPENAI_API_KEY`    | 否   | OpenAI API 密钥               |
| `GITHUB_TOKEN`      | 否   | GitHub Token（提高 API 限额） |
| `WECHAT_APP_ID`     | 否   | 微信公众号 AppID              |
| `WECHAT_APP_SECRET` | 否   | 微信公众号 AppSecret          |

**说明**：至少需要设置一个 LLM API 密钥（Mimo/DeepSeek/Qwen/OpenAI）

### 运行

```bash
# 方式一：使用启动脚本（推荐）
./start.sh              # 运行一次流水线（采集→分析→整理→保存）
./start.sh web          # 启动 Web UI
./start.sh schedule     # 启动定时调度（每天自动运行）
./start.sh test         # 测试模式（立即执行一次）

# 方式二：直接运行
python pipeline/pipeline.py
python scripts/scheduler.py
python web/app.py
```

**说明**：

- `start.sh` 会自动检测 Python 环境（虚拟环境或系统 Python）
- 如果缺少依赖，会自动安装
- 无需手动创建 `.env` 文件，会自动读取系统环境变量

### Web UI

启动 Web 服务后，访问 http://localhost:8000

```bash
./start.sh web
```

功能：

- 📚 **知识库浏览**：文章列表、搜索、筛选
- 📝 **文章详情**：摘要、要点、标签、评分
- 🚀 **发布文章**：选择文章 → 预览 → 确认发布
- ⚙️ **管理后台**：系统状态、触发 Pipeline
- 🔗 **RESTful API**：完整的 API 接口

**发布流程**：

1. 访问 `/publish` 页面
2. 选择要发布的文章（支持按评分、时间排序）
3. 预览文章内容、封面图和微信效果
4. 选择主题风格
5. 确认发布

### 命令行参数

```bash
# 完整流水线（采集 → 分析 → 整理 → 保存）
python pipeline/pipeline.py

# 仅采集
python pipeline/pipeline.py --step 1

# 仅分析（需要 API Key）
python pipeline/pipeline.py --step 2 --step 3 --step 4

# 按日期处理（只处理特定日期的数据）
python pipeline/pipeline.py --date 20260501

# 预览模式（不实际保存）
python pipeline/pipeline.py --dry-run
```

## 项目架构

```
WeWrite/
├── pipeline/                    # 核心流水线
│   ├── pipeline.py              # 四步流水线主程序
│   ├── model_client.py          # LLM 调用客户端
│   ├── wechat_api.py            # 微信公众号 API
│   ├── cover_generator.py       # 配图生成器
│   └── rss_sources.yaml         # RSS 源配置
├── web/                         # Web UI
│   ├── app.py                   # FastAPI 服务
│   ├── templates/               # HTML 模板
│   └── static/                  # 静态资源
├── knowledge/                   # 数据层
│   ├── raw/                     # 原始采集数据
│   └── articles/                # 结构化知识条目
├── scripts/                     # 辅助脚本
│   ├── publish_wechat.py        # 微信公众号发布
│   ├── scheduler.py             # 定时任务调度器
│   └── generate_knowledge_site.py
├── hooks/                       # 质量门禁
│   ├── check_quality.py         # 质量评分
│   └── validate_json.py         # JSON 校验
├── tests/                       # 单元测试
├── .opencode/skills/            # 项目级 Skill
├── mcp_knowledge_server.py      # MCP 协议服务器
├── install.sh                   # 一键安装脚本
├── start.sh                     # 启动脚本
├── requirements.txt             # Python 依赖
├── pyproject.toml               # 项目配置
├── .env.example                 # 环境变量模板
├── AGENTS.md                    # 项目规范
├── CONTRIBUTING.md              # 贡献指南
├── CHANGELOG.md                 # 更新日志
└── README.md                    # 项目说明
```

### 工作流

```
自动部分（scheduler 每天 08:00）：

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   采集器    │ ──▶ │   分析器    │ ──▶ │   整理器    │ ──▶ │   存储      │
│  Collector  │     │  Analyzer   │     │  Organizer  │     │    Save     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
 GitHub API           DeepSeek            去重校验           JSON 文件
 RSS 源               Qwen API           格式标准化        knowledge/

手动部分（用户通过 Web UI）：

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   选择文章  │ ──▶ │   预览内容  │ ──▶ │   选择主题  │ ──▶ │   确认发布  │
│  /publish   │     │   原文+微信 │     │   4种风格   │     │  微信公众号 │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## 知识条目格式

```json
{
  "id": "uuid",
  "title": "项目/文章标题",
  "source_url": "https://...",
  "source_type": "github | rss",
  "summary": "AI 生成的摘要",
  "key_points": ["要点1", "要点2", "要点3"],
  "tags": ["LLM", "Agent", "Python"],
  "category": "开源项目 | 技术动态 | 行业新闻",
  "score": 8,
  "status": "analyzed"
}
```

## 使用指南

### 生成知识库网站

```bash
python scripts/generate_knowledge_site.py
# 输出: site/knowledge/
# 浏览器打开: site/knowledge/index.html
```

### 定时任务（macOS）

```bash
# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.kailiang.ai-kb-collect.plist
launchctl load ~/Library/LaunchAgents/com.kailiang.ai-kb-analyze.plist

# 查看状态
launchctl list | grep kailiang

# 手动触发
launchctl start com.kailiang.ai-kb-collect
```

### 查看日志

```bash
# 采集日志
tail -f logs/collect.log

# 分析日志
tail -f logs/analyze.log
```

## 配置说明

### RSS 源配置

编辑 `pipeline/rss_sources.yaml`：

```yaml
sources:
  - name: "Hacker News"
    url: "https://hnrss.org/newest?q=AI+OR+LLM+OR+agent"
    limit: 20
  - name: "AI News"
    url: "https://example.com/rss"
    limit: 10
```

### 分类定义

| 分类     | 说明                        |
| -------- | --------------------------- |
| 开源项目 | GitHub 上的 AI 相关开源项目 |
| 技术动态 | 技术文章、教程、最佳实践    |
| 行业新闻 | AI 行业新闻、产品发布、观点 |

## 技术栈

- **语言**: Python 3.12+
- **AI 模型**: DeepSeek / Qwen / OpenAI / Mimo（通过 API）
- **数据采集**: httpx + GitHub API + RSS
- **数据存储**: JSON 文件
- **网站生成**: Tailwind CSS + Alpine.js
- **定时调度**: macOS launchd / Linux systemd

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 迭代计划

完善多数据源类型，向情感洞察（两性情感、家庭故事、历史）、舆情监测分析、行业调研、竞品分析（例如业内理财产品对比、信用卡卡种分析）、深度研究助手、开源智选、智能体前沿洞察、趋势分析等方向，还可以扩展写小说功能，每个方向都做单独的agent，Sub-Agent独立上下文有助于对上下文清洁度的掌控，专业的人做专业的事。

完善推送机制及自定义配置，多渠道推送（Telegram、飞书Bot等），增加Web UI界面用于管理和展示，安装网页设计skill。

## 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/gooden-cyber">gooden-cyber</a>
</p>

<p align="center">
  <img src="assets/demo-banner.png" alt="AI Knowledge Base" width="100%">
</p>
