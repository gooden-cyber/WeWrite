# 更新日志

所有重要更改都会记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## 未发布

### 新增

- **封面图预览**：预览文章时自动生成并显示封面图

### 优化

- **移除token剩余限额**：移除硬编码的token剩余限额显示，改为仅显示实际使用量
- **简化成本控制**：移除每日token上限和成本上限的硬编码限制

## [0.2.2] - 2026-05-05

### 新增

- **成本控制**：
  - 每日 token 上限（100,000）和成本上限（$1.00）
  - 今日 token 消耗统计和剩余限额显示
  - AI 调用详细记录（`knowledge/ai_call_log.jsonl`）
- **管理页面**：
  - 今日 token 使用统计面板
  - AI 调用记录列表
  - Pipeline 运行历史
  - 预览缓存列表
- **API 端点**：
  - `/api/ai-call-log` - AI 调用记录
  - `/api/drafts` - 预览缓存列表
  - `/api/publish/history` - 发布历史
  - `/api/pipeline/history` - Pipeline 运行历史

### 优化

- **预览/发布复用**：发布时优先使用预览缓存，避免重复调用 AI
- **测试时间优化**：新增 `--quick` 和 `--skip-ai` 参数，快速模式 0.25 秒完成
- **Token 统计**：区分今日/总计统计，按提供商分类

### 修复

- 修复预览和发布重复调用 AI 的问题
- 修复预览时看不到自动生成的封面图的问题

### 文档

- 新增 `docs/cost-optimization.md` 成本控制优化方案
- 新增 `docs/feature-roadmap.md` 项目功能优化方向
- 新增 `.opencode/skills/development-workflow.md` 功能设计规范

## [0.2.1] - 2026-05-05

### 优化

- **Web UI**：
  - 替换 emoji 为 SVG 图标，更专业
  - 添加 cursor-pointer 和 hover 交互反馈
  - 优化空状态设计，添加引导按钮
  - 发布按钮添加加载动画 spinner
- **start.sh**：
  - 自动检测 Python >= 3.12 版本
  - 首次运行自动创建虚拟环境并安装依赖
  - 后续运行跳过依赖检查，秒启动
  - 添加彩色日志输出

### 修复

- 修复 `web/app.py` 的 Python 3.9 兼容性问题（`dict | None` → `Optional[dict]`）
- 修复 `TemplateResponse` 参数格式，兼容新版 Starlette
- 修复发布页预览功能，调用真实渲染 API

### 文档

- 更新 `AGENTS.md`，添加代码修改工作流（强制执行）

## [0.2.0] - 2026-05-05

### 新增

- **Web UI**：新增基于 FastAPI 的 Web 界面
  - 首页：知识库列表，支持搜索、筛选
  - 详情页：文章完整内容展示
  - API：RESTful API 接口
- **一键脚本**：
  - `install.sh`：一键安装
  - `start.sh`：支持多种启动模式（once/schedule/test/web）
- **项目级 Skill**：
  - `wechat-publish.md`：微信公众号发布技能
  - `data-collection.md`：数据采集技能
  - `quality-check.md`：质量检查技能

### 优化

- **增量处理**：Step 2/3/4 支持增量处理，避免重复分析
- **状态管理**：原始数据添加 `analyzed`/`organized` 状态标记
- **日期过滤**：支持 `--date YYYYMMDD` 参数
- **scheduler.py**：优化定时任务，处理所有未分析的数据

### 修复

- 修复 RSS URL 格式错误（Markdown 链接格式）
- 修复 `pipeline.py` 的 `@staticmethod` bug
- 修复 `cover_generator.py` 裸 `except:` 问题
- 修复 `wechat_api.py` warm 主题 CSS 错误
- 修复 `validate_json.py` ID 正则匹配
- 修复 LICENSE 声明矛盾（Apache 2.0）
- 修复 HTML 实体未解码问题

### 文档

- 更新 `AGENTS.md`，与实际代码结构同步
- 更新 `README.md`，添加一键安装说明
- 新增 `CONTRIBUTING.md` 贡献指南
- 新增 `CHANGELOG.md` 更新日志

## [0.1.0] - 2026-05-01

### 新增

- **核心流水线**：四步自动化（采集→分析→整理→保存）
- **多 LLM 支持**：DeepSeek/Qwen/OpenAI/Mimo
- **GitHub 采集**：支持 GitHub Search API
- **RSS 采集**：支持 12 个 RSS 源
- **微信发布**：支持微信公众号发布
- **质量保障**：JSON Schema 校验 + 5 维度质量评分
- **MCP 服务器**：支持 AI 工具搜索知识库
- **定时调度**：支持 macOS launchd 和 schedule 库
