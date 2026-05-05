# 贡献指南

感谢你对 WeWrite 项目的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

1. 在 [GitHub Issues](https://github.com/gooden-cyber/WeWrite/issues) 中搜索是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息（Python 版本、操作系统等）

### 提交功能建议

1. 在 Issues 中创建功能建议
2. 说明使用场景和期望的行为
3. 等待讨论和确认

### 提交代码

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 开发环境

### 环境要求

- Python 3.12+
- Git

### 设置开发环境

```bash
# 克隆项目
git clone https://github.com/gooden-cyber/WeWrite.git
cd WeWrite

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖（包含开发依赖）
pip install -r requirements.txt
pip install pytest ruff

# 运行测试
pytest tests/

# 代码检查
ruff check .
```

## 代码规范

### Python 代码风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/)
- 使用类型提示（Type Hints）
- 使用 Google 风格的 Docstring
- 禁止裸 `print()`，使用 `logging` 模块

### 命名约定

- 变量、函数、文件：`snake_case`
- 类：`CamelCase`
- 常量：`UPPER_SNAKE_CASE`

### 示例

```python
"""模块文档字符串。"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

## 提交规范

### Commit Message 格式

```
<类型>(<范围>): <描述>

<详细说明>

<关联 Issue>
```

### 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建、工具相关

### 示例

```
feat(web): 添加知识库搜索功能

- 支持按标题、摘要搜索
- 支持按分类、标签筛选
- 添加搜索结果高亮

Closes #123
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_pipeline.py

# 运行并显示覆盖率
pytest tests/ --cov=pipeline --cov-report=html
```

### 编写测试

- 测试文件放在 `tests/` 目录
- 文件名格式：`test_<模块名>.py`
- 使用 pytest fixtures
- 测试用例要有清晰的命名

```python
def test_valid_item():
    """有效条目应该通过验证。"""
    item = {"title": "Test", "url": "https://example.com"}
    assert validate_item(item) is True
```

## Pull Request 流程

1. 确保代码通过所有测试
2. 确保代码通过 lint 检查
3. 更新文档（如果需要）
4. 填写 PR 描述，说明：
   - 做了什么改动
   - 为什么做这个改动
   - 如何测试
5. 等待代码审查

## 联系方式

- Issues: [GitHub Issues](https://github.com/gooden-cyber/WeWrite/issues)
- Discussions: [GitHub Discussions](https://github.com/gooden-cyber/WeWrite/discussions)

## 许可证

提交代码即表示你同意将代码以 [Apache 2.0 许可证](LICENSE) 发布。
