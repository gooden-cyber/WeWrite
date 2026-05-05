# Data Collection Skill

数据采集技能。从 GitHub API 和 RSS 源采集 AI/LLM 相关内容。

## 功能

- GitHub Search API 采集（按 stars、语言、时间过滤）
- RSS 源采集（支持 12 个预设源）
- 自动去重（按 URL）
- 增量采集（跳过已存在的数据）

## 使用方法

```bash
# 完整流水线（包含采集）
python pipeline/pipeline.py --step 1

# 只采集
python pipeline/pipeline.py --step 1 --sources github,rss

# 限制采集数量
python pipeline/pipeline.py --step 1 --limit 20

# 按日期采集
python pipeline/pipeline.py --step 1 --date 20260501
```

## 数据源

### GitHub Search API
- `llm framework language:python stars:>100`
- `ai agent language:python pushed:>2025-01-01`
- `rag retrieval augmented generation stars:>50`

### RSS 源（12 个，5 个启用）
- Hacker News Best (AI)
- Lobsters AI/ML
- OpenAI Blog
- Anthropic Research
- Hugging Face Blog

## 配置

RSS 源配置文件：`pipeline/rss_sources.yaml`

```yaml
sources:
  - name: "Hacker News Best (AI)"
    url: "https://hnrss.org/best?q=AI+OR+LLM"
    category: "综合技术"
    enabled: true
```

## 环境变量

```bash
GITHUB_TOKEN=your-github-token  # 可选，提高 API 限额
```

## 输出

原始数据保存到 `knowledge/raw/` 目录，文件名格式：`{source}_{timestamp}.json`
