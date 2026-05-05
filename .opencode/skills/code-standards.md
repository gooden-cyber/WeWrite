# Code Change Standards Skill

代码修改规范技能。每次修改代码时自动遵守以下规范。

## 修改代码检查清单

### 修改前检查

1. **理解上下文**：阅读相关文件，理解代码结构
2. **检查依赖**：确认修改是否影响其他模块
3. **备份重要数据**：如有必要，先备份

### 修改时规范

#### Python 代码

```python
# ✅ 正确示例
def process_data(data: dict, limit: Optional[int] = None) -> list[dict]:
    """处理数据。

    Args:
        data: 输入数据。
        limit: 返回数量限制。

    Returns:
        处理后的数据列表。

    Raises:
        ValueError: 数据格式错误。
    """
    if not isinstance(data, dict):
        raise ValueError("数据必须是字典类型")
    
    logger.info("处理数据: %d 条", len(data))
    return []
```

#### 代码风格

- 遵循 PEP 8
- 使用类型提示（Type Hints）
- 使用 Google 风格的 Docstring
- 禁止裸 `print()`，使用 `logging` 模块
- 禁止裸 `except:`，捕获特定异常

#### 命名约定

- 变量、函数、文件：`snake_case`
- 类：`CamelCase`
- 常量：`UPPER_SNAKE_CASE`

### 修改后检查

#### 必须同步更新的文件

| 修改类型 | 需要同步更新的文件 |
|----------|-------------------|
| 新增功能 | README.md, CHANGELOG.md |
| 修改 API | README.md, AGENTS.md |
| 修复 Bug | CHANGELOG.md |
| 修改配置 | README.md, .env.example |
| 新增依赖 | requirements.txt, pyproject.toml |
| 修改命令 | README.md, start.sh |

#### 同步更新脚本

```bash
# 运行文档同步检查
python scripts/sync_docs.py

# 或使用 make
make sync-docs
```

#### 测试验证

```bash
# 运行测试
pytest tests/ -v

# 代码检查
ruff check .

# 类型检查（可选）
mypy pipeline/ hooks/
```

## 自动同步机制

### 1. 文档同步脚本

```bash
python scripts/sync_docs.py
```

功能：
- 检查 README.md 中的命令是否与 start.sh 一致
- 检查 requirements.txt 是否包含所有导入的依赖
- 检查 .env.example 是否包含所有环境变量
- 自动生成 CHANGELOG.md 的未发布部分

### 2. Pre-commit Hook

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 手动运行
pre-commit run --all-files
```

功能：
- 代码风格检查（ruff）
- 类型检查（mypy）
- 测试运行（pytest）
- 文档同步检查

### 3. CI/CD 检查

GitHub Actions 会自动运行：
- Lint 检查
- 测试运行
- 文档同步检查

## 常见修改场景

### 场景 1：修改 pipeline.py

```bash
# 1. 修改代码
vim pipeline/pipeline.py

# 2. 运行测试
pytest tests/test_pipeline.py -v

# 3. 同步文档（如果修改了命令行参数）
python scripts/sync_docs.py

# 4. 更新 CHANGELOG.md
vim CHANGELOG.md
```

### 场景 2：新增依赖

```bash
# 1. 安装依赖
pip install new-package

# 2. 更新 requirements.txt
pip freeze > requirements.txt

# 3. 更新 pyproject.toml
vim pyproject.toml

# 4. 测试
pytest tests/
```

### 场景 3：修改 Web UI

```bash
# 1. 修改代码
vim web/app.py

# 2. 测试 Web UI
./start.sh web

# 3. 同步文档
python scripts/sync_docs.py
```

## 违规处理

### 严重违规（必须修复）

- 硬编码敏感信息
- 裸 `except:`
- 缺少类型提示
- 缺少 Docstring
- 未同步更新文档

### 警告（建议修复）

- 函数超过 50 行
- 嵌套超过 3 层
- 重复代码
- 未使用变量

## 工具推荐

### IDE 配置

```json
// VS Code settings.json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### Git Hooks

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 安装 commit-msg hook
pre-commit install --hook-type commit-msg
```
