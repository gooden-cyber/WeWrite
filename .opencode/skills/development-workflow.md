# 功能设计与开发规范

每次进行功能设计和代码编写时，必须自动考虑以下问题并执行相应检查。

## 设计阶段检查清单

### 1. 数据持久化
- [ ] 数据是否需要持久化？选择：文件 / 数据库 / 缓存
- [ ] 缓存策略：内存缓存 vs 文件缓存？重启后是否丢失？
- [ ] 数据目录是否在 .gitignore 中（如不需要版本控制）

### 2. 成本控制
- [ ] 是否涉及 API 调用（LLM、第三方服务）？
- [ ] Token 消耗估算：每次调用约 X tokens，每天约 Y 次
- [ ] 是否有缓存机制避免重复调用？
- [ ] 是否有成本监控和告警？

### 3. 用户体验
- [ ] 操作是否有实时反馈（loading 状态）？
- [ ] 错误信息是否友好且可操作？
- [ ] 是否有空状态引导？

### 4. 测试覆盖
- [ ] 是否有单元测试？
- [ ] 是否有 Web 功能测试？
- [ ] 测试是否会被自动执行？

## 开发阶段检查清单

### 1. 代码质量
```bash
# 必须通过
ruff check .
pytest tests/ -v
```

### 2. 功能测试
```bash
# 启动服务
./start.sh web &
sleep 5

# 运行 Web 测试
python scripts/test_web.py

# 关闭服务
kill %1
```

### 3. 文档同步
- [ ] README.md 是否需要更新？
- [ ] AGENTS.md 是否需要更新？
- [ ] CHANGELOG.md 是否记录变更？

## 工作流集成

### 修改代码后自动执行

```bash
# Step 1: 质量检查
ruff check . --fix

# Step 2: 单元测试
pytest tests/ -q

# Step 3: 启动服务并测试
./start.sh web &
sleep 5
python scripts/test_web.py
kill %1

# Step 4: 更新文档
# 根据修改类型更新相应文档
```

### 测试失败自动修复

1. 读取测试失败信息
2. 分析失败原因
3. 修复代码
4. 重新运行测试
5. 循环直到通过

## 常见问题预防

### 1. API 设计
- 统一响应格式：`{"status": "success/error", "data": ..., "message": ...}`
- 错误码标准化
- 请求参数验证

### 2. 缓存设计
- 缓存键命名规范：`{type}:{id}:{version}`
- 缓存失效策略：TTL / 手动清除
- 缓存目录：`knowledge/{type}/cache/` 或 `knowledge/.cache/`

### 3. 成本控制
- Token 使用统计：`knowledge/token_stats.json`
- 每日成本上限（可配置）
- 成本告警阈值

### 4. 日志记录
- 使用 logging 模块，禁止 print
- 日志级别：DEBUG / INFO / WARNING / ERROR
- 日志文件：`logs/app.log`

## 文件结构规范

```
knowledge/
├── articles/          # 结构化文章
├── raw/               # 原始采集数据
├── wechat/            # 微信相关内容
│   ├── preview/       # 预览缓存（AI 生成内容）
│   ├── content/       # 发布内容
│   └── images/        # 封面图
├── token_stats.json   # Token 使用统计
└── .cache/            # 通用缓存目录
```
