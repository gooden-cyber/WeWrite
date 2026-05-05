# 成本控制优化方案

## 当前 Token 消耗分析

### 主要消耗点

| 操作 | 预估 Token | 频率 | 日消耗 |
|------|-----------|------|--------|
| Pipeline 分析 | ~1000/篇 | 每天 20 篇 | ~20,000 |
| 预览生成 | ~3000/次 | 用户触发 | 可变 |
| 标题生成 | ~200/次 | 发布时 | ~200 |
| 内容生成 | ~3000/次 | 发布时 | ~3000 |

### 成本估算（Mimo）

- 输入：¥0.002/千token
- 输出：¥0.006/千token
- 日均消耗：约 ¥0.5-2.0

## 优化方案

### 1. 缓存策略（已实现）

- [x] 预览内容缓存到文件
- [x] 重复预览直接读取缓存
- [ ] Pipeline 分析结果缓存

### 2. 增量处理（已实现）

- [x] 只分析未分析的数据
- [x] 按日期过滤
- [ ] 按内容变化检测

### 3. 成本限制（待实现）

```python
# 建议实现
DAILY_TOKEN_LIMIT = 100000  # 每日 token 上限
DAILY_COST_LIMIT_USD = 1.0  # 每日成本上限

def check_cost_limit():
    stats = get_token_stats()
    today = datetime.now().date().isoformat()
    
    # 检查今日消耗
    if stats.get("last_reset_date") != today:
        reset_daily_stats()
    
    if stats["today"]["total_tokens"] >= DAILY_TOKEN_LIMIT:
        raise CostLimitExceeded("今日 Token 消耗已达上限")
```

### 4. 模型选择优化

| 场景 | 推荐模型 | 原因 |
|------|----------|------|
| Pipeline 分析 | qwen-turbo | 便宜、快速 |
| 预览生成 | mimo-v2.5-pro | 质量好 |
| 标题生成 | qwen-turbo | 简单任务 |
| 内容生成 | mimo-v2.5-pro | 质量要求高 |

### 5. 批量处理

```python
# 当前：逐篇调用
for article in articles:
    analyze(article)  # 每篇一次 API 调用

# 优化：批量处理
batch_prompt = "\n---\n".join([article.summary for article in articles])
analyze_batch(batch_prompt)  # 一次调用处理多篇
```

## 实施优先级

1. **P0**：实现每日成本上限
2. **P1**：优化模型选择策略
3. **P2**：实现批量处理
4. **P3**：添加成本告警通知
