# Quality Check Skill

质量检查技能。对知识条目进行 JSON Schema 校验和质量评分。

## 功能

- JSON Schema 校验（必填字段、ID 格式、status 枚举）
- 5 维度质量评分（满分 100）
- 批量检查支持
- 可视化评分报告

## 使用方法

### JSON 校验

```bash
# 校验单个文件
python hooks/validate_json.py knowledge/articles/01a751a2.json

# 校验所有文件
python hooks/validate_json.py knowledge/articles/*.json
```

### 质量评分

```bash
# 评分单个文件
python hooks/check_quality.py knowledge/articles/01a751a2.json

# 评分所有文件
python hooks/check_quality.py knowledge/articles/*.json
```

## 校验规则

### 必填字段
- `id` (UUID 格式)
- `title` (字符串)
- `source_url` (URL 格式)
- `summary` (字符串，≥20 字)
- `tags` (列表，≥1 个)
- `status` (枚举值)

### 状态枚举
`draft`, `review`, `published`, `archived`, `analyzed`, `raw`, `curated`, `distributed`

## 质量评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 摘要质量 | 25 | 长度 + 技术关键词 |
| 技术深度 | 25 | 基于 score 字段 |
| 格式规范 | 20 | 必填字段完整性 |
| 标签精度 | 15 | 1-3 个合法标签 |
| 空洞词检测 | 15 | 不含空洞词 |

## 等级标准

- **A 级**：≥ 80 分
- **B 级**：≥ 60 分
- **C 级**：< 60 分

## 退出码

- `0`：全部通过
- `1`：存在失败
