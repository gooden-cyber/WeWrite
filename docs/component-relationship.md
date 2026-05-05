# AGENTS.md / agents / skills / knowledge 关系图

```mermaid
flowchart TB
    subgraph 规格层["🔵 规格层 (Specification)"]
        AGENTS[📋 AGENTS.md<br/>项目宪章 / 总蓝图<br/>━━━━━━━━━━━━━<br/>• 编码规范 & 红线<br/>• 数据结构 Schema<br/>• 流水线架构概览]
    end

    subgraph 角色层["🟢 角色层 (Role Definitions)"]
        direction LR
        COLLECTOR[🤖 collector.md<br/>知识采集器<br/>━━━━━━━━━<br/>抓取 GitHub/HN<br/>过滤 AI 相关<br/>写入 knowledge/raw/]
        ANALYZER[🤖 analyzer.md<br/>知识分析器<br/>━━━━━━━━━<br/>读取 raw 数据<br/>AI 分析 & 评分<br/>写入 knowledge/raw/]
        ORGANIZER[🤖 organizer.md<br/>知识整理器<br/>━━━━━━━━━<br/>去重 & 分类<br/>生成唯一 ID<br/>写入 knowledge/articles/]
    end

    subgraph 能力层["🟡 能力层 (Skill Modules)"]
        direction LR
        GH_TREND[🧩 github-trending<br/>SKILL.md<br/>━━━━━━━━━<br/>抓取 GitHub Trending<br/>过滤 AI/LLM 领域<br/>→ raw/github-trending-{date}.json]
        TECH_SUMM[🧩 tech-summary<br/>SKILL.md<br/>━━━━━━━━━<br/>深度 AI 分析<br/>摘要 / 亮点 / 标签<br/>→ raw/analysis-{date}.json]
    end

    subgraph 数据层["🟠 数据层 (Data Storage)"]
        direction LR
        RAW[📁 knowledge/raw/<br/>原始数据 & 中间结果<br/>━━━━━━━━━━━━━━━<br/>github-trending-{date}.json<br/>analysis-{date}.json]
        ARTICLES[📁 knowledge/articles/<br/>最终知识条目<br/>━━━━━━━━━━━━━━━<br/>{date}-{source}-{slug}.json<br/>结构化知识库]
    end

    %% AGENTS.md 定义所有
    AGENTS -->|"定义项目结构"| COLLECTOR
    AGENTS -->|"定义项目结构"| ANALYZER
    AGENTS -->|"定义项目结构"| ORGANIZER
    AGENTS -->|"定义项目结构"| GH_TREND
    AGENTS -->|"定义项目结构"| TECH_SUMM
    AGENTS -->|"定义数据 Schema"| RAW
    AGENTS -->|"定义数据 Schema"| ARTICLES

    %% Agents 调用 Skills
    COLLECTOR -->|"调用"| GH_TREND
    ANALYZER -->|"调用"| TECH_SUMM

    %% Skills 读写 knowledge
    GH_TREND -->|"写入"| RAW
    TECH_SUMM -->|"读取"| RAW
    TECH_SUMM -->|"写入"| RAW

    %% Agents 读写 knowledge
    COLLECTOR -.->|"读取/写入"| RAW
    ANALYZER -.->|"读取/写入"| RAW
    ANALYZER -.->|"读取参考"| ARTICLES
    ORGANIZER -.->|"读取"| RAW
    ORGANIZER -.->|"读取/写入"| ARTICLES

    %% 数据流
    RAW ==>|"整理 & 去重"| ARTICLES
```

## 各组成部分的隐喻

| 组件 | 隐喻 | 职责 |
|------|------|------|
| `AGENTS.md` | 🏛️ **宪章 / 蓝图** | 定义编码规范、红线、项目架构、数据 Schema |
| `.opencode/agents/` | 📋 **岗位说明** | 定义谁负责什么：采集器、分析器、整理器的权限和职责 |
| `.opencode/skills/` | 📖 **标准作业程序(SOP)** | 定义怎么做：采集 GitHub Trending、深度分析的具体步骤 |
| `knowledge/` | 🏭 **数据工厂** | 存放流水线中各阶段的数据：raw → articles |

## 数据流向

```
GitHub Trending / Hacker News
        │
        ▼
[Collector] ──调用──▶ [github-trending skill] ──写入──▶ knowledge/raw/
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ▼
[Analyzer]  ──调用──▶ [tech-summary skill] ──写入──▶ knowledge/raw/
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ▼
[Organizer] ──去重&整理──▶ knowledge/articles/  (最终知识库)
```
